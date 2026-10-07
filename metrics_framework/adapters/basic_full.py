"""Shared full-metric adapter flow for fixed-point basic modules."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from metrics_framework.adapters.basic_area import (
    prediction_metrics,
    read_area_reference,
    validation_metrics,
)
from metrics_framework.adapters.common import configured_latency
from metrics_framework.testing.run_basic_rtl_case import run_report_rtl_case


def _latency_params(
    module_name: str, module: Any, config: dict[str, Any]
) -> Any | None:
    try:
        return module.parameters(config)
    except ValueError:
        # The DC workbook is the source of truth for area cases. Legacy RTL tests
        # cover fixed, different parameter sets, so do not run one as this case.
        read_area_reference(module_name, config)
        return None


def _latency_cycles(
    module_name: str, module: Any, config: dict[str, Any], params: Any | None
) -> int:
    if params is not None:
        return int(module.latency_cycles(params))
    cycles = (
        1
        if module_name == "counter"
        else 0
        if module_name == "mux"
        else int(config["n_pipeline"])
    )
    if cycles < 0:
        raise ValueError("n_pipeline must be nonnegative")
    return cycles


def _latency(
    module_name: str, module: Any, config: dict[str, Any]
) -> tuple[int, Any | None]:
    params = _latency_params(module_name, module, config)
    return _latency_cycles(module_name, module, config, params), params


def predict(module_name: str, module: Any, config: dict[str, Any]) -> dict[str, Any]:
    # Parameter parsing and workbook-backed case validation are preparation,
    # not part of the latency formula's prediction time.
    params = _latency_params(module_name, module, config)
    started = time.perf_counter()
    cycles = _latency_cycles(module_name, module, config, params)
    latency_time_ms = (time.perf_counter() - started) * 1000.0
    latency: dict[str, Any] = {
        "predicted_cycles": cycles,
        "prediction_time_ms": latency_time_ms,
        "source": "formula" if params is not None else "report_configuration_formula",
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
    expected_cycles, params = _latency(module_name, module, config)
    configured_cycles, _configured_time, configured_interval, latency_speedup = configured_latency(config)
    if params is None:
        simulation = run_report_rtl_case(module_name, config_path, config)
    else:
        simulation = module.simulate_latency(params)
    if simulation.get("functional_match") is not True:
        raise RuntimeError(f"{display_name} RTL functional comparison failed")
    actual_cycles = int(simulation["sim_latency_cycles"])
    interval = int(simulation.get("sim_output_interval_cycles", 1))
    simulation_time_ms = float(simulation["rtl_simulation_time_ms"])
    source = "tests_rtl_config" if params is None else "tests_rtl"
    print(
        f"Success. The RTL latency of {config_path.stem} is {actual_cycles} cycles",
        file=sys.stderr,
    )
    if configured_cycles is not None and configured_cycles != actual_cycles:
        raise ValueError(
            f"validation.latency.actual_cycles does not match {display_name} {source}"
        )
    if configured_interval is not None and configured_interval != interval:
        raise ValueError(
            f"validation.latency.output_interval_cycles does not match {display_name} {source}"
        )
    result: dict[str, Any] = {
        "latency": {
            "actual_cycles": actual_cycles,
            "simulation_time_ms": simulation_time_ms,
            "output_interval_cycles": interval,
            "reported_speedup": latency_speedup,
            "source": source,
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
