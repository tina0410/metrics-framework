#!/usr/bin/env python3
"""Canonical BP RTL latency simulation entrypoint."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_FILES = [PROJECT_DIR / "config" / f"config{i}.json" for i in range(1, 6)]

sys.path.insert(0, str(PROJECT_DIR))
ORIGINAL_ARGV = sys.argv[:]
sys.argv = [sys.argv[0]]
from cpp_modules import ModuleConfig  # noqa: E402
from decoder import Moduletest  # noqa: E402
from pytv import moduleloader  # noqa: E402
from utils import (  # noqa: E402
    merge_2_files,
    merge_files,
    move_and_rename_file,
    run_iverilog_flow,
)
sys.argv = ORIGINAL_ARGV


def load_config(path: Path) -> dict[str, object]:
    config = json.loads(path.read_text(encoding="utf-8"))
    period_ns = float(config.get("Clock Period (ns)", 20.0))
    if period_ns <= 0:
        raise ValueError(f"Clock Period (ns) must be positive, got {period_ns}")
    return {
        "archi": config.get("Hardware Architecture", "TypeI"),
        "algo": config.get("Decoding Algorithm", "MS"),
        "N": int(config.get("Code Length", 1024)),
        "M": int(config.get("Parallelism", 1024)),
        "width": int(config.get("Data Width", 5)),
        "rate": float(config.get("Code Rate", 0.5)),
        "ebn0_db": float(config.get("Eb/N0 (dB)", 10.0)),
        "period_ns": period_ns,
    }


def fixed_widths(width: int) -> tuple[int, int]:
    widths = {5: (3, 1), 7: (4, 2), 8: (4, 3), 12: (3, 8)}
    if width not in widths:
        raise ValueError(f"Unsupported data width: {width}")
    return widths[width]


def run_cpp_iteration_simulation(
    case_dir: Path,
    config: dict[str, object],
    frac_width: int,
) -> tuple[float, Path, float]:
    """Run the existing C++ fixed-point decoder and return this run's mean Iter."""
    cpp_tmp = case_dir / "cpp_tmp"
    cpp_include = case_dir / "cpp_include"
    cpp_tmp.mkdir()
    cpp_include.mkdir()

    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.set_root_dir(str(cpp_tmp))
    ModuleConfig(
        data_width=config["width"],
        frac_width=frac_width,
        n=config["N"],
        k=round(config["N"] * config["rate"]),
        LANGUAGE_MODE="cpp_header",
    )
    header_name = "Config0000000001.h"
    move_and_rename_file(
        str(cpp_tmp),
        str(cpp_include),
        header_name,
        header_name,
    )
    header_path = cpp_include / header_name
    if not header_path.exists():
        raise RuntimeError(f"C++ configuration header was not generated: {header_path}")
    header_text = header_path.read_text(encoding="utf-8", errors="ignore")
    expected_n = int(config["N"])
    expected_k = round(expected_n * float(config["rate"]))
    if f"const int N = {expected_n};" not in header_text:
        raise RuntimeError(
            f"Generated C++ header does not contain the requested N={expected_n}: "
            f"{header_path}"
        )
    if f"const int K = {expected_k};" not in header_text:
        raise RuntimeError(
            f"Generated C++ header does not contain the requested K={expected_k}: "
            f"{header_path}"
        )

    requested_compiler = os.environ.get("CXX")
    compiler = None
    for candidate in (requested_compiler, "clang++-20", "clang++"):
        if not candidate:
            continue
        resolved = shutil.which(candidate)
        if resolved:
            compiler = resolved
            break
    if compiler is None:
        raise FileNotFoundError(
            "C++ simulator requires Clang 20+; set CXX or install clang++-20"
        )
    version_output = subprocess.run(
        [compiler, "--version"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout
    version_match = re.search(r"clang version\s+(\d+)", version_output, re.IGNORECASE)
    if version_match is None or int(version_match.group(1)) < 20:
        raise RuntimeError(
            "BP C++ reference requires Clang 20+ with C++23 support; "
            f"selected compiler: {compiler}\n{version_output}"
        )
    binary_name = "bp_cpp_sim"
    binary_path = case_dir / binary_name
    compile_command = [
        compiler,
        "-std=c++23",
        # The per-run header must precede the project's stale default header.
        f"-I{cpp_include}",
        f"-I{PROJECT_DIR / 'include'}",
        "-O3",
        "-o",
        str(binary_path),
        str(PROJECT_DIR / "bp_polar_decoder.cpp"),
    ]
    compiled = subprocess.run(
        compile_command,
        cwd=case_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if compiled.returncode != 0:
        raise RuntimeError("BP C++ reference compilation failed:\n" + compiled.stdout)
    executable = binary_path
    if sys.platform == "win32" and not executable.exists():
        executable = binary_path.with_suffix(".exe")
    started = time.perf_counter()
    executed = subprocess.run(
        [str(executable), str(config["ebn0_db"])],
        cwd=case_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if executed.returncode != 0:
        raise RuntimeError("BP C++ reference execution failed:\n" + executed.stdout)

    iteration_log = case_dir / "comparison_files" / "iter_frame_log.txt"
    if not iteration_log.exists():
        raise RuntimeError(
            f"C++ simulation did not produce iteration log: {iteration_log}"
        )
    values = [
        float(line.strip())
        for line in iteration_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not values:
        raise RuntimeError(f"C++ iteration log is empty: {iteration_log}")
    if any(value <= 0 for value in values):
        raise RuntimeError(f"C++ iteration log contains a non-positive value: {values}")

    cpp_output = case_dir / "comparison_files" / "u_route_log.txt"
    output_length = len(
        [
            line
            for line in cpp_output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    )
    if output_length != expected_n:
        raise RuntimeError(
            "C++ fixed-point output length does not match this config: "
            f"output={output_length}, expected N={expected_n}. "
            f"Generated header: {header_path}"
        )
    return sum(values) / len(values), iteration_log, elapsed_ms


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def prepare_simulation_io(case_dir: Path) -> None:
    """Copy the immutable baseline vectors into this run's isolated workspace."""
    input_dir = case_dir / "input_files"
    output_dir = case_dir / "output_files"
    comparison_dir = case_dir / "comparison_files"
    input_dir.mkdir()
    output_dir.mkdir()
    comparison_dir.mkdir()
    for source in (PROJECT_DIR / "input_files").glob("*"):
        if source.is_file():
            shutil.copy2(source, input_dir / source.name)


def validate_baseline_stimulus(
    case_dir: Path,
    config: dict[str, object],
    int_width: int,
    frac_width: int,
) -> dict[str, Path]:
    suffix = (
        f"N{config['N']}K{round(config['N'] * config['rate'])}"
        f"INTDWT{int_width}FRACDWT{frac_width}MS.txt"
    )
    files = {
        "channel": case_dir / "input_files" / f"y1{suffix}",
        "left_messages": case_dir / "input_files" / f"L{suffix}",
        "right_messages": case_dir / "input_files" / f"R{suffix}",
        "matlab_decoded": case_dir / "input_files" / f"u1_esti{suffix}",
        "matlab_route": case_dir / "input_files" / f"u2{suffix}",
        "cpp_reference": case_dir / "comparison_files" / "u_route_log.txt",
    }
    expected_lines = {
        "channel": int(config["N"]),
        "left_messages": int(config["N"]) * int(config["width"]),
        "right_messages": int(config["N"]) * int(config["width"]),
        "matlab_decoded": int(config["N"]),
        "matlab_route": int(config["N"]),
        "cpp_reference": int(config["N"]),
    }
    for key, path in files.items():
        if not path.exists():
            raise RuntimeError(f"Baseline BP stimulus is missing {key}: {path}")
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(lines) != expected_lines[key]:
            raise RuntimeError(
                f"Baseline BP stimulus length mismatch for {key}: "
                f"actual={len(lines)}, expected={expected_lines[key]}, path={path}"
            )
    return files


def verify_decoding_output(actual: Path, expected: Path) -> None:
    if not actual.exists():
        raise RuntimeError(f"RTL simulation did not produce decoding output: {actual}")
    actual_lines = [
        line.strip()
        for line in actual.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_lines = [
        line.strip()
        for line in expected.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(actual_lines) != len(expected_lines):
        raise RuntimeError(
            "Fixed-point output length mismatch: "
            f"RTL={len(actual_lines)}, reference={len(expected_lines)}"
        )
    for line_number, (actual_line, expected_line) in enumerate(
        zip(actual_lines, expected_lines), start=1
    ):
        if actual_line.strip() != expected_line.strip():
            raise RuntimeError(
                "Fixed-point output mismatch at line "
                f"{line_number}: RTL={actual_line!r}, reference={expected_line!r}"
            )


def assemble_testbench(case_dir: Path) -> Path:
    designs = "designs.v"
    testbench = "test0000000001.v"
    merged = "BP_tb.v"
    merge_files(
        case_dir,
        designs,
        exclude_files={testbench, merged},
        suffix=".v",
        sort_files=True,
    )
    merge_2_files(case_dir, designs, testbench, merged)
    return case_dir / merged


def enable_timeout(testbench_path: Path) -> None:
    text = testbench_path.read_text(encoding="utf-8", errors="ignore")
    text = text.replace(
        "// #6000  $finish;",
        '#2000000\n    $display("Failure. Timeout waiting for out_valid after %0d cycles.", cycle_count);\n    $finish;',
    )
    testbench_path.write_text(text, encoding="utf-8", errors="ignore")


def simulate_bp_latency(
    config_path: Path,
    output_dir: Path,
    *,
    skip_run: bool = False,
    label: str | None = None,
) -> dict[str, object]:
    """Generate and optionally simulate one BP decoder configuration."""
    config_path = config_path.resolve()
    output_dir = output_dir.resolve()
    config = load_config(config_path)
    int_width, frac_width = fixed_widths(config["width"])
    label = label or config_path.stem

    reset_dir(output_dir)
    prepare_simulation_io(output_dir)

    # C++ consumes the copied baseline vectors and creates this run's reference.
    cpp_iterations, cpp_iteration_log, cpp_time_ms = (
        run_cpp_iteration_simulation(output_dir, config, frac_width)
    )
    stimulus_files = validate_baseline_stimulus(
        output_dir, config, int_width, frac_width
    )
    comparison_reference = stimulus_files["cpp_reference"]

    moduleloader.reset()
    moduleloader.disEnableWarning()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.set_root_dir(str(output_dir))
    moduleloader.set_debug_mode(True)

    Moduletest(
        width=config["width"],
        N=config["N"],
        M=config["M"],
        archi=config["archi"],
        algo=config["algo"],
        int_width=int_width,
        frac_width=frac_width,
        code_rate=config["rate"],
        clock_period_ns=config["period_ns"],
        root_path=str(output_dir),
        testcase_name=label,
        relative_io_paths=True,
    )
    testbench_path = output_dir / "test0000000001.v"
    enable_timeout(testbench_path)
    merged_path = assemble_testbench(output_dir)

    result = {
        "config_file": str(config_path),
        "artifact_dir": str(output_dir),
        "testbench": str(merged_path),
        "waveform": str(output_dir / "wave.vcd"),
        "comparison_reference": str(comparison_reference),
        "decoding_output": str(output_dir / "output_files" / "decoding_output.txt"),
        "sim_latency_cycles": None,
        "cpp_iterations": None,
        "cpp_iteration_log": None,
        "cpp_simulation_time_ms": None,
        "rtl_simulation_time_ms": None,
        "waveform_verified": False,
        "decoding_verified": False,
        "simulation_log": None,
        "clock_period_ns": config["period_ns"],
        "stimulus_source": "baseline_input_files",
        "stimulus_files": {key: str(path) for key, path in stimulus_files.items()},
    }
    result["cpp_iterations"] = cpp_iterations
    result["cpp_iteration_log"] = str(cpp_iteration_log)
    result["cpp_simulation_time_ms"] = cpp_time_ms
    if skip_run:
        print(f"Generated BP {label} simulation files: {output_dir}")
        return result

    rtl_started = time.perf_counter()
    simulation_output = run_iverilog_flow(
        output_dir, capture_output=True, raise_errors=True
    )
    result["rtl_simulation_time_ms"] = (
        time.perf_counter() - rtl_started
    ) * 1000.0
    log_path = output_dir / "simulation.log"
    log_path.write_text(simulation_output, encoding="utf-8", errors="ignore")
    result["simulation_log"] = str(log_path)

    latency_source = output_dir / "output_files" / "latency_output.txt"
    if not latency_source.exists():
        raise RuntimeError(
            f"RTL simulation did not produce latency output: {latency_source}"
        )
    latency_copy = output_dir / "latency_output.txt"
    shutil.copy2(latency_source, latency_copy)
    result["sim_latency_cycles"] = int(latency_source.read_text().strip())

    waveform = output_dir / "wave.vcd"
    if not waveform.exists() or waveform.stat().st_size == 0:
        raise RuntimeError(f"RTL simulation did not produce a valid waveform: {waveform}")
    result["waveform_verified"] = True

    decoding_output = output_dir / "output_files" / "decoding_output.txt"
    verify_decoding_output(decoding_output, comparison_reference)
    result["decoding_verified"] = True
    result["success_message"] = (
        f"Success. The latency of {label} is "
        f"{result['sim_latency_cycles']} cycles."
    )

    print(simulation_output, end="")
    print("Success. Fixed-point RTL output matches comparison reference.")
    print(f"BP {label} simulation artifacts: {output_dir}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BP RTL latency simulation.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--case", type=int, choices=range(1, 6))
    group.add_argument("--config-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--result-json", type=Path)
    parser.add_argument("--label")
    parser.add_argument("--skip-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = [args.case] if args.case else range(1, 6)
    if args.config_path is not None:
        output_dir = args.output_dir or PROJECT_DIR / "testcase" / args.config_path.stem
        result: object = simulate_bp_latency(
            args.config_path,
            output_dir,
            skip_run=args.skip_run,
            label=args.label,
        )
    else:
        results = [
            simulate_bp_latency(
                CONFIG_FILES[index - 1],
                PROJECT_DIR / "testcase" / f"RTL{index}",
                skip_run=args.skip_run,
                label=f"Testcase{index}",
            )
            for index in cases
        ]
        result = results[0] if args.case else results

    if args.result_json is not None:
        args.result_json.parent.mkdir(parents=True, exist_ok=True)
        args.result_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
