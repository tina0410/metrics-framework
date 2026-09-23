from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
PUSCH_ROOT = ROOT / "Generator" / "PUSCH_CE"
if str(PUSCH_ROOT) not in sys.path:
    sys.path.insert(0, str(PUSCH_ROOT))

from hardware_complexity_interface import (
    GE_REFERENCE_CELL,
    area_to_ge,
    evaluate_hardware_complexity,
    hardware_complexity_ge_cycles,
    read_ge_area,
)


def test_pusch_ce_uses_shared_nand2_reference_area() -> None:
    assert GE_REFERENCE_CELL == "LVT_NAND2HDV0"
    assert read_ge_area() == 1.12


def test_predicted_and_actual_complexity_and_error() -> None:
    result = evaluate_hardware_complexity(
        112.0,
        40,
        actual_area_um2=123.2,
        actual_latency_cycles=50,
    )
    assert result["predicted_ge_cycles"] == pytest.approx(4000.0)
    assert result["actual_ge_cycles"] == pytest.approx(5500.0)
    assert result["error_percent"] == pytest.approx(27.2727272727)
    assert result["ge_area_um2"] == 1.12


def test_actual_inputs_must_be_provided_as_a_pair() -> None:
    result = evaluate_hardware_complexity(112.0, 40)
    assert result["actual_ge_cycles"] is None
    assert result["error_percent"] is None
    with pytest.raises(ValueError, match="provided together"):
        evaluate_hardware_complexity(112.0, 40, actual_area_um2=123.2)


def test_reference_cell_must_be_unique(tmp_path: Path) -> None:
    area_file = tmp_path / "cells.txt"
    area_file.write_text(
        "Cell: library/LVT_NAND2HDV0, Area: 1.250000\n",
        encoding="utf-8",
    )
    assert read_ge_area(area_file) == 1.25
    area_file.write_text("Cell: library/OTHER, Area: 1.0\n", encoding="utf-8")
    read_ge_area.cache_clear()
    with pytest.raises(LookupError):
        read_ge_area(area_file)


@pytest.mark.parametrize(
    "call",
    [
        lambda: area_to_ge(-1.0, 1.12),
        lambda: area_to_ge(1.0, 0.0),
        lambda: hardware_complexity_ge_cycles(1.0, -1, 1.12),
        lambda: hardware_complexity_ge_cycles(1.0, 1.5, 1.12),
    ],
)
def test_invalid_complexity_inputs_are_rejected(call) -> None:
    with pytest.raises(ValueError):
        call()
