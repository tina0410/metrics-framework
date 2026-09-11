#!/usr/bin/env python3
"""Unified MIMO metric-evaluation entry point (latency phase)."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from hardware_complexity_interface import (
    GE_REFERENCE_CELL,
    evaluate_hardware_complexity,
    read_ge_area,
)
from latency_interface import evaluate_latency, predict_latency
from throughput_interface import (
    evaluate_throughput,
    predicted_output_interval_cycles,
    throughput_gbps,
    valid_bits_per_output,
)


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
CONFIG_DIR = ROOT / "configs"
DEFAULT_CONFIG = CONFIG_DIR / "config_case5.json"
DEFAULT_CONFIGS = tuple(CONFIG_DIR / f"config_case{i}.json" for i in range(1, 6))
AREA_ROOT = PROJECT_ROOT / "Area_TP_Estimator" / "Est_INSA_MMSE"
AREA_INTERFACE = AREA_ROOT / "mimo_area_interface.py"
GE_AREA_UM2 = read_ge_area()


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as stream:
        config = json.load(stream)
    for key in (
        "Number of Transmit Antennas",
        "Number of Receiving Antennas",
        "Iterations",
        "Adder Tree Pipelines",
    ):
        if key not in config:
            raise ValueError(f"{path}: missing required MIMO parameter {key!r}")
        if int(config[key]) <= 0:
            raise ValueError(f"{path}: {key!r} must be greater than zero")
    iterations = int(config["Iterations"])
    if iterations > 3:
        raise ValueError(
            f"{path}: Iterations={iterations} is unsupported; the original "
            "lNSA/test_PE generator currently provides x1 through x4 only"
        )
    period_ns = float(config.get("clock", {}).get("period_ns", 10.0))
    if not math.isfinite(period_ns) or period_ns <= 0:
        raise ValueError(f"{path}: clock.period_ns must be a finite value greater than zero")
    if "QAM Order" in config:
        qam_order = int(config["QAM Order"])
        if qam_order < 2 or qam_order & (qam_order - 1):
            raise ValueError(f"{path}: 'QAM Order' must be a power of two not less than 2")
    area = config.get("area", {})
    if not isinstance(area, dict):
        raise ValueError(f"{path}: area must be an object")
    for switch in ("use_config_actual_area", "use_config_actual_time"):
        if switch in area and not isinstance(area[switch], bool):
            raise ValueError(f"{path}: area.{switch} must be boolean")
    return config


def configured_output_dir(config_path: Path, config: dict[str, Any]) -> Path:
    if config_path.is_relative_to(ROOT.resolve()):
        return ROOT / "evaluation_output" / config_path.stem
    relative = config.get("flow", {}).get("output_dir", "evaluation_output")
    return (config_path.parent / relative).resolve()


def _case_id(config_path: Path) -> int:
    prefix = "config_case"
    if not config_path.stem.startswith(prefix):
        raise ValueError("RTL simulation requires a config_caseN.json file")
    match = re.match(r"(\d+)", config_path.stem[len(prefix) :])
    if not match:
        raise ValueError("RTL simulation requires a config_caseN.json file")
    return int(match.group(1))


def simulate_rtl(config_path: Path) -> dict[str, Any]:
    case_id = _case_id(config_path)
    script = ROOT / "BehaviorialVerification" / "validate_mimo_timing.py"
    result_path = (
        ROOT
        / "BehaviorialVerification"
        / "sim"
        / f"Testcase{case_id}"
        / "simulation_result.json"
    )
    result_path.unlink(missing_ok=True)
    process = subprocess.run(
        [sys.executable, str(script), "--case", str(case_id), "--config", str(config_path)],
        cwd=script.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stdout)
    if not result_path.exists():
        raise FileNotFoundError(f"MIMO RTL timing result was not generated: {result_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    return result


def evaluate_area(config_path: Path) -> dict[str, Any]:
    """Run the INSA area estimator in an isolated Python process.

    The legacy estimator uses top-level module names that overlap with the MIMO
    RTL generator.  Process isolation prevents either project from resolving the
    other's ``PyTU``/``lNSA`` modules through ``sys.modules`` or ``sys.path``.
    """
    if not AREA_INTERFACE.is_file():
        raise FileNotFoundError(f"MIMO area interface not found: {AREA_INTERFACE}")
    process = subprocess.run(
        [sys.executable, str(AREA_INTERFACE), str(config_path)],
        cwd=AREA_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        details = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"MIMO area evaluation failed:\n{details}")
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "MIMO area interface returned invalid JSON:\n" + process.stdout
        ) from error
    required = (
        "predicted_area_um2",
        "actual_area_um2",
        "error_percent",
        "prediction_time_ms",
        "synthesis_time_ms",
        "speedup",
    )
    missing = [key for key in required if key not in result]
    if missing:
        raise RuntimeError("MIMO area result missing fields: " + ", ".join(missing))
    return result


def cleanup_previous_run(config_paths: list[Path]) -> None:
    """Reset only generated workspaces/results for selected cases."""
    for config_path in config_paths:
        try:
            case_id = _case_id(config_path)
        except ValueError:
            case_id = None
        if case_id is not None:
            workspace = (
                ROOT
                / "BehaviorialVerification"
                / "sim"
                / f"Testcase{case_id}"
                / "workspace"
            )
            if workspace.exists():
                shutil.rmtree(workspace)
        config = load_config(config_path)
        result = configured_output_dir(config_path, config) / "mimo_metrics.json"
        if result.exists():
            result.unlink()

def save_result(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "mimo_metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_mimo_evaluation(
    config_filename: str | Path = DEFAULT_CONFIG,
    *,
    clean_previous: bool = True,
) -> dict[str, Any]:
    """Evaluate one MIMO configuration."""
    config_path = Path(config_filename).resolve()
    config = load_config(config_path)
    if clean_previous:
        cleanup_previous_run([config_path])

    started = time.perf_counter()
    latency = evaluate_latency(config)
    predicted_latency = latency["predicted_cycles"]
    prediction_time_ms = (time.perf_counter() - started) * 1000.0
    throughput = evaluate_throughput(config)
    area = evaluate_area(config_path)
    predicted_area = float(area["predicted_area_um2"])
    actual_area = float(area["actual_area_um2"])
    complexity = evaluate_hardware_complexity(predicted_area, predicted_latency)
    result: dict[str, Any] = {
        "\u5ef6\u8fdf": {
            "\u9884\u6d4b\u7ed3\u679c (cycles)": predicted_latency,
            "\u4eff\u771f\u7ed3\u679c (cycles)": None,
            "\u8bef\u5dee (%)": None,
            "\u9884\u6d4b\u65f6\u95f4 (ms)": round(prediction_time_ms, 6),
            "\u4eff\u771f\u65f6\u95f4 (ms)": None,
            "\u901f\u5ea6\u63d0\u5347\u500d\u6570 (\u00d7)": None,
        },
        "\u9762\u79ef": {
            "\u9884\u6d4b\u7ed3\u679c (\u03bcm\u00b2)": round(predicted_area, 2),
            "\u771f\u5b9e\u7ed3\u679c (\u03bcm\u00b2)": round(actual_area, 2),
            "\u8bef\u5dee (%)": round(float(area["error_percent"]), 2),
            "\u9884\u6d4b\u65f6\u95f4 (ms)": round(
                float(area["prediction_time_ms"]), 6
            ),
            "\u7efc\u5408\u65f6\u95f4 (ms)": round(
                float(area["synthesis_time_ms"]), 3
            ),
            "\u901f\u5ea6\u63d0\u5347\u500d\u6570 (\u00d7)": round(
                float(area["speedup"]), 2
            ),
        },
        "Throughput": {
            "\u9884\u6d4b\u7ed3\u679c (Gbps)": (
                round(throughput["predicted_gbps"], 9)
                if throughput["predicted_gbps"] is not None
                else None
            ),
            "\u4eff\u771f\u7ed3\u679c (Gbps)": None,
        },
        "\u786c\u4ef6\u590d\u6742\u5ea6": {
            "\u9884\u6d4b\u7ed3\u679c (GE\u00b7cycles)": round(
                complexity["predicted_ge_cycles"], 2
            ),
            "\u771f\u5b9e\u7ed3\u679c (GE\u00b7cycles)": None,
            "\u8bef\u5dee (%)": None,
            "GE\u57fa\u51c6\u5355\u5143": complexity["ge_reference_cell"],
            "1 GE\u9762\u79ef (\u03bcm\u00b2)": complexity["ge_area_um2"],
        },
    }

    if bool(config.get("flow", {}).get("run_simulation", False)):
        sim_started = time.perf_counter()
        simulation = simulate_rtl(config_path)
        simulation_time_ms = (time.perf_counter() - sim_started) * 1000.0
        simulated_latency = int(simulation["sim_latency_cycles"])
        latency = evaluate_latency(
            config,
            actual_latency_cycles=simulated_latency,
        )
        speedup = simulation_time_ms / prediction_time_ms if prediction_time_ms else None
        result["\u5ef6\u8fdf"].update(
            {
                "\u4eff\u771f\u7ed3\u679c (cycles)": simulated_latency,
                "\u8bef\u5dee (%)": round(latency["error_percent"], 2),
                "\u4eff\u771f\u65f6\u95f4 (ms)": round(simulation_time_ms, 3),
                "\u901f\u5ea6\u63d0\u5347\u500d\u6570 (\u00d7)": round(speedup, 2) if speedup else None,
            }
        )
        simulated_interval = simulation.get("sim_output_interval_cycles")
        throughput = evaluate_throughput(
            config,
            simulated_output_interval_cycles=simulated_interval,
        )
        result["Throughput"].update(
            {
                "\u4eff\u771f\u7ed3\u679c (Gbps)": (
                    round(throughput["simulated_gbps"], 9)
                    if throughput["simulated_gbps"] is not None
                    else None
                ),
            }
        )
        complexity = evaluate_hardware_complexity(
            predicted_area,
            predicted_latency,
            actual_area_um2=actual_area,
            actual_latency_cycles=simulated_latency,
        )
        result["\u786c\u4ef6\u590d\u6742\u5ea6"].update(
            {
                "\u771f\u5b9e\u7ed3\u679c (GE\u00b7cycles)": round(
                    complexity["actual_ge_cycles"], 2
                ),
                "\u8bef\u5dee (%)": round(complexity["error_percent"], 2),
            }
        )
        print(f"Success. The latency is {simulated_latency} cycles.")

    save_result(result, configured_output_dir(config_path, config))
    return result


def resolve_config_selection(config: str | Path | None = None) -> list[Path]:
    if config is None:
        paths = list(DEFAULT_CONFIGS)
    else:
        value = str(config)
        paths = (
            [CONFIG_DIR / f"config_case{value}.json"]
            if value.isdigit()
            else [Path(config)]
        )
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Config file not found: " + ", ".join(map(str, missing)))
    return [path.resolve() for path in paths]


def run_mimo_evaluations(
    config: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    paths = resolve_config_selection(config)
    cleanup_previous_run(paths)
    return {
        path.stem: run_mimo_evaluation(path, clean_previous=False) for path in paths
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] in {"predict", "evaluate"}:
        project_root_text = str(PROJECT_ROOT)
        sys.path.insert(0, project_root_text)
        try:
            from metrics_framework.cli import main as framework_main
        finally:
            sys.path.remove(project_root_text)
        raise SystemExit(framework_main(["mimo", *sys.argv[1:]]))
    parser = argparse.ArgumentParser(description="Evaluate all configured MIMO cases or one case")
    parser.add_argument("config", nargs="?", help="Config path or numeric case ID")
    args = parser.parse_args()
    try:
        results = run_mimo_evaluations(args.config)
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from None

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
