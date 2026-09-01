#!/usr/bin/env python3
"""Evaluate LS channel-estimator metrics with the same interface as BP."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import os
import re
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
CONFIG_DIR = ROOT / "configs"
DEFAULT_CONFIG = CONFIG_DIR / "config_case1.json"
DEFAULT_CONFIGS = tuple(CONFIG_DIR / f"config_case{i}.json" for i in range(1, 6))


def _configured_area_root() -> Path:
    """Resolve the optional model directory override without searching other trees."""
    override = os.environ.get("LSCE_AREA_ROOT")
    if override is not None:
        if not override.strip():
            raise ValueError("LSCE_AREA_ROOT must name the directory containing EstLS.py")
        return Path(override).expanduser().resolve()
    return PROJECT_ROOT / "Area_TP_Estimator" / "Est_LS_CE_M2V"


AREA_ROOT = _configured_area_root()
AREA_RESULTS = AREA_ROOT / "LSCE结果.xlsx"
GE_REFERENCE_CELL = "LVT_NAND2HDV0"
GE_AREA_UM2 = 1.12
AREA_COLUMN_ALIASES = ("dc综合面积", "dc×ÛºÏÃæ»ý", "Area (μm²)", "Area (um^2)")
SYNTHESIS_TIME_COLUMN_ALIASES = ("time", "综合时间", "Synthesis Time (s)")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        config = json.load(file)

    return validate_config(config, path)


def _integer(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not an integer parameter")
    result = int(value)
    if not isinstance(value, str) and value != result:
        raise ValueError("fractional value is not an integer parameter")
    return result


def validate_config(config: dict[str, Any], path: Path) -> dict[str, Any]:
    """Validate one loaded configuration before generating or cleaning files."""
    if not isinstance(config, dict):
        raise ValueError(f"{path}: configuration must be an object")
    positive_integer_fields = (
        "Number of Transmit Antennas",
        "Number of Receiving Antennas",
        "Parallelism T",
        "Parallelism R",
    )
    for key in positive_integer_fields:
        if key not in config:
            raise ValueError(f"{path}: missing required LSCE parameter {key!r}")
        try:
            value = _integer(config[key])
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"{path}: {key!r} must be an integer") from None
        if value <= 0:
            raise ValueError(f"{path}: {key!r} must be greater than zero")

    n_t = int(config["Number of Transmit Antennas"])
    n_r = int(config["Number of Receiving Antennas"])
    p_t = int(config["Parallelism T"])
    p_r = int(config["Parallelism R"])
    if p_t > n_t or n_t % p_t != 0:
        raise ValueError(
            f"{path}: Parallelism T={p_t} must divide "
            f"Number of Transmit Antennas={n_t}"
        )
    if p_r > n_r or n_r % p_r != 0:
        raise ValueError(
            f"{path}: Parallelism R={p_r} must divide "
            f"Number of Receiving Antennas={n_r}"
        )

    pipeline_key = "Pipeline Stages ([Multiplication, Adder Tree])"
    pipelines = config.get(pipeline_key)
    if not isinstance(pipelines, list) or len(pipelines) != 2:
        raise ValueError(f"{path}: {pipeline_key!r} must contain exactly two integers")
    try:
        parsed_pipelines = [_integer(value) for value in pipelines]
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{path}: {pipeline_key!r} must contain exactly two integers") from None
    if any(value < 0 for value in parsed_pipelines):
        raise ValueError(f"{path}: pipeline stages must be non-negative")

    for key in (
        "Quantization format of Y",
        "Quantization format of P",
        "Quantization format of H",
        "Quantization format of M_V",
    ):
        value = config.get(key)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: missing required LSCE parameter {key!r}")
        try:
            bitwidth = _integer(value["bitwidth"])
            fractional_width = _integer(value["fractional width"])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError(
                f"{path}: {key!r} requires integer bitwidth and fractional width"
            ) from None
        if bitwidth <= 0 or not 0 <= fractional_width <= bitwidth:
            raise ValueError(
                f"{path}: {key!r} requires bitwidth > 0 and "
                "0 <= fractional width <= bitwidth"
            )
        if not isinstance(value.get("signed"), bool):
            raise ValueError(f"{path}: {key!r}.signed must be boolean")

    clock = config.get("clock", {})
    if not isinstance(clock, dict):
        raise ValueError(f"{path}: clock must be an object")
    try:
        period_ns = float(clock.get("period_ns", 10.0))
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{path}: clock.period_ns must be finite and positive") from None
    if isinstance(clock.get("period_ns"), bool) or not math.isfinite(period_ns) or period_ns <= 0:
        raise ValueError(f"{path}: clock.period_ns must be greater than zero")

    flow = config.get("flow", {})
    if not isinstance(flow, dict):
        raise ValueError(f"{path}: flow must be an object")
    if "run_simulation" in flow and not isinstance(flow["run_simulation"], bool):
        raise ValueError(f"{path}: flow.run_simulation must be boolean")

    area = config.get("area", {})
    if not isinstance(area, dict):
        raise ValueError(f"{path}: area must be an object")
    if "use_config_actual_area" in area and not isinstance(
        area["use_config_actual_area"], bool
    ):
        raise ValueError(f"{path}: area.use_config_actual_area must be boolean")
    if "use_config_actual_time" in area and not isinstance(
        area["use_config_actual_time"], bool
    ):
        raise ValueError(f"{path}: area.use_config_actual_time must be boolean")
    from BehaviorialVerification.lsce_binding import QUANTIZATION_MODES, OVERFLOW_MODES
    if config.get("Quantization Mode", "TRN.TCPL") not in QUANTIZATION_MODES:
        raise ValueError(f"{path}: unsupported Quantization Mode")
    if config.get("Overflow Mode", "WRP.TCPL") not in OVERFLOW_MODES:
        raise ValueError(f"{path}: unsupported Overflow Mode")
    if flow.get("run_simulation", False):
        _case_id(path)
        if p_r != n_r:
            raise ValueError(f"{path}: complete RTL simulation requires P_R == N_R")
    return config


def _quantization_key(value: dict[str, Any]) -> str:
    return f"{int(value['bitwidth'])}\\{int(value['fractional width'])}"


def _area_key(config: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(config["Parallelism T"]),
        int(config["Number of Transmit Antennas"]),
        int(config["Parallelism R"]),
        _quantization_key(config["Quantization format of Y"]),
        _quantization_key(config["Quantization format of P"]),
        _quantization_key(config["Quantization format of H"]),
        _quantization_key(config["Quantization format of M_V"]),
        [int(x) for x in config["Pipeline Stages ([Multiplication, Adder Tree])"]],
    )


def select_actual_area(
    config: dict[str, Any], workbook_actual_area_um2: float | None = None
) -> float:
    """Select actual area from config when enabled, otherwise use workbook data."""
    area_config = config.get("area", {})
    use_config_value = bool(area_config.get("use_config_actual_area", False))
    if use_config_value:
        try:
            actual = float(area_config["actual_area_um2"])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError(
                "Configuration error: area.actual_area_um2 must be greater than 0 "
                "when area.use_config_actual_area=true."
            ) from None
    else:
        if workbook_actual_area_um2 is None:
            raise ValueError(
                "Workbook actual area is required when the config value is disabled."
            )
        actual = float(workbook_actual_area_um2)
    if not math.isfinite(actual) or actual <= 0:
        if use_config_value:
            raise ValueError(
                "Configuration error: area.actual_area_um2 must be greater than 0 "
                "when area.use_config_actual_area=true."
            )
        raise ValueError(f"Workbook actual area must be greater than 0; got {actual}.")
    return actual


def select_actual_time(
    config: dict[str, Any], workbook_actual_time_ms: float | None = None
) -> float:
    """Select actual synthesis time from config when enabled, otherwise workbook."""
    area_config = config.get("area", {})
    use_config_value = bool(area_config.get("use_config_actual_time", False))
    if use_config_value:
        try:
            actual = float(area_config["actual_time_ms"])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError(
                "Configuration error: area.actual_time_ms must be greater than 0 "
                "when area.use_config_actual_time=true."
            ) from None
    else:
        if workbook_actual_time_ms is None:
            raise ValueError(
                "Workbook actual synthesis time is required when the config value "
                "is disabled."
            )
        actual = float(workbook_actual_time_ms)
    if not math.isfinite(actual) or actual <= 0:
        if use_config_value:
            raise ValueError(
                "Configuration error: area.actual_time_ms must be greater than 0 "
                "when area.use_config_actual_time=true."
            )
        raise ValueError(
            f"Workbook actual synthesis time must be greater than 0; got {actual}."
        )
    return actual


@lru_cache(maxsize=1)
def _load_area_evaluator() -> tuple[Any, Any, Any, Any, Any]:
    """Load the existing LSCE estimator and its models once per process."""
    required = (
        "EstLS.py", "EstModule.py", "KeyParam.py", "PyTU.py",
        "model/SU_in.xlsx", "model/ADD_area.pkl",
        "model/pure_MUL_area.pkl", "model/SU_out_FxP_area.pkl",
    )
    missing = [name for name in required if not (AREA_ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"LSCE area model directory is incomplete: {AREA_ROOT}\n"
            f"Missing: {', '.join(missing)}\n"
            "The area estimator is a separate repository, not a pip package. "
            "Set LSCE_AREA_ROOT to the existing Est_LS_CE_M2V directory "
            "before starting Python. Keep its model files and LSCE结果.xlsx "
            "from the original area/synthesis data source."
        )
    import joblib
    import pandas as pd
    area_root_text = str(AREA_ROOT)
    sys.path.insert(0, area_root_text)
    try:
        from EstLS import EstLSCE_GUI
    finally:
        sys.path.remove(area_root_text)

    model_root = AREA_ROOT / "model"
    su_in = pd.read_excel(model_root / "SU_in.xlsx", sheet_name="SU_in")
    model_add = joblib.load(model_root / "ADD_area.pkl")
    model_mul = joblib.load(model_root / "pure_MUL_area.pkl")
    model_su_out = joblib.load(model_root / "SU_out_FxP_area.pkl")
    return EstLSCE_GUI, model_add, model_mul, model_su_out, su_in


def evaluate_predicted_area(config_path: Path) -> dict[str, float]:
    """Call the existing LSCE area estimator and measure its real execution time."""
    evaluator, model_add, model_mul, model_su_out, su_in = _load_area_evaluator()
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        evaluated = evaluator(
            model_add,
            model_mul,
            model_su_out,
            su_in,
            ConfigFileName=str(config_path),
        )
    prediction_time_ms = (time.perf_counter() - started) * 1000.0
    if evaluated is None:
        raise RuntimeError("LSCE area estimator returned no result.")
    predicted = float(evaluated[0])
    if not math.isfinite(predicted) or predicted <= 0:
        raise ValueError(f"LSCE area estimator returned an invalid area: {predicted}.")
    return {
        "predicted_area_um2": predicted,
        "prediction_time_ms": prediction_time_ms,
    }


def _resolve_column(columns: list[str], aliases: tuple[str, ...], label: str) -> str:
    match = next((alias for alias in aliases if alias in columns), None)
    if match is None:
        raise KeyError(
            f"{AREA_RESULTS.name} missing {label}; accepted names: {', '.join(aliases)}"
        )
    return match


def read_workbook_area_reference(config: dict[str, Any]) -> dict[str, float]:
    """Read the uniquely matched DC synthesis area and time from the workbook."""
    import pandas as pd
    workbook = pd.ExcelFile(AREA_RESULTS)
    sheet_name = (
        "LSCE"
        if "LSCE" in workbook.sheet_names
        else "LS"
        if "LS" in workbook.sheet_names
        else workbook.sheet_names[0]
    )
    table = pd.read_excel(workbook, sheet_name=sheet_name)
    table.columns = [str(column).strip() for column in table.columns]
    area_column = _resolve_column(
        list(table.columns), AREA_COLUMN_ALIASES, "actual area"
    )
    time_column = _resolve_column(
        list(table.columns), SYNTHESIS_TIME_COLUMN_ALIASES, "synthesis time"
    )
    wanted = _area_key(config)
    matches = []
    for _, row in table.iterrows():
        try:
            pipelines = json.loads(str(row["n_pipelines"]))
            candidate = (
                int(row["P_T"]), int(row["N_T"]), int(row["P_R"]),
                str(row["QU_Y"]), str(row["QU_P"]), str(row["QU_H"]),
                str(row["QU_M_V"]), [int(x) for x in pipelines],
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if candidate == wanted:
            matches.append(row)
    if len(matches) != 1:
        raise LookupError(
            f"Expected one LSCE area/time row for {_area_key(config)}, "
            f"found {len(matches)}"
        )
    row = matches[0]
    return {
        "actual_area_um2": select_actual_area({}, float(row[area_column])),
        "synthesis_time_ms": select_actual_time(
            {}, float(row[time_column]) * 1000.0
        ),
    }


def read_workbook_actual_area(config: dict[str, Any]) -> float:
    """Compatibility wrapper returning only the matched DC synthesis area."""
    reference = read_workbook_area_reference(config)
    return select_actual_area(config, reference["actual_area_um2"])


def evaluate_lsce_area(config_path: Path, config: dict[str, Any]) -> dict[str, float]:
    """Evaluate area and resolve configured/workbook actual area and time."""
    prediction = evaluate_predicted_area(config_path)
    use_config_actual_area = bool(
        config.get("area", {}).get("use_config_actual_area", False)
    )
    use_config_actual_time = bool(
        config.get("area", {}).get("use_config_actual_time", False)
    )
    reference = (
        {}
        if use_config_actual_area and use_config_actual_time
        else read_workbook_area_reference(config)
    )
    actual = (
        select_actual_area(config)
        if use_config_actual_area
        else float(reference["actual_area_um2"])
    )
    synthesis_time_ms = (
        select_actual_time(config)
        if use_config_actual_time
        else float(reference["synthesis_time_ms"])
    )
    estimated = prediction["predicted_area_um2"]
    prediction_time_ms = prediction["prediction_time_ms"]
    return {
        "predicted_area_um2": estimated,
        "actual_area_um2": actual,
        "error_percent": abs(estimated - actual) / actual * 100.0,
        "prediction_time_ms": prediction_time_ms,
        "synthesis_time_ms": synthesis_time_ms,
        "speedup": (
            synthesis_time_ms / prediction_time_ms
            if prediction_time_ms > 0
            else 0.0
        ),
    }

def latency_cycles(config: dict[str, Any]) -> int:
    pipelines = [int(x) for x in config["Pipeline Stages ([Multiplication, Adder Tree])"]]
    stages_t = math.ceil(
        int(config["Number of Transmit Antennas"]) / int(config["Parallelism T"])
    )
    return sum(pipelines) + (stages_t if stages_t > 1 else 0)


def throughput_kchannels_s(config: dict[str, Any], period_ns: float) -> float:
    stages_t = math.ceil(
        int(config["Number of Transmit Antennas"]) / int(config["Parallelism T"])
    )
    return 1e6 / stages_t / period_ns / int(config["Number of Receiving Antennas"])


def configured_output_dir(config_path: Path, config: dict[str, Any]) -> Path:
    if config_path.is_relative_to(ROOT.resolve()):
        return ROOT / "evaluation_output" / config_path.stem
    relative = config.get("flow", {}).get("output_dir", "evaluation_output")
    return (config_path.parent / relative).resolve()


def _case_id(config_path: Path) -> int:
    match = re.fullmatch(r"config_case(\d+)", config_path.stem)
    if match is None or config_path.suffix != ".json":
        raise ValueError("RTL simulation requires a config_caseN.json file")
    return int(match.group(1))


def simulate_lsce(config_path: Path, *, config: dict[str, Any] | None = None) -> dict[str, int]:
    """Return fresh probe measurements directly, without a JSON round trip."""
    from BehaviorialVerification.validate_lsce_latency import run_validation
    measured = run_validation(config_path, _case_id(config_path), config=config)
    return {"latency_cycles": measured["sim_latency_cycles"],
            "output_interval_cycles": measured["sim_output_interval_cycles"]}


def save_result(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "lsce_metrics.json").open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


def cleanup_generated_simulation_outputs() -> None:
    """Preserve all sim/TestcaseN directories between evaluations."""
    validation_root = (
        ROOT / "BehaviorialVerification" / "sim"
    )
    validation_root.mkdir(parents=True, exist_ok=True)


def cleanup_previous_run(config_paths: list[Path]) -> None:
    """Remove only selected metrics files, preserving other cases and user files."""
    for path in config_paths:
        config = load_config(path)
        (configured_output_dir(path, config) / "lsce_metrics.json").unlink(missing_ok=True)


def run_lsce_evaluation(
    config_filename: str | Path = DEFAULT_CONFIG,
    *,
    clean_previous: bool = True,
) -> dict[str, Any]:
    """Evaluate one LSCE config and write lsce_metrics.json."""
    config_path = Path(config_filename).resolve()
    config = load_config(config_path)
    return _evaluate_config(config_path, config, clean_previous=clean_previous)


def _evaluate_config(config_path: Path, config: dict[str, Any], *, clean_previous: bool) -> dict[str, Any]:
    if clean_previous:
        (configured_output_dir(config_path, config) / "lsce_metrics.json").unlink(missing_ok=True)

    period_ns = float(config.get("clock", {}).get("period_ns", 10.0))
    flow = config.get("flow", {})
    started = time.perf_counter()
    predicted_latency = latency_cycles(config)
    latency_time_ms = (time.perf_counter() - started) * 1000.0

    area = evaluate_lsce_area(config_path, config)

    predicted_complexity = area["predicted_area_um2"] / GE_AREA_UM2 * predicted_latency
    result: dict[str, Any] = {
        "延迟": {
            "预测结果 (cycles)": predicted_latency,
            "仿真结果 (cycles)": None,
            "误差 (%)": None,
            "预测时间 (ms)": round(latency_time_ms, 6),
            "仿真时间 (ms)": None,
            "速度提升倍数 (×)": None,
        },
        "面积": {
            "预测结果 (μm²)": round(area["predicted_area_um2"], 2),
            "真实结果 (μm²)": round(area["actual_area_um2"], 2),
            "误差 (%)": round(area["error_percent"], 2),
            "预测时间 (ms)": round(area["prediction_time_ms"], 6),
            "综合时间 (ms)": round(area["synthesis_time_ms"], 3),
            "速度提升倍数 (×)": round(area["speedup"], 2),
        },
        "Throughput": {
            "预测结果 (kChannels/s)": round(throughput_kchannels_s(config, period_ns), 5),
            "仿真结果 (kChannels/s)": None,
        },
        "硬件复杂度": {
            "预测结果 (GE·cycles)": round(predicted_complexity, 2),
            "真实结果 (GE·cycles)": None,
            "误差 (%)": None,
            "GE基准单元": GE_REFERENCE_CELL,
            "1 GE面积 (μm²)": GE_AREA_UM2,
        },
    }

    if bool(flow.get("run_simulation", False)):
        sim_started = time.perf_counter()
        simulation = simulate_lsce(config_path, config=config)
        simulated_latency = simulation["latency_cycles"]
        simulated_output_interval = simulation["output_interval_cycles"]
        simulation_time_ms = (time.perf_counter() - sim_started) * 1000.0
        error = (
            (simulated_latency - predicted_latency) / predicted_latency * 100.0
            if predicted_latency else None
        )
        speedup = simulation_time_ms / latency_time_ms if latency_time_ms > 0 else None
        result["延迟"].update({
            "仿真结果 (cycles)": simulated_latency,
            "误差 (%)": round(error, 2) if error is not None else None,
            "仿真时间 (ms)": round(simulation_time_ms, 3),
            "速度提升倍数 (×)": round(speedup, 2) if speedup is not None else None,
        })
        result["Throughput"]["仿真结果 (kChannels/s)"] = round(
            1e6
            / simulated_output_interval
            / period_ns
            / int(config["Number of Receiving Antennas"]),
            5,
        )
        actual_complexity = area["actual_area_um2"] / GE_AREA_UM2 * simulated_latency
        complexity_error = abs(predicted_complexity - actual_complexity) / actual_complexity * 100.0
        result["硬件复杂度"].update({
            "真实结果 (GE·cycles)": round(actual_complexity, 2),
            "误差 (%)": round(complexity_error, 2),
        })

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


def run_lsce_evaluations(config: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Run case1-case5, or one selected config, matching the BP batch API."""
    paths = resolve_config_selection(config)
    loaded = [(path, load_config(path)) for path in paths]
    return {path.stem: _evaluate_config(path, value, clean_previous=True)
            for path, value in loaded}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LSCE config_case1..5, or one selected config."
    )
    parser.add_argument("config", nargs="?", help="Config path, or non-negative case number")
    args = parser.parse_args()
    try:
        results = run_lsce_evaluations(args.config)
    except (ValueError, RuntimeError, OSError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
