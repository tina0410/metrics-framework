"""Shared full-metric adapter flow for fixed-point basic modules."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from metrics_framework.adapters.basic_area import prediction_metrics, validation_metrics
from metrics_framework.adapters.common import configured_latency


def predict(module_name: str, module: Any, config: dict[str, Any]) -> dict[str, Any]:
    params = module.parameters(config)
    started = time.perf_counter()
    cycles = int(module.latency_cycles(params))
    latency_time_ms = (time.perf_counter() - started) * 1000.0
    latency: dict[str, Any] = {
        "predicted_cycles": cycles,
        "prediction_time_ms": latency_time_ms,
        "source": "formula",
    }
    result = {"latency": latency}
    result.update(prediction_metrics(module_name, config, cycles))
    return result


def validate(
    module_name: str,
    display_name: str,
    module: Any,
    config_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    params = module.parameters(config)
    configured_cycles, _configured_time, configured_interval, latency_speedup = configured_latency(config)
    simulation = module.simulate_latency(params)
    if simulation.get("functional_match") is not True:
        raise RuntimeError(f"{display_name} RTL functional comparison failed")
    actual_cycles = int(simulation["sim_latency_cycles"])
    interval = int(simulation.get("sim_output_interval_cycles", 1))
    if configured_cycles is not None and configured_cycles != actual_cycles:
        raise ValueError(
            f"validation.latency.actual_cycles does not match fresh {display_name} RTL simulation"
        )
    if configured_interval is not None and configured_interval != interval:
        raise ValueError(
            f"validation.latency.output_interval_cycles does not match fresh {display_name} RTL simulation"
        )
    print(
        f"Success. The RTL latency of {config_path.stem} is {actual_cycles} cycles",
        file=sys.stderr,
    )
    result: dict[str, Any] = {
        "latency": {
            "actual_cycles": actual_cycles,
            "simulation_time_ms": float(simulation["rtl_simulation_time_ms"]),
            "output_interval_cycles": interval,
            "reported_speedup": latency_speedup,
            "source": "tests_rtl",
        }
    }
    result.update(
        validation_metrics(
            module_name,
            config,
            actual_cycles,
            interval_cycles=interval,
        )
    )
    return result
