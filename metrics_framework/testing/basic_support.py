"""Small shared RTL-test runner for BasicModules' test suites."""

from __future__ import annotations

import inspect
import re
import subprocess
from pathlib import Path

from pytv.ModuleLoader import moduleloader


def decode(bits, qu):
    bits &= (1 << qu.DWT) - 1
    return bits - (1 << qu.DWT) if qu.IF_SIGNED and bits & (1 << (qu.DWT - 1)) else bits


def convert_int(value, frac, out, rounding, overflow):
    shift = frac - out.FRAC
    mode = str(rounding)
    if shift <= 0:
        value <<= -shift
    else:
        divisor = 1 << shift
        lower, remainder = divmod(value, divisor)
        if mode == "TRN.TCPL":
            value = lower
        elif mode == "TRN.SMGN":
            value = lower + int(value < 0 and remainder != 0)
        else:
            twice = remainder * 2
            up = twice > divisor
            if twice == divisor:
                up = {
                    "RND.POS_INF": True,
                    "RND.NEG_INF": False,
                    "RND.ZERO": value < 0,
                    "RND.INF": value >= 0,
                    "RND.CONV": bool(lower & 1),
                }[mode]
            value = lower + int(up)
    high = (1 << (out.DWT - int(out.IF_SIGNED))) - 1
    low = -(1 << (out.DWT - 1)) if out.IF_SIGNED else 0
    policy = str(overflow)
    if policy == "SAT.SMGN" and out.IF_SIGNED:
        low = -high
    if policy == "SAT.ZERO":
        value = value if low <= value <= high else 0
    elif policy != "WRP.TCPL":
        value = min(high, max(low, value))
    return value & ((1 << out.DWT) - 1)


def pack(real, imag, width):
    mask = (1 << width) - 1
    return (real & mask) | ((imag & mask) << width)


def unpack(bits, qu):
    return decode(bits, qu), decode(bits >> qu.DWT, qu)


def generate(dut, params, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(directory))
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    dut(**params)
    prefix = inspect.getclosurevars(dut).nonlocals["func"].__name__[6:]
    paths = list(directory.glob(prefix + "*.v"))
    if len(paths) != 1:
        raise AssertionError(f"expected one generated {prefix} RTL file, got {paths}")
    return re.search(r"\bmodule\s+(\w+)", paths[0].read_text(encoding="utf-8")).group(1)


def simulate(directory, testbench):
    directory = Path(directory)
    (directory / "tb.v").write_text(testbench, encoding="utf-8")
    sources = sorted(str(path) for path in directory.glob("*.v"))
    commands = (
        ["iverilog", "-g2012", "-s", "tb", "-o", str(directory / "wave"), *sources],
        ["vvp", str(directory / "wave")],
    )
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
    if "PASS" not in result.stdout:
        raise AssertionError(result.stdout)


def datapath_tb(top, widths, output_width, vectors, latency=0, reset=False):
    lines = ["module tb;", "reg i_clk=0; reg i_rst_n=1;"]
    lines += [f"reg [{width - 1}:0] {name}=0;" for name, width in widths.items()]
    lines += [f"wire [{output_width - 1}:0] o_data;"]
    ports = [f".{name}({name})" for name in widths] + [".o_data(o_data)"]
    if latency:
        ports.append(".i_clk(i_clk)")
        if reset:
            ports.append(".i_rst_n(i_rst_n)")
    lines += [top + " dut(" + ",".join(ports) + ");", "initial begin"]
    queue = [None] * latency
    vectors = list(vectors)
    vectors += [vectors[-1]] * latency
    for index, (inputs, expected) in enumerate(vectors):
        if latency and reset and index in (0, len(vectors) // 2):
            lines += [
                '#2; i_rst_n=0; #1; if (o_data !== 0) $fatal(1, "async reset"); i_rst_n=1;'
            ]
            queue = [0] * latency
        lines += [f"{name}={widths[name]}'h{value:x};" for name, value in inputs.items()]
        if latency:
            queue.append(expected)
            queue.pop(0)
            expected = queue[0]
            lines += ["#5; i_clk=1; #1;"]
        else:
            lines += ["#1;"]
        if expected is not None:
            lines += [
                f'if (o_data !== {output_width}\'h{expected:x}) '
                f'$fatal(1, "vector {index}: got %h expected {expected:x}", o_data);'
            ]
        if latency:
            lines += ["i_clk=0; #1;"]
    lines += ["$display(\"PASS\"); $finish;", "end", "endmodule"]
    return "\n".join(lines)


def check_datapath(dut, params, widths, output_width, vectors, tmp_path):
    top = generate(dut, params, tmp_path)
    simulate(
        tmp_path,
        datapath_tb(
            top,
            widths,
            output_width,
            vectors,
            params.get("N_CLK", 0),
            params.get("IF_RST_N", False),
        ),
    )
