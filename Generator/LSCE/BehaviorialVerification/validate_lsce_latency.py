#!/usr/bin/env python3
"""Independently measure LSCE RTL latency and throughput from cycle samples.

The generated testbench is temporarily instrumented with a per-cycle ``o_H``
probe. The C++ behavioral output supplies the expected frame sequence. The
first matching RTL cycle and constant interval between all matching frames are
searched directly; neither latency nor output interval comes from a prediction.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LSCE_ROOT = ROOT.parent
SIM_DIR = ROOT / "sim"
VALIDATION_DIR = ROOT / "sim"
PROBE_FILENAME = "latency_probe.txt"
_VALIDATION_LOCK = threading.RLock()


def testcase_workspace(case_id: int) -> Path:
    """Return the mutable workspace for one simulation case."""
    return VALIDATION_DIR / f"Testcase{case_id}" / "workspace"


def tool(name: str, fallback: str) -> str:
    fallback_path = Path(fallback)
    if fallback_path.exists():
        return str(fallback_path)
    found = shutil.which(name)
    return found or name


def read_nonempty_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def load_case(case_id: int, config_path: Path | None = None, *, config: dict | None = None) -> dict:
    config_path = (
        config_path.resolve()
        if config_path is not None
        else LSCE_ROOT / "configs" / f"config_case{case_id}.json"
    )
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    sys.path.insert(0, str(LSCE_ROOT))
    try:
        from evaluate_lsce import load_config, latency_cycles
        config = load_config(config_path) if config is None else config
    finally:
        sys.path.pop(0)
    n_t = int(config["Number of Transmit Antennas"])
    p_t = int(config["Parallelism T"])
    n_pipelines = [int(x) for x in config["Pipeline Stages ([Multiplication, Adder Tree])"]]
    stg_t = math.ceil(n_t / p_t)
    predicted_latency = latency_cycles(config)
    clock_period_ns = float(config.get("clock", {}).get("period_ns", 10.0))
    if not math.isfinite(clock_period_ns) or clock_period_ns <= 0:
        raise ValueError("clock.period_ns must be a finite value greater than zero")

    return {
        "config_path": config_path,
        "n_t": n_t,
        "p_t": p_t,
        "stg_t": stg_t,
        "n_pipelines": n_pipelines,
        "latency_cycles": predicted_latency,
        "clock_period_ns": clock_period_ns,
    }


def parse_n_frames(case_dir: Path) -> int:
    tb_files = sorted(case_dir.glob("Tb*.v"))
    if not tb_files:
        raise FileNotFoundError(f"No Tb*.v testbench found in {case_dir}")
    text = tb_files[0].read_text(errors="ignore")
    marker = "for (iter_out = 0; iter_out <"
    for line in text.splitlines():
        if marker in line:
            tail = line.split(marker, 1)[1]
            return int(tail.split(";", 1)[0].strip())
    raise RuntimeError(f"Cannot detect N_FRAMES from output dump loop in {tb_files[0]}")


def parse_testbench_clock_period_ns(case_dir: Path) -> float:
    """Read the generated ``forever #half_period`` delay in nanoseconds."""
    tb_files = sorted(case_dir.glob("Tb*.v"))
    if not tb_files:
        raise FileNotFoundError(f"No Tb*.v testbench found in {case_dir}")
    text = tb_files[0].read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"forever\s+#([0-9]+(?:\.[0-9]+)?)", text)
    if match is None:
        raise RuntimeError(f"Cannot detect clock period from {tb_files[0]}")
    return 2.0 * float(match.group(1))


def check_input_reference_consistency(case_id: int, case_dir: Path, case: dict) -> tuple[bool, str]:
    generated_period_ns = parse_testbench_clock_period_ns(case_dir)
    configured_period_ns = float(case["clock_period_ns"])
    if not math.isclose(generated_period_ns, configured_period_ns, rel_tol=0.0, abs_tol=1e-9):
        return (
            False,
            f"testbench clock mismatch: config={configured_period_ns} ns, "
            f"generated={generated_period_ns} ns",
        )

    n_frames = parse_n_frames(case_dir)
    expected_input_rows = n_frames * case["stg_t"]
    case_name = f"Testcase{case_id}"
    input_dir = SIM_DIR / "Input_Files" / case_name
    comp_path = SIM_DIR / "Comparison_Files" / case_name / "o_H.txt"

    checks = [
        (input_dir / "i_Y.txt", expected_input_rows, "input i_Y rows"),
        (input_dir / "i_P.txt", expected_input_rows, "input i_P rows"),
        (comp_path, n_frames, "behavioral o_H rows"),
    ]
    if case["stg_t"] > 1:
        expected_ctrl_rows = expected_input_rows + sum(case["n_pipelines"])
        checks.append((input_dir / "i_ctrl_stg.txt", expected_ctrl_rows, "input ctrl rows"))

    for path, expected_rows, label in checks:
        actual_rows = len(read_nonempty_lines(path))
        if actual_rows != expected_rows:
            return (
                False,
                f"{label} mismatch for Testcase{case_id}: "
                f"expected {expected_rows}, found {actual_rows} in {path}",
            )

    return True, f"N_FRAMES={n_frames}, input rows={expected_input_rows}"


