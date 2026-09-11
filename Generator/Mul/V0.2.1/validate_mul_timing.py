#!/usr/bin/env python3
"""Run the canonical MUL C++/RTL simulation and measure timing from VCD."""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
TESTS_ROOT = ROOT / "tests"
DESIGNS_ROOT = ROOT / "designs"
PYTV_ROOT = PROJECT_ROOT / "Generator" / "LSCE" / "BehaviorialVerification"
SIM_ROOT = Path(os.environ.get("MUL_SIM_ROOT", ROOT / "sim")).resolve()
QUBLAS_SOURCE = TESTS_ROOT / "sim" / "CppModules" / "include" / "QuBLAS.h"


def _run(command: list[str], cwd: Path) -> str:
    process = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Command failed in {cwd}: {' '.join(command)}\n{process.stdout}")
    return process.stdout


def _single(path: Path, pattern: str) -> Path:
    matches = list(path.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one {pattern} in {path}, found {len(matches)}")
    return matches[0]


def _load_generators():
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    sys.path[:0] = [str(TESTS_ROOT), str(DESIGNS_ROOT), str(PYTV_ROOT), str(ROOT)]
    try:
        import PyTU
        from BehavModel_Mul import ModuleCppConfig, ModuleCppRun
        from tb_Mul import ModuleTbMul
        from pytv.ModuleLoader import moduleloader
    finally:
        sys.argv = original_argv
    return PyTU, ModuleCppConfig, ModuleCppRun, ModuleTbMul, moduleloader


def _qu_type(py_tu: Any, config: dict[str, Any], name: str):
    value = config[name]
    return py_tu.QuType(
        int(value["bitwidth"]), int(value["fractional_width"]), bool(value["signed"])
    )


def _modes(py_tu: Any, config: dict[str, Any]) -> tuple[Any, Any]:
    quantization = str(config.get("quantization_mode", "TRN.TCPL")).upper()
    overflow = str(config.get("overflow_mode", "WRP.TCPL")).upper()
    quantization_modes = {
        "TRN.TCPL": py_tu.QuMode.TRN.TCPL,
        "TRN.SMGN": py_tu.QuMode.TRN.SMGN,
        "RND.POS_INF": py_tu.QuMode.RND.POS_INF,
        "RND.NEG_INF": py_tu.QuMode.RND.NEG_INF,
        "RND.INF": py_tu.QuMode.RND.INF,
        "RND.ZERO": py_tu.QuMode.RND.ZERO,
        "RND.CONV": py_tu.QuMode.RND.CONV,
    }
    overflow_modes = {
        "WRP.TCPL": py_tu.OfMode.WRP.TCPL,
        "SAT.TCPL": py_tu.OfMode.SAT.TCPL,
        "SAT.SMGN": py_tu.OfMode.SAT.SMGN,
        "SAT.ZERO": py_tu.OfMode.SAT.ZERO,
    }
    try:
        return quantization_modes[quantization], overflow_modes[overflow]
    except KeyError as error:
        raise ValueError(f"Unsupported MUL quantization/overflow mode: {error.args[0]}") from error


def _generate_case(config_path: Path, config: dict[str, Any], case_root: Path) -> dict[str, Path]:
    workspace = case_root / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    rtl_dir = workspace / "RTL"
    input_dir = workspace / "Input_Files"
    expected_dir = workspace / "Comparison_Files"
    output_dir = workspace / "Output_Files"
    cpp_dir = workspace / "CppModules"
    include_dir = cpp_dir / "include"
    for path in (rtl_dir, input_dir, expected_dir, output_dir, include_dir):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, case_root / "config_snapshot.json")
    shutil.copy2(QUBLAS_SOURCE, include_dir / "QuBLAS.h")

    py_tu, cpp_config, cpp_run, tb_mul, moduleloader = _load_generators()
    qu_in1 = _qu_type(py_tu, config, "input_1")
    qu_in2 = _qu_type(py_tu, config, "input_2")
    qu_out = _qu_type(py_tu, config, "output")
    qu_mode, of_mode = _modes(py_tu, config)
    n_frames = int(config.get("flow", {}).get("simulation_frames", 8))
    if n_frames < 3:
        raise ValueError("flow.simulation_frames must be at least 3")

    moduleloader.reset()
    moduleloader.set_language_mode("CPP_HEADER")
    moduleloader.set_root_dir(str(include_dir))
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    with contextlib.redirect_stdout(sys.stderr):
        cpp_config(
            QU_IN_1=qu_in1, QU_IN_2=qu_in2, QU_OUT=qu_out,
            QU_MODE=qu_mode, OF_MODE=of_mode,
        )
    _single(include_dir, "CppConfig*.h").replace(include_dir / "config.h")

    moduleloader.set_language_mode("CPP")
    moduleloader.set_root_dir(str(cpp_dir))
    with contextlib.redirect_stdout(sys.stderr):
        cpp_run(N_FRAMES=n_frames)
    _single(cpp_dir, "CppRun*.cpp").replace(cpp_dir / "Mul.cpp")
    compiler = shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        raise FileNotFoundError("MUL simulation requires clang++ or g++ on PATH")
    executable = cpp_dir / ("mul_reference.exe" if os.name == "nt" else "mul_reference")
    _run([compiler, "Mul.cpp", "-std=c++23", "-Iinclude", "-o", str(executable)], cpp_dir)
    _run([str(executable)], cpp_dir)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    with contextlib.redirect_stdout(sys.stderr):
        tb_mul(
            QU_IN_1=qu_in1,
            QU_IN_2=qu_in2,
            QU_OUT=qu_out,
            N_CLK=int(config["n_pipeline"]),
            IF_RST_N=config.get("if_rst_n", False),
            QU_MODE=qu_mode,
            OF_MODE=of_mode,
            # The generated Verilog runs from workspace/RTL. A relative ASCII
            # path also avoids simulator filename-encoding differences.
            input_file_dir="../",
            N_FRAMES=n_frames,
            CLK_PERIOD=float(config["clock"]["period_ns"]),
        )
    return {
        "workspace": workspace,
        "rtl_dir": rtl_dir,
        "expected": expected_dir / "Mul_o_data.txt",
        "observed": output_dir / "Mul_o_data.txt",
        "input1": input_dir / "Mul_i_data_1.txt",
        "input2": input_dir / "Mul_i_data_2.txt",
        "testbench": _single(rtl_dir, "TbMul*.v"),
    }


