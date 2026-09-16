# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Pytest verification for Neg

import itertools
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pytv.ModuleLoader import moduleloader

import PyTB
import PyTU
from BehavModel_Neg import (
    ModuleNegCppConfig as ModuleCppConfig,
    ModuleNegCppRun as ModuleCppRun,
)
from tb_Neg import ModuleTbNeg


TEST_DIR = Path(__file__).resolve().parent
SIM_DIR = TEST_DIR / "sim"


class Testcase:
    __test__ = False
    DUT_NAME = "Neg"
    CPP_CONFIG_FILE_NAME_PREFIX = "NegCppConfig"
    CPP_RUN_FILE_NAME_PREFIX = "NegCppRun"
    CPP_CONFIG_FILE_NAME_DEST = "config.h"
    CPP_RUN_FILE_NAME_DEST = "Neg.cpp"

    def __init__(self, case_id, qu_type_in, qu_type_out, qu_mode, of_mode, if_rst_n, n_clk, n_frames=32):
        self.CASE_ID = case_id
        self.QU_IN = qu_type_in
        self.QU_OUT = qu_type_out
        self.QU_MODE = qu_mode
        self.OF_MODE = of_mode
        self.IF_RST_N = if_rst_n
        self.N_CLK = n_clk
        self.N_FRAMES = n_frames

    def display_info(self):
        return (
            f"CASE_ID: {self.CASE_ID}\n"
            f"QU_IN({self.QU_IN.DWT}, {self.QU_IN.FRAC}, {self.QU_IN.IF_SIGNED})\n"
            f"QU_OUT({self.QU_OUT.DWT}, {self.QU_OUT.FRAC}, {self.QU_OUT.IF_SIGNED})\n"
            f"QU_MODE: {self.QU_MODE.cppType()}    OF_MODE: {self.OF_MODE.cppType()}\n"
            f"IF_RST_N: {self.IF_RST_N}    N_CLK: {self.N_CLK}\n"
        )


def generate_testcases():
    return [
        Testcase(
            "signed_same_wrap",
            PyTU.QuType(8, 4, True),
            PyTU.QuType(8, 4, True),
            PyTU.QuMode.TRN.TCPL,
            PyTU.OfMode.WRP.TCPL,
            False,
            0,
        ),
        Testcase(
            "signed_guard_wide",
            PyTU.QuType(8, 4, True),
            PyTU.QuType(9, 4, True),
            PyTU.QuMode.RND.CONV,
            PyTU.OfMode.SAT.TCPL,
            True,
            2,
        ),
        Testcase(
            "signed_narrow_sat",
            PyTU.QuType(8, 4, True),
            PyTU.QuType(5, 2, True),
            PyTU.QuMode.RND.POS_INF,
            PyTU.OfMode.SAT.TCPL,
            False,
            1,
        ),
        Testcase(
            "signed_to_nonnegative",
            PyTU.QuType(7, 3, True),
            PyTU.QuType(6, 2, False),
            PyTU.QuMode.RND.ZERO,
            PyTU.OfMode.SAT.ZERO,
            True,
            1,
        ),
        Testcase(
            "nonnegative_to_signed_wide",
            PyTU.QuType(8, 3, False),
            PyTU.QuType(9, 3, True),
            PyTU.QuMode.TRN.TCPL,
            PyTU.OfMode.WRP.TCPL,
            False,
            0,
        ),
        Testcase(
            "nonnegative_to_nonnegative_wrap",
            PyTU.QuType(8, 2, False),
            PyTU.QuType(8, 2, False),
            PyTU.QuMode.RND.INF,
            PyTU.OfMode.WRP.TCPL,
            True,
            1,
        ),
        Testcase(
            "nonnegative_to_nonnegative_sat_tcpl",
            PyTU.QuType(7, 2, False),
            PyTU.QuType(7, 2, False),
            PyTU.QuMode.RND.ZERO,
            PyTU.OfMode.SAT.TCPL,
            False,
            0,
        ),
        Testcase(
            "nonnegative_to_nonnegative_sat_smgn",
            PyTU.QuType(7, 2, False),
            PyTU.QuType(6, 1, False),
            PyTU.QuMode.RND.NEG_INF,
            PyTU.OfMode.SAT.SMGN,
            True,
            1,
        ),
        Testcase(
            "negative_fraction_position",
            PyTU.QuType(6, -2, True),
            PyTU.QuType(7, -1, True),
            PyTU.QuMode.TRN.SMGN,
            PyTU.OfMode.SAT.SMGN,
            False,
            2,
        ),
        Testcase(
            "fraction_only",
            PyTU.QuType(5, 7, True),
            PyTU.QuType(6, 6, True),
            PyTU.QuMode.RND.NEG_INF,
            PyTU.OfMode.WRP.TCPL,
            False,
            0,
        ),
        Testcase(
            "convergent_nonnegative_output",
            PyTU.QuType(9, 5, True),
            PyTU.QuType(4, 2, False),
            PyTU.QuMode.RND.CONV,
            PyTU.OfMode.SAT.ZERO,
            True,
            2,
        ),
    ]


TESTCASES = generate_testcases()


