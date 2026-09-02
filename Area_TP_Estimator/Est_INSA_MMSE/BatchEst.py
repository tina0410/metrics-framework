"""Batch evaluation for the lNSA MMSE area estimator.

The quantization columns in the input workbook use ``dwt,frac`` values.
Every :class:`PyTU.QuType` created here is signed (``IF_SIGNED=1``).
Each sample row is interpreted as one complete, independent configuration.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import math
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

import DataflowPE
import lNSA
from EstlNSA_MMSE import EstlNSA_MMSE
from PyTU import QuType


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EXCEL_PATH = (
    BASE_DIR
    / "INSA.xlsx"
)
DEFAULT_SHEET_NAME = "INSA"
DEFAULT_MODEL_DIR = BASE_DIR / "model"

# EstlNSA_MMSE keyword -> accepted Excel headers.  The source workbook contains
# two historical header variants: QU_IN_Y and the typo QU_OUT+d2.
QUANTIZATION_COLUMNS: dict[str, tuple[str, ...]] = {
    "QU_IN_H": ("QU_IN_H",),
    "QU_IN_y": ("QU_IN_Y", "QU_IN_y"),
    "QU_IN_a": ("QU_IN_a",),
    "QU_IN_D": ("QU_IN_D",),
    "QU_OUT_ymf": ("QU_OUT_ymf",),
    "QU_OUT_x1": ("QU_OUT_x1",),
    "QU_OUT_b2": ("QU_OUT_b2",),
    "QU_OUT_d2": ("QU_OUT_d2", "QU_OUT+d2"),
    "QU_OUT_Dx1": ("QU_OUT_Dx1",),
    "QU_OUT_x2": ("QU_OUT_x2",),
    "QU_OUT_b3": ("QU_OUT_b3",),
    "QU_OUT_d3": ("QU_OUT_d3",),
    "QU_OUT_Dx2": ("QU_OUT_Dx2",),
    "QU_OUT_x3": ("QU_OUT_x3",),
    "QU_OUT_b4": ("QU_OUT_b4",),
    "QU_OUT_d4": ("QU_OUT_d4",),
    "QU_OUT_Dx3": ("QU_OUT_Dx3",),
    "QU_OUT_x4": ("QU_OUT_x4",),
}

INTEGER_COLUMNS = ("Tx", "Rx", "AT_PIPELINES", "iterations")
TRUE_AREA_COLUMN = "dc综合面积"
TRUE_AREA_COLUMNS = (TRUE_AREA_COLUMN, "DC综合面积")
_QU_PATTERN = re.compile(
    r"^\s*[\[(]?\s*([+-]?\d+)\s*[,，]\s*([+-]?\d+)\s*[\])]?\s*$"
)


def _resolve_quantization_columns(columns: pd.Index) -> dict[str, str]:
    """Resolve estimator arguments to the actual column names in the workbook."""
    available = set(columns)
    resolved: dict[str, str] = {}
    missing: list[str] = []

    for argument, candidates in QUANTIZATION_COLUMNS.items():
        source = next((name for name in candidates if name in available), None)
        if source is None:
            missing.append("/".join(candidates))
        else:
            resolved[argument] = source

    required_plain = [*INTEGER_COLUMNS]
    missing.extend(name for name in required_plain if name not in available)
    if missing:
        raise ValueError(f"Excel缺少必要列: {', '.join(missing)}")

    return resolved


def _resolve_true_area_column(columns: pd.Index) -> str:
    """Resolve the true-area column while accepting historical capitalization."""
    available = set(columns)
    source = next((name for name in TRUE_AREA_COLUMNS if name in available), None)
    if source is None:
        raise ValueError(f"Excel缺少真实面积列: {'/'.join(TRUE_AREA_COLUMNS)}")
    return source


def _parse_qu_pair(value: Any, column: str, excel_row: int) -> tuple[int, int]:
    """Parse one Excel ``dwt,frac`` cell into an integer pair."""
    match = _QU_PATTERN.fullmatch(str(value))
    if match is None:
        raise ValueError(
            f"Excel第{excel_row}行的 {column}={value!r}，应为'dwt,frac'格式"
        )

    dwt, frac = (int(part) for part in match.groups())
    if dwt <= 0:
        raise ValueError(f"Excel第{excel_row}行的 {column} 中dwt必须大于0")
    return dwt, frac


def _parse_qu_type(value: Any, column: str, excel_row: int) -> QuType:
    """Convert an Excel ``dwt,frac`` cell into a signed QuType."""
    dwt, frac = _parse_qu_pair(value, column, excel_row)
    return QuType(dwt, frac, 1)


def _parse_integer(value: Any, column: str, excel_row: int) -> int:
    """Read an integer-valued Excel cell without silently truncating it."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Excel第{excel_row}行的 {column}={value!r} 不是整数") from exc

    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"Excel第{excel_row}行的 {column}={value!r} 不是整数")
    return int(number)