def _signal_ids(vcd_path: Path) -> dict[str, str]:
    wanted = {"clk", "i_data_1", "i_data_2", "o_data"}
    scope: list[str] = []
    result: dict[str, str] = {}
    with vcd_path.open("r", encoding="ascii", errors="replace") as stream:
        for line in stream:
            words = line.split()
            if not words:
                continue
            if words[0] == "$scope":
                scope.append(words[2])
            elif words[0] == "$upscope":
                scope.pop()
            elif words[0] == "$var" and len(scope) == 1 and words[4] in wanted:
                result[words[4]] = words[3]
            elif words[0] == "$enddefinitions":
                break
    missing = wanted - result.keys()
    if missing:
        raise ValueError(f"{vcd_path}: missing top-level signals {sorted(missing)}")
    return result


def _posedge_samples(vcd_path: Path) -> list[dict[str, str]]:
    ids = _signal_ids(vcd_path)
    names = {identifier: name for name, identifier in ids.items()}
    values = {identifier: "x" for identifier in names}
    pending_posedge = False
    samples: list[dict[str, str]] = []

    def finish_timestamp() -> None:
        nonlocal pending_posedge
        if pending_posedge:
            samples.append({name: values[identifier] for identifier, name in names.items()})
        pending_posedge = False

    with vcd_path.open("r", encoding="ascii", errors="replace") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("$"):
                continue
            if line.startswith("#"):
                finish_timestamp()
                continue
            if line[0] in "01xz":
                value, identifier = line[0], line[1:]
            elif line[0] in "bB":
                parts = line.split()
                if len(parts) != 2:
                    continue
                value, identifier = parts[0][1:].lower(), parts[1]
            else:
                continue
            old = values.get(identifier)
            if identifier in values:
                values[identifier] = value
            if identifier == ids["clk"] and old == "0" and value == "1":
                pending_posedge = True
    finish_timestamp()
    return samples


def _bits(value: str, width: int) -> str:
    return value.lower().replace("z", "x").zfill(width)[-width:]


def _read_bits(path: Path) -> list[str]:
    return [line.strip().lower() for line in path.read_text().splitlines() if line.strip()]