def find_top_module(case_dir: Path) -> str:
    tb_files = sorted(case_dir.glob("Tb*.v"))
    if not tb_files:
        raise FileNotFoundError(f"No Tb*.v testbench found in {case_dir}")

    text = tb_files[0].read_text(errors="ignore")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("module "):
            return line.split()[1].split("(")[0].strip()
    raise RuntimeError(f"Cannot detect top module from {tb_files[0]}")


def run_cmd(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed in {cwd}\n"
            f"Command: {' '.join(cmd)}\n"
            f"Output:\n{proc.stdout}"
        )


def regenerate_testcase(config_path: Path, case_id: int, *, config: dict | None = None) -> dict[str, list[str]]:
    """Generate and return the fresh C++ reference without a subprocess."""
    if __package__:
        from .generate_lsce_testcase import generate_testcase
    else:
        from generate_lsce_testcase import generate_testcase
    return generate_testcase(config_path, case_id, config=config)


def run_iverilog(case_dir: Path, top: str, probe_cycles: int) -> Path:
    """Run RTL with a temporary per-cycle output probe in the generated TB."""
    iverilog = tool("iverilog", "D:/Tools/oss-cad-suite/bin/iverilog.exe")
    vvp = tool("vvp", "D:/Tools/oss-cad-suite/bin/vvp.exe")

    verilog_files = sorted(p.name for p in case_dir.glob("*.v"))
    if not verilog_files:
        raise FileNotFoundError(f"No Verilog files found in {case_dir}")
    tb_files = sorted(case_dir.glob("Tb*.v"))
    if not tb_files:
        raise FileNotFoundError(f"No Tb*.v testbench found in {case_dir}")

    probe_path = case_dir / PROBE_FILENAME
    if probe_path.exists():
        probe_path.unlink()
    tb_path = tb_files[0]
    original_tb = tb_path.read_text(encoding="utf-8", errors="ignore")
    marker = "\n endmodule"
    marker_index = original_tb.rfind(marker)
    if marker_index < 0:
        marker = "\nendmodule"
        marker_index = original_tb.rfind(marker)
    if marker_index < 0:
        raise RuntimeError(f"Cannot instrument testbench without endmodule: {tb_path}")
    probe_block = f"""
 integer lsce_latency_probe_handle;
 integer lsce_latency_probe_cycle;
 initial begin
     @(posedge en);
     @(posedge clk);
     lsce_latency_probe_handle = $fopen(\"{PROBE_FILENAME}\", \"w\");
     for (lsce_latency_probe_cycle = 0;
          lsce_latency_probe_cycle < {probe_cycles};
          lsce_latency_probe_cycle = lsce_latency_probe_cycle + 1) begin
         #0.001;
         $fdisplay(lsce_latency_probe_handle, \"%0d %b\",
                   lsce_latency_probe_cycle, o_H);
         @(posedge clk);
     end
     $fclose(lsce_latency_probe_handle);
 end
"""
    tb_path.write_text(
        original_tb[:marker_index] + probe_block + original_tb[marker_index:],
        encoding="utf-8",
    )
    try:
        (case_dir / "files.f").write_text(
            "\n".join(verilog_files) + "\n", encoding="utf-8"
        )
        run_cmd(
            [iverilog, "-g2012", "-s", top, "-o", "wave", "-f", "files.f"],
            case_dir,
        )
        run_cmd([vvp, "-n", "wave", "-lxt2"], case_dir)
    finally:
        tb_path.write_text(original_tb, encoding="utf-8")
    if not probe_path.exists():
        raise FileNotFoundError(f"RTL latency probe was not produced: {probe_path}")
    return probe_path


