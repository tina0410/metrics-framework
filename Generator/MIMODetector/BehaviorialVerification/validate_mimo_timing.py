#!/usr/bin/env python3
"""Run an isolated MIMO RTL testcase and measure latency/throughput from VCD."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MIMO_ROOT = ROOT.parent
SIM_ROOT = ROOT / "sim"


def parse_testbench_clock_period_ns(testbench: Path) -> float:
    """Return the full clock period from ``forever #half_period``."""
    # Generated comments may use the Windows locale encoding.  Clock syntax is
    # ASCII, so replacing undecodable comment bytes is safe and deterministic.
    text = testbench.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"forever\s+#([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        raise ValueError(f"{testbench}: generated clock delay was not found")
    return 2.0 * float(match.group(1))


def _run(command: list[str], cwd: Path) -> None:
    process = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Command failed in {cwd}: {' '.join(command)}\n{process.stdout}")


def _top_signal_ids(vcd_path: Path) -> dict[str, str]:
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
                if reference in {"clk", "en", "o_data"}:
                    result[reference] = identifier
            elif words[0] == "$enddefinitions":
                break
    missing = {"clk", "en", "o_data"} - result.keys()
    if missing:
        raise ValueError(f"{vcd_path}: missing top-level VCD signals {sorted(missing)}")
    return result


def _posedge_samples(vcd_path: Path) -> tuple[int, list[tuple[int, str]]]:
    ids = _top_signal_ids(vcd_path)
    values: dict[str, str] = {ids["clk"]: "x", ids["en"]: "0", ids["o_data"]: "x"}
    current_time = 0
    pending_posedge = False
    samples: list[tuple[int, str]] = []
    en_rise_time: int | None = None

    def finish_timestamp() -> None:
        nonlocal pending_posedge
        if pending_posedge:
            samples.append((current_time, values[ids["o_data"]]))
        pending_posedge = False

    with vcd_path.open("r", encoding="ascii", errors="replace") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("$"):
                continue
            if line.startswith("#"):
                finish_timestamp()
                current_time = int(line[1:])
                continue
            if line[0] in "01xz":
                value, identifier = line[0], line[1:]
            elif line[0] in "bBrR":
                parts = line.split()
                if len(parts) != 2:
                    continue
                value, identifier = parts[0][1:].lower(), parts[1]
            else:
                continue
            old_value = values.get(identifier)
            values[identifier] = value
            if identifier == ids["clk"] and old_value == "0" and value == "1":
                pending_posedge = True
            if identifier == ids["en"] and old_value == "0" and value == "1":
                en_rise_time = current_time
    finish_timestamp()
    if en_rise_time is None:
        raise ValueError(f"{vcd_path}: input stimulus-valid signal en never rose")
    accepted = next((i for i, (stamp, _) in enumerate(samples) if stamp > en_rise_time), None)
    if accepted is None:
        raise ValueError(f"{vcd_path}: no clock edge sampled after input valid")
    return accepted, samples


def _split_lanes(value: str, width: int, lanes: int) -> list[str]:
    padded = value.lower().replace("z", "x").zfill(width * lanes)
    return [padded[-(lane + 1) * width : len(padded) - lane * width or None] for lane in range(lanes)]


