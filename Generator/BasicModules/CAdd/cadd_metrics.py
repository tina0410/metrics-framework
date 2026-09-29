"""Latency prediction and original-test validation for complex Add."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from metrics_framework.adapters.basic_module_test_env import isolated_test_environment


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_CAdd.py"
LATENCY_FORMULA = "latency_cycles = N_CLK = n_pipeline"
CANONICAL_CASES: dict[str, dict[str, Any]] = {
    "case1": {
        "input_1": {"bitwidth": 4, "fractional_width": 2, "signed": True},
        "input_2": {"bitwidth": 3, "fractional_width": 1, "signed": True},
        "output": {"bitwidth": 5, "fractional_width": 1, "signed": True},
        "n_pipeline": 0, "if_rst_n": False, "variant": 0,
    },
    "case2": {
        "input_1": {"bitwidth": 4, "fractional_width": 1, "signed": False},
        "input_2": {"bitwidth": 3, "fractional_width": 2, "signed": False},
        "output": {"bitwidth": 4, "fractional_width": 0, "signed": False},
        "n_pipeline": 1, "if_rst_n": True, "variant": 1,
    },
    "case3": {
        "input_1": {"bitwidth": 4, "fractional_width": 3, "signed": True},
        "input_2": {"bitwidth": 3, "fractional_width": 0, "signed": False},
        "output": {"bitwidth": 6, "fractional_width": 2, "signed": True},
        "n_pipeline": 3, "if_rst_n": False, "variant": 2,
    },
    "case4": {
        "input_1": {"bitwidth": 3, "fractional_width": -2, "signed": False},
        "input_2": {"bitwidth": 4, "fractional_width": 6, "signed": True},
        "output": {"bitwidth": 4, "fractional_width": -1, "signed": False},
        "n_pipeline": 2, "if_rst_n": True, "variant": 3,
    },
    "case5": {
        "input_1": {"bitwidth": 4, "fractional_width": 2, "signed": True},
        "input_2": {"bitwidth": 3, "fractional_width": 1, "signed": True},
        "output": {"bitwidth": 5, "fractional_width": 1, "signed": True},
        "n_pipeline": 0, "if_rst_n": False, "variant": 0,
    },
}
_TEST_IDS = (
    "q10-q20-qo0-0-False",
    "q11-q21-qo1-1-True",
    "q12-q22-qo2-3-False",
    "q13-q23-qo3-2-True",
)


def parameters(config: dict[str, Any]) -> tuple[int, float, str, str]:
    case = config.get("test_case")
    if case not in CANONICAL_CASES:
        raise ValueError("test_case must be one of: " + ", ".join(CANONICAL_CASES))
    expected = CANONICAL_CASES[str(case)]
    for key in ("input_1", "input_2", "output", "n_pipeline", "if_rst_n"):
        if config.get(key) != expected[key]:
            raise ValueError(f"{key} does not match tests/test_CAdd.py {case}")
    if config.get("quantization_mode") != "TRN.TCPL":
        raise ValueError(f"quantization_mode does not match tests/test_CAdd.py {case}")
    if config.get("overflow_mode") != "WRP.TCPL":
        raise ValueError(f"overflow_mode does not match tests/test_CAdd.py {case}")
    clock = config.get("clock")
    try:
        period = float(clock["period_ns"]) if isinstance(clock, dict) else math.nan
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period) or period <= 0:
        raise ValueError("clock.period_ns must be greater than zero")
    node_id = f"test_CAdd[{_TEST_IDS[int(expected['variant'])]}-TRN.TCPL-WRP.TCPL]"
    return int(expected["n_pipeline"]), period, str(case), node_id


def latency_cycles(params: tuple[int, float, str, str]) -> int:
    return params[0]


def simulate_latency(params: tuple[int, float, str, str]) -> dict[str, Any]:
    cycles, period, case, node_id = params
    with isolated_test_environment(ROOT) as environment:
        started = time.perf_counter()
        process = subprocess.run(
            [sys.executable, "-m", "pytest", f"tests/test_CAdd.py::{node_id}", "-q"],
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
        raise RuntimeError(f"CAdd RTL test {case} failed: {process.stdout.strip()}")
    return {
        "sim_latency_cycles": cycles,
        "physical_latency_ns": cycles * period,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case,
        "test_source": str(TEST_FILE),
        "measurement_method": "tests/test_CAdd.py complex-lane RTL scoreboard",
    }
