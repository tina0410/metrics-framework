"""BP decoder area prediction and DC-reference comparison."""

from __future__ import annotations

import contextlib
import io
import time
from functools import lru_cache
from pathlib import Path

import pandas as pd

from EstBP import Esttop


ROOT = Path(__file__).resolve().parent
AREA_WORKBOOK_CANDIDATES = (ROOT / "area.xlsx", ROOT / "BP.xlsx")

COLUMN_ALIASES = {
    "architecture": ("archi", "Architecture"),
    "algorithm": ("algo", "Algorithm"),
    "width": ("width", "Width (bits)"),
    "n": ("N", "N (coded bits/frame)"),
    "m": ("M", "M (LLRs/cycle)"),
    "actual_area": ("dc综合面积", "Area (μm²)", "Area (um^2)", "Area"),
    "synthesis_time": ("time", "综合时间", "Synthesis Time (s)"),
    "stored_prediction": ("自动评估结果", "Predicted Area (μm²)"),
    "stored_prediction_time": ("评估时间", "Prediction Time (s)"),
    "report": ("Report序列", "Report"),
}


def _resolve_columns(columns: list[str]) -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    required = {"architecture", "algorithm", "width", "n", "m", "actual_area", "synthesis_time"}
    for canonical, aliases in COLUMN_ALIASES.items():
        match = next((alias for alias in aliases if alias in columns), None)
        if match is None and canonical in required:
            raise KeyError(
                f"area.xlsx missing {canonical}; accepted names: {', '.join(aliases)}"
            )
        resolved[canonical] = match
    return resolved


def _resolve_area_workbook() -> Path:
    for candidate in AREA_WORKBOOK_CANDIDATES:
        if candidate.exists():
            return candidate
    expected = ", ".join(str(path) for path in AREA_WORKBOOK_CANDIDATES)
    raise FileNotFoundError(f"Area workbook not found; expected one of: {expected}")


@lru_cache(maxsize=1)
def _load_area_table() -> tuple[pd.DataFrame, dict[str, str | None]]:
    workbook_path = _resolve_area_workbook()
    with pd.ExcelFile(workbook_path) as workbook:
        sheet_name = next(
            (name for name in ("ALL", "BP") if name in workbook.sheet_names),
            None,
        )
        if sheet_name is None:
            raise ValueError(
                f"Area workbook {workbook_path} must contain an ALL or BP worksheet; "
                f"available worksheets: {workbook.sheet_names}"
            )
        table = pd.read_excel(workbook, sheet_name=sheet_name)
    table.columns = [str(column).strip() for column in table.columns]
    return table, _resolve_columns(list(table.columns))


def read_area(
    architecture: str,
    algorithm: str,
    n: int,
    m: int,
    width: int,
) -> dict[str, float | str]:
    """Read one exact DC-synthesis reference from Area_TP's area.xlsx."""
    table, columns = _load_area_table()
    architecture_values = table[columns["architecture"]].astype(str).str.strip().str.casefold()
    algorithm_values = table[columns["algorithm"]].astype(str).str.strip().str.casefold()
    width_values = pd.to_numeric(table[columns["width"]], errors="coerce")
    n_values = pd.to_numeric(table[columns["n"]], errors="coerce")
    m_values = pd.to_numeric(table[columns["m"]], errors="coerce")
    matches = table.loc[
        architecture_values.eq(architecture.strip().casefold())
        & algorithm_values.eq(algorithm.strip().casefold())
        & width_values.eq(width)
        & n_values.eq(n)
        & m_values.eq(m)
    ]
    key = (
        f"Architecture={architecture}, Algorithm={algorithm}, "
        f"Width={width}, N={n}, M={m}"
    )
    if matches.empty:
        raise LookupError(f"No matching DC area in area.xlsx: {key}")
    if len(matches) > 1:
        raise LookupError(f"Found {len(matches)} duplicate DC areas in area.xlsx: {key}")

    row = matches.iloc[0]
    actual_area = pd.to_numeric(row[columns["actual_area"]], errors="coerce")
    synthesis_time_s = pd.to_numeric(row[columns["synthesis_time"]], errors="coerce")
    if pd.isna(actual_area) or pd.isna(synthesis_time_s):
        raise ValueError(f"Matched DC area or synthesis time is not numeric: {key}")
    report_column = columns.get("report")
    report = "" if report_column is None else str(row[report_column])
    return {
        "actual_area_um2": float(actual_area),
        "synthesis_time_ms": float(synthesis_time_s) * 1000.0,
        "report": report,
    }


def evaluate_area(
    architecture: str,
    algorithm: str,
    n: int,
    m: int,
    width: int,
    *,
    actual_area_um2: float | None = None,
    synthesis_time_ms: float | None = None,
) -> dict[str, float | str | None]:
    """Run Esttop and compare with a workbook or config actual-area reference."""
    prediction_started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        predicted_area = float(
            Esttop(archi=architecture, algo=algorithm, N=n, M=m, width=width)
        )
    prediction_time_ms = (time.perf_counter() - prediction_started) * 1000.0

    if actual_area_um2 is None:
        reference = read_area(architecture, algorithm, n, m, width)
        actual_area = float(reference["actual_area_um2"])
        synthesis_time_ms: float | None = float(reference["synthesis_time_ms"])
        report = str(reference["report"])
    else:
        actual_area = float(actual_area_um2)
        if actual_area <= 0:
            raise ValueError(f"Actual area must be greater than 0, got {actual_area}")
        if synthesis_time_ms is not None:
            synthesis_time_ms = float(synthesis_time_ms)
            if synthesis_time_ms <= 0:
                raise ValueError(
                    "Synthesis time must be greater than 0, "
                    f"got {synthesis_time_ms}"
                )
        report = "config.area.actual_area_um2"

    error_percent = abs(predicted_area - actual_area) / actual_area * 100.0
    speedup = (
        synthesis_time_ms / prediction_time_ms
        if synthesis_time_ms is not None and prediction_time_ms > 0
        else None
    )
    return {
        "predicted_area_um2": predicted_area,
        "actual_area_um2": actual_area,
        "error_percent": error_percent,
        "prediction_time_ms": prediction_time_ms,
        "synthesis_time_ms": synthesis_time_ms,
        "speedup": speedup,
        "report": report,
    }
