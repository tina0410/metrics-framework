from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PUSCH_ROOT = Path(__file__).resolve().parent / "Generator" / "PUSCH_CE"
sys.path.insert(0, str(PUSCH_ROOT))

from latency_interface import (  # noqa: E402
    LatencyRuntime,
    LatencyTiming,
    evaluate_latency,
    load_case_config,
    predict_from_terms,
    runtime_from_config,
)


def _runtime(*, double: bool = False) -> LatencyRuntime:
    return LatencyRuntime(
        num_rbs=10,
        num_symbols=12,
        dmrs_type=1,
        is_double_dmrs=double,
        dmrs_type_a_pos="pos2",
        n_additional_dmrs=0,
        clock_period_ns=10.0,
    )


def test_post_fi_formula_matches_rtl_loop_structure():
    timing = LatencyTiming(2, 3, 4, 3, False, 1, 0, 0)
    result = predict_from_terms(timing, _runtime())

    assert result["formula_case"] == "post_fi"
    assert result["breakdown"]["cycles_before_ti"] == 20
    assert result["breakdown"]["ti_total_cycles"] == 44
    assert result["predicted_cycles"] == 64
    assert result["predicted_time_ns"] == 640.0


def test_pre_fi_double_uses_full_fi_occurrence_cost():
    timing = LatencyTiming(2, 6, 3, 2, True, 4, 11, 7)
    result = predict_from_terms(timing, _runtime(double=True))

    assert result["formula_case"] == "pre_fi"
    assert result["breakdown"]["fi_window_count"] == 3
    assert result["breakdown"]["fi_cycles_per_window"] == 11
    assert result["breakdown"]["ti_sweep_cycles"] == 8
    assert result["breakdown"]["ti_total_cycles"] == 60


def test_pre_fi_single_uses_short_hybrid_cost():
    timing = LatencyTiming(2, 6, 3, 2, True, 4, 11, 7)
    result = predict_from_terms(timing, _runtime())

    assert result["formula_case"] == "pre_fi_hybrid_single"
    assert result["breakdown"]["fi_cycles_per_window"] == 7
    assert result["breakdown"]["ti_total_cycles"] == 48


def test_partial_final_post_fi_beat_keeps_all_rtl_lanes():
    timing = LatencyTiming(4, 12, 1, 0, False, 1, 0, 0)
    result = predict_from_terms(timing, _runtime())

    assert result["breakdown"]["rb_beats_per_symbol"] == 3
    assert result["breakdown"]["ti_sweep_cycles"] == 12


def test_evaluation_uses_actual_rtl_cycles_as_error_denominator(monkeypatch):
    prediction = {
        "predicted_cycles": 90,
        "predicted_time_ns": 900.0,
        "prediction_time_ms": 2.0,
        "formula_case": "post_fi",
        "breakdown": {},
        "runtime": {"clock_period_ns": 10.0},
        "timing": {},
    }
    monkeypatch.setattr("latency_interface.predict_latency", lambda _config: prediction)

    result = evaluate_latency({}, actual_cycles=100, simulation_time_ms=40.0)

    assert result["actual_time_ns"] == 1000.0
    assert result["error_percent"] == pytest.approx(10.0)
    assert result["speedup"] == pytest.approx(20.0)


@pytest.mark.parametrize("double", [False, True])
def test_dmrs_symbol_type_changes_last_symbol(double):
    timing = LatencyTiming(2, 12, 1, 0, False, 1, 0, 0)
    result = predict_from_terms(timing, _runtime(double=double))

    assert result["breakdown"]["last_dmrs_symbol"] == 2 + int(double)


@pytest.mark.parametrize("case", range(1, 6))
def test_runtime_cases_are_kept_outside_area_configs(case):
    path = PUSCH_ROOT / "cases" / f"config{case}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    combined = load_case_config(path)

    assert "latency" not in raw
    assert runtime_from_config(combined).num_rbs > 0
