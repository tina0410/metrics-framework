from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
PUSCH_ROOT = ROOT / "Generator" / "PUSCH_CE"
if str(PUSCH_ROOT) not in sys.path:
    sys.path.insert(0, str(PUSCH_ROOT))

import throughput_interface as throughput


def _config() -> dict:
    return {
        "protocol": {"antenna_ports": [10, 12]},
        "quantization": {"H_TI": "QuType(14, 2, True)"},
        "latency": {
            "clock_period_ns": 10.0,
            "runtime": {
                "num_RBs": 5,
                "num_symbols": 8,
                "dmrs_type": 1,
                "is_double_dmrs": True,
                "dmrs_typeA_pos": "pos3",
                "n_additional_dmrs": 0,
            },
        },
    }


def test_effective_output_bits_counts_complex_channel_estimates() -> None:
    # 5 RB * 12 RE * 8 symbols * 2 ports * (real+imag) * 14 bits.
    assert throughput.effective_output_bits(_config()) == 26_880


def test_throughput_gbps_uses_bit_per_ns_equivalence() -> None:
    assert throughput.throughput_gbps(26_880, 280, 10.0) == 9.6


def test_evaluation_compares_prediction_with_rtl_interval(monkeypatch) -> None:
    monkeypatch.setattr(
        throughput,
        "predict_latency",
        lambda _config: {
            "predicted_cycles": 280,
            "prediction_time_ms": 0.1,
            "runtime": {"clock_period_ns": 10.0},
        },
    )
    result = throughput.evaluate_throughput(
        _config(), actual_interval_cycles=300, actual_output_bits=26_880
    )
    assert result["predicted_gbps"] == 9.6
    assert result["actual_gbps"] == 8.96
    assert result["error_percent"] == pytest.approx(100 / 14)
    assert result["interval_boundary"] == "adjacent_slot_ce_done_rising_edges"


def test_evaluation_rejects_incomplete_rtl_output(monkeypatch) -> None:
    monkeypatch.setattr(
        throughput,
        "predict_latency",
        lambda _config: {
            "predicted_cycles": 280,
            "prediction_time_ms": 0.1,
            "runtime": {"clock_period_ns": 10.0},
        },
    )
    with pytest.raises(ValueError, match="RTL produced"):
        throughput.evaluate_throughput(
            _config(), actual_interval_cycles=300, actual_output_bits=1
        )
