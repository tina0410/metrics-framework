from __future__ import annotations

import pytest

from latency_interface import evaluate_latency, predict_latency


@pytest.mark.parametrize(
    ("tx", "iterations", "pipelines", "expected"),
    [
        (8, 2, 3, 40),
        (4, 2, 3, 28),
        (4, 2, 5, 34),
        (4, 3, 3, 39),
    ],
)
def test_standard_latency_formula(
    tx: int, iterations: int, pipelines: int, expected: int
) -> None:
    config = {
        "Number of Transmit Antennas": tx,
        "Iterations": iterations,
        "Adder Tree Pipelines": pipelines,
    }
    assert predict_latency(config) == expected


def test_optional_actual_latency_and_signed_error() -> None:
    config = {
        "Number of Transmit Antennas": 4,
        "Iterations": 3,
        "Adder Tree Pipelines": 3,
    }
    assert evaluate_latency(config) == {
        "predicted_cycles": 39,
        "actual_cycles": None,
        "error_percent": None,
    }
    assert evaluate_latency(config, actual_latency_cycles=40) == {
        "predicted_cycles": 39,
        "actual_cycles": 40,
        "error_percent": pytest.approx(100.0 / 39.0),
    }


@pytest.mark.parametrize("value", [0, -1, 1.5, float("inf")])
def test_invalid_latency_inputs_are_rejected(value: float) -> None:
    config = {
        "Number of Transmit Antennas": value,
        "Iterations": 2,
        "Adder Tree Pipelines": 3,
    }
    with pytest.raises(ValueError):
        predict_latency(config)
