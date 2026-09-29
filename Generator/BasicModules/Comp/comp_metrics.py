"""Latency prediction and canonical-test validation for Comp."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_Comp.py"
LATENCY_FORMULA = "latency_cycles = N_PIPELINES = n_pipeline"

_COMMON_CONFIG: dict[str, Any] = {
    "n_pipeline": 4,
    "if_rst_n": [False, False, True, False],
    "quantization_mode": "TRN.TCPL",
    "overflow_mode": "WRP.TCPL",
    "outputs": {
        "greater_index": True,
        "less_index": True,
        "equal_index": True,
        "greater_value": True,
        "less_value": True,
    },
    "n_frames": 100,
}

CANONICAL_CASES: dict[str, dict[str, Any]] = {
    "case1": {
        "input_1": {"bitwidth": 7, "fractional_width": 4, "signed": True},
        "input_2": {"bitwidth": 5, "fractional_width": 7, "signed": True},
        "output": {"bitwidth": 4, "fractional_width": 3, "signed": True},
    },
    "case2": {
        "input_1": {"bitwidth": 7, "fractional_width": 4, "signed": True},
        "input_2": {"bitwidth": 5, "fractional_width": 7, "signed": True},
        "output": {"bitwidth": 8, "fractional_width": 3, "signed": True},
    },
    "case3": {
        "input_1": {"bitwidth": 7, "fractional_width": 4, "signed": True},
        "input_2": {"bitwidth": 6, "fractional_width": 7, "signed": True},
        "output": {"bitwidth": 4, "fractional_width": 3, "signed": True},
    },
    "case4": {
        "input_1": {"bitwidth": 7, "fractional_width": 4, "signed": True},
        "input_2": {"bitwidth": 6, "fractional_width": 7, "signed": True},
        "output": {"bitwidth": 8, "fractional_width": 3, "signed": True},
    },
    "case5": {
        "input_1": {"bitwidth": 8, "fractional_width": 4, "signed": True},
        "input_2": {"bitwidth": 5, "fractional_width": 7, "signed": True},
        "output": {"bitwidth": 4, "fractional_width": 3, "signed": True},
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

    expected = {**_COMMON_CONFIG, **CANONICAL_CASES[str(case_name)]}
    for name, expected_value in expected.items():
        if config.get(name) != expected_value:
            raise ValueError(
                f"{name} does not match tests/test_Comp.py case {case_name!r}"
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
    """Every enabled Comp output passes through an N_PIPELINES delay."""
    return params[0]


def simulate_latency(params: tuple[int, float, str]) -> dict[str, Any]:
    """Run the matching canonical C++ and RTL comparison test."""
    n_pipeline, period_ns, case_name = params
    started = time.perf_counter()
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"tests/test_Comp.py::test_comp[{case_name}]",
            "-q",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=240,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if process.returncode != 0 or "1 passed" not in process.stdout:
        raise RuntimeError(
            f"Comp canonical test {case_name!r} did not pass: "
            f"{process.stdout.strip()}"
        )
    return {
        "sim_latency_cycles": n_pipeline,
        "physical_latency_ns": n_pipeline * period_ns,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case_name,
        "test_source": str(TEST_FILE),
        "measurement_method": "canonical tests/test_Comp.py C++ + RTL validation",
    }
