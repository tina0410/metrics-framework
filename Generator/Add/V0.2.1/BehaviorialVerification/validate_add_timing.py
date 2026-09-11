#!/usr/bin/env python3
"""Validate ADD with its original testbench and QuBLAS reference chain."""

from __future__ import annotations

import argparse
import bisect
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
ADD_ROOT = ROOT.parent
SIM_ROOT = Path(os.environ.get("ADD_SIM_ROOT", ADD_ROOT / "sim")).resolve()


def _top_signal_ids(vcd_path: Path) -> dict[str, str]:
    wanted = {"clk", "Input_rdy", "Output_rdy"}
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
            elif words[0] == "$var" and len(scope) == 1:
                identifier, reference = words[3], words[4]
                if reference in wanted:
                    result[reference] = identifier
            elif words[0] == "$enddefinitions":
                break
    missing = wanted - result.keys()
    if missing:
        raise ValueError(f"{vcd_path}: missing ADD timing signals {sorted(missing)}")
    return result


def _rising_times(vcd_path: Path) -> dict[str, list[int]]:
    ids = _top_signal_ids(vcd_path)
    by_id = {identifier: name for name, identifier in ids.items()}
    values = {identifier: "x" for identifier in by_id}
    rises = {name: [] for name in ids}
    current_time = 0
    with vcd_path.open("r", encoding="ascii", errors="replace") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("$"):
                continue
            if line.startswith("#"):
                current_time = int(line[1:])
                continue
            if line[0] not in "01xz":
                continue
            value, identifier = line[0], line[1:]
            if identifier not in by_id:
                continue
            old_value = values[identifier]
            values[identifier] = value
            if value == "1" and old_value != "1":
                rises[by_id[identifier]].append(current_time)
    return rises


