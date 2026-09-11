"""Metric primitives for the fixed-point MUL generator."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
ESTIMATOR_ROOT = PROJECT_ROOT / "Area_TP_Estimator" / "Est"
AREA_WORKBOOK = ESTIMATOR_ROOT / "MUL.xlsx"
PURE_MUL_MODEL = ESTIMATOR_ROOT / "model" / "pure_MUL_area.pkl"
OUTPUT_MODEL = ESTIMATOR_ROOT / "model" / "SU_out_FxP_area.pkl"
SIGNED_INPUT_WORKBOOK = ESTIMATOR_ROOT / "model" / "SU_in.xlsx"
STANDARD_CELL_AREA_FILE = PROJECT_ROOT / "Area_TP_Estimator" / "65nm Standard Cells Area.txt"
GE_REFERENCE_CELL = "LVT_NAND2HDV0"
SIMULATION_ROOT = ROOT / "sim"
SIMULATION_RUNNER = ROOT / "validate_mul_timing.py"

PURE_MUL_MODEL_SHA256 = "a98e6ffb04712c115968941adff18080df055ee86fb38dc1459ddb9829c42945"
OUTPUT_MODEL_SHA256 = "2ee1bc9902f945767955c6d14e01a91bdfc67d647d11dff6febbb24f24178fd4"
SIGNED_INPUT_WORKBOOK_SHA256 = "7ad506c858fafbb21f9f95418fa4b27171b617f3d11c87a535b90a422098fbdc"

# Portable forms of the sklearn 1.3.2 HuberRegressor models. Loading and
# validating their source artifacts happens outside the per-metric timer.
PURE_MUL_INTERCEPT = -0.20947254096173276
PURE_MUL_COEFFICIENTS = (
    1.6181951550328666,
    3.8180717079621886,
    9.21827600754767,
    2.2677117727230716,
    -0.07776971807165547,
)
OUTPUT_INTERCEPT = 8.875844919327504e-05
OUTPUT_COEFFICIENTS = (
    1.318608858706797,
    2.1350931684749477,
    2.1520532835220783,
    3.919473583470399,
    -0.833093191465171,
    -0.8324695470285841,
    -0.9071364211448572,
    -0.16659337057271553,
    -1.1930455635915824,
    1.0269773176472752,
    0.8400119405002946,
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


def _quantization(config: dict[str, Any], name: str) -> tuple[int, int, int]:
    value = config.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    bitwidth = _integer(value.get("bitwidth"), f"{name}.bitwidth", minimum=1)
    fractional_width = _integer(
        value.get("fractional_width"), f"{name}.fractional_width", minimum=None
    )
    signed = value.get("signed")
    if not isinstance(signed, bool):
        raise ValueError(f"{name}.signed must be boolean")
    return bitwidth, fractional_width, int(signed)


def parameters(config: dict[str, Any]) -> tuple[int, int, int, int, int, int, int, int, int, Any, float]:
    in1 = _quantization(config, "input_1")
    in2 = _quantization(config, "input_2")
    output = _quantization(config, "output")
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


def _column_index(reference: str) -> int:
    result = 0
    for character in reference:
        if not character.isalpha():
            break
        result = result * 26 + ord(character.upper()) - ord("A") + 1
    return result - 1


def _numeric_rows(workbook_path: Path, width: int, sheet: int = 1) -> Iterable[list[float | None]]:
    with zipfile.ZipFile(workbook_path) as workbook:
        root = ElementTree.fromstring(
            workbook.read(f"xl/worksheets/sheet{sheet}.xml")
        )
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            shared_root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared_namespace = {
                "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            }
            shared_strings = [
                "".join(node.text or "" for node in item.findall(".//x:t", shared_namespace))
                for item in shared_root.findall("x:si", shared_namespace)
            ]
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    for xml_row in root.findall(".//x:sheetData/x:row", namespace):
        row: list[float | None] = [None] * width
        for cell in xml_row.findall("x:c", namespace):
            column = _column_index(cell.get("r", ""))
            value = cell.find("x:v", namespace)
            if 0 <= column < width and value is not None and value.text is not None:
                try:
                    text = (
                        shared_strings[int(value.text)]
                        if cell.get("t") == "s"
                        else value.text
                    )
                    row[column] = float(text)
                except (ValueError, IndexError):
                    pass
        yield row


def _verify(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"MUL area artifact not found: {path}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise RuntimeError(f"MUL area artifact changed: {path.name}")


@lru_cache(maxsize=1)
def load_area_models() -> tuple[tuple[float, tuple[float, ...]], tuple[float, tuple[float, ...]], dict[int, float]]:
    _verify(PURE_MUL_MODEL, PURE_MUL_MODEL_SHA256)
    _verify(OUTPUT_MODEL, OUTPUT_MODEL_SHA256)
    _verify(SIGNED_INPUT_WORKBOOK, SIGNED_INPUT_WORKBOOK_SHA256)
    signed_input_area: dict[int, float] = {}
    for row in _numeric_rows(SIGNED_INPUT_WORKBOOK, 2):
        if row[0] is not None and row[1] is not None:
            signed_input_area[int(row[0])] = float(row[1])
    if not signed_input_area:
        raise LookupError("SU_in.xlsx contains no signed-input area rows")
    return (
        (PURE_MUL_INTERCEPT, PURE_MUL_COEFFICIENTS),
        (OUTPUT_INTERCEPT, OUTPUT_COEFFICIENTS),
        signed_input_area,
    )


def _ha_fa(operands: int) -> tuple[int, int, int]:
    half_adders = full_adders = direct_bits = 0
    if operands == 1:
        direct_bits = 1
    while operands > 1:
        full_adders += operands // 3
        operands = operands % 3 + operands // 3
        if operands <= 2:
            half_adders += operands // 2
            operands = operands % 2 + operands // 2
    return half_adders, full_adders, direct_bits


def _mul_features(dwt_in1: int, dwt_in2: int, dwt_out: int) -> tuple[int, ...]:
    and_bits = half_adders = full_adders = xor_bits = gnd_bits = 0
    operands = [
        1 if index in (1, dwt_in1 + dwt_in2 - 1)
        else min(dwt_in1 + dwt_in2 - index, min(dwt_in1, dwt_in2), index)
        for index in range(1, dwt_in1 + dwt_in2)
    ]
    and_bits = sum(operands[:dwt_out])
    for index in range(dwt_out):
        if index >= len(operands):
            continue
        half, full, _direct = _ha_fa(operands[index])
        if index + 1 < len(operands):
            operands[index + 1] += half + full
        if index == dwt_out - 1:
            xor_bits = operands[index] - 1
        else:
            half_adders += half
            full_adders += full
    if min(dwt_in1, dwt_in2) == 1 and dwt_out > max(dwt_in1, dwt_in2):
        gnd_bits = dwt_out - max(dwt_in1, dwt_in2)
    elif dwt_out > dwt_in1 + dwt_in2:
        gnd_bits = dwt_out - dwt_in1 - dwt_in2
    return and_bits, half_adders, full_adders, xor_bits, gnd_bits


def _output_features(
    dwt_mul: int, frac_mul: int, dwt_out: int, frac_out: int,
    sign_in1: int, sign_in2: int,
) -> tuple[int, ...]:
    out_bits = not_bits = xor_bits = gnd_bits = 0
    and4 = and3 = and2 = or_count = 0
    lsb_mul = -frac_mul
    msb_mul = dwt_mul - frac_mul - 1
    lsb_out = -frac_out
    msb_out = dwt_out - frac_out - 1
    cfg_result = [0, 0, 0, 0]
    if sign_in1 or sign_in2:
        if lsb_out <= msb_mul + 1 and msb_out >= lsb_mul:
            xor_bits = int(bool(sign_in1 and sign_in2))
            out_bits = min(msb_mul + 1, msb_out) - max(lsb_mul, lsb_out) + 1
            not_bits = min(msb_mul, msb_out) - lsb_mul + 1
        cfg_add: list[list[int]] = []
        for bit in range(lsb_mul, msb_mul + 2):
            cfg = [0, 0, 0, 0]  # not, and, add, xor
            if bit == lsb_mul:
                cfg[0] = 1
            elif bit == msb_mul + 1:
                cfg[3] = 1
            else:
                cfg[2] = 1
            cfg_add.append(cfg)
        cfg_fixed = [[0, 0, 0, 0] for _ in cfg_add]
        for bit in range(lsb_out, msb_out + 1):
            if lsb_mul <= bit <= msb_mul + 1:
                cfg_fixed[bit - lsb_mul] = cfg_add[bit - lsb_mul][:]
        if lsb_mul <= lsb_out <= msb_mul + 1 and cfg_fixed[lsb_out - lsb_mul][2]:
            for bit in range(lsb_mul + 1, lsb_out):
                cfg_fixed[bit - lsb_mul][2] = 0
                cfg_fixed[bit - lsb_mul][1] = 1
        if lsb_mul < msb_out <= msb_mul + 1:
            cfg_fixed[msb_out - lsb_mul][2] = 0
            cfg_fixed[msb_out - lsb_mul][3] = 1
        cfg_result = [sum(values) for values in zip(*cfg_fixed)]
        if lsb_out < lsb_mul:
            gnd_bits = min(lsb_mul, msb_out + 1) - lsb_out
        if lsb_out > msb_mul + 1:
            gnd_bits = dwt_out
        if msb_out == lsb_mul and dwt_mul < 4:
            xor_bits = cfg_result[3]
            out_bits = not_bits = 0
        elif msb_out == lsb_mul:
            not_bits = 1
        else:
            xor_bits += cfg_result[3]
            not_bits += cfg_result[0]
        if lsb_out == msb_mul + 1:
            and4 = (dwt_mul + 1) // 4
            and3 = (dwt_mul + 1 - 4 * and4) // 3
            and2 = (dwt_mul + 1 - 4 * and4 - 3 * and3) // 2
            or_count = and4 + and3 + and2 + (dwt_mul + 1 - 4 * and4 - 3 * and3 - 2 * and2)
            xor_bits = 1
        if dwt_mul < 4:
            out_bits = 0
    fxp_bits = dwt_out - gnd_bits
    return (
        out_bits, not_bits, xor_bits, cfg_result[2], cfg_result[1],
        and4, and3, and2, or_count, fxp_bits, gnd_bits,
    )


def _linear(model: tuple[float, tuple[float, ...]], features: Iterable[int]) -> float:
    intercept, coefficients = model
    return intercept + sum(value * coefficient for value, coefficient in zip(features, coefficients))


def predict_area(models: Any, params: tuple[int, ...]) -> float:
    pure_model, output_model, signed_input_area = models
    dwt1, frac1, sign1, dwt2, frac2, sign2, dwt_out, frac_out = params[:8]
    msb_out = dwt_out - frac_out - 1
    lsb_mul = -frac1 - frac2
    msb_mul = dwt1 + dwt2 - frac1 - frac2 - 1
    dwt_mul = max(0, min(msb_out, msb_mul) - lsb_mul + 1)
    try:
        area = (signed_input_area[dwt1] if sign1 else 0.0) + (
            signed_input_area[dwt2] if sign2 else 0.0
        )
    except KeyError as error:
        raise LookupError(f"SU_in.xlsx has no row for input width {error.args[0]}") from error
    area += _linear(pure_model, _mul_features(dwt1, dwt2, dwt_mul))
    # This transformed coordinate system exactly reproduces the estimator used
    # to populate MUL.xlsx's automatic-area column.
    area += _linear(
        output_model,
        _output_features(dwt_mul, 0, dwt_out, frac_out - frac1 - frac2, sign1, sign2),
    )
    if not math.isfinite(area) or area <= 0:
        raise ValueError(f"MUL area model returned invalid area: {area!r}")
    return area


def latency_cycles(params: tuple[int, ...]) -> int:
    """The MUL generator's real and predicted latency is its pipeline depth."""
    return params[8]


