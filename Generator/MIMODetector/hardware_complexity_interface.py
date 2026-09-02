"""NAND2-equivalent hardware-complexity interface for MIMO evaluation."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import TypedDict


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
STANDARD_CELL_AREA_FILE = PROJECT_ROOT / "Area_TP_Estimator" / "65nm Standard Cells Area.txt"
GE_REFERENCE_CELL = "LVT_NAND2HDV0"


class HardwareComplexityEvaluation(TypedDict):
    """Full-precision values returned by the complexity interface."""

    predicted_ge_cycles: float
    actual_ge_cycles: float | None
    error_percent: float | None
    ge_reference_cell: str
    ge_area_um2: float


def _finite_nonnegative(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be a finite non-negative value: {value}")
    return result


def _nonnegative_cycles(value: int, name: str) -> int:
    numeric = float(value)
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric < 0:
        raise ValueError(f"{name} must be a non-negative integer: {value}")
    return int(numeric)


@lru_cache(maxsize=None)
def read_ge_area(
    area_file: Path = STANDARD_CELL_AREA_FILE,
    reference_cell: str = GE_REFERENCE_CELL,
) -> float:
    """Read the unique reference-cell area used as one gate equivalent."""
    area_file = Path(area_file)
    if not area_file.is_file():
        raise FileNotFoundError(f"standard-cell area file not found: {area_file}")
    pattern = re.compile(
        rf"^Cell:\s+[^,]*/{re.escape(reference_cell)},\s*"
        r"Area:\s*([0-9]+(?:\.[0-9]+)?)\s*$"
    )
    matches = [
        float(match.group(1))
        for line in area_file.read_text(encoding="utf-8").splitlines()
        if (match := pattern.match(line.strip()))
    ]
    if not matches:
        raise LookupError(f"GE reference cell {reference_cell} not found in {area_file}")
    if len(matches) != 1:
        raise LookupError(
            f"found {len(matches)} entries for GE reference cell "
            f"{reference_cell} in {area_file}"
        )
    if not math.isfinite(matches[0]) or matches[0] <= 0:
        raise ValueError(f"GE reference-cell area must be positive: {matches[0]}")
    return matches[0]


def area_to_ge(area_um2: float, ge_area_um2: float) -> float:
    """Convert square micrometres to NAND2-equivalent gates."""
    area = _finite_nonnegative(area_um2, "circuit area")
    ge_area = float(ge_area_um2)
    if not math.isfinite(ge_area) or ge_area <= 0:
        raise ValueError(f"GE area must be a finite positive value: {ge_area_um2}")
    return area / ge_area


def hardware_complexity_ge_cycles(
    area_um2: float, latency_cycles: int, ge_area_um2: float
) -> float:
    """Return area in GE multiplied by latency in cycles."""
    latency = _nonnegative_cycles(latency_cycles, "latency")
    return area_to_ge(area_um2, ge_area_um2) * latency


def evaluate_hardware_complexity(
    predicted_area_um2: float,
    predicted_latency_cycles: int,
    *,
    actual_area_um2: float | None = None,
    actual_latency_cycles: int | None = None,
    area_file: Path = STANDARD_CELL_AREA_FILE,
    reference_cell: str = GE_REFERENCE_CELL,
) -> HardwareComplexityEvaluation:
    """Evaluate predicted and optional measured hardware complexity."""
    if (actual_area_um2 is None) != (actual_latency_cycles is None):
        raise ValueError("actual area and actual latency must be provided together")
    ge_area = read_ge_area(Path(area_file), reference_cell)
    predicted = hardware_complexity_ge_cycles(
        predicted_area_um2, predicted_latency_cycles, ge_area
    )
    actual = None
    error_percent = None
    if actual_area_um2 is not None and actual_latency_cycles is not None:
        actual = hardware_complexity_ge_cycles(
            actual_area_um2, actual_latency_cycles, ge_area
        )
        if actual <= 0:
            raise ValueError("actual hardware complexity must be greater than zero")
        error_percent = abs(predicted - actual) / actual * 100.0
    return {
        "predicted_ge_cycles": predicted,
        "actual_ge_cycles": actual,
        "error_percent": error_percent,
        "ge_reference_cell": reference_cell,
        "ge_area_um2": ge_area,
    }
