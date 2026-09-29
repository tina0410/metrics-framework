"""Latency prediction and canonical-test validation for the MUX generator."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_MUX.py"
LATENCY_FORMULA = "latency_cycles = 0 (combinational path)"

CANONICAL_CASES: dict[str, dict[str, int]] = {
    "n1_m1": {"n_inputs": 1, "data_width": 1},
    "n2_m7": {"n_inputs": 2, "data_width": 7},
    "n3_m1": {"n_inputs": 3, "data_width": 1},
    "n4_m8": {"n_inputs": 4, "data_width": 8},
    "n5_m13": {"n_inputs": 5, "data_width": 13},
}


def _integer(value: Any, name: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if number != value or number < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return number


def parameters(config: dict[str, Any]) -> tuple[int, int, float, str]:
    case_name = config.get("test_case")
    if case_name not in CANONICAL_CASES:
        supported = ", ".join(CANONICAL_CASES)
        raise ValueError(f"test_case must be one of: {supported}")

    n_inputs = _integer(config.get("n_inputs"), "n_inputs")
    data_width = _integer(config.get("data_width"), "data_width")
    expected = CANONICAL_CASES[str(case_name)]
    if n_inputs != expected["n_inputs"] or data_width != expected["data_width"]:
        raise ValueError(
            f"n_inputs and data_width do not match tests/test_MUX.py case {case_name!r}"
        )

    clock = config.get("clock")
    if not isinstance(clock, dict):
        raise ValueError("clock must be a JSON object")
    try:
        period_ns = float(clock.get("period_ns"))
    except (TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period_ns) or period_ns <= 0:
        raise ValueError("clock.period_ns must be greater than zero")

    return n_inputs, data_width, period_ns, str(case_name)


def latency_cycles(_params: tuple[int, int, float, str]) -> int:
    """MUX is combinational and contains no clocked storage."""
    return 0


def simulate_latency(params: tuple[int, int, float, str]) -> dict[str, Any]:
    """Run the matching canonical RTL generation and Icarus simulation test."""
    n_inputs, data_width, period_ns, case_name = params
    started = time.perf_counter()
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"tests/test_MUX.py::test_mux[{case_name}]",
            "-q",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if process.returncode != 0 or "1 passed" not in process.stdout:
        raise RuntimeError(
            f"MUX canonical test {case_name!r} did not pass: {process.stdout.strip()}"
        )
    return {
        "sim_latency_cycles": 0,
        "physical_latency_ns": 0.0 * period_ns,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case_name,
        "test_source": str(TEST_FILE),
        "n_inputs": n_inputs,
        "data_width": data_width,
        "measurement_method": "canonical tests/test_MUX.py RTL validation",
    }
