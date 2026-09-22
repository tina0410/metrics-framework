from __future__ import annotations

import json
from pathlib import Path

import pytest

import pusch_ce_area_interface as area_interface


def _minimal_config() -> dict:
    return {
        "protocol": {},
        "architecture": {},
        "quantization": {},
        "arithmetic": {},
        "implementation": {},
        "area": {
            "use_config_actual_area": False,
            "actual_area_um2": None,
            "use_config_actual_time": False,
            "actual_time_ms": None,
        },
    }


def test_evaluate_area_uses_workbook_reference(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_minimal_config()), encoding="utf-8")
    monkeypatch.setattr(
        area_interface,
        "predict_area",
        lambda _path: {"predicted_area_um2": 90.0, "prediction_time_ms": 2.0},
    )
    monkeypatch.setattr(
        area_interface,
        "read_reference_area",
        lambda _config: {
            "actual_area_um2": 100.0,
            "design_id": 7,
            "reference_sources": ["param.xlsx"],
        },
    )
    result = area_interface.evaluate_area(config_path)
    assert result["actual_area_um2"] == 100.0
    assert result["error_percent"] == pytest.approx(10.0)
    assert result["actual_value_kind"] == "historical_dc_reference"


def test_evaluate_area_prefers_enabled_json_values(monkeypatch, tmp_path):
    config = _minimal_config()
    config["area"] = {
        "use_config_actual_area": True,
        "actual_area_um2": 120.0,
        "use_config_actual_time": True,
        "actual_time_ms": 30.0,
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(
        area_interface,
        "predict_area",
        lambda _path: {"predicted_area_um2": 90.0, "prediction_time_ms": 2.0},
    )
    monkeypatch.setattr(
        area_interface,
        "read_reference_area",
        lambda _config: pytest.fail("JSON override must bypass workbook lookup"),
    )
    result = area_interface.evaluate_area(config_path)
    assert result["actual_area_um2"] == 120.0
    assert result["error_percent"] == pytest.approx(25.0)
    assert result["speedup"] == pytest.approx(15.0)
    assert result["actual_value_kind"] == "configured_known_value"


@pytest.mark.parametrize("case", range(1, 6))
def test_real_case_has_prediction_and_unique_param_reference(case):
    config_path = (
        Path(__file__).resolve().parents[2]
        / "Generator"
        / "PUSCH_CE"
        / "cases"
        / f"config{case}.json"
    )
    result = area_interface.evaluate_area(config_path)

    assert result["predicted_area_um2"] > 0
    assert result["actual_area_um2"] > 0
    assert result["prediction_time_ms"] >= 0
    assert result["error_percent"] >= 0
    assert result["reference_sources"] == ["param.xlsx"]
    assert result["actual_value_kind"] == "historical_dc_reference"
