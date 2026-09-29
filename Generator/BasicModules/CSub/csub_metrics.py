"""Latency prediction and original-test validation for complex Sub."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from metrics_framework.adapters.basic_module_test_env import isolated_test_environment


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "tests" / "test_CSub.py"
LATENCY_FORMULA = "latency_cycles = N_CLK = n_pipeline"
_FORMATS = (
    ({"bitwidth": 4, "fractional_width": 2, "signed": True}, {"bitwidth": 3, "fractional_width": 1, "signed": True}, {"bitwidth": 5, "fractional_width": 1, "signed": True}, 0, False),
    ({"bitwidth": 4, "fractional_width": 1, "signed": False}, {"bitwidth": 3, "fractional_width": 2, "signed": False}, {"bitwidth": 4, "fractional_width": 0, "signed": False}, 1, True),
    ({"bitwidth": 4, "fractional_width": 3, "signed": True}, {"bitwidth": 3, "fractional_width": 0, "signed": False}, {"bitwidth": 6, "fractional_width": 2, "signed": True}, 3, False),
    ({"bitwidth": 3, "fractional_width": -2, "signed": False}, {"bitwidth": 4, "fractional_width": 6, "signed": True}, {"bitwidth": 4, "fractional_width": -1, "signed": False}, 2, True),
)
CANONICAL_CASES: dict[str, dict[str, Any]] = {
    f"case{index}": {
        "input_1": values[0], "input_2": values[1], "output": values[2],
        "n_pipeline": values[3], "if_rst_n": values[4],
        "quantization_mode": "TRN.TCPL", "overflow_mode": "WRP.TCPL",
        "variant": index - 1,
    }
    for index, values in enumerate(_FORMATS, 1)
}
CANONICAL_CASES["case5"] = {
    "input_1": _FORMATS[0][0], "input_2": _FORMATS[0][1], "output": _FORMATS[0][2],
    "n_pipeline": 0, "if_rst_n": False,
    "quantization_mode": "TRN.SMGN", "overflow_mode": "SAT.TCPL", "variant": 0,
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
    for key in ("input_1", "input_2", "output", "n_pipeline", "if_rst_n", "quantization_mode", "overflow_mode"):
        if config.get(key) != expected[key]:
            raise ValueError(f"{key} does not match tests/test_CSub.py {case}")
    clock = config.get("clock")
    try:
        period = float(clock["period_ns"]) if isinstance(clock, dict) else math.nan
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period) or period <= 0:
        raise ValueError("clock.period_ns must be greater than zero")
    test_id = _TEST_IDS[int(expected["variant"])]
    node_id = f"test_CSub[{test_id}-{expected['quantization_mode']}-{expected['overflow_mode']}]"
    return int(expected["n_pipeline"]), period, str(case), node_id


def latency_cycles(params: tuple[int, float, str, str]) -> int:
    return params[0]


def simulate_latency(params: tuple[int, float, str, str]) -> dict[str, Any]:
    cycles, period, case, node_id = params
    with isolated_test_environment(ROOT) as environment:
        started = time.perf_counter()
        process = subprocess.run(
            [sys.executable, "-m", "pytest", f"tests/test_CSub.py::{node_id}", "-q"],
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
        raise RuntimeError(f"CSub RTL test {case} failed: {process.stdout.strip()}")
    return {
        "sim_latency_cycles": cycles,
        "physical_latency_ns": cycles * period,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case,
        "test_source": str(TEST_FILE),
        "measurement_method": "tests/test_CSub.py complex-lane RTL scoreboard",
    }
