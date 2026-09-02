from __future__ import annotations

import json
from pathlib import Path

import pytest

import mimo_area_interface as area_interface
from mimo_area_interface import (
    evaluate_mimo_area,
    read_reference_area,
    select_actual_area,
    select_actual_time,
)


ROOT = Path(__file__).resolve().parent


def _reference_config() -> dict:
    default_output = {"bitwidth": 9, "fractional width": 4, "signed": True}
    config = {
        "Number of Transmit Antennas": 4,
        "Number of Receiving Antennas": 32,
        "Adder Tree Pipelines": 3,
        "Iterations": 2,
        "Quantization format of H": {
            "bitwidth": 9,
            "fractional width": 8,
            "signed": True,
        },
        "Quantization format of y": default_output,
        "Quantization format of a": {
            "bitwidth": 4,
            "fractional width": 4,
            "signed": True,
        },
        "Quantization format of D": {
            "bitwidth": 5,
            "fractional width": 4,
            "signed": True,
        },
    }
    for name in (
        "ymf", "x1", "b2", "d2", "Dx1", "x2", "b3", "d3",
        "Dx2", "x3", "b4", "d4", "Dx3", "x4",
    ):
        config[f"Quantization format of {name}"] = default_output
    return config


def test_reference_row_matches_all_structural_parameters() -> None:
    result = read_reference_area(_reference_config())
    assert result["actual_area_um2"] == pytest.approx(200918.757999)
    assert result["synthesis_time_ms"] == pytest.approx(248343.116521835)
    assert result["reference_excel_rows"] == [2]
    assert result["reference_replicates"] == 1


def test_unsigned_quantization_is_rejected() -> None:
    config = _reference_config()
    config["Quantization format of x4"] = {
        "bitwidth": 9,
        "fractional width": 4,
        "signed": False,
    }
    with pytest.raises(ValueError, match="仅支持有符号量化"):
        read_reference_area(config)


def test_real_estimator_matches_reference_prediction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(_reference_config(), ensure_ascii=False), encoding="utf-8"
    )
    result = evaluate_mimo_area(config_path)
    assert result["predicted_area_um2"] == pytest.approx(196352.188761683)
    assert result["actual_area_um2"] == pytest.approx(200918.757999)
    assert result["error_percent"] == pytest.approx(2.2728436522286864)
    assert result["prediction_time_ms"] > 0
    assert result["speedup"] > 0
    assert result["actual_value_kind"] == "historical_dc_reference"


def test_configured_actual_area_and_time_skip_workbook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "unmatched_config.json"
    config_path.write_text(
        json.dumps(
            {
                "area": {
                    "use_config_actual_area": True,
                    "actual_area_um2": 240000.0,
                    "use_config_actual_time": True,
                    "actual_time_ms": 12000.0,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        area_interface,
        "predict_area",
        lambda *_args, **_kwargs: {
            "predicted_area_um2": 228000.0,
            "prediction_time_ms": 2.0,
        },
    )
    monkeypatch.setattr(
        area_interface,
        "read_reference_area",
        lambda *_args, **_kwargs: pytest.fail("workbook must not be read"),
    )

    result = evaluate_mimo_area(config_path)

    assert result["actual_area_um2"] == 240000.0
    assert result["synthesis_time_ms"] == 12000.0
    assert result["error_percent"] == pytest.approx(5.0)
    assert result["speedup"] == 6000.0
    assert result["actual_value_kind"] == "configured_known_value"
    assert "reference_excel_rows" not in result


def test_config_values_are_independently_selected() -> None:
    config = {
        "area": {
            "use_config_actual_area": True,
            "actual_area_um2": 456.75,
            "use_config_actual_time": False,
            "actual_time_ms": None,
        }
    }
    assert select_actual_area(config, 123.5) == 456.75
    assert select_actual_time(config, 678.0) == 678.0


@pytest.mark.parametrize(
    ("field", "value"),
    [("actual_area_um2", None), ("actual_area_um2", 0), ("actual_time_ms", -1)],
)
def test_enabled_config_value_must_be_positive(field: str, value: object) -> None:
    is_area = field == "actual_area_um2"
    config = {
        "area": {
            "use_config_actual_area": is_area,
            "actual_area_um2": value if is_area else None,
            "use_config_actual_time": not is_area,
            "actual_time_ms": value if not is_area else None,
        }
    }
    with pytest.raises(ValueError, match=field):
        (select_actual_area if is_area else select_actual_time)(config)