def measure_rtl_timing(
    probe_path: Path,
    expected_path: Path,
    *, expected_rows: list[str] | None = None,
) -> tuple[int, int, list[str]]:
    """Measure latency and steady-state output interval from RTL cycle samples.

    The C++ behavioral output supplies only the expected frame values. Both the
    first valid-output cycle and the interval between frames are discovered by
    searching the per-cycle RTL probe; neither value is taken from the latency
    or throughput prediction formulas.
    """
    expected = read_nonempty_lines(expected_path) if expected_rows is None else expected_rows
    samples: dict[int, str] = {}
    for line in read_nonempty_lines(probe_path):
        cycle_text, value = line.split(maxsplit=1)
        samples[int(cycle_text)] = value
    if len(expected) < 2:
        raise RuntimeError(
            "At least two behavioral output frames are required to measure throughput"
        )
    if not samples:
        raise RuntimeError("Cannot measure RTL timing from an empty cycle probe")

    max_cycle = max(samples)
    matches: list[tuple[int, int, list[str]]] = []
    max_interval = max_cycle // (len(expected) - 1)
    for interval in range(1, max_interval + 1):
        sequence_span = (len(expected) - 1) * interval
        for start_cycle in range(max_cycle - sequence_span + 1):
            observed = [
                samples.get(start_cycle + index * interval)
                for index in range(len(expected))
            ]
            if observed == expected:
                matches.append(
                    (start_cycle, interval, [str(value) for value in observed])
                )

    if not matches:
        raise RuntimeError(
            "No constant-interval RTL cycle sequence matched the complete C++ "
            "behavioral output; latency and throughput could not be measured"
        )

    start_cycle, output_interval, observed = min(
        matches, key=lambda match: (match[0], match[1])
    )
    return start_cycle + 1, output_interval, observed

def clean_case_generated_outputs(case_id: int, case_dir: Path) -> None:
    """Keep TestcaseN and let this run overwrite only standard result files."""
    (VALIDATION_DIR / f"Testcase{case_id}").mkdir(parents=True, exist_ok=True)
    (SIM_DIR / "Output_Files" / f"Testcase{case_id}").mkdir(
        parents=True, exist_ok=True
    )
    case_dir.mkdir(parents=True, exist_ok=True)


