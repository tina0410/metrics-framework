from __future__ import annotations

from pathlib import Path

import pytest

from hardware_complexity_interface import (
    GE_REFERENCE_CELL,
    area_to_ge,
    evaluate_hardware_complexity,
    hardware_complexity_ge_cycles,
    read_ge_area,
)


def test_canonical_ge_reference_area_is_loaded() -> None:
    assert read_ge_area() == 1.12


def test_predicted_and_actual_complexity_contract() -> None:
    result = evaluate_hardware_complexity(
        112.0,
        40,
        actual_area_um2=123.2,
        actual_latency_cycles=50,
    )
    assert result["predicted_ge_cycles"] == pytest.approx(4000.0)
    assert result["actual_ge_cycles"] == pytest.approx(5500.0)
    assert result["error_percent"] == pytest.approx(27.2727272727)
    assert result["ge_reference_cell"] == GE_REFERENCE_CELL
    assert result["ge_area_um2"] == 1.12


def test_actual_complexity_is_optional_but_inputs_are_paired() -> None:
    result = evaluate_hardware_complexity(112.0, 40)
    assert result["actual_ge_cycles"] is None
    assert result["error_percent"] is None
    with pytest.raises(ValueError, match="provided together"):
        evaluate_hardware_complexity(112.0, 40, actual_area_um2=123.2)


def test_ge_file_requires_one_unique_reference(tmp_path: Path) -> None:
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
