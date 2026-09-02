"""Reusable throughput calculations for the MIMO detector flow."""

from __future__ import annotations

import math
from typing import Any, Mapping, TypedDict


class ThroughputEvaluation(TypedDict):
    """Full-precision values returned by :func:`evaluate_throughput`."""

    valid_bits_per_output: int | None
    predicted_output_interval_cycles: int
    simulated_output_interval_cycles: int | None
    predicted_gbps: float | None
    simulated_gbps: float | None


def _positive_integer(value: Any, name: str) -> int:
    numeric = float(value)
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric <= 0:
        raise ValueError(f"{name} must be a positive integer")
    result = int(numeric)
    return result


def _clock_period_ns(config: Mapping[str, Any]) -> float:
    clock = config.get("clock", {})
    period_ns = float(clock.get("period_ns", 10.0))
    if not math.isfinite(period_ns) or period_ns <= 0:
        raise ValueError("clock.period_ns must be a finite value greater than zero")
    return period_ns


def valid_bits_per_output(config: Mapping[str, Any]) -> int | None:
    """Return the information bits in one complete detected MIMO vector."""
    if "QAM Order" not in config:
        return None
    tx = _positive_integer(config["Number of Transmit Antennas"], "transmit antennas")
    qam_order = _positive_integer(config["QAM Order"], "QAM order")
    if qam_order < 2 or qam_order & (qam_order - 1):
        raise ValueError("QAM order must be a power of two not less than 2")
    return tx * (qam_order.bit_length() - 1)


def predicted_output_interval_cycles(config: Mapping[str, Any]) -> int:
    """Return the back-to-back vector initiation interval confirmed by RTL."""
    return _positive_integer(
        config["Number of Transmit Antennas"], "transmit antennas"
    )


def throughput_gbps(
    config: Mapping[str, Any], output_interval_cycles: int | None
) -> float | None:
    """Convert vector information bits and an initiation interval to Gbps."""
    bits = valid_bits_per_output(config)
    if bits is None or output_interval_cycles is None:
        return None
    interval = _positive_integer(output_interval_cycles, "output interval")
    return bits / interval / _clock_period_ns(config)


def evaluate_throughput(
    config: Mapping[str, Any],
    *,
    simulated_output_interval_cycles: int | None = None,
) -> ThroughputEvaluation:
    """Evaluate predicted throughput and an optional RTL-measured throughput."""
    predicted_interval = predicted_output_interval_cycles(config)
    return {
        "valid_bits_per_output": valid_bits_per_output(config),
        "predicted_output_interval_cycles": predicted_interval,
        "simulated_output_interval_cycles": simulated_output_interval_cycles,
        "predicted_gbps": throughput_gbps(config, predicted_interval),
        "simulated_gbps": throughput_gbps(config, simulated_output_interval_cycles),
    }