def _load_estimation_resources(model_dir: Path) -> tuple[Any, Any, Any, pd.DataFrame, pd.DataFrame]:
    """Load regression models and SU lookup tables once for the whole batch."""
    paths = {
        "SU输入表": model_dir / "SU_in.xlsx",
        "加法器模型": model_dir / "ADD_area.pkl",
        "乘法器模型": model_dir / "pure_MUL_area.pkl",
        "SU输出模型": model_dir / "SU_out_FxP_area.pkl",
    }
    missing = [f"{label}: {path}" for label, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError("缺少评估模型文件:\n" + "\n".join(missing))

    su_in_db = pd.read_excel(paths["SU输入表"], sheet_name="SU_in", header=0)
    sub_db = pd.read_excel(paths["SU输入表"], sheet_name="Sub", header=0)
    model_add = joblib.load(paths["加法器模型"])
    model_mul = joblib.load(paths["乘法器模型"])
    model_su_out = joblib.load(paths["SU输出模型"])
    return model_add, model_mul, model_su_out, su_in_db, sub_db


def _reset_cross_sample_state() -> None:
    """Clear performance caches so each sample remains independently reproducible."""
    DataflowPE._cached_qu_layers.clear()
    lNSA._cached_min_values.clear()


def calculate_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | int]:
    """Calculate MAPE (percent), RRSE and Pearson's correlation coefficient r."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("真实值和预测值的形状不一致")

    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual = actual[valid]
    predicted = predicted[valid]
    if actual.size == 0:
        raise ValueError("没有可用于计算指标的有效预测结果")
    if np.any(actual == 0):
        raise ValueError("真实值中包含0，MAPE无定义")

    mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100.0)

    rrse_denominator = float(np.sum((actual - np.mean(actual)) ** 2))
    rrse = (
        float(np.sqrt(np.sum((actual - predicted) ** 2) / rrse_denominator))
        if rrse_denominator > 0.0
        else float("nan")
    )

    if actual.size < 2 or np.std(actual) == 0.0 or np.std(predicted) == 0.0:
        correlation = float("nan")
    else:
        correlation = float(np.corrcoef(actual, predicted)[0, 1])

    return {
        "sample_count": int(actual.size),
        "MAPE": mape,
        "RRSE": rrse,
        "r": correlation,
    }


def BatchEst(
    excel_path: str | Path = DEFAULT_EXCEL_PATH,
    *,
    sheet_name: str | int = DEFAULT_SHEET_NAME,
    model_dir: str | Path = DEFAULT_MODEL_DIR,
    if_rst_n: bool = True,
    limit: int | None = None,
    progress_every: int = 0,
    show_estimator_output: bool = False,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Independently estimate every complete sample row in an Excel sheet.

    Args:
        excel_path: Workbook containing lNSA parameters and ``dc综合面积``.
        sheet_name: Sheet name or zero-based sheet index.
        model_dir: Directory containing ``SU_in.xlsx`` and the three ``.pkl`` models.
        if_rst_n: Passed to ``EstlNSA_MMSE``.  ``True`` reproduces the prediction
            convention used by the existing ``自动评估结果`` column.
        limit: Optional number of leading samples, useful for a quick smoke test.
        progress_every: Print progress every N samples; 0 disables progress output.
        show_estimator_output: Show the per-sample text printed by the estimator.

    Returns:
        ``(results, metrics)``.  ``results`` contains the source data plus
        ``Excel行``, ``预测值``, ``绝对百分比误差(%)`` and ``估算时间(s)``;
        ``metrics`` contains ``sample_count``, ``MAPE`` (percent), ``RRSE`` and ``r``.
    """
    excel_path = Path(excel_path).expanduser().resolve()
    model_dir = Path(model_dir).expanduser().resolve()
    if not excel_path.is_file():
        raise FileNotFoundError(f"找不到Excel文件: {excel_path}")
    if limit is not None and limit <= 0:
        raise ValueError("limit必须大于0")
    if progress_every < 0:
        raise ValueError("progress_every不能为负数")

    source = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)
    qu_columns = _resolve_quantization_columns(source.columns)
    true_area_column = _resolve_true_area_column(source.columns)

    # Rows without a true area are footer/summary rows, not evaluation samples.
    sample_mask = source[true_area_column].notna()
    results = source.loc[sample_mask].copy()
    results.insert(0, "Excel行", results.index.to_numpy() + 2)
    results.reset_index(drop=True, inplace=True)
    if limit is not None:
        results = results.iloc[:limit].copy()
    if results.empty:
        raise ValueError(f"{true_area_column}列中没有有效样本")

    model_add, model_mul, model_su_out, su_in_db, sub_db = _load_estimation_resources(model_dir)

    predicted_areas: list[float] = []
    elapsed_times: list[float] = []
    total = len(results)

    for position, row in results.iterrows():
        excel_row = int(row["Excel行"])
        integer_values = {
            column: _parse_integer(row[column], column, excel_row)
            for column in INTEGER_COLUMNS
        }
        qu_types = {
            argument: _parse_qu_type(row[source_column], source_column, excel_row)
            for argument, source_column in qu_columns.items()
        }

        _reset_cross_sample_state()

        def estimate_one() -> tuple[float, float]:
            return EstlNSA_MMSE(
                model_add,
                model_mul,
                model_su_out,
                su_in_db,
                sub_db,
                Tx=integer_values["Tx"],
                Rx=integer_values["Rx"],
                AdderTree_PIPELINES=integer_values["AT_PIPELINES"],
                iterations=integer_values["iterations"],
                IF_RST_N=if_rst_n,
                **qu_types,
            )

        if show_estimator_output:
            area, elapsed = estimate_one()
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                area, elapsed = estimate_one()

        area = float(area)
        elapsed = float(elapsed)
        if not math.isfinite(area):
            raise ValueError(f"Excel第{excel_row}行得到非有限预测值: {area}")
        predicted_areas.append(area)
        elapsed_times.append(elapsed)

        completed = position + 1
        if progress_every and (completed % progress_every == 0 or completed == total):
            print(f"已完成 {completed}/{total}")

    results["预测值"] = predicted_areas
    actual = pd.to_numeric(results[true_area_column], errors="raise").to_numpy(dtype=float)
    predicted = np.asarray(predicted_areas, dtype=float)
    metrics = calculate_metrics(actual, predicted)
    results["绝对百分比误差(%)"] = np.abs((actual - predicted) / actual) * 100.0
    results["估算时间(s)"] = elapsed_times

    return results, metrics


