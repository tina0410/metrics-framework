#!/usr/bin/env python3
"""Evaluate Polar BP decoder metrics from config.json."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in {
    "predict",
    "evaluate",
}:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))
    from metrics_framework.cli import main as framework_main

    raise SystemExit(framework_main(["bp", *sys.argv[1:]]))


from area_tp_integration import evaluate_bp_area
from bp_latency import (
    calculate_latency,
    cycle_terms,
    latency_error,
)
from hardware_complexity import GE_REFERENCE_CELL, area_to_ge, read_ge_area
from PredIter import predict_iter

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
DEFAULT_CONFIG = CONFIG_DIR / "config1.json"
DEFAULT_CONFIGS = tuple(CONFIG_DIR / f"config{i}.json" for i in range(1, 6))


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def generate_rtl(config_path: Path, output_dir: Path) -> None:
    from polar_decoder_integration import generate_bp_rtl

    output_dir.mkdir(parents=True, exist_ok=True)
    generate_bp_rtl(config_path, output_dir)


def simulate_rtl(
    config_path: Path,
    case_dir: Path,
    label: str | None = None,
) -> dict[str, object]:
    from polar_decoder_integration import simulate_bp_rtl

    return simulate_bp_rtl(config_path, case_dir, label=label)


def save_result(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "bp_metrics.json").open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


def configured_actual_area(config: dict[str, Any]) -> float | None:
    """Return a validated config actual-area override, or ``None`` for workbook mode."""
    reference = config.get("area")
    if reference is None:
        reference = config.get("area_reference", {})
    if not isinstance(reference, dict):
        raise TypeError("Configuration error: area must be a JSON object.")

    use_config_value = reference.get("use_config_actual_area", False)
    if not isinstance(use_config_value, bool):
        raise TypeError(
            "Configuration error: area.use_config_actual_area must be true or false."
        )
    if not use_config_value:
        return None

    configured_area = reference.get("actual_area_um2")
    error_message = (
        "Configuration error: area.actual_area_um2 must be greater than 0 "
        "when area.use_config_actual_area=true.\n"
        "Hint: set area.actual_area_um2 to a positive value in μm², or set "
        "area.use_config_actual_area=false to read the actual area from area.xlsx."
    )
    try:
        actual_area = float(configured_area)
    except (TypeError, ValueError) as error:
        raise ValueError(error_message) from error
    if actual_area <= 0:
        raise ValueError(error_message)
    return actual_area


def configured_synthesis_time_ms(config: dict[str, Any]) -> float | None:
    """Return an optional positive config synthesis time in milliseconds."""
    if configured_actual_area(config) is None:
        return None
    reference = config.get("area")
    if reference is None:
        reference = config.get("area_reference", {})
    configured_time = reference.get("synthesis_time_ms")
    if configured_time is None:
        return None
    error_message = (
        "Configuration error: area.synthesis_time_ms must be greater than 0 "
        "or null when area.use_config_actual_area=true."
    )
    try:
        synthesis_time_ms = float(configured_time)
    except (TypeError, ValueError) as error:
        raise ValueError(error_message) from error
    if synthesis_time_ms <= 0:
        raise ValueError(error_message)
    return synthesis_time_ms

def select_actual_area(
    area_result: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Apply a validated config actual-area override to an area result."""
    actual_area = configured_actual_area(config)
    if actual_area is None:
        return area_result

    selected = dict(area_result)
    predicted_area = float(selected["predicted_area_um2"])
    selected["actual_area_um2"] = actual_area
    selected["error_percent"] = abs(predicted_area - actual_area) / actual_area * 100.0
    selected["report"] = "config.area.actual_area_um2"
    return selected

