"""Unified metrics adapter for Abs latency evaluation."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = PROJECT_ROOT / "Generator" / "BasicModules" / "Abs"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MODULE_ROOT))

from metrics_framework.adapters.common import run_cli  # noqa: E402


def _module():
    import abs_metrics

    return abs_metrics


def _unavailable_prediction() -> dict[str, Any]:
    return {
        "area": {
            "predicted_um2": None,
            "prediction_time_ms": None,
            "source": "unavailable",
        },
        "hardware_complexity": {
            "predicted_ge_cycles": None,
            "prediction_time_ms": None,
            "ge_reference_cell": None,
            "ge_area_um2": None,
            "source": "unavailable",
        },
    }


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    module = _module()
    params = module.parameters(config)
    started = time.perf_counter()
    latency = module.latency_cycles(params)
    latency_time_ms = (time.perf_counter() - started) * 1000.0

    metrics: dict[str, Any] = {
        "latency": {
            "predicted_cycles": latency,
            "prediction_time_ms": latency_time_ms,
            "source": "formula",
        },
    }
    metrics.update(_unavailable_prediction())
    return metrics


def validate(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    module = _module()
    params = module.parameters(config)
    simulation = module.simulate_latency(params)
    if simulation.get("functional_match") is not True:
        raise RuntimeError("Abs RTL functional comparison failed")
    actual_cycles = int(simulation["sim_latency_cycles"])
    print(
        f"Success. The RTL latency of {config_path.stem} is {actual_cycles} cycles",
        file=sys.stderr,
    )
    return {
        "latency": {
            "actual_cycles": actual_cycles,
            "simulation_time_ms": float(simulation["rtl_simulation_time_ms"]),
            "reported_speedup": None,
            "source": "tests_rtl",
        },
        "area": {
            "actual_um2": None,
            "synthesis_time_ms": None,
            "reported_speedup": None,
            "source": "unavailable",
        },
        "hardware_complexity": {
            "actual_ge_cycles": None,
            "source": "unavailable",
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_cli("abs", predict, validate))
