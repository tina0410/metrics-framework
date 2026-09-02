from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LSCE_ROOT = PROJECT_ROOT / "Generator" / "LSCE"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(LSCE_ROOT))
os.environ.setdefault(
    "LSCE_AREA_ROOT",
    str(PROJECT_ROOT / "Area_TP_Estimator" / "Est_LS_CE_M2V"),
)

from metrics_framework.adapters.common import (  # noqa: E402
    configured_area,
    configured_latency,
    run_cli,
)


GE_AREA_UM2 = 1.12
GE_REFERENCE_CELL = "LVT_NAND2HDV0"


def _module():
    import evaluate_lsce

    return evaluate_lsce


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    module = _module()
    config = module.validate_config(config, config_path)
    started = time.perf_counter()
    predicted_latency = module.latency_cycles(config)
    latency_time_ms = (time.perf_counter() - started) * 1000.0
    area = module.evaluate_predicted_area(config_path)
    period_ns = float(config.get("clock", {}).get("period_ns", 10.0))
    throughput = module.throughput_kchannels_s(config, period_ns)
    complexity = float(area["predicted_area_um2"]) / GE_AREA_UM2 * predicted_latency
    return {
        "latency": {
            "predicted_cycles": predicted_latency,
            "prediction_time_ms": latency_time_ms,
            "source": "formula",
        },
        "area": {
            "predicted_um2": float(area["predicted_area_um2"]),
            "prediction_time_ms": float(area["prediction_time_ms"]),
            "source": "model",
        },
        "throughput": {
            "predicted": throughput,
            "unit": "kChannels/s",
            "precision": 5,
            "source": "formula",
        },
        "hardware_complexity": {
            "predicted_ge_cycles": complexity,
            "ge_reference_cell": GE_REFERENCE_CELL,
            "ge_area_um2": GE_AREA_UM2,
            "source": "derived",
        },
    }


def validate(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    module = _module()
    config = module.validate_config(config, config_path)
    actual_area, synthesis_time, area_speedup = configured_area(config)
    area_had_config = any(
        value is not None for value in (actual_area, synthesis_time, area_speedup)
    )
    area_source = "config"
    if actual_area is None or (synthesis_time is None and area_speedup is None):
        reference = module.read_workbook_area_reference(config)
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
        simulation = module.simulate_lsce(config_path, config=config)
        measured_time = (time.perf_counter() - started) * 1000.0
        rtl_cycles = int(simulation["latency_cycles"])
        print(
            f"Success. The RTL latency of {config_path.stem} is "
            f"{rtl_cycles} cycles",
            file=sys.stderr,
        )
        actual_cycles = actual_cycles or rtl_cycles
        interval = interval or int(simulation["output_interval_cycles"])
        simulation_time = simulation_time or measured_time
        latency_source = "config+rtl" if latency_had_config else "rtl"

    period_ns = float(config.get("clock", {}).get("period_ns", 10.0))
    receivers = int(config["Number of Receiving Antennas"])
    actual_throughput = 1e6 / int(interval) / period_ns / receivers
    actual_complexity = float(actual_area) / GE_AREA_UM2 * int(actual_cycles)
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
        "throughput": {"actual": actual_throughput, "source": "derived"},
        "hardware_complexity": {
            "actual_ge_cycles": actual_complexity,
            "source": "derived",
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_cli("ls", predict, validate))
