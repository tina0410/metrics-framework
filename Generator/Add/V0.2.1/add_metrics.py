"""Metric primitives for the fixed-point ADD generator."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
ESTIMATOR_ROOT = PROJECT_ROOT / "Area_TP_Estimator" / "Est"
AREA_WORKBOOK = ESTIMATOR_ROOT / "ADD.xlsx"
AREA_MODEL = ESTIMATOR_ROOT / "model" / "ADD_area.pkl"
STANDARD_CELL_AREA_FILE = PROJECT_ROOT / "Area_TP_Estimator" / "65nm Standard Cells Area.txt"
GE_REFERENCE_CELL = "LVT_NAND2HDV0"
SIMULATION_ROOT = ROOT / "sim"
RTL_VALIDATOR = ROOT / "BehaviorialVerification" / "validate_add_timing.py"
AREA_MODEL_SHA256 = "73da04ec6b1ef70d8859397b1a92c9e5c6537a5b04d5297e5e9aa55b0cdefdc9"
# Portable representation of the sklearn 1.3.2 HuberRegressor in ADD_area.pkl.
AREA_MODEL_INTERCEPT = 2.015116402119283e-08
AREA_MODEL_COEFFICIENTS = (
    0.8399999890054713,
    3.9199999838292836,
    0.8971591598237119,
    3.302825494915321,
    4.048772067501846,
    0.6343857123584669,
    -4.0740408520406765e-09,
    8.119999995740566,
)


def _integer(value: Any, name: str, *, minimum: int | None = 0) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if number != value or (minimum is not None and number < minimum):
        suffix = "" if minimum is None else f" >= {minimum}"
        raise ValueError(f"{name} must be an integer{suffix}")
    return number


def _quantization(config: dict[str, Any], name: str, *, signed_required: bool) -> tuple[int, int, int]:
    value = config.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    bitwidth = _integer(value.get("bitwidth"), f"{name}.bitwidth", minimum=1)
    fractional_width = _integer(
        value.get("fractional_width"), f"{name}.fractional_width", minimum=None
    )
    signed_value = value.get("signed")
    if signed_required and not isinstance(signed_value, bool):
        raise ValueError(f"{name}.signed must be boolean")
    return bitwidth, fractional_width, int(bool(signed_value))


def parameters(config: dict[str, Any]) -> tuple[int, int, int, int, int, int, int, int, int, Any, float]:
    in1 = _quantization(config, "input_1", signed_required=True)
    in2 = _quantization(config, "input_2", signed_required=True)
    output = _quantization(config, "output", signed_required=True)
    n_pipeline = _integer(config.get("n_pipeline"), "n_pipeline", minimum=1)
    if_rst_n = config.get("if_rst_n", False)
    if not isinstance(if_rst_n, bool):
        if not isinstance(if_rst_n, list) or len(if_rst_n) != n_pipeline or not all(
            isinstance(value, bool) for value in if_rst_n
        ):
            raise ValueError("if_rst_n must be boolean or a boolean list of n_pipeline items")
    clock = config.get("clock")
    if not isinstance(clock, dict):
        raise ValueError("clock must be a JSON object")
    try:
        period_ns = float(clock.get("period_ns"))
    except (TypeError, ValueError) as error:
        raise ValueError("clock.period_ns must be numeric") from error
    if not math.isfinite(period_ns) or period_ns <= 0:
        raise ValueError("clock.period_ns must be greater than zero")
    return (*in1, *in2, output[0], output[1], n_pipeline, if_rst_n, period_ns)


@lru_cache(maxsize=1)
def load_area_model() -> tuple[float, tuple[float, ...]]:
    if not AREA_MODEL.is_file():
        raise FileNotFoundError(f"ADD area model not found: {AREA_MODEL}")
    digest = hashlib.sha256(AREA_MODEL.read_bytes()).hexdigest()
    if digest != AREA_MODEL_SHA256:
        raise RuntimeError(
            "ADD_area.pkl changed; regenerate the portable model coefficients"
        )
    return AREA_MODEL_INTERCEPT, AREA_MODEL_COEFFICIENTS


def predict_area(model: Any, params: tuple[int, int, int, int, int, int, int, int, int, Any, float]) -> float:
    if str(ESTIMATOR_ROOT) not in sys.path:
        sys.path.insert(0, str(ESTIMATOR_ROOT))
    from KeyParam import adder_config_v2

    dwt_in1, frac_in1, sign_in1, dwt_in2, frac_in2, sign_in2, dwt_out, frac_out, n_pipeline = params[:9]
    # The trained regressor models the combinational adder; register and
    # fixed-point matching areas are added exactly as in Est.Est_ADD.
    features = adder_config_v2(
        dwt_in1, frac_in1, sign_in1, dwt_in2, frac_in2, sign_in2,
        dwt_out, frac_out, 0,
    )
    intercept, coefficients = model
    area = intercept + sum(value * coefficient for value, coefficient in zip(features, coefficients))

    dwt_fix = fixed_width(params)
    area += 1.12 * dwt_fix * 2
    if isinstance(params[9], bool):
        area += (6.72 if params[9] else 5.88) * dwt_fix * n_pipeline
    else:
        area += dwt_fix * sum(6.72 if flag else 5.88 for flag in params[9])
    if not math.isfinite(area) or area <= 0:
        raise ValueError(f"ADD area model returned invalid area: {area!r}")
    return area


def fixed_width(params: tuple[int, int, int, int, int, int, int, int, int, Any, float]) -> int:
    dwt_in1, frac_in1, sign_in1, dwt_in2, frac_in2, sign_in2, dwt_out, frac_out = params[:8]
    msb_out = dwt_out - frac_out - 1
    max_msb_in = max(dwt_in1 - frac_in1 - 1, dwt_in2 - frac_in2 - 1) + 1
    if not (sign_in1 or sign_in2) and msb_out > max_msb_in:
        msb_out = max_msb_in
    lsb_out = -min(max(frac_in1, frac_in2), frac_out)
    return msb_out - lsb_out + 1


def latency_cycles(params: tuple[int, int, int, int, int, int, int, int, int, Any, float]) -> int:
    """The ADD generator's real and predicted latency is its pipeline depth."""
    return params[8]


