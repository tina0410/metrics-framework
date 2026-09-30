"""PUSCH CE effective-output-bit throughput prediction and RTL comparison.

Throughput is the number of useful channel-estimate output bits in one slot
divided by the steady-state interval between adjacent ``slot_ce_done`` pulses.
The first accepted-``start`` latency has the same predicted cycle count because
both boundaries place the controller at the entry to its ``RUN`` state.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys
import time
from typing import Any, Mapping

from latency_interface import predict_latency, runtime_from_config


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a positive integer") from error
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(numeric)


def _qutype_data_width(expression: Any, name: str) -> int:
    match = re.fullmatch(
        r"\s*QuType\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(?:True|False)\s*\)\s*",
        str(expression),
    )
    if match is None:
        raise ValueError(f"invalid {name} QuType expression: {expression!r}")
    return _positive_int(match.group(1), f"{name} data width")


def effective_output_bits(config: Mapping[str, Any]) -> int:
    """Return useful complex H_TI bits produced for one runtime slot."""

    runtime = runtime_from_config(config)
    ports = config["protocol"].get("antenna_ports")
    if not isinstance(ports, list) or not ports:
        raise ValueError("protocol.antenna_ports must be a non-empty list")
    component_width = _qutype_data_width(
        config["quantization"].get("H_TI"), "quantization.H_TI"
    )
    return (
        runtime.num_rbs
        * 12
        * runtime.num_symbols
        * len(ports)
        * 2
        * component_width
    )


def throughput_gbps(bits_per_slot: Any, interval_cycles: Any, period_ns: Any) -> float:
    """Convert useful bits per slot and a cycle interval to Gbit/s."""

    bits = _positive_int(bits_per_slot, "bits per slot")
    interval = _positive_int(interval_cycles, "slot interval")
    try:
        period = float(period_ns)
    except (TypeError, ValueError) as error:
        raise ValueError("clock period must be greater than zero") from error
    if not math.isfinite(period) or period <= 0:
        raise ValueError("clock period must be greater than zero")
    # bit/ns is numerically equal to Gbit/s.
    return bits / (interval * period)


def predict_throughput(
    config: Mapping[str, Any],
    *,
    latency_prediction: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    latency = (
        dict(latency_prediction)
        if latency_prediction is not None
        else predict_latency(config)
    )
    bits = effective_output_bits(config)
    interval = int(latency["predicted_cycles"])
    period = float(latency["runtime"]["clock_period_ns"])
    return {
        "predicted_gbps": throughput_gbps(bits, interval, period),
        "predicted_output_bits": bits,
        "predicted_interval_cycles": interval,
        "clock_period_ns": period,
        "interval_boundary": "adjacent_slot_ce_done_rising_edges",
        "prediction_time_ms": (time.perf_counter() - started) * 1000.0,
        "latency_prediction": latency,
    }


def evaluate_throughput(
    config: Mapping[str, Any],
    *,
    actual_interval_cycles: int | None = None,
    actual_output_bits: int | None = None,
    simulation_time_ms: float | None = None,
) -> dict[str, Any]:
    prediction = predict_throughput(config)
    if actual_interval_cycles is None and actual_output_bits is None:
        return {
            **prediction,
            "actual_gbps": None,
            "actual_interval_cycles": None,
            "actual_output_bits": None,
            "error_percent": None,
            "simulation_time_ms": simulation_time_ms,
            "speedup": None,
        }
    if actual_interval_cycles is None or actual_output_bits is None:
        raise ValueError("actual interval and RTL-counted output bits are both required")

    interval = _positive_int(actual_interval_cycles, "actual slot interval")
    bits = _positive_int(actual_output_bits, "actual output bits")
    expected_bits = int(prediction["predicted_output_bits"])
    if bits != expected_bits:
        raise ValueError(
            f"RTL produced {bits} useful bits, expected {expected_bits} for one slot"
        )
    actual = throughput_gbps(bits, interval, prediction["clock_period_ns"])
    predicted = float(prediction["predicted_gbps"])
    prediction_time = float(prediction["prediction_time_ms"])
    return {
        **prediction,
        "actual_gbps": actual,
        "actual_interval_cycles": interval,
        "actual_output_bits": bits,
        "error_percent": abs(predicted - actual) / actual * 100.0,
        "simulation_time_ms": simulation_time_ms,
        "speedup": (
            simulation_time_ms / prediction_time
            if simulation_time_ms is not None and prediction_time > 0
            else None
        ),
    }


__all__ = [
    "effective_output_bits",
    "evaluate_throughput",
    "predict_throughput",
    "throughput_gbps",
]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} CONFIG", file=sys.stderr)
        return 1
    try:
        from latency_interface import load_case_config

        config = load_case_config(Path(sys.argv[1]).expanduser().resolve())
        sys.stdout.write(json.dumps(predict_throughput(config), ensure_ascii=False))
        return 0
    except (FileNotFoundError, KeyError, LookupError, RuntimeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
