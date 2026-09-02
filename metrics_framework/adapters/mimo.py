from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = PROJECT_ROOT / "Generator" / "MIMODetector"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MODULE_ROOT))

from metrics_framework.adapters.common import (  # noqa: E402
    configured_area,
    configured_latency,
    run_cli,
)


def _modules():
    import evaluate_mimo
    from hardware_complexity_interface import (
        GE_REFERENCE_CELL,
        area_to_ge,
        read_ge_area,
    )
    from latency_interface import predict_latency
    from throughput_interface import evaluate_throughput

    return (
        evaluate_mimo,
        GE_REFERENCE_CELL,
        area_to_ge,
        read_ge_area,
        predict_latency,
        evaluate_throughput,
    )


def _area(action: str, config_path: Path) -> dict[str, Any]:
    worker = Path(__file__).with_name("mimo_area_worker.py")
    process = subprocess.run(
        [sys.executable, str(worker), action, str(config_path)],
        cwd=worker.parent,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stderr:
        print(process.stderr, end="" if process.stderr.endswith("\n") else "\n", file=sys.stderr)
    if process.returncode != 0:
        raise RuntimeError(process.stdout.strip() or f"MIMO area {action} failed")
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("MIMO area worker returned invalid JSON") from error
    if not isinstance(result, dict):
        raise RuntimeError("MIMO area worker returned a non-object")
    return result


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    evaluator, ge_cell, area_to_ge, read_ge_area, predict_latency, evaluate_throughput = _modules()
    config = evaluator.load_config(config_path)
    started = time.perf_counter()
    predicted_latency = predict_latency(config)
    latency_time_ms = (time.perf_counter() - started) * 1000.0
    area = _area("predict", config_path)
    throughput = evaluate_throughput(config)
    ge_area = read_ge_area()
    complexity = area_to_ge(float(area["predicted_area_um2"]), ge_area) * predicted_latency
    return {
        "latency": {
            "predicted_cycles": predicted_latency,
            "prediction_time_ms": latency_time_ms,
            "source": "model",
        },
        "area": {
            "predicted_um2": float(area["predicted_area_um2"]),
            "prediction_time_ms": float(area["prediction_time_ms"]),
            "source": "model",
        },
        "throughput": {
            "predicted": float(throughput["predicted_gbps"]),
            "unit": "Gbps",
            "precision": 9,
            "source": "formula",
        },
        "hardware_complexity": {
            "predicted_ge_cycles": complexity,
            "ge_reference_cell": ge_cell,
            "ge_area_um2": ge_area,
            "source": "derived",
        },
    }


def validate(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    evaluator, _ge_cell, area_to_ge, read_ge_area, _predict_latency, evaluate_throughput = _modules()
    config = evaluator.load_config(config_path)
    actual_area, synthesis_time, area_speedup = configured_area(config)
    area_had_config = any(
        value is not None for value in (actual_area, synthesis_time, area_speedup)
    )
    area_source = "config"
    if actual_area is None or (synthesis_time is None and area_speedup is None):
        reference = _area("validate", config_path)
        actual_area = actual_area or float(reference["actual_area_um2"])
        synthesis_time = synthesis_time or float(reference["synthesis_time_ms"])
        area_source = "config+dc_reference" if area_had_config else "dc_reference"

    actual_cycles, simulation_time, interval, latency_speedup = configured_latency(config)
    latency_had_config = actual_cycles is not None or interval is not None or simulation_time is not None
    latency_source = "config"
    if (
        actual_cycles is None
        or interval is None
        or (simulation_time is None and latency_speedup is None)
    ):
        started = time.perf_counter()
        simulation = evaluator.simulate_rtl(config_path)
        measured_time = (time.perf_counter() - started) * 1000.0
        if simulation.get("functional_match") is False:
            raise RuntimeError("MIMO RTL functional comparison failed")
        actual_cycles = actual_cycles or int(simulation["sim_latency_cycles"])
        interval = interval or int(simulation["sim_output_interval_cycles"])
        simulation_time = simulation_time or measured_time
        latency_source = "config+rtl" if latency_had_config else "rtl"

    throughput = evaluate_throughput(
        config, simulated_output_interval_cycles=int(interval)
    )
    ge_area = read_ge_area()
    actual_complexity = area_to_ge(float(actual_area), ge_area) * int(actual_cycles)
    return {
        "latency": {
            "actual_cycles": actual_cycles,
            "simulation_time_ms": simulation_time,
            "output_interval_cycles": interval,
            "reported_speedup": latency_speedup,
            "source": latency_source,
        },
        "area": {
            "actual_um2": actual_area,
            "synthesis_time_ms": synthesis_time,
            "reported_speedup": area_speedup,
            "source": area_source,
        },
        "throughput": {
            "actual": float(throughput["simulated_gbps"]),
            "source": "derived",
        },
        "hardware_complexity": {
            "actual_ge_cycles": actual_complexity,
            "source": "derived",
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_cli("mimo", predict, validate))
