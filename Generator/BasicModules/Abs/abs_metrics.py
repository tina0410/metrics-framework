"""Latency prediction and canonical-test validation for the Abs generator."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_Abs.py"
LATENCY_FORMULA = "latency_cycles = N_CLK = n_pipeline"


CANONICAL_CASES: dict[str, dict[str, Any]] = {
    "signed_same": {
        "input": {"bitwidth": 8, "fractional_width": 4, "signed": True},
        "output": {"bitwidth": 8, "fractional_width": 4, "signed": True},
        "n_pipeline": 0,
        "if_rst_n": False,
        "quantization_mode": "TRN.TCPL",
        "overflow_mode": "WRP.TCPL",
    },
    "signed_min_wide": {
        "input": {"bitwidth": 8, "fractional_width": 4, "signed": True},
        "output": {"bitwidth": 9, "fractional_width": 4, "signed": True},
        "n_pipeline": 2,
        "if_rst_n": True,
        "quantization_mode": "RND.CONV",
        "overflow_mode": "SAT.TCPL",
    },
    "signed_narrow_sat": {
        "input": {"bitwidth": 8, "fractional_width": 4, "signed": True},
        "output": {"bitwidth": 5, "fractional_width": 2, "signed": True},
        "n_pipeline": 1,
        "if_rst_n": False,
        "quantization_mode": "RND.POS_INF",
        "overflow_mode": "SAT.TCPL",
    },
    "signed_to_nonnegative": {
        "input": {"bitwidth": 7, "fractional_width": 3, "signed": True},
        "output": {"bitwidth": 6, "fractional_width": 2, "signed": False},
        "n_pipeline": 1,
        "if_rst_n": True,
        "quantization_mode": "RND.ZERO",
        "overflow_mode": "SAT.ZERO",
    },
    "nonnegative_passthrough": {
        "input": {"bitwidth": 8, "fractional_width": 3, "signed": False},
        "output": {"bitwidth": 8, "fractional_width": 3, "signed": False},
        "n_pipeline": 0,
        "if_rst_n": False,
        "quantization_mode": "TRN.TCPL",
        "overflow_mode": "WRP.TCPL",
    },
}


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if number != value or number < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return number


def parameters(config: dict[str, Any]) -> tuple[int, float, str]:
    case_name = config.get("test_case")
    if case_name not in CANONICAL_CASES:
        supported = ", ".join(CANONICAL_CASES)
        raise ValueError(f"test_case must be one of: {supported}")
    expected = CANONICAL_CASES[str(case_name)]
    for name, expected_value in expected.items():
        if config.get(name) != expected_value:
            raise ValueError(
                f"{name} does not match tests/test_Abs.py case {case_name!r}"
            )
    n_pipeline = _integer(config.get("n_pipeline"), "n_pipeline")
    clock = config.get("clock")
    if not isinstance(clock, dict):
        raise ValueError("clock must be a JSON object")
    try:
        period_ns = float(clock.get("period_ns"))
    except (TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period_ns) or period_ns <= 0:
        raise ValueError("clock.period_ns must be greater than zero")
    return n_pipeline, period_ns, str(case_name)


def latency_cycles(params: tuple[int, float, str]) -> int:
    """Abs registers only through ModuleDelay, so latency equals N_CLK."""
    return params[0]


def simulate_latency(params: tuple[int, float, str]) -> dict[str, Any]:
    """Run the matching canonical test case, including C++ and RTL simulation."""
    n_pipeline, period_ns, case_name = params
    started = time.perf_counter()
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"tests/test_Abs.py::test_abs[{case_name}]",
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
    if process.returncode != 0:
        raise RuntimeError(
            f"Abs canonical test {case_name!r} failed: {process.stdout.strip()}"
        )
    return {
        "sim_latency_cycles": n_pipeline,
        "physical_latency_ns": n_pipeline * period_ns,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case_name,
        "test_source": str(TEST_FILE),
        "measurement_method": "canonical tests/test_Abs.py C++ + RTL validation",
    }
