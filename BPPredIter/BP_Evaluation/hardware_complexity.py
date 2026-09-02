"""Convert silicon area to NAND2-equivalent gate complexity (GE)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STANDARD_CELL_AREA_FILE = ROOT.parent.parent / "Area_TP_Estimator" / "65nm Standard Cells Area.txt"
GE_REFERENCE_CELL = "LVT_NAND2HDV0"


@lru_cache(maxsize=None)
def read_ge_area(
    area_file: Path = STANDARD_CELL_AREA_FILE,
    reference_cell: str = GE_REFERENCE_CELL,
) -> float:
    """Read the minimum-drive two-input NAND area used as one GE."""
    area_file = Path(area_file)
    if not area_file.exists():
        raise FileNotFoundError(f"65nm standard-cell area file not found: {area_file}")
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
            f"Found {len(matches)} entries for GE reference cell {reference_cell} in {area_file}"
        )
    if matches[0] <= 0:
        raise ValueError(f"GE reference-cell area must be positive: {matches[0]}")
    return matches[0]


def area_to_ge(area_um2: float, ge_area_um2: float) -> float:
    """Convert an area in square micrometres to NAND2-equivalent gates."""
    if area_um2 < 0:
        raise ValueError(f"Circuit area cannot be negative: {area_um2}")
    if ge_area_um2 <= 0:
        raise ValueError(f"GE area must be positive: {ge_area_um2}")
    return area_um2 / ge_area_um2
