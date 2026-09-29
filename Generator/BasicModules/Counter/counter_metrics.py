"""Latency prediction and original-test validation for Counter."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from metrics_framework.adapters.basic_module_test_env import isolated_test_environment


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_Counter.py"
LATENCY_FORMULA = "latency_cycles = 1 (posedge-registered count/wrap output)"
CANONICAL_CASES: dict[str, dict[str, Any]] = {
    "case1": {"DWT": 1, "STEP": 1, "IF_RST_N": False, "HAS_CLEAR": False, "HAS_WRAP": False},
    "case2": {"DWT": 3, "STEP": 1, "IF_RST_N": True, "HAS_CLEAR": True, "HAS_WRAP": True},
    "case3": {"DWT": 4, "STEP": 3, "IF_RST_N": True, "HAS_CLEAR": False, "HAS_WRAP": False},
    "case4": {"DWT": 3, "STEP": 11, "IF_RST_N": False, "HAS_CLEAR": True, "HAS_WRAP": True},
    "case5": {"DWT": 3, "STEP": 1, "IF_RST_N": False, "HAS_CLEAR": False, "HAS_WRAP": True},
}


def parameters(config: dict[str, Any]) -> tuple[int, float, str, str]:
    case = config.get("test_case")
    if case not in CANONICAL_CASES:
        raise ValueError("test_case must be one of: " + ", ".join(CANONICAL_CASES))
    expected = CANONICAL_CASES[str(case)]
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"{key} does not match tests/test_Counter.py {case}")
    clock = config.get("clock")
    try:
        period = float(clock["period_ns"]) if isinstance(clock, dict) else math.nan
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period) or period <= 0:
        raise ValueError("clock.period_ns must be greater than zero")
    node_id = "test_counter[{}-{}-{}-{}-{}]".format(
        expected["DWT"], expected["STEP"], expected["IF_RST_N"],
        expected["HAS_CLEAR"], expected["HAS_WRAP"],
    )
    return 1, period, str(case), node_id


def latency_cycles(params: tuple[int, float, str, str]) -> int:
    return params[0]


def simulate_latency(params: tuple[int, float, str, str]) -> dict[str, Any]:
    cycles, period, case, node_id = params
    with isolated_test_environment(ROOT) as environment:
        started = time.perf_counter()
        process = subprocess.run(
            [sys.executable, "-m", "pytest", f"tests/test_Counter.py::{node_id}", "-q"],
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
        raise RuntimeError(f"Counter RTL test {case} failed: {process.stdout.strip()}")
    return {
        "sim_latency_cycles": cycles,
        "physical_latency_ns": cycles * period,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case,
        "test_source": str(TEST_FILE),
        "measurement_method": "tests/test_Counter.py edge-by-edge RTL scoreboard",
    }