def measure_rtl_timing(
    vcd_path: Path, expected_path: Path, *, tx: int, output_width: int
) -> dict[str, Any]:
    """Match every complete C++ output vector and measure frame intervals."""
    expected = [
        line.strip().lower()
        for line in expected_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(expected) < tx or len(expected) % tx:
        raise ValueError(
            f"{expected_path}: expected a whole number of {tx}-element vectors, found {len(expected)} values"
        )
    accepted_index, samples = _posedge_samples(vcd_path)
    frame_count = len(expected) // tx
    match_starts: list[int] = []
    cursor = accepted_index
    for frame_index in range(frame_count):
        wanted = expected[frame_index * tx : (frame_index + 1) * tx]
        match_start = next(
            (
                start
                for start in range(cursor, len(samples) - tx + 1)
                if all(
                    wanted[offset]
                    in _split_lanes(samples[start + offset][1], output_width, tx)
                    for offset in range(tx)
                )
            ),
            None,
        )
        if match_start is None:
            raise ValueError(
                f"{vcd_path}: C++ output vector {frame_index + 1}/{frame_count} was not found on consecutive RTL edges"
            )
        match_starts.append(match_start)
        cursor = match_start + tx

    completion_indices = [start + tx - 1 for start in match_starts]
    intervals = [right - left for left, right in zip(match_starts, match_starts[1:])]
    stable_interval = intervals[0] if intervals and len(set(intervals)) == 1 else None
    first_start = match_starts[0]
    first_completion = completion_indices[0]
    return {
        "sim_latency_cycles": first_completion - accepted_index,
        "sim_output_interval_cycles": stable_interval,
        "sim_output_interval_cycle_list": intervals,
        "matched_output_frames": frame_count,
        "input_accept_cycle": 0,
        "first_output_cycle": first_start - accepted_index,
        "complete_output_cycle": first_completion - accepted_index,
        "input_sample_time": samples[accepted_index][0],
        "first_output_sample_time": samples[first_start][0],
        "complete_output_sample_time": samples[first_completion][0],
        "frame_first_output_sample_times": [samples[index][0] for index in match_starts],
        "measurement_method": (
            "VCD clock-edge positions independently matching every complete C++ output vector; "
            "latency ends at the first vector's final component and throughput uses adjacent vector intervals"
        ),
    }


def _regenerate_testcase(config_path: Path, case_id: int) -> None:
    script = ROOT / "generate_mimo_testcase.py"
    process = subprocess.run(
        [sys.executable, str(script), "--config", str(config_path), "--case", str(case_id)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stdout)


def validate_case(case_id: int, config_path: Path | None = None) -> dict[str, Any]:
    config_path = (
        config_path.resolve()
        if config_path is not None
        else MIMO_ROOT / "configs" / f"config_case{case_id}.json"
    )
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    _regenerate_testcase(config_path, case_id)

    case_name = f"Testcase{case_id}"
    case_root = SIM_ROOT / case_name
    workspace = case_root / "workspace"
    snapshot = json.loads((case_root / "config_snapshot.json").read_text(encoding="utf-8-sig"))
    if snapshot != config:
        raise ValueError(f"{case_root / 'config_snapshot.json'} does not match the active config")

    rtl_dir = workspace / "RTL" / case_name
    testbenches = list(rtl_dir.glob("TbPE*.v"))
    if len(testbenches) != 1:
        raise FileNotFoundError(f"Expected one generated MIMO testbench in {rtl_dir}, found {len(testbenches)}")
    testbench = testbenches[0]
    configured_period_ns = float(config.get("clock", {}).get("period_ns", 10.0))
    if not math.isfinite(configured_period_ns) or configured_period_ns <= 0:
        raise ValueError("clock.period_ns must be a finite value greater than zero")
    generated_period_ns = parse_testbench_clock_period_ns(testbench)
    if not math.isclose(generated_period_ns, configured_period_ns, rel_tol=0.0, abs_tol=1e-3):
        raise ValueError(
            f"testbench clock mismatch: config={configured_period_ns} ns, generated={generated_period_ns} ns"
        )

    expected_path = workspace / "Comparison_Files" / "PE_o_data.txt"
    output_path = workspace / "Output_Files" / "PE_o_data.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)
    for artifact in (rtl_dir / "wave", rtl_dir / "wave.vcd"):
        artifact.unlink(missing_ok=True)

    verilog_files = sorted(path.name for path in rtl_dir.glob("*.v"))
    started = time.perf_counter()
    _run(["iverilog", "-o", "wave", *verilog_files], rtl_dir)
    _run(["vvp", "-n", "wave"], rtl_dir)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if not output_path.exists():
        raise FileNotFoundError(f"RTL simulation did not generate {output_path}")
    expected = [line.strip() for line in expected_path.read_text().splitlines() if line.strip()]
    actual = [line.strip() for line in output_path.read_text().splitlines() if line.strip()]
    if actual != expected:
        raise ValueError(
            f"RTL output mismatch for config_case{case_id}: expected {len(expected)} values, got {len(actual)}"
        )

    tx = int(config["Number of Transmit Antennas"])
    configured_frames = int(config.get("flow", {}).get("simulation_frames", 3))
    if len(expected) != tx * configured_frames:
        raise ValueError(
            f"Expected {configured_frames} frames x {tx} values, got {len(expected)} reference values"
        )
    final_output_name = f"x{int(config['Iterations']) + 1}"
    quantization_key = f"Quantization format of {final_output_name}"
    output_width = int(config[quantization_key]["bitwidth"])
    result = measure_rtl_timing(
        rtl_dir / "wave.vcd", expected_path, tx=tx, output_width=output_width
    )
    result.update(
        {
            "case": case_name,
            "clock_period_ns": configured_period_ns,
            "clock_frequency_mhz": 1000.0 / configured_period_ns,
            "physical_latency_ns": result["sim_latency_cycles"] * configured_period_ns,
            "functional_match": True,
            "rtl_compile_and_simulation_time_ms": round(elapsed_ms, 3),
        }
    )

    shutil.copy2(expected_path, case_root / "behavioral_output_reference.txt")
    shutil.copy2(output_path, case_root / "rtl_output.txt")
    shutil.copy2(rtl_dir / "wave.vcd", case_root / "wave.vcd")
    (case_root / "latency_check.txt").write_text(
        "\n".join(
            (
                f"sim_latency_cycles={result['sim_latency_cycles']}",
                f"sim_output_interval_cycles={result['sim_output_interval_cycles']}",
                f"sim_output_interval_cycle_list={result['sim_output_interval_cycle_list']}",
                f"clock_period_ns={configured_period_ns}",
                f"clock_frequency_mhz={result['clock_frequency_mhz']}",
            )
        ) + "\n",
        encoding="utf-8",
    )
    (case_root / "simulation_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure MIMO RTL latency and throughput")
    parser.add_argument("--case", type=int, required=True)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_case(args.case, args.config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
