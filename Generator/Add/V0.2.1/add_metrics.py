"""Metric primitives for the fixed-point ADD generator."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
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
RTL_GENERATOR = ROOT / "generate_add_rtl.py"
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


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"ADD latency simulation requires {name} on PATH")
    return path


def simulate_latency(
    config_path: Path,
    config: dict[str, Any],
    params: tuple[int, int, int, int, int, int, int, int, int, Any, float],
) -> dict[str, Any]:
    """Generate the real ADD RTL, then measure its latency and interval."""
    n_pipeline = params[8]
    case_dir = SIMULATION_ROOT / config_path.stem
    case_dir.mkdir(parents=True, exist_ok=True)
    rtl_dir = case_dir / "rtl"
    rtl_dir.mkdir(parents=True, exist_ok=True)
    tb_path = case_dir / "tb_add_latency.sv"
    wave_path = case_dir / "wave"
    generator = subprocess.run(
        [sys.executable, str(RTL_GENERATOR), str(config_path), str(rtl_dir)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    if generator.returncode != 0:
        raise RuntimeError("ADD RTL generation failed: " + generator.stdout.strip())
    manifest = json.loads((rtl_dir / "rtl_manifest.json").read_text(encoding="utf-8"))
    pipelined_top = manifest["pipelined_top"]
    combinational_top = manifest["combinational_top"]
    dwt_in_1 = int(config["input_1"]["bitwidth"])
    dwt_in_2 = int(config["input_2"]["bitwidth"])
    dwt_out = int(config["output"]["bitwidth"])
    has_reset = any(params[9]) if isinstance(params[9], list) else params[9]
    reset_port = ", .i_rst_n(rst_n)" if has_reset else ""
    tb_path.write_text(
        f"""`timescale 1ns/1ps
module tb_add_latency;
  localparam integer N_PIPELINE = {n_pipeline};
  reg clk = 0;
  reg rst_n = 0;
  reg valid_i = 0;
  reg [{dwt_in_1 - 1}:0] data_i_1 = 0;
  reg [{dwt_in_2 - 1}:0] data_i_2 = 0;
  wire [{dwt_out - 1}:0] dut_o;
  wire [{dwt_out - 1}:0] reference_o;
  reg [N_PIPELINE-1:0] valid_pipe = 0;
  reg [{dwt_out - 1}:0] expected_pipe [0:N_PIPELINE-1];
  integer cycle = 0;
  integer input_cycle = -1;
  integer first_output_cycle = -1;
  integer previous_output_cycle = -1;
  integer output_count = 0;
  integer i;

  {pipelined_top} dut(
    .i_data_1(data_i_1), .i_data_2(data_i_2), .o_data(dut_o),
    .i_clk(clk){reset_port}
  );
  {combinational_top} reference_add(
    .i_data_1(data_i_1), .i_data_2(data_i_2), .o_data(reference_o)
  );
  always #5 clk = ~clk;

  always @(posedge clk) begin
    if (!rst_n) begin
      cycle = 0;
      valid_pipe <= 0;
      for (i = 0; i < N_PIPELINE; i = i + 1)
        expected_pipe[i] <= 0;
    end else begin
      cycle = cycle + 1;
      if (valid_i && input_cycle < 0)
        input_cycle = cycle;
      if (valid_pipe[N_PIPELINE-1]) begin
        if (dut_o !== expected_pipe[N_PIPELINE-1]) begin
          $display("ADD_DATA_MISMATCH expected=%0d actual=%0d", expected_pipe[N_PIPELINE-1], dut_o);
          $fatal(1);
        end
        if (first_output_cycle < 0)
          first_output_cycle = cycle;
        if (output_count == 2) begin
          $display("ADD_LATENCY cycles=%0d interval=%0d", first_output_cycle - input_cycle, cycle - previous_output_cycle);
          $finish;
        end
        previous_output_cycle = cycle;
        output_count = output_count + 1;
      end
      valid_pipe[0] <= valid_i;
      expected_pipe[0] <= reference_o;
      for (i = 1; i < N_PIPELINE; i = i + 1) begin
        valid_pipe[i] <= valid_pipe[i-1];
        expected_pipe[i] <= expected_pipe[i-1];
      end
    end
  end

  initial begin
    repeat (2) @(posedge clk);
    @(negedge clk); rst_n = 1;
    @(negedge clk); valid_i = 1; data_i_1 = 1; data_i_2 = 1;
    @(negedge clk); data_i_1 = 2; data_i_2 = 1;
    @(negedge clk); data_i_1 = 3; data_i_2 = 2;
    @(negedge clk); valid_i = 0;
    repeat ({n_pipeline + 8}) @(posedge clk);
    $fatal(1, "ADD latency simulation timed out");
  end
endmodule
""",
        encoding="utf-8",
    )
    started = time.perf_counter()
    rtl_files = [Path(path) for path in manifest["rtl_files"]]
    compile_process = subprocess.run(
        [
            _tool("iverilog"), "-g2012", "-s", "tb_add_latency",
            "-o", str(wave_path), *(str(path) for path in rtl_files), str(tb_path),
        ],
        cwd=case_dir,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    if compile_process.returncode != 0:
        raise RuntimeError("ADD RTL compilation failed: " + compile_process.stdout.strip())
    simulation = subprocess.run(
        [_tool("vvp"), "-n", str(wave_path)],
        cwd=case_dir,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if simulation.returncode != 0:
        raise RuntimeError("ADD RTL simulation failed: " + simulation.stdout.strip())
    match = re.search(r"ADD_LATENCY cycles=(\d+) interval=(\d+)", simulation.stdout)
    if match is None:
        raise RuntimeError("ADD RTL simulation did not report latency")
    result = {
        "sim_latency_cycles": int(match.group(1)),
        "sim_output_interval_cycles": int(match.group(2)),
        "rtl_simulation_time_ms": elapsed_ms,
        "functional_match": "ADD_DATA_MISMATCH" not in simulation.stdout,
        "console_log": simulation.stdout,
        "pipelined_top": pipelined_top,
        "combinational_top": combinational_top,
        "rtl_files": [str(path) for path in rtl_files],
    }
    (case_dir / "simulation_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


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