def throughput_gframes_s(params: tuple[int, int, int, int, int, int, int, int, int, Any, float]) -> float:
    """The ADD design processes one frame per clock cycle."""
    return 1.0 / params[10]


def simulate_latency(
    config_path: Path,
    config: dict[str, Any],
    params: tuple[int, int, int, int, int, int, int, int, int, Any, float],
) -> dict[str, Any]:
    """Run the original ADD testbench/reference chain and return its measurements."""
    result_path = SIMULATION_ROOT / config_path.stem / "simulation_result.json"
    result_path.unlink(missing_ok=True)
    environment = os.environ.copy()
    environment["ADD_SIM_ROOT"] = str(SIMULATION_ROOT)
    process = subprocess.run(
        [
            sys.executable,
            str(RTL_VALIDATOR),
            "--config",
            str(config_path),
            "--case-label",
            config_path.stem,
        ],
        cwd=RTL_VALIDATOR.parent,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        env=environment,
    )
    if process.returncode != 0:
        raise RuntimeError("Original ADD RTL validation failed: " + process.stdout.strip())
    if not result_path.is_file():
        raise FileNotFoundError(f"ADD RTL timing result was not generated: {result_path}")
    return json.loads(result_path.read_text(encoding="utf-8"))


def read_area_reference(params: tuple[int, int, int, int, int, int, int, int, int, Any, float]) -> dict[str, float]:
    if not AREA_WORKBOOK.is_file():
        raise FileNotFoundError(f"ADD DC reference workbook not found: {AREA_WORKBOOK}")
    expected = params[:9]
    matches: list[list[float | None]] = []
    with zipfile.ZipFile(AREA_WORKBOOK) as workbook:
        root = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        for row in root.findall(".//x:sheetData/x:row", namespace)[1:]:
            values: list[float | None] = [None] * 14
            for cell in row.findall("x:c", namespace):
                reference = cell.get("r", "")
                letters = "".join(character for character in reference if character.isalpha())
                column = 0
                for character in letters:
                    column = column * 26 + ord(character.upper()) - ord("A") + 1
                if 1 <= column <= len(values):
                    value = cell.find("x:v", namespace)
                    if value is not None and value.text is not None:
                        values[column - 1] = float(value.text)
            if tuple(values[:9]) == expected:
                matches.append(values)
    if len(matches) != 1:
        raise LookupError(
            f"ADD.xlsx expected one DC row for parameters {expected}, found {len(matches)}"
        )
    row = matches[0]
    # The supplied workbook stores DC area at column K and synthesis time in seconds at column N.
    actual_area = float(row[10])
    synthesis_time_ms = float(row[13]) * 1000.0
    if actual_area <= 0 or synthesis_time_ms <= 0:
        raise ValueError("ADD.xlsx contains a non-positive DC area or synthesis time")
    return {"actual_area_um2": actual_area, "synthesis_time_ms": synthesis_time_ms}


@lru_cache(maxsize=1)
def read_ge_area() -> float:
    pattern = re.compile(
        rf"^Cell:\s+[^,]*/{re.escape(GE_REFERENCE_CELL)},\s*Area:\s*([0-9]+(?:\.[0-9]+)?)\s*$"
    )
    matches = [
        float(match.group(1))
        for line in STANDARD_CELL_AREA_FILE.read_text(encoding="utf-8").splitlines()
        if (match := pattern.match(line.strip()))
    ]
    if len(matches) != 1 or matches[0] <= 0:
        raise LookupError(f"Expected one positive {GE_REFERENCE_CELL} area entry")
    return matches[0]
