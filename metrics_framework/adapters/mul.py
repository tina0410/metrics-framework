"""Unified metrics adapter for the fixed-point MUL generator."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = PROJECT_ROOT / "Generator" / "Mul" / "V0.2.1"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MODULE_ROOT))

from metrics_framework.adapters.common import configured_area, configured_latency, run_cli  # noqa: E402


def _module():
    import mul_metrics

    return mul_metrics


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    module = _module()
    params = module.parameters(config)

    started = time.perf_counter()
    latency = module.latency_cycles(params)
    latency_time_ms = (time.perf_counter() - started) * 1000.0

    models = module.load_area_models()
    started = time.perf_counter()
    area = module.predict_area(models, params)
    area_time_ms = (time.perf_counter() - started) * 1000.0

    started = time.perf_counter()
    throughput = module.throughput_gframes_s(params)
    throughput_time_ms = (time.perf_counter() - started) * 1000.0

    ge_area = module.read_ge_area()
    started = time.perf_counter()
    complexity = area / ge_area * latency
    complexity_time_ms = (time.perf_counter() - started) * 1000.0
    return {
        "latency": {
            "predicted_cycles": latency,
            "prediction_time_ms": latency_time_ms,
            "source": "formula",
        },
        "area": {
            "predicted_um2": area,
            "prediction_time_ms": area_time_ms,
            "source": "model",
        },
        "throughput": {
            "predicted": throughput,
            "unit": "Gframes/s",
            "precision": 3,
            "prediction_time_ms": throughput_time_ms,
            "source": "simulation_formula",
        },
        "hardware_complexity": {
            "predicted_ge_cycles": complexity,
            "prediction_time_ms": complexity_time_ms,
            "ge_reference_cell": module.GE_REFERENCE_CELL,
            "ge_area_um2": ge_area,
            "source": "derived",
        },
    }


def validate(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    module = _module()
    params = module.parameters(config)
    actual_area, synthesis_time, area_speedup = configured_area(config)
    area_had_config = any(
        value is not None for value in (actual_area, synthesis_time, area_speedup)
    )
    area_source = "config"
    if actual_area is None or (synthesis_time is None and area_speedup is None):
        reference = module.read_area_reference(params)
        actual_area = actual_area or reference["actual_area_um2"]
        synthesis_time = synthesis_time or reference["synthesis_time_ms"]
        area_source = "config+dc_reference" if area_had_config else "dc_reference"

    configured_cycles, validation_time, interval, latency_speedup = configured_latency(config)
    expected_cycles = module.latency_cycles(params)
    if configured_cycles is not None and configured_cycles != expected_cycles:
        raise ValueError("validation.latency.actual_cycles must equal n_pipeline for MUL")
    if interval is not None and interval != 1:
        raise ValueError(
            "validation.latency.output_interval_cycles must equal 1 for pipelined MUL"
        )
    started = time.perf_counter()
    simulation = module.simulate_latency(config_path, config, params)
    measured_time_ms = (time.perf_counter() - started) * 1000.0
    if simulation.get("functional_match") is not True:
        raise RuntimeError("MUL RTL functional comparison failed")
    measured_cycles = int(simulation["sim_latency_cycles"])
    measured_interval = int(simulation["sim_output_interval_cycles"])
    if measured_cycles != expected_cycles:
        raise RuntimeError(
            f"MUL RTL latency {measured_cycles} does not equal n_pipeline {params[8]}"
        )
    if measured_interval != 1:
        raise RuntimeError(
            f"MUL RTL output interval {measured_interval} does not equal 1 cycle"
        )
    if configured_cycles is not None and configured_cycles != measured_cycles:
        raise ValueError("validation.latency.actual_cycles does not match fresh MUL RTL simulation")
    if interval is not None and interval != measured_interval:
        raise ValueError(
            "validation.latency.output_interval_cycles does not match fresh MUL RTL simulation"
        )
    configured_cycles = measured_cycles
    interval = measured_interval
    validation_time = measured_time_ms
    latency_source = "rtl"
    print(
        f"Success. The RTL latency of {config_path.stem} is {measured_cycles} cycles",
        file=sys.stderr,
    )

    throughput = module.throughput_gframes_s(params, interval_cycles=int(interval))
    ge_area = module.read_ge_area()
    complexity = float(actual_area) / ge_area * int(configured_cycles)
    return {
        "latency": {
            "actual_cycles": configured_cycles,
            "simulation_time_ms": validation_time,
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
        "throughput": {"actual": throughput, "source": "rtl_derived"},
        "hardware_complexity": {
            "actual_ge_cycles": complexity,
            "source": "derived",
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_cli("mul", predict, validate))