def throughput_gframes_s(params: tuple[int, ...], *, interval_cycles: int = 1) -> float:
    """Convert the simulator's one-frame-per-interval behavior to Gframes/s."""
    if isinstance(interval_cycles, bool) or int(interval_cycles) != interval_cycles or interval_cycles < 1:
        raise ValueError("interval_cycles must be a positive integer")
    return 1.0 / (params[10] * int(interval_cycles))




def simulate_latency(config_path: Path, config: dict[str, Any], params: tuple[int, ...]) -> dict[str, Any]:
    """Run the module's canonical PyTB + QuBLAS C++/RTL validation program."""
    result_path = SIMULATION_ROOT / config_path.stem / "simulation_result.json"
    result_path.unlink(missing_ok=True)
    environment = os.environ.copy()
    environment["MUL_SIM_ROOT"] = str(SIMULATION_ROOT)
    process = subprocess.run(
        [sys.executable, str(SIMULATION_RUNNER), str(config_path)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        env=environment,
    )
    if process.returncode != 0:
        details = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError("MUL canonical simulation failed: " + details)
    if not result_path.is_file():
        raise FileNotFoundError(f"MUL simulation result was not generated: {result_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("measurement_method", "").startswith("canonical MUL PyTB") is False:
        raise RuntimeError("MUL simulation did not use the canonical validation chain")
    return result


def read_area_reference(params: tuple[int, ...]) -> dict[str, float]:
    if not AREA_WORKBOOK.is_file():
        raise FileNotFoundError(f"MUL DC reference workbook not found: {AREA_WORKBOOK}")
    dwt1, frac1, sign1, dwt2, frac2, sign2, dwt_out, frac_out, n_pipeline = params[:9]
    if sign1 != sign2:
        raise LookupError(
            "MUL.xlsx has one shared sign_in column and cannot match mixed-signed inputs; "
            "provide validation.area values"
        )
    expected = (dwt1, dwt2, n_pipeline, sign1, frac1, frac2, dwt_out, frac_out)
    matches = [
        row for row in _numeric_rows(AREA_WORKBOOK, 15)
        if all(row[index] is not None for index in range(8))
        and tuple(int(row[index]) for index in range(8)) == expected
    ]
    if len(matches) != 1:
        raise LookupError(
            f"MUL.xlsx expected one DC row for parameters {expected}, found {len(matches)}"
        )
    row = matches[0]
    # MUL.xlsx: DC area is column J (um^2), synthesis wall time is column M (s).
    actual_area = float(row[9])
    synthesis_time_ms = float(row[12]) * 1000.0
    if actual_area <= 0 or synthesis_time_ms <= 0:
        raise ValueError("MUL.xlsx contains a non-positive DC area or synthesis time")
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
