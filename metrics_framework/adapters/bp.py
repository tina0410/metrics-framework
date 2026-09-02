from __future__ import annotations

import contextlib
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = PROJECT_ROOT / "BPPredIter" / "BP_Evaluation"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MODULE_ROOT))

from metrics_framework.adapters.common import (  # noqa: E402
    configured_area,
    configured_latency,
    run_cli,
)


def _modules():
    import area_tp_integration
    import evaluate_bp
    from bp_latency import calculate_latency, cycle_terms, iterations_from_latency
    from hardware_complexity import GE_REFERENCE_CELL, area_to_ge, read_ge_area
    from PredIter import predict_iter

    return (
        area_tp_integration,
        evaluate_bp,
        calculate_latency,
        cycle_terms,
        iterations_from_latency,
        GE_REFERENCE_CELL,
        area_to_ge,
        read_ge_area,
        predict_iter,
    )


def _parameters(config: dict[str, Any]) -> tuple[str, str, int, int, int, float, float, float]:
    decoder = config["decoder"]
    return (
        str(decoder["hardware_architecture"]),
        str(decoder["decoding_algorithm"]),
        int(decoder["code_length"]),
        int(decoder["parallelism"]),
        int(decoder["data_width"]),
        float(decoder.get("code_rate", 0.5)),
        float(decoder.get("ebn0_db", 10.0)),
        float(config["clock"]["period_ns"]),
    )


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    area_integration, _evaluator, calculate_latency, cycle_terms, _iterations_from_latency, ge_cell, area_to_ge, read_ge_area, predict_iter = _modules()
    architecture, algorithm, n, m, width, rate, ebn0_db, period_ns = _parameters(config)
    started = time.perf_counter()
    iterations = predict_iter(ebn0_db, n, rate)
    latency = calculate_latency(iterations, cycle_terms(n, m))
    latency_time_ms = (time.perf_counter() - started) * 1000.0
    area_module = area_integration._load_area_module()
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        predicted_area = float(
            area_module.Esttop(
                archi=architecture, algo=algorithm, N=n, M=m, width=width
            )
        )
    area_time_ms = (time.perf_counter() - started) * 1000.0
    throughput = round(n * rate) / (period_ns * latency)
    ge_area = read_ge_area()
    complexity = area_to_ge(predicted_area, ge_area) * latency
    return {
        "latency": {
            "predicted_cycles": latency,
            "prediction_time_ms": latency_time_ms,
            "source": "formula",
        },
        "iterations": {"predicted": iterations, "source": "model"},
        "area": {
            "predicted_um2": predicted_area,
            "prediction_time_ms": area_time_ms,
            "source": "model",
        },
        "throughput": {
            "predicted": throughput,
            "unit": "Gbps",
            "precision": 2,
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
    area_integration, evaluator, _calculate_latency, cycle_terms, iterations_from_latency, _ge_cell, area_to_ge, read_ge_area, _predict_iter = _modules()
    architecture, algorithm, n, m, width, rate, _ebn0_db, period_ns = _parameters(config)
    actual_area, synthesis_time, area_speedup = configured_area(config)
    area_had_config = any(
        value is not None for value in (actual_area, synthesis_time, area_speedup)
    )
    area_source = "config"
    if actual_area is None or (synthesis_time is None and area_speedup is None):
        reference = area_integration._load_area_module().read_area(
            architecture, algorithm, n, m, width
        )
        actual_area = actual_area or float(reference["actual_area_um2"])
        synthesis_time = synthesis_time or float(reference["synthesis_time_ms"])
        area_source = "config+dc_reference" if area_had_config else "dc_reference"

    actual_cycles, simulation_time, _interval, latency_speedup = configured_latency(config)
    latency_had_config = actual_cycles is not None or simulation_time is not None
    latency_source = "config"
    actual_iterations: float | None = None
    if actual_cycles is None or (simulation_time is None and latency_speedup is None):
        output_dir = evaluator.configured_output_dir(config_path)
        simulation_dir = output_dir / "simulation"
        simulation_dir.mkdir(parents=True, exist_ok=True)
        rtl_config = {
            "Hardware Architecture": architecture,
            "Decoding Algorithm": algorithm,
            "Code Length": n,
            "Parallelism": m,
            "Data Width": width,
            "Code Rate": rate,
            "Eb/N0 (dB)": float(config["decoder"].get("ebn0_db", 10.0)),
            "Clock Period (ns)": period_ns,
        }
        rtl_config_path = output_dir / "rtl_config.json"
        rtl_config_path.write_text(json.dumps(rtl_config, indent=2), encoding="utf-8")
        simulation = evaluator.simulate_rtl(
            rtl_config_path, simulation_dir, label=config_path.stem
        )
        if simulation.get("waveform_verified") is False or simulation.get("decoding_verified") is False:
            raise RuntimeError("BP RTL functional comparison failed")
        actual_cycles = actual_cycles or int(simulation["sim_latency_cycles"])
        simulation_time = simulation_time or float(simulation["rtl_simulation_time_ms"])
        if simulation.get("cpp_iterations") is not None:
            actual_iterations = float(simulation["cpp_iterations"])
        latency_source = "config+rtl" if latency_had_config else "rtl"
    if actual_iterations is None:
        actual_iterations = iterations_from_latency(actual_cycles, cycle_terms(n, m))

    throughput = round(n * rate) / (period_ns * int(actual_cycles))
    ge_area = read_ge_area()
    complexity = area_to_ge(float(actual_area), ge_area) * int(actual_cycles)
    return {
        "latency": {
            "actual_cycles": actual_cycles,
            "simulation_time_ms": simulation_time,
            "output_interval_cycles": None,
            "reported_speedup": latency_speedup,
            "source": latency_source,
        },
        "iterations": {"actual": actual_iterations, "source": latency_source},
        "area": {
            "actual_um2": actual_area,
            "synthesis_time_ms": synthesis_time,
            "reported_speedup": area_speedup,
            "source": area_source,
        },
        "throughput": {"actual": throughput, "source": "derived"},
        "hardware_complexity": {
            "actual_ge_cycles": complexity,
            "source": "derived",
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_cli("bp", predict, validate))