def _timescale_ns(vcd_path: Path) -> float:
    header = vcd_path.read_text(encoding="ascii", errors="replace")
    match = re.search(
        r"\$timescale\s+([0-9]+(?:\.[0-9]+)?)\s*(s|ms|us|ns|ps|fs)\s+\$end",
        header,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError(f"{vcd_path}: missing or unsupported VCD timescale")
    unit_ns = {
        "s": 1e9,
        "ms": 1e6,
        "us": 1e3,
        "ns": 1.0,
        "ps": 1e-3,
        "fs": 1e-6,
    }
    return float(match.group(1)) * unit_ns[match.group(2).lower()]


def measure_timing(vcd_path: Path) -> dict[str, Any]:
    rises = _rising_times(vcd_path)
    clocks = rises["clk"]
    inputs = rises["Input_rdy"]
    outputs = rises["Output_rdy"]
    if not clocks or not inputs or len(outputs) < 3:
        raise ValueError(f"{vcd_path}: insufficient ADD ready/clock transitions")

    def cycle_at(timestamp: int) -> int:
        return bisect.bisect_right(clocks, timestamp) - 1

    input_cycle = cycle_at(inputs[0])
    output_cycles = [cycle_at(timestamp) for timestamp in outputs[:3]]
    intervals = [right - left for left, right in zip(output_cycles, output_cycles[1:])]
    if len(set(intervals)) != 1:
        raise ValueError(f"ADD output interval is not stable: {intervals}")
    timescale_ns = _timescale_ns(vcd_path)
    output_times_ns = [timestamp * timescale_ns for timestamp in outputs[:3]]
    output_interval_ns_list = [
        right - left for left, right in zip(output_times_ns, output_times_ns[1:])
    ]
    measured_span_ns = output_times_ns[-1] - output_times_ns[0]
    if measured_span_ns <= 0:
        raise ValueError(f"{vcd_path}: ADD output timestamp span must be positive")
    simulated_throughput = (len(output_times_ns) - 1) / measured_span_ns
    return {
        "sim_latency_cycles": output_cycles[0] - input_cycle,
        "sim_output_interval_cycles": intervals[0],
        "sim_output_interval_cycle_list": intervals,
        "input_ready_time": inputs[0],
        "output_ready_times": outputs[:3],
        "vcd_timescale_ns": timescale_ns,
        "output_ready_times_ns": output_times_ns,
        "output_interval_ns_list": output_interval_ns_list,
        "average_output_interval_ns": measured_span_ns / (len(output_times_ns) - 1),
        "simulated_throughput_gframes_s": simulated_throughput,
        "measurement_method": (
            "original ADD testbench Input_rdy/Output_rdy transitions sampled against "
            "VCD clock edges; throughput measured directly from the first and last "
            "of three Output_rdy timestamps"
        ),
    }


def _run_original_chain(config_path: Path, case_label: str) -> str:
    script = ROOT / "generate_add_testcase.py"
    process = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(config_path),
            "--case-label",
            case_label,
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    if process.returncode != 0:
        raise RuntimeError("Original ADD validation chain failed:\n" + process.stdout)
    return process.stdout


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


def validate_case(config_path: Path, case_label: str) -> dict[str, Any]:
    if not case_label or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in case_label
    ):
        raise ValueError(f"Invalid ADD case label: {case_label!r}")
    case_root = SIM_ROOT / case_label
    case_root.mkdir(parents=True, exist_ok=True)
    for artifact_name in (
        "simulation_result.json",
        "behavioral_output_reference.txt",
        "rtl_output.txt",
        "wave.vcd",
    ):
        (case_root / artifact_name).unlink(missing_ok=True)
    started = time.perf_counter()
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    console_log = _run_original_chain(config_path, case_label)
    workspace = case_root / "workspace"
    snapshot = json.loads((case_root / "config_snapshot.json").read_text(encoding="utf-8-sig"))
    if snapshot != config:
        raise ValueError("ADD simulation config snapshot does not match the active config")

    rtl_dir = workspace / "RTL"
    testbenches = list(rtl_dir.glob("TbAdd*.v"))
    if len(testbenches) != 1:
        raise FileNotFoundError(
            f"Expected one original ADD testbench in {rtl_dir}, found {len(testbenches)}"
        )
    testbench_text = testbenches[0].read_text(encoding="utf-8", errors="replace")
    half_period = re.search(r"forever\s+#\(?([0-9]+(?:\.[0-9]+)?)\)?", testbench_text)
    if half_period is None:
        raise ValueError("Generated ADD testbench clock period was not found")
    generated_period_ns = 2.0 * float(half_period.group(1))
    configured_period_ns = float(config["clock"]["period_ns"])
    if not math.isclose(generated_period_ns, configured_period_ns, abs_tol=1e-9):
        raise ValueError(
            f"ADD testbench clock mismatch: config={configured_period_ns}, generated={generated_period_ns}"
        )

    rtl_files = sorted(path.name for path in rtl_dir.glob("*.v"))
    if not rtl_files:
        raise FileNotFoundError(f"No generated ADD RTL files found in {rtl_dir}")
    console_log += _run(["iverilog", "-o", "wave", *rtl_files], rtl_dir)
    console_log += _run(["vvp", "-n", "wave"], rtl_dir)

    expected_path = workspace / "Comparison_Files" / "add_o_data.txt"
    output_path = workspace / "Output_Files" / "add_o_data.txt"
    expected = [line.strip() for line in expected_path.read_text().splitlines() if line.strip()]
    actual = [line.strip() for line in output_path.read_text().splitlines() if line.strip()]
    frames = int(config.get("flow", {}).get("simulation_frames", 3))
    functional_match = expected == actual and len(expected) == frames
    if not functional_match:
        raise ValueError(
            f"Original ADD comparison failed: expected {len(expected)} frames, got {len(actual)}"
        )

    result = measure_timing(rtl_dir / "wave.vcd")
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    result.update(
        {
            "case": case_label,
            "clock_period_ns": configured_period_ns,
            "physical_latency_ns": result["sim_latency_cycles"] * configured_period_ns,
            "functional_match": functional_match,
            "matched_output_frames": len(actual),
            "rtl_simulation_time_ms": elapsed_ms,
            "testbench_source": str(ADD_ROOT / "tests" / "tb_Add.py"),
            "reference_source": "original ModuleCppConfig/ModuleCppRun with QuBLAS",
            "console_log": console_log,
            "rtl_files": [str(path) for path in sorted(rtl_dir.glob("*.v"))],
        }
    )
    shutil.copy2(expected_path, case_root / "behavioral_output_reference.txt")
    shutil.copy2(output_path, case_root / "rtl_output.txt")
    shutil.copy2(rtl_dir / "wave.vcd", case_root / "wave.vcd")
    (case_root / "simulation_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate ADD timing with its original chain")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--case-label", required=True)
    args = parser.parse_args()
    # Escaping non-ASCII paths keeps CLI output portable on GBK Windows consoles.
    print(json.dumps(validate_case(args.config, args.case_label), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