def run_bp_evaluation(
    config_filename: str | Path = DEFAULT_CONFIG,
    *,
    clean_previous: bool = True,
) -> dict[str, Any]:
    """Read the named config file, evaluate BP metrics, and write bp_metrics.json."""
    config_path = Path(config_filename).resolve()
    config = load_config(config_path)
    if clean_previous:
        cleanup_previous_run([config_path])

    decoder = config["decoder"]
    flow = config.get("flow", {})
    architecture = decoder["hardware_architecture"]
    algorithm = decoder["decoding_algorithm"]
    n = int(decoder["code_length"])
    m = int(decoder["parallelism"])
    width = int(decoder["data_width"])
    rate = float(decoder.get("code_rate", 0.5))
    ebn0_db = float(decoder.get("ebn0_db", 10.0))
    period_ns = float(config["clock"]["period_ns"])
    prediction_started = time.perf_counter()
    average_iterations = predict_iter(ebn0_db, n, rate)
    terms = cycle_terms(n, m)
    latency = calculate_latency(average_iterations, terms)
    prediction_time_ms = (time.perf_counter() - prediction_started) * 1000.0
    throughput = round(n * rate) / (period_ns * latency)
    actual_area_override = configured_actual_area(config)
    synthesis_time_override_ms = configured_synthesis_time_ms(config)
    area = select_actual_area(
        evaluate_bp_area(
            architecture,
            algorithm,
            n,
            m,
            width,
            actual_area_um2=actual_area_override,
            synthesis_time_ms=synthesis_time_override_ms,
        ),
        config,
    )
    ge_area_um2 = read_ge_area()
    predicted_ge = area_to_ge(float(area["predicted_area_um2"]), ge_area_um2)
    actual_ge = area_to_ge(float(area["actual_area_um2"]), ge_area_um2)
    predicted_hardware_complexity = predicted_ge * latency

    result = {
        "延迟": {
            "预测结果 (cycles)": latency,
            "仿真结果 (cycles)": None,
            "误差 (%)": None,
            "预测时间 (ms)": round(prediction_time_ms, 6),
            "仿真时间 (ms)": None,
            "速度提升倍数 (×)": None,
        },
        "round前迭代次数 (iter)": {
            "模型原始输出 (iter)": round(average_iterations, 6),
            "C++仿真值 (iter)": None,
            "误差 (%)": None,
        },
        "面积": {
            "预测结果 (μm²)": round(float(area["predicted_area_um2"]), 2),
            "真实结果 (μm²)": round(float(area["actual_area_um2"]), 2),
            "误差 (%)": round(float(area["error_percent"]), 2),
            "预测时间 (ms)": round(float(area["prediction_time_ms"]), 6),
            "综合时间 (ms)": (
                round(float(area["synthesis_time_ms"]), 3)
                if area.get("synthesis_time_ms") is not None
                else None
            ),
            "速度提升倍数 (×)": (
                round(float(area["speedup"]), 2)
                if area.get("speedup") is not None
                else None
            ),
        },
        "Throughput": {
            "预测结果 (Gbps)": round(throughput, 2),
            "仿真结果 (Gbps)": None,
        },
        "硬件复杂度": {
            "预测结果 (GE·cycles)": round(predicted_hardware_complexity, 2),
            "仿真结果 (GE·cycles)": None,
            "误差 (%)": None,
            "GE基准单元": GE_REFERENCE_CELL,
            "1 GE面积 (μm²)": ge_area_um2,
        },
    }

    output_dir = configured_output_dir(config_path)
    simulation_dir = configured_simulation_dir(config_path)
    generate_enabled = bool(flow.get("generate_rtl", False))
    simulation_enabled = bool(flow.get("run_simulation", False))
    if generate_enabled or simulation_enabled:
        simulation_dir.mkdir(parents=True, exist_ok=True)
        (simulation_dir / "config_snapshot.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rtl_config = {
            "Hardware Architecture": architecture,
            "Decoding Algorithm": algorithm,
            "Code Length": n,
            "Parallelism": m,
            "Data Width": width,
            "Code Rate": rate,
            "Eb/N0 (dB)": ebn0_db,
            "Clock Period (ns)": period_ns,
        }
        rtl_config_path = simulation_dir / "rtl_config.json"
        rtl_config_path.write_text(json.dumps(rtl_config, indent=2), encoding="utf-8")
        if simulation_enabled:
            simulation = simulate_rtl(
                rtl_config_path,
                simulation_dir,
                config_path.stem,
            )
            cpp_iterations_value = simulation.get("cpp_iterations")
            if cpp_iterations_value is None:
                raise RuntimeError(
                    "C++ simulation did not provide cpp_iterations from "
                    "iter_frame_log.txt"
                )

            cpp_iterations = float(cpp_iterations_value)
            actual_latency = int(simulation["sim_latency_cycles"])
            simulation_time_ms = float(simulation["rtl_simulation_time_ms"])
            speedup = (
                simulation_time_ms / prediction_time_ms
                if prediction_time_ms > 0
                else None
            )
            latency_comparison = latency_error(latency, actual_latency)
            iteration_comparison = latency_error(
                average_iterations,
                cpp_iterations,
            )

            print(
                "Simulation Result: Success. The RTL latency of "
                f"{config_path.stem} is {actual_latency} cycles; "
                f"the C++ iteration count is {cpp_iterations:.6g} iter."
            )
            result["延迟"].update({
                "仿真结果 (cycles)": actual_latency,
                "误差 (%)": (
                    round(latency_comparison.percent, 2)
                    if latency_comparison.percent is not None
                    else None
                ),
                "仿真时间 (ms)": round(simulation_time_ms, 3),
                "速度提升倍数 (×)": (
                    round(speedup, 2) if speedup is not None else None
                ),
            })
            result["round前迭代次数 (iter)"].update({
                "C++仿真值 (iter)": round(cpp_iterations, 6),
                "误差 (%)": (
                    round(iteration_comparison.percent, 2)
                    if iteration_comparison.percent is not None
                    else None
                ),
            })

            actual_hardware_complexity = actual_ge * actual_latency
            complexity_error = (
                abs(predicted_hardware_complexity - actual_hardware_complexity)
                / actual_hardware_complexity
                * 100.0
                if actual_hardware_complexity
                else None
            )
            result["硬件复杂度"].update({
                "仿真结果 (GE·cycles)": round(actual_hardware_complexity, 2),
                "误差 (%)": (
                    round(complexity_error, 2) if complexity_error is not None else None
                ),
            })
            result["Throughput"]["仿真结果 (Gbps)"] = round(
                round(n * rate) / (period_ns * actual_latency), 2
            )
        elif generate_enabled:
            workspace = simulation_dir / "workspace"
            if workspace.exists():
                shutil.rmtree(workspace)
            generate_rtl(rtl_config_path, workspace / "RTL")

    save_result(result, output_dir)
    return result


