"""Unified metrics adapter for the fixed-point ADD generator."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = PROJECT_ROOT / "Generator" / "Add" / "V0.2.1"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MODULE_ROOT))

from metrics_framework.adapters.common import configured_area, configured_latency, run_cli  # noqa: E402


def _module():
    import add_metrics

    return add_metrics


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    module = _module()
    params = module.parameters(config)

    started = time.perf_counter()
    latency = module.latency_cycles(params)
    latency_time_ms = (time.perf_counter() - started) * 1000.0

    model = module.load_area_model()
    started = time.perf_counter()
    area = module.predict_area(model, params)
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
            "source": "formula",
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
        reference_source = reference.get("source", "dc_reference")
        area_source = f"config+{reference_source}" if area_had_config else reference_source

    configured_cycles, validation_time, interval, latency_speedup = configured_latency(config)
    predicted_cycles = module.latency_cycles(params)
    if configured_cycles is not None and configured_cycles != predicted_cycles:
        raise ValueError(
            "validation.latency.actual_cycles must equal n_pipeline for ADD"
        )
    if interval is not None and interval != 1:
        raise ValueError(
            "validation.latency.output_interval_cycles must equal 1 for pipelined ADD"
        )
    latency_had_config = configured_cycles is not None or interval is not None or validation_time is not None
    latency_source = "config"
    if (
        configured_cycles is None
        or interval is None
        or (validation_time is None and latency_speedup is None)
    ):
        simulation = module.simulate_latency(config_path, params)
        if simulation.get("functional_match") is not True:
            raise RuntimeError("ADD RTL functional comparison failed")
        measured_cycles = int(simulation["sim_latency_cycles"])
        measured_interval = int(simulation["sim_output_interval_cycles"])
        if measured_cycles != predicted_cycles:
            raise RuntimeError(
                f"ADD RTL latency {measured_cycles} does not equal n_pipeline {params[8]}"
            )
        configured_cycles = configured_cycles or measured_cycles
        interval = interval or measured_interval
        validation_time = validation_time or float(simulation["rtl_simulation_time_ms"])
        latency_source = "config+rtl" if latency_had_config else "rtl"
        print(
            f"Success. The RTL latency of {config_path.stem} is {measured_cycles} cycles",
            file=sys.stderr,
        )
    actual_cycles = configured_cycles

    throughput = 1.0 / (params[10] * int(interval))
    ge_area = module.read_ge_area()
    complexity = float(actual_area) / ge_area * actual_cycles
    return {
        "latency": {
            "actual_cycles": actual_cycles,
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
    raise SystemExit(run_cli("add", predict, validate))
