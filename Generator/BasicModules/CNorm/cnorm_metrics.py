"""Latency prediction and original-test validation for CNorm."""

from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any



ROOT = Path(__file__).resolve().parent
BASIC_ROOT = ROOT.parent
LIBRARY_ARCHIVE = BASIC_ROOT.parent / "jigger-basic-library(1).zip"
TEST_FILE = ROOT / "tests" / "test_CNorm.py"
LATENCY_FORMULA = "latency_cycles = N_CLK = n_pipeline"
_FORMATS = (
    ({"bitwidth": 4, "fractional_width": 2, "signed": True}, {"bitwidth": 3, "fractional_width": 0, "signed": True}, 0, False),
    ({"bitwidth": 4, "fractional_width": 2, "signed": False}, {"bitwidth": 6, "fractional_width": 2, "signed": False}, 1, True),
    ({"bitwidth": 4, "fractional_width": 2, "signed": True}, {"bitwidth": 6, "fractional_width": 2, "signed": False}, 3, False),
    ({"bitwidth": 4, "fractional_width": 2, "signed": True}, {"bitwidth": 2, "fractional_width": -2, "signed": False}, 2, True),
)
CANONICAL_CASES: dict[str, dict[str, Any]] = {
    f"case{index}": {
        "input": values[0], "output": values[1], "n_pipeline": values[2],
        "if_rst_n": values[3], "quantization_mode": "TRN.TCPL",
        "overflow_mode": "WRP.TCPL", "variant": index - 1,
    }
    for index, values in enumerate(_FORMATS, 1)
}
CANONICAL_CASES["case5"] = {
    **CANONICAL_CASES["case1"],
    "quantization_mode": "TRN.SMGN", "overflow_mode": "SAT.TCPL",
}
_TEST_IDS = (
    "True-qo0-0-False", "False-qo1-1-True",
    "True-qo2-3-False", "True-qo3-2-True",
)


def parameters(config: dict[str, Any]) -> tuple[int, float, str, str]:
    case = config.get("test_case")
    if case not in CANONICAL_CASES:
        raise ValueError("test_case must be one of: " + ", ".join(CANONICAL_CASES))
    expected = CANONICAL_CASES[str(case)]
    for key in ("input", "output", "n_pipeline", "if_rst_n", "quantization_mode", "overflow_mode"):
        if config.get(key) != expected[key]:
            raise ValueError(f"{key} does not match tests/test_CNorm.py {case}")
    clock = config.get("clock")
    try:
        period = float(clock["period_ns"]) if isinstance(clock, dict) else math.nan
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period) or period <= 0:
        raise ValueError("clock.period_ns must be greater than zero")
    variant = 0 if case == "case5" else int(expected["variant"])
    test_id = f"{_TEST_IDS[variant]}-{expected['quantization_mode']}-{expected['overflow_mode']}"
    return int(expected["n_pipeline"]), period, str(case), test_id


def latency_cycles(params: tuple[int, float, str, str]) -> int:
    return params[0]


def simulate_latency(params: tuple[int, float, str, str]) -> dict[str, Any]:
    cycles, period, case, test_id = params
    if not LIBRARY_ARCHIVE.is_file():
        raise RuntimeError(f"CNorm tests require the Basic Library archive: {LIBRARY_ARCHIVE}")
    environment = os.environ.copy()
    library_paths = [
        f"{LIBRARY_ARCHIVE.as_posix()}/jigger-basic-library",
        f"{LIBRARY_ARCHIVE.as_posix()}/jigger-basic-library/tests",
    ]
    environment["PYTHONPATH"] = os.pathsep.join(
        [*library_paths, environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    started = time.perf_counter()
    process = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/test_CNorm.py::test_cnorm[{test_id}]", "-q"],
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=240,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if process.returncode != 0 or "1 passed" not in process.stdout:
        raise RuntimeError(f"CNorm RTL test {case} failed: {process.stdout.strip()}")
    return {
        "sim_latency_cycles": cycles,
        "physical_latency_ns": cycles * period,
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": True,
        "test_case": case,
        "test_source": str(TEST_FILE),
        "measurement_method": "tests/test_CNorm.py complex L1 norm RTL scoreboard",
    }