# Lower-case alias for callers following PEP 8 naming conventions.
batch_estimate = BatchEst


def _parse_sheet_name(value: str) -> str | int:
    return int(value) if value.isdigit() else value


def main() -> None:
    parser = argparse.ArgumentParser(description="批量评估lNSA MMSE面积并计算MAPE、RRSE和r")
    parser.add_argument("excel", nargs="?", default=DEFAULT_EXCEL_PATH, help="输入Excel文件")
    parser.add_argument(
        "--sheet",
        default=DEFAULT_SHEET_NAME,
        help=f"工作表名称或从0开始的序号（默认: {DEFAULT_SHEET_NAME}）",
    )
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR, help="模型文件目录")
    parser.add_argument("--limit", type=int, default=None, help="只评估前N条样本")
    parser.add_argument("--progress-every", type=int, default=25, help="每N条显示一次进度，0为关闭")
    parser.add_argument("--show-estimator-output", action="store_true", help="显示估算器逐条输出")
    parser.add_argument(
        "--no-rst-n",
        action="store_true",
        help="令IF_RST_N=False；默认True以匹配原表的自动评估结果",
    )
    args = parser.parse_args()

    results, metrics = BatchEst(
        args.excel,
        sheet_name=_parse_sheet_name(args.sheet),
        model_dir=args.model_dir,
        if_rst_n=not args.no_rst_n,
        limit=args.limit,
        progress_every=args.progress_every,
        show_estimator_output=args.show_estimator_output,
    )

    print("\n前5条预测:")
    true_area_column = _resolve_true_area_column(results.columns)
    print(
        results[["Excel行", true_area_column, "预测值", "绝对百分比误差(%)"]]
        .head()
        .to_string(index=False)
    )
    print("\n汇总指标:")
    print(f"样本数: {metrics['sample_count']}")
    print(f"MAPE: {metrics['MAPE']:.6f}%")
    print(f"RRSE: {metrics['RRSE']:.6f}")
    print(f"r: {metrics['r']:.6f}")


if __name__ == "__main__":
    main()
