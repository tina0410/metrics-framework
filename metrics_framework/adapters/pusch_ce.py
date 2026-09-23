"""Unified PUSCH CE prediction and fresh RTL-validation adapter."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from metrics_framework.adapters.common import configured_area, run_cli


MODULE_NAME = "pusch_ce"
REQUIRED_SECTIONS = (
    "protocol",
    "architecture",
    "quantization",
    "arithmetic",
    "implementation",
    "area",
)


def validate_scaffold_config(config: Mapping[str, Any]) -> None:
    """Validate fields shared by every future PUSCH_CE metric implementation."""

    missing = [name for name in REQUIRED_SECTIONS if not isinstance(config.get(name), dict)]
    if missing:
        raise ValueError("missing object sections: " + ", ".join(missing))

    area = config["area"]
    for key in ("use_config_actual_area", "use_config_actual_time"):
        if key in area and not isinstance(area[key], bool):
            raise ValueError(f"area.{key} must be boolean")


def _area(action: str, config_path: Path) -> dict[str, Any]:
    """Run the legacy estimator in isolation, matching the MIMO adapter."""

    interface = (
        Path(__file__).resolve().parents[2]
        / "Area_TP_Estimator"
        / "PUSCH_Est_pack"
        / "pusch_ce_area_interface.py"
    )
    process = subprocess.run(
        [sys.executable, str(interface), action, str(config_path)],
        cwd=interface.parent,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip())
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("PUSCH_CE area interface returned invalid JSON") from error
    if not isinstance(result, dict):
        raise RuntimeError("PUSCH_CE area interface returned a non-object")
    return result


def _modules():
    module_root = Path(__file__).resolve().parents[2] / "Generator" / "PUSCH_CE"
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))
    from hardware_complexity_interface import (
        GE_REFERENCE_CELL,
        evaluate_hardware_complexity,
    )
    from latency_interface import load_case_config, predict_latency
    from throughput_interface import predict_throughput

    return (
        GE_REFERENCE_CELL,
        evaluate_hardware_complexity,
        load_case_config,
        predict_latency,
        predict_throughput,
    )


def _rtl(config_path: Path) -> dict[str, Any]:
    script = (
        Path(__file__).resolve().parents[2]
        / "Generator"
        / "PUSCH_CE"
        / "tests"
        / "validate_pusch_ce_latency.py"
    )
    process = subprocess.run(
        [sys.executable, str(script), str(config_path)],
        cwd=script.parent,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stderr:
        print(process.stderr, end="" if process.stderr.endswith("\n") else "\n", file=sys.stderr)
    if process.returncode != 0:
        raise RuntimeError(process.stdout.strip() or "PUSCH_CE RTL validation failed")
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("PUSCH_CE RTL validator returned invalid JSON") from error
    if not isinstance(result, dict):
        raise RuntimeError("PUSCH_CE RTL validator returned a non-object")
    return result


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    validate_scaffold_config(config)
    ge_cell, complexity_evaluator, load_case, latency_predictor, throughput_predictor = _modules()
    runtime_config = load_case(config_path)

    latency = latency_predictor(runtime_config)
    area = _area("predict", config_path)
    throughput = throughput_predictor(
        runtime_config, latency_prediction=latency
    )

    started = time.perf_counter()
    complexity = complexity_evaluator(
        float(area["predicted_area_um2"]), int(latency["predicted_cycles"])
    )
    complexity_time_ms = (time.perf_counter() - started) * 1000.0
    return {
        "latency": {
            "predicted_cycles": int(latency["predicted_cycles"]),
            "prediction_time_ms": float(latency["prediction_time_ms"]),
            "source": "formula",
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
            "prediction_time_ms": float(throughput["prediction_time_ms"]),
            "source": "formula",
        },
        "hardware_complexity": {
            "predicted_ge_cycles": float(complexity["predicted_ge_cycles"]),
            "prediction_time_ms": complexity_time_ms,
            "ge_reference_cell": ge_cell,
            "ge_area_um2": float(complexity["ge_area_um2"]),
            "source": "derived",
        },
    }


def validate(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    validate_scaffold_config(config)
    _ge_cell, complexity_evaluator, _load_case, _latency_predictor, _throughput_predictor = _modules()

    configured_actual, synthesis_time, area_speedup = configured_area(config)
    area_source = "config"
    if configured_actual is None:
        reference = _area("validate", config_path)
        configured_actual = float(reference["actual_area_um2"])
        area_source = str(reference.get("actual_value_kind", "dc_reference"))

    simulation = _rtl(config_path)
    latency = simulation.get("latency", {})
    throughput = simulation.get("throughput", {})
    actual_cycles = int(latency["actual_cycles"])
    actual_gbps = float(throughput["actual_gbps"])
    simulation_time_ms = float(
        latency.get("simulation_time_ms")
        or simulation.get("rtl", {}).get("simulation_time_ms")
    )
    complexity = complexity_evaluator(
        float(configured_actual),
        actual_cycles,
        actual_area_um2=float(configured_actual),
        actual_latency_cycles=actual_cycles,
    )
    return {
        "latency": {
            "actual_cycles": actual_cycles,
            "simulation_time_ms": simulation_time_ms,
            "output_interval_cycles": int(
                simulation.get("rtl", {}).get("throughput_interval_cycles")
                or throughput["actual_interval_cycles"]
            ),
            "source": "rtl",
        },
        "area": {
            "actual_um2": float(configured_actual),
            "synthesis_time_ms": synthesis_time,
            "reported_speedup": area_speedup,
            "synthesis_time_available": (
                synthesis_time is not None or area_speedup is not None
            ),
            "source": area_source,
        },
        "throughput": {
            "actual": actual_gbps,
            "source": "rtl_measured",
        },
        "hardware_complexity": {
            "actual_ge_cycles": float(complexity["actual_ge_cycles"]),
            "source": "derived",
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE_NAME, predict, validate))