def evaluate_bp(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Backward-compatible alias for :func:`run_bp_evaluation`."""
    return run_bp_evaluation(config_path)


def configured_output_dir(config_path: Path) -> Path:
    config_path = config_path.resolve()
    if config_path.is_relative_to(ROOT.resolve()):
        return ROOT / "evaluation_output" / config_path.stem
    config = load_config(config_path)
    relative = config.get("flow", {}).get("output_dir", "evaluation_output")
    return (config_path.parent / relative).resolve()


def configured_simulation_dir(config_path: Path) -> Path:
    """Return the persistent per-config simulation artifact directory."""
    config_path = config_path.resolve()
    if config_path.is_relative_to(ROOT.resolve()):
        return ROOT / "sim" / config_path.stem
    return configured_output_dir(config_path) / "sim"


def cleanup_previous_run(config_paths: list[Path]) -> None:
    """Remove only selected final metrics; never delete persistent case roots."""
    paths = [path.resolve() for path in config_paths]
    use_project_root = all(path.is_relative_to(ROOT.resolve()) for path in paths)
    for target in [configured_output_dir(path) for path in paths]:
        artifact = target / "bp_metrics.json"
        if artifact.exists():
            artifact.unlink()
    for table_name in ("latency.csv", "latency.xlsx"):
        table = ROOT / table_name if use_project_root else paths[0].parent / table_name
        if table.exists():
            table.unlink()




def resolve_config_selection(config: str | Path | None = None) -> list[Path]:
    """Return five defaults, or one config selected by path/positive number."""
    if config is None:
        paths = list(DEFAULT_CONFIGS)
    else:
        value = str(config)
        if value.isdecimal() and int(value) > 0:
            paths = [CONFIG_DIR / f"config{int(value)}.json"]
        else:
            paths = [Path(config)]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Config file not found: " + ", ".join(map(str, missing)))
    return [path.resolve() for path in paths]


def run_bp_evaluations(config: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Run selected configs and return their categorized metrics."""
    paths = resolve_config_selection(config)
    cleanup_previous_run(paths)
    results = {
        config_path.stem: run_bp_evaluation(
            config_path, clean_previous=False
        )
        for config_path in paths
    }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all config/config1.json..config5.json, or one selected config."
    )
    parser.add_argument(
        "config",
        nargs="?",
        help=(
            "Config path, or any positive config number N for config/configN.json. "
            "Omit to run the five default configs."
        ),
    )
    args = parser.parse_args()
    print(json.dumps(run_bp_evaluations(args.config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