@pytest.mark.parametrize("case", TESTCASES, ids=lambda case: case.CASE_ID)
def test_neg(case: Testcase):
    input_dir = SIM_DIR / "Input_Files"
    comparison_dir = SIM_DIR / "Comparison_Files"
    output_dir = SIM_DIR / "Output_Files"
    log_dir = SIM_DIR / "Log_Files"
    cpp_dir = SIM_DIR / "CppModules"
    cpp_include_dir = cpp_dir / "include"
    rtl_dir = SIM_DIR / "RTL" / case.CASE_ID

    for directory in (input_dir, comparison_dir, output_dir, log_dir, cpp_dir, cpp_include_dir):
        directory.mkdir(parents=True, exist_ok=True)

    shutil.rmtree(rtl_dir, ignore_errors=True)
    rtl_dir.mkdir(parents=True)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")

    ModuleTbNeg(
        QU_IN=case.QU_IN,
        QU_OUT=case.QU_OUT,
        N_CLK=case.N_CLK,
        IF_RST_N=case.IF_RST_N,
        QU_MODE=case.QU_MODE,
        OF_MODE=case.OF_MODE,
        N_FRAMES=case.N_FRAMES,
    )
    moduleloader.reset()

    moduleloader.set_root_dir(str(cpp_include_dir))
    moduleloader.set_language_mode("CPP_HEADER")
    ModuleCppConfig(
        QU_IN=case.QU_IN,
        QU_OUT=case.QU_OUT,
        QU_MODE=case.QU_MODE,
        OF_MODE=case.OF_MODE,
    )

    moduleloader.set_root_dir(str(cpp_dir))
    moduleloader.set_language_mode("CPP")
    ModuleCppRun(
        N_FRAMES=case.N_FRAMES,
        DWT_IN=case.QU_IN.DWT,
        FRAC_IN=case.QU_IN.FRAC,
        IF_SIGNED_IN=case.QU_IN.IF_SIGNED,
    )

    generated_config = list(moduleloader.getParams(case.CPP_CONFIG_FILE_NAME_PREFIX)[-1].keys())[-1] + ".h"
    generated_runner = list(moduleloader.getParams(case.CPP_RUN_FILE_NAME_PREFIX)[-1].keys())[-1] + ".cpp"
    os.replace(cpp_include_dir / generated_config, cpp_include_dir / case.CPP_CONFIG_FILE_NAME_DEST)
    os.replace(cpp_dir / generated_runner, cpp_dir / case.CPP_RUN_FILE_NAME_DEST)
    moduleloader.reset()

    run_subprocess(
        [
            "clang++",
            case.CPP_RUN_FILE_NAME_DEST,
            "-std=c++23",
            "-Iinclude",
            "-o",
            "fxp2.out",
        ],
        cwd=cpp_dir,
    )
    run_subprocess(["./fxp2.out"], cwd=cpp_dir)

    verilog_files = sorted(str(path.name) for path in rtl_dir.glob("*.v"))
    assert verilog_files, f"No Verilog files were generated in {rtl_dir}"
    run_subprocess(["iverilog", "-o", "wave", *verilog_files], cwd=rtl_dir)
    run_subprocess(["vvp", "-n", "wave", "-lxt2"], cwd=rtl_dir)

    inputs = (input_dir / "neg_i_data.txt").read_text(encoding="utf-8").splitlines()
    expected = (comparison_dir / "neg_o_data.txt").read_text(encoding="utf-8").splitlines()
    actual = (output_dir / "neg_o_data.txt").read_text(encoding="utf-8").splitlines()

    error_record = compare_streams(
        inputs=inputs,
        expected=expected,
        actual=actual,
        input_is_signed=case.QU_IN.IF_SIGNED,
        output_is_signed=case.QU_OUT.IF_SIGNED,
    )

    if error_record:
        PyTB.Log.write_error_info(case, str(log_dir), error_record)

    assert not error_record, "".join(error_record)


def compare_streams(inputs, expected, actual, input_is_signed, output_is_signed):
    errors = []
    if len(inputs) != len(expected) or len(expected) != len(actual):
        errors.append(
            "Stream length mismatch: "
            f"input={len(inputs)}, expected={len(expected)}, actual={len(actual)}\n"
        )

    for line_number, (input_bits, expected_bits, actual_bits) in enumerate(
        itertools.zip_longest(inputs, expected, actual),
        start=1,
    ):
        if expected_bits == actual_bits and None not in (input_bits, expected_bits, actual_bits):
            continue

        input_value = decode_bits(input_bits, input_is_signed)
        expected_value = decode_bits(expected_bits, output_is_signed)
        actual_value = decode_bits(actual_bits, output_is_signed)
        errors.append(
            f"line {line_number}: "
            f"input={input_bits} (d{input_value}), "
            f"expected={expected_bits} (d{expected_value}), "
            f"actual={actual_bits} (d{actual_value})\n"
        )

    return errors


def decode_bits(bits, is_signed):
    if bits is None:
        return "missing"
    value, _ = PyTB.binary_complement_to_decimal(bits, is_signed=is_signed)
    return value


def run_subprocess(command, cwd):
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        command_text = " ".join(command)
        pytest.fail(
            f"Command failed in {cwd}: {command_text}\n"
            f"stdout:\n{error.stdout}\n"
            f"stderr:\n{error.stderr}"
        )
