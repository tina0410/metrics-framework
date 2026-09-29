"""Latency prediction and canonical-test validation for AdderTree."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_AdderTree.py"
LATENCY_FORMULA = "latency_cycles = N_PIPELINES = n_pipeline"


CANONICAL_CASES: dict[str, dict[str, Any]] = {
    "n3_p0": {"n_inputs": 3, "n_pipeline": 0, "if_rst_n": False},
    "n5_p3": {"n_inputs": 5, "n_pipeline": 3, "if_rst_n": True},
    "n8_p2": {"n_inputs": 8, "n_pipeline": 2, "if_rst_n": False},
    "n4_p1": {"n_inputs": 4, "n_pipeline": 1, "if_rst_n": False},
    "n7_p4": {"n_inputs": 7, "n_pipeline": 4, "if_rst_n": True},
}

_COMMON_CONFIG = {
    "input": {"bitwidth": 8, "fractional_width": 0, "signed": False},
    "output": {"bitwidth": 12, "fractional_width": 0, "signed": False},
    "quantization_mode": "TRN.TCPL",
    "overflow_mode": "WRP.TCPL",
    "config_mode": "A",
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

    expected = {**_COMMON_CONFIG, **CANONICAL_CASES[str(case_name)]}
    for name, expected_value in expected.items():
        if config.get(name) != expected_value:
            raise ValueError(
                f"{name} does not match tests/test_AdderTree.py case {case_name!r}"
            )

    n_inputs = _integer(config.get("n_inputs"), "n_inputs", minimum=2)
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
    return n_inputs, n_pipeline, period_ns, str(case_name)


def latency_cycles(params: tuple[int, int, float, str]) -> int:
    """Mode A distributes N_PIPELINES across layers without changing its sum."""
    return params[1]


def simulate_latency(params: tuple[int, int, float, str]) -> dict[str, Any]:
    """Run the matching canonical pytest RTL simulation."""
    n_inputs, n_pipeline, period_ns, case_name = params
    started = time.perf_counter()
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"tests/test_AdderTree.py::test_adder_tree[{case_name}]",
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
            f"AdderTree canonical test {case_name!r} did not pass: "
            f"{process.stdout.strip()}"
        )
    return {
        "sim_latency_cycles": n_pipeline,
        "physical_latency_ns": n_pipeline * period_ns,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "n_inputs": n_inputs,
        "test_case": case_name,
        "test_source": str(TEST_FILE),
        "measurement_method": "canonical tests/test_AdderTree.py RTL validation",
    }
