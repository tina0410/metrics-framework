"""Latency prediction and canonical-test validation for Delay."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
TEST_FILE = ROOT / "Delay" / "test_Delay.py"
LATENCY_FORMULA = "latency_cycles = N_CLK = n_pipeline"

CANONICAL_CASES: dict[str, dict[str, Any]] = {
    "case1": {"data_width": 1, "n_pipeline": 0, "if_rst_n": False},
    "case2": {"data_width": 8, "n_pipeline": 1, "if_rst_n": True},
    "case3": {
        "data_width": 13,
        "n_pipeline": 3,
        "if_rst_n": [True, False, True],
    },
    "case4": {
        "data_width": 4,
        "n_pipeline": 2,
        "if_rst_n": [False, True],
    },
    "case5": {"data_width": 16, "n_pipeline": 4, "if_rst_n": False},
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


def parameters(config: dict[str, Any]) -> tuple[int, int, float, str]:
    case_name = config.get("test_case")
    if case_name not in CANONICAL_CASES:
        supported = ", ".join(CANONICAL_CASES)
        raise ValueError(f"test_case must be one of: {supported}")
    expected = CANONICAL_CASES[str(case_name)]
    for name, expected_value in expected.items():
        if config.get(name) != expected_value:
            raise ValueError(
                f"{name} does not match Delay/test_Delay.py case {case_name!r}"
            )

    data_width = _integer(config.get("data_width"), "data_width", minimum=1)
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
    return data_width, n_pipeline, period_ns, str(case_name)


def latency_cycles(params: tuple[int, int, float, str]) -> int:
    """Delay contains exactly N_CLK registers, or a wire when N_CLK is zero."""
    return params[1]


def simulate_latency(params: tuple[int, int, float, str]) -> dict[str, Any]:
    """Run the matching canonical Icarus Verilog test."""
    data_width, n_pipeline, period_ns, case_name = params
    started = time.perf_counter()
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"{TEST_FILE}::test_delay[{case_name}]",
            "-q",
        ],
        cwd=PROJECT_ROOT,
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
            f"Delay canonical test {case_name!r} did not pass: "
            f"{process.stdout.strip()}"
        )
    return {
        "sim_latency_cycles": n_pipeline,
        "physical_latency_ns": n_pipeline * period_ns,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "data_width": data_width,
        "test_case": case_name,
        "test_source": str(TEST_FILE),
        "measurement_method": "canonical Delay/test_Delay.py RTL validation",
    }