def _find_sequence(samples: list[dict[str, str]], names: tuple[str, ...], expected: list[tuple[str, ...]], widths: tuple[int, ...], start: int = 0) -> int:
    for index in range(start, len(samples) - len(expected) + 1):
        if all(
            all(_bits(samples[index + offset][name], width) == value for name, width, value in zip(names, widths, row))
            for offset, row in enumerate(expected)
        ):
            return index
    raise ValueError(f"VCD does not contain the complete consecutive {names} reference sequence")


def validate(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    period_ns = float(config["clock"]["period_ns"])
    if not math.isfinite(period_ns) or period_ns <= 0:
        raise ValueError("clock.period_ns must be finite and greater than zero")
    case_root = SIM_ROOT / config_path.stem
    case_root.mkdir(parents=True, exist_ok=True)
    for artifact_name in (
        "simulation_result.json",
        "latency_check.txt",
        "behavioral_output_reference.txt",
        "rtl_output.txt",
        "wave.vcd",
    ):
        (case_root / artifact_name).unlink(missing_ok=True)
    started = time.perf_counter()
    paths = _generate_case(config_path, config, case_root)
    rtl_files = sorted(path.name for path in paths["rtl_dir"].glob("*.v"))
    _run(["iverilog", "-o", "wave", *rtl_files], paths["rtl_dir"])
    _run(["vvp", "-n", "wave"], paths["rtl_dir"])
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    expected = _read_bits(paths["expected"])
    observed = _read_bits(paths["observed"])
    if observed != expected:
        raise ValueError(
            f"MUL RTL output mismatch: expected {len(expected)} values, got {len(observed)}"
        )
    inputs1 = _read_bits(paths["input1"])
    inputs2 = _read_bits(paths["input2"])
    if not (len(inputs1) == len(inputs2) == len(expected)):
        raise ValueError("MUL C++ input/output reference lengths differ")

    samples = _posedge_samples(paths["rtl_dir"] / "wave.vcd")
    input_rows = list(zip(inputs1, inputs2))
    input_start = _find_sequence(
        samples, ("i_data_1", "i_data_2"), input_rows,
        (int(config["input_1"]["bitwidth"]), int(config["input_2"]["bitwidth"])),
    )
    output_rows = [(value,) for value in expected]
    output_start = _find_sequence(
        samples, ("o_data",), output_rows, (int(config["output"]["bitwidth"]),),
        start=input_start,
    )
    latency = output_start - input_start
    output_positions = list(range(output_start, output_start + len(expected)))
    intervals = [right - left for left, right in zip(output_positions, output_positions[1:])]
    stable_interval = intervals[0] if intervals and len(set(intervals)) == 1 else None
    result = {
        "sim_latency_cycles": latency,
        "sim_output_interval_cycles": stable_interval,
        "sim_output_interval_cycle_list": intervals,
        "matched_output_frames": len(expected),
        "input_accept_cycle": 0,
        "first_output_cycle": latency,
        "vcd_input_sample_index": input_start,
        "vcd_output_sample_indices": output_positions,
        "clock_period_ns": period_ns,
        "clock_frequency_mhz": 1000.0 / period_ns,
        "physical_latency_ns": latency * period_ns,
        "functional_match": True,
        "rtl_simulation_time_ms": elapsed_ms,
        "measurement_method": (
            "canonical MUL PyTB + QuBLAS C++ reference; VCD clock-edge positions "
            "matching the complete input and output sequences"
        ),
        "testbench": str(paths["testbench"]),
        "rtl_files": [str(paths["rtl_dir"] / name) for name in rtl_files],
    }
    shutil.copy2(paths["expected"], case_root / "behavioral_output_reference.txt")
    shutil.copy2(paths["observed"], case_root / "rtl_output.txt")
    shutil.copy2(paths["rtl_dir"] / "wave.vcd", case_root / "wave.vcd")
    (case_root / "simulation_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (case_root / "latency_check.txt").write_text(
        "\n".join(
            (
                f"sim_latency_cycles={latency}",
                f"expected_n_pipeline={int(config['n_pipeline'])}",
                f"sim_output_interval_cycles={stable_interval}",
                f"sim_output_interval_cycle_list={intervals}",
                f"matched_output_frames={len(expected)}",
                f"clock_period_ns={period_ns}",
                f"physical_latency_ns={latency * period_ns}",
                "functional_match=true",
            )
        ) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_mul_timing.py CONFIG", file=sys.stderr)
        return 1
    try:
        print(json.dumps(validate(Path(sys.argv[1])), ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