def save_measured_artifacts(
    case_id: int,
    case: dict,
    case_dir: Path,
    measured_latency: int,
    measured_output_interval: int,
    measured_rows: list[str],
    expected_src: Path,
) -> dict[str, Path]:
    """Save independently measured RTL outputs and a machine-readable result."""
    dest_dir = VALIDATION_DIR / f"Testcase{case_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    observed_dst = dest_dir / f"rtl_o_H_latency_{measured_latency}cycles.txt"
    expected_dst = dest_dir / "behavioral_o_H_reference.txt"
    wave_dst = dest_dir / "wave.vcd"
    meta_dst = dest_dir / "latency_check.txt"
    result_dst = dest_dir / "simulation_result.json"

    observed_dst.write_text("\n".join(measured_rows) + "\n", encoding="utf-8")
    shutil.copy2(expected_src, expected_dst)
    if (case_dir / "wave.vcd").exists():
        shutil.copy2(case_dir / "wave.vcd", wave_dst)

    result = {
        "case": f"Testcase{case_id}",
        "predicted_latency_cycles": int(case["latency_cycles"]),
        "sim_latency_cycles": int(measured_latency),
        "sim_output_interval_cycles": int(measured_output_interval),
        "clock_period_ns": float(case["clock_period_ns"]),
        "measurement_method": "RTL cycle positions matching the complete C++ output sequence",
    }
    result_dst.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    meta_dst.write_text(
        "\n".join(
            [
                f"case=Testcase{case_id}",
                f"predicted_latency_cycles={case['latency_cycles']}",
                f"rtl_measured_latency_cycles={measured_latency}",
                f"rtl_measured_output_interval_cycles={measured_output_interval}",
                f"clock_period_ns={case['clock_period_ns']}",
                "measurement_method=RTL cycle positions matching the complete C++ output sequence",
                f"N_PIPELINES={case['n_pipelines']}",
                f"STG_T={case['stg_t']}",
                f"rtl_output={observed_dst.name}",
                f"behavioral_reference={expected_dst.name}",
                f"waveform={wave_dst.name if wave_dst.exists() else 'not_copied'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "observed": observed_dst,
        "expected": expected_dst,
        "wave": wave_dst,
        "meta": meta_dst,
        "result": result_dst,
    }

def compare_outputs(expected_path: Path, observed_path: Path) -> tuple[bool, str]:
    expected = read_nonempty_lines(expected_path)
    observed = read_nonempty_lines(observed_path)

    if len(expected) != len(observed):
        return (
            False,
            f"line count mismatch: expected {len(expected)}, observed {len(observed)}",
        )

    for idx, (exp, obs) in enumerate(zip(expected, observed), start=1):
        if exp != obs:
            return (
                False,
                f"first mismatch at output row {idx}: expected {exp}, observed {obs}",
            )

    return True, f"{len(expected)} output row(s) matched"


def run_validation(config_path: Path, case_id: int, *, config: dict | None = None) -> dict:
    """Build fresh reference/RTL and return independently measured timing."""
    global SIM_DIR
    with _VALIDATION_LOCK:
        previous_sim_dir = SIM_DIR
        try:
            sys.path.insert(0, str(LSCE_ROOT))
            try:
                from evaluate_lsce import load_config, validate_config, _case_id
                config_path = config_path.resolve()
                config = load_config(config_path) if config is None else validate_config(config, config_path)
                if isinstance(case_id, bool) or not isinstance(case_id, int) or case_id < 0 or _case_id(config_path) != case_id:
                    raise ValueError("case_id must match config_caseN.json")
                if int(config["Parallelism R"]) != int(config["Number of Receiving Antennas"]):
                    raise ValueError("Complete RTL simulation requires P_R == N_R")
            finally:
                sys.path.pop(0)
            case = load_case(case_id, config_path, config=config)
            SIM_DIR = testcase_workspace(case_id)
            case_dir = SIM_DIR / "RTL" / f"Testcase{case_id}"
            expected_path = SIM_DIR / "Comparison_Files" / f"Testcase{case_id}" / "o_H.txt"
            rows = regenerate_testcase(case["config_path"], case_id, config=config)
            consistent, detail = check_input_reference_consistency(case_id, case_dir, case)
            if not consistent:
                raise RuntimeError(detail)
            n_frames = len(rows["o_H"])
            probe_cycles = int(case["latency_cycles"]) + (n_frames - 1) * int(case["stg_t"]) + 32
            clean_case_generated_outputs(case_id, case_dir)
            probe = run_iverilog(case_dir, find_top_module(case_dir), probe_cycles)
            measured_latency, interval, observed = measure_rtl_timing(
                probe, expected_path, expected_rows=rows["o_H"])
            save_measured_artifacts(case_id, case, case_dir, measured_latency,
                                    interval, observed, expected_path)
            return {
                "case": f"Testcase{case_id}",
                "predicted_latency_cycles": int(case["latency_cycles"]),
                "sim_latency_cycles": measured_latency,
                "sim_output_interval_cycles": interval,
                "clock_period_ns": float(case["clock_period_ns"]),
                "measurement_method": "RTL cycle positions matching the complete C++ output sequence",
            }
        finally:
            SIM_DIR = previous_sim_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure LSCE RTL latency and output interval with Icarus Verilog."
    )
    parser.add_argument("--case", type=int, default=1, help="non-negative LSCE case id")
    parser.add_argument(
        "--config",
        type=Path,
        help="configuration path; defaults to configs/config_caseN.json",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Reuse the last independently measured validation artifacts.",
    )

    args = parser.parse_args()

    if not args.skip_run:
        selected = args.config or LSCE_ROOT / "configs" / f"config_case{args.case}.json"
        result = run_validation(selected, args.case)
        print(json.dumps(result, indent=2))
        return 0

    if args.case < 0:
        raise ValueError("LSCE case id must be non-negative")
    case = load_case(args.case, args.config)
    case_name = f"Testcase{args.case}"
    artifacts_dir = VALIDATION_DIR / case_name
    snapshot = artifacts_dir / "config_snapshot.json"
    current = json.loads(case["config_path"].read_text(encoding="utf-8-sig"))
    if not snapshot.is_file() or json.loads(snapshot.read_text(encoding="utf-8")) != current:
        raise ValueError("Saved RTL artifacts belong to a different config; rerun without --skip-run")
    result_path = artifacts_dir / "simulation_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if "sim_output_interval_cycles" not in result:
        raise ValueError("Saved result has no RTL interval; rerun without --skip-run")
    observed_path = artifacts_dir / f"rtl_o_H_latency_{int(result['sim_latency_cycles'])}cycles.txt"
    ok, detail = compare_outputs(artifacts_dir / "behavioral_o_H_reference.txt", observed_path)
    if not ok:
        raise RuntimeError(detail)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
