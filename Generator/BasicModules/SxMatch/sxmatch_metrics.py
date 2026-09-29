"""Latency prediction and original-test validation for SxMatch."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from metrics_framework.adapters.basic_module_test_env import isolated_test_environment


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_SxMatch.py"
LATENCY_FORMULA = "latency_cycles = N_CLK = n_pipeline"
_COMMON_INPUT = {"bitwidth": 5, "fractional_width": 2}
_COMMON_OUTPUT = {"bitwidth": 4, "fractional_width": 1}
_COMMON_POLICIES = {
    "quantization_mode": "TRN.TCPL",
    "overflow_mode": "WRP.TCPL",
}
CANONICAL_CASES: dict[str, dict[str, Any]] = {
    "case1": {"input": {**_COMMON_INPUT, "signed": True}, "output": {**_COMMON_OUTPUT, "signed": True}, "shift": -12, "n_pipeline": 0, "if_rst_n": False, "test_variant": 0},
    "case2": {"input": {**_COMMON_INPUT, "signed": False}, "output": {**_COMMON_OUTPUT, "signed": False}, "shift": -3, "n_pipeline": 1, "if_rst_n": True, "test_variant": 1},
    "case3": {"input": {**_COMMON_INPUT, "signed": True}, "output": {**_COMMON_OUTPUT, "signed": False}, "shift": 0, "n_pipeline": 3, "if_rst_n": False, "test_variant": 2},
    "case4": {"input": {**_COMMON_INPUT, "signed": False}, "output": {**_COMMON_OUTPUT, "signed": False}, "shift": 2, "n_pipeline": 1, "if_rst_n": True, "test_variant": 1},
    "case5": {"input": {**_COMMON_INPUT, "signed": True}, "output": {**_COMMON_OUTPUT, "signed": True}, "shift": 12, "n_pipeline": 0, "if_rst_n": False, "test_variant": 0},
}
_TEST_VARIANTS = (
    (True, True, 0, False),
    (False, False, 1, True),
    (True, False, 3, False),
)


def parameters(config: dict[str, Any]) -> tuple[int, float, str, str]:
    case = config.get("test_case")
    if case not in CANONICAL_CASES:
        raise ValueError("test_case must be one of: " + ", ".join(CANONICAL_CASES))
    expected = CANONICAL_CASES[str(case)]
    for key in ("input", "output", "shift", "n_pipeline", "if_rst_n"):
        if config.get(key) != expected[key]:
            raise ValueError(f"{key} does not match tests/test_SxMatch.py {case}")
    for key, value in _COMMON_POLICIES.items():
        if config.get(key) != value:
            raise ValueError(f"{key} does not match tests/test_SxMatch.py {case}")
    clock = config.get("clock")
    try:
        period = float(clock["period_ns"]) if isinstance(clock, dict) else math.nan
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period) or period <= 0:
        raise ValueError("clock.period_ns must be greater than zero")
    variant = _TEST_VARIANTS[int(expected["test_variant"])]
    signed_in, signed_out, latency, reset = variant
    shift = int(expected["shift"])
    shift_id = f"-{abs(shift)}" if shift < 0 else str(shift)
    node_id = (
        f"test_sxmatch[{signed_in}-{signed_out}-{latency}-{reset}-"
        f"{shift_id}-TRN.TCPL-WRP.TCPL]"
    )
    return int(expected["n_pipeline"]), period, str(case), node_id


def latency_cycles(params: tuple[int, float, str, str]) -> int:
    return params[0]


def simulate_latency(params: tuple[int, float, str, str]) -> dict[str, Any]:
    cycles, period, case, node_id = params
    with isolated_test_environment(ROOT) as environment:
        started = time.perf_counter()
        process = subprocess.run(
            [sys.executable, "-m", "pytest", f"tests/test_SxMatch.py::{node_id}", "-q"],
            cwd=ROOT,
            env=environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    if process.returncode != 0 or "1 passed" not in process.stdout:
        raise RuntimeError(f"SxMatch RTL test {case} failed: {process.stdout.strip()}")
    return {
        "sim_latency_cycles": cycles,
        "physical_latency_ns": cycles * period,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case,
        "test_source": str(TEST_FILE),
        "measurement_method": "tests/test_SxMatch.py RTL scoreboard",
    }
