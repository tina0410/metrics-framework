"""Single-configuration area interface for the MIMO metric evaluator."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from EstlNSA_MMSE import EstlNSA_GUI


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_DIR = ROOT / "model"
DEFAULT_REFERENCE_WORKBOOK = ROOT / "INSA.xlsx"
DEFAULT_REFERENCE_SHEET = "INSA"

CONFIG_QUANTIZATION_COLUMNS = {
    "Quantization format of H": ("QU_IN_H",),
    "Quantization format of y": ("QU_IN_Y", "QU_IN_y"),
    "Quantization format of a": ("QU_IN_a",),
    "Quantization format of D": ("QU_IN_D",),
    "Quantization format of ymf": ("QU_OUT_ymf",),
    "Quantization format of x1": ("QU_OUT_x1",),
    "Quantization format of b2": ("QU_OUT_b2",),
    "Quantization format of d2": ("QU_OUT_d2", "QU_OUT+d2"),
    "Quantization format of Dx1": ("QU_OUT_Dx1",),
    "Quantization format of x2": ("QU_OUT_x2",),
    "Quantization format of b3": ("QU_OUT_b3",),
    "Quantization format of d3": ("QU_OUT_d3",),
    "Quantization format of Dx2": ("QU_OUT_Dx2",),
    "Quantization format of x3": ("QU_OUT_x3",),
    "Quantization format of b4": ("QU_OUT_b4",),
    "Quantization format of d4": ("QU_OUT_d4",),
    "Quantization format of Dx3": ("QU_OUT_Dx3",),
    "Quantization format of x4": ("QU_OUT_x4",),
}

_QU_PAIR_PATTERN = re.compile(
    r"^\s*[\[(]?\s*([+-]?\d+)\s*[,，\\/]\s*([+-]?\d+)\s*[\])]?\s*$"
)


def _resolve_column(columns: pd.Index, aliases: tuple[str, ...], label: str) -> str:
    available = {str(column).strip(): str(column) for column in columns}
    for alias in aliases:
        if alias in available:
            return available[alias]
    raise KeyError(f"参考表缺少{label}列；可接受列名: {', '.join(aliases)}")


def _config_integer(config: dict[str, Any], key: str) -> int:
    try:
        value = int(config[key])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"MIMO配置缺少有效整数参数 {key!r}") from None
    if value <= 0:
        raise ValueError(f"MIMO配置参数 {key!r} 必须大于0")
    return value


def _config_quantization(config: dict[str, Any], key: str) -> tuple[int, int]:
    value = config.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"MIMO配置缺少量化参数 {key!r}")
    try:
        bitwidth = int(value["bitwidth"])
        fractional_width = int(value["fractional width"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            f"MIMO配置参数 {key!r} 需要整数 bitwidth 和 fractional width"
        ) from None
    if bitwidth <= 0 or fractional_width < 0:
        raise ValueError(f"MIMO配置参数 {key!r} 的位宽必须有效")
    if not isinstance(value.get("signed"), bool):
        raise ValueError(f"MIMO配置参数 {key!r}.signed 必须是布尔值")
    if not value["signed"]:
        raise ValueError(f"当前面积参考模型仅支持有符号量化: {key!r}")
    return bitwidth, fractional_width


def _workbook_quantization(value: Any, column: str) -> tuple[int, int]:
    match = _QU_PAIR_PATTERN.fullmatch(str(value))
    if match is None:
        raise ValueError(f"参考表 {column}={value!r} 不是有效的位宽,小数位格式")
    return tuple(int(part) for part in match.groups())


@lru_cache(maxsize=4)
def _load_models(model_dir: Path) -> tuple[Any, Any, Any, pd.DataFrame, pd.DataFrame]:
    model_dir = model_dir.resolve()
    required = {
        "SU输入表": model_dir / "SU_in.xlsx",
        "加法器模型": model_dir / "ADD_area.pkl",
        "乘法器模型": model_dir / "pure_MUL_area.pkl",
        "SU输出模型": model_dir / "SU_out_FxP_area.pkl",
    }
    missing = [f"{label}: {path}" for label, path in required.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError("缺少MIMO面积模型文件:\n" + "\n".join(missing))
    su_in = pd.read_excel(required["SU输入表"], sheet_name="SU_in")
    sub = pd.read_excel(required["SU输入表"], sheet_name="Sub")
    return (
        joblib.load(required["加法器模型"]),
        joblib.load(required["乘法器模型"]),
        joblib.load(required["SU输出模型"]),
        su_in,
        sub,
    )


def predict_area(
    config_path: str | Path,
    *,
    model_dir: str | Path = DEFAULT_MODEL_DIR,
) -> dict[str, float]:
    """Run the existing estimator and report its live wall-clock time."""
    config_path = Path(config_path).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"找不到MIMO配置文件: {config_path}")
    resources = _load_models(Path(model_dir).expanduser().resolve())
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        evaluated = EstlNSA_GUI(*resources, ConfigFileName=str(config_path))
    prediction_time_ms = (time.perf_counter() - started) * 1000.0
    if evaluated is None:
        raise RuntimeError("MIMO面积估算器未返回结果")
    predicted = float(evaluated[0])
    if not math.isfinite(predicted) or predicted <= 0:
        raise ValueError(f"MIMO面积估算器返回无效面积: {predicted}")
    return {
        "predicted_area_um2": predicted,
        "prediction_time_ms": prediction_time_ms,
    }


def _configured_positive_value(
    config: dict[str, Any], *, switch_key: str, value_key: str
) -> float | None:
    """Return an enabled positive value, or ``None`` for workbook fallback."""
    area_config = config.get("area", {})
    if not isinstance(area_config, dict):
        raise ValueError("Configuration error: area must be an object.")
    switch = area_config.get(switch_key, False)
    if not isinstance(switch, bool):
        raise ValueError(f"Configuration error: area.{switch_key} must be boolean.")
    if not switch:
        return None
    try:
        value = float(area_config[value_key])
    except (KeyError, TypeError, ValueError):
        value = math.nan
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"Configuration error: area.{value_key} must be greater than 0 "
            f"when area.{switch_key}=true."
        )
    return value


def select_actual_area(
    config: dict[str, Any], workbook_actual_area_um2: float | None = None
) -> float:
    """Select actual area from config when enabled, otherwise from the workbook."""
    configured = _configured_positive_value(
        config,
        switch_key="use_config_actual_area",
        value_key="actual_area_um2",
    )
    if configured is not None:
        return configured
    if workbook_actual_area_um2 is None:
        raise ValueError(
            "Workbook actual area is required when the config value is disabled."
        )
    actual = float(workbook_actual_area_um2)
    if not math.isfinite(actual) or actual <= 0:
        raise ValueError(f"Workbook actual area must be greater than 0; got {actual}.")
    return actual


def select_actual_time(
    config: dict[str, Any], workbook_actual_time_ms: float | None = None
) -> float:
    """Select synthesis time from config when enabled, otherwise from workbook."""
    configured = _configured_positive_value(
        config,
        switch_key="use_config_actual_time",
        value_key="actual_time_ms",
    )
    if configured is not None:
        return configured
    if workbook_actual_time_ms is None:
        raise ValueError(
            "Workbook actual synthesis time is required when the config value is disabled."
        )
    actual = float(workbook_actual_time_ms)
    if not math.isfinite(actual) or actual <= 0:
        raise ValueError(
            f"Workbook actual synthesis time must be greater than 0; got {actual}."
        )
    return actual


def read_reference_area(
    config: dict[str, Any],
    *,
    workbook_path: str | Path = DEFAULT_REFERENCE_WORKBOOK,
    sheet_name: str = DEFAULT_REFERENCE_SHEET,
) -> dict[str, Any]:
    """Match historical DC rows and combine equivalent repeated measurements."""
    workbook_path = Path(workbook_path).expanduser().resolve()
    if not workbook_path.is_file():
        raise FileNotFoundError(f"找不到MIMO面积参考表: {workbook_path}")
    table = pd.read_excel(workbook_path, sheet_name=sheet_name)
    table.columns = [str(column).strip() for column in table.columns]

    integer_columns = {
        "Tx": _config_integer(config, "Number of Transmit Antennas"),
        "Rx": _config_integer(config, "Number of Receiving Antennas"),
        "AT_PIPELINES": _config_integer(config, "Adder Tree Pipelines"),
        "iterations": _config_integer(config, "Iterations"),
    }
    matches = pd.Series(True, index=table.index)
    for column, expected in integer_columns.items():
        actual_column = _resolve_column(table.columns, (column,), column)
        numeric = pd.to_numeric(table[actual_column], errors="coerce")
        matches &= numeric.eq(expected)

    for config_key, aliases in CONFIG_QUANTIZATION_COLUMNS.items():
        expected = _config_quantization(config, config_key)
        column = _resolve_column(table.columns, aliases, config_key)
        parsed = table[column].map(
            lambda value: _workbook_quantization(value, column)
            if pd.notna(value)
            else None
        )
        matches &= parsed.map(lambda actual: actual == expected)

    matched = table.loc[matches]
    if matched.empty:
        raise ValueError(
            "参考表未匹配到MIMO配置: "
            f"Tx={integer_columns['Tx']}, Rx={integer_columns['Rx']}, "
            f"AT_PIPELINES={integer_columns['AT_PIPELINES']}, "
            f"iterations={integer_columns['iterations']}"
        )
    area_column = _resolve_column(table.columns, ("dc综合面积", "DC综合面积"), "DC综合面积")
    time_column = _resolve_column(
        table.columns, ("time", "综合时间", "Synthesis Time (s)"), "综合时间"
    )
    areas = pd.to_numeric(matched[area_column], errors="raise").astype(float)
    synthesis_times_ms = (
        pd.to_numeric(matched[time_column], errors="raise").astype(float) * 1000.0
    )
    actual_area = float(areas.iloc[0])
    if not all(
        math.isclose(float(area), actual_area, rel_tol=1e-12, abs_tol=1e-6)
        for area in areas
    ):
        rows = [int(index) + 2 for index in matched.index]
        raise ValueError(f"参考表匹配行{rows}的DC综合面积不一致")
    # Repeated rows are independent historical runs of the same structure.
    # Area must agree exactly; median synthesis time is robust to run-to-run noise.
    synthesis_time_ms = float(synthesis_times_ms.median())
    if not math.isfinite(actual_area) or actual_area <= 0:
        raise ValueError(f"参考表包含无效DC综合面积: {actual_area}")
    if not math.isfinite(synthesis_time_ms) or synthesis_time_ms <= 0:
        raise ValueError(f"参考表包含无效综合时间: {synthesis_time_ms} ms")
    return {
        "actual_area_um2": actual_area,
        "synthesis_time_ms": synthesis_time_ms,
        "reference_workbook": str(workbook_path),
        "reference_sheet": sheet_name,
        "reference_excel_rows": [int(index) + 2 for index in matched.index],
        "reference_replicates": int(len(matched)),
        "synthesis_time_aggregation": "median_of_matching_historical_runs",
    }


def evaluate_mimo_area(
    config_path: str | Path,
    *,
    model_dir: str | Path = DEFAULT_MODEL_DIR,
    workbook_path: str | Path = DEFAULT_REFERENCE_WORKBOOK,
    sheet_name: str = DEFAULT_REFERENCE_SHEET,
) -> dict[str, Any]:
    """Return predicted area plus configured or workbook actual area and time."""
    config_path = Path(config_path).expanduser().resolve()
    with config_path.open("r", encoding="utf-8-sig") as stream:
        config = json.load(stream)
    predicted = predict_area(config_path, model_dir=model_dir)
    configured_area = _configured_positive_value(
        config,
        switch_key="use_config_actual_area",
        value_key="actual_area_um2",
    )
    configured_time = _configured_positive_value(
        config,
        switch_key="use_config_actual_time",
        value_key="actual_time_ms",
    )
    reference = (
        {}
        if configured_area is not None and configured_time is not None
        else read_reference_area(
            config, workbook_path=workbook_path, sheet_name=sheet_name
        )
    )
    actual_area = select_actual_area(config, reference.get("actual_area_um2"))
    synthesis_time_ms = select_actual_time(
        config, reference.get("synthesis_time_ms")
    )
    predicted_area = float(predicted["predicted_area_um2"])
    prediction_time_ms = float(predicted["prediction_time_ms"])
    return {
        **predicted,
        **reference,
        "actual_area_um2": actual_area,
        "synthesis_time_ms": synthesis_time_ms,
        "error_percent": abs(predicted_area - actual_area) / actual_area * 100.0,
        "speedup": synthesis_time_ms / prediction_time_ms,
        "actual_value_kind": (
            "configured_known_value"
            if configured_area is not None
            else "historical_dc_reference"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="评估单个MIMO配置的面积")
    parser.add_argument("config", help="MIMO JSON配置文件")
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    parser.add_argument("--workbook", default=DEFAULT_REFERENCE_WORKBOOK)
    parser.add_argument("--sheet", default=DEFAULT_REFERENCE_SHEET)
    args = parser.parse_args()
    result = evaluate_mimo_area(
        args.config,
        model_dir=args.model_dir,
        workbook_path=args.workbook,
        sheet_name=args.sheet,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

