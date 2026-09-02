"""Reusable latency interface for the MIMO detector flow."""

from __future__ import annotations

import math
from typing import Any, Mapping, TypedDict


class LatencyEvaluation(TypedDict):
    """Full-precision values returned by :func:`evaluate_latency`."""

    predicted_cycles: int
    actual_cycles: int | None
    error_percent: float | None


def _positive_integer(value: Any, name: str) -> int:
    numeric = float(value)
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(numeric)


def predict_latency(config: Mapping[str, Any]) -> int:
    """Predict cycles from accepted input to a complete output vector."""
    tx = _positive_integer(
        config["Number of Transmit Antennas"], "transmit antennas"
    )
    iterations = _positive_integer(config["Iterations"], "iterations")
    adder_pipelines = _positive_integer(
        config["Adder Tree Pipelines"], "adder-tree pipelines"
    )
    return (iterations + 1) * (tx + adder_pipelines) + 4 * iterations - 1


def evaluate_latency(
    config: Mapping[str, Any],
    *,
    actual_latency_cycles: int | None = None,
) -> LatencyEvaluation:
    """Evaluate predicted latency and an optional RTL-measured latency."""
    predicted = predict_latency(config)
    actual = None
    error_percent = None
    if actual_latency_cycles is not None:
        actual = _positive_integer(actual_latency_cycles, "actual latency")
        error_percent = (actual - predicted) / predicted * 100.0
    return {
        "predicted_cycles": predicted,
        "actual_cycles": actual,
        "error_percent": error_percent,
    }
