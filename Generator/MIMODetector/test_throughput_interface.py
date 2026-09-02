from __future__ import annotations

import pytest

from throughput_interface import (
    evaluate_throughput,
    throughput_gbps,
    valid_bits_per_output,
)


def _config(*, qam_order: int | None = 16, period_ns: float = 10.0) -> dict:
    config = {
        "Number of Transmit Antennas": 4,
        "clock": {"period_ns": period_ns},
    }
    if qam_order is not None:
        config["QAM Order"] = qam_order
    return config


def test_evaluate_throughput_matches_case5_contract() -> None:
    result = evaluate_throughput(
        _config(), simulated_output_interval_cycles=4
    )
    assert result == {
        "valid_bits_per_output": 16,
        "predicted_output_interval_cycles": 4,
        "simulated_output_interval_cycles": 4,
        "predicted_gbps": 0.4,
        "simulated_gbps": 0.4,
    }


def test_missing_optional_inputs_produce_none() -> None:
    result = evaluate_throughput(_config(qam_order=None))
    assert valid_bits_per_output(_config(qam_order=None)) is None
    assert result["predicted_gbps"] is None
    assert result["simulated_gbps"] is None


@pytest.mark.parametrize(
    ("config", "interval"),
    [
        (_config(qam_order=3), 4),
        (_config(period_ns=0.0), 4),
        (_config(), 0),
        ({**_config(), "Number of Transmit Antennas": 4.5}, 4),
    ],
)
def test_invalid_physical_inputs_are_rejected(config: dict, interval: int) -> None:
    with pytest.raises(ValueError):
        throughput_gbps(config, interval)
