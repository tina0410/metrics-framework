# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Pytest verification for Comp

import itertools
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pytv.ModuleLoader import moduleloader

import PyTB
import PyTU
from BehavModel_Comp import ModuleCppConfigComp, ModuleCppRunComp
from tb_Comp import ModuleTbComp


TEST_DIR = Path(__file__).resolve().parent
SIM_DIR = TEST_DIR / "sim"


class Testcase:
    __test__ = False
    DUT_NAME = "Comp"
    CPP_CONFIG_FILE_NAME_PREFIX = "CppConfigComp"
    CPP_RUN_FILE_NAME_PREFIX = "CppRunComp"
    CPP_CONFIG_FILE_NAME_DEST = "config.h"
    CPP_RUN_FILE_NAME_DEST = f"{DUT_NAME}.cpp"

    def __init__(self, qu_type_in_1: PyTU.QuType, qu_type_in_2: PyTU.QuType,
                 qu_type_out_1: PyTU.QuType, qu_mode, of_mode, if_rst_n,
                 n_clk, n_frames, if_gpos, if_spos, if_epos, if_gval, if_sval):
        self.QU_IN_1 = qu_type_in_1
        self.QU_IN_2 = qu_type_in_2
        self.QU_OUT = qu_type_out_1
        self.IF_RST_N = if_rst_n
        self.N_CLK = n_clk
        self.N_FRAMES = n_frames
        self.QU_MODE = qu_mode
        self.OF_MODE = of_mode
        self.IF_GPOS = if_gpos
        self.IF_SPOS = if_spos
        self.IF_EPOS = if_epos
        self.IF_GVAL = if_gval
        self.IF_SVAL = if_sval

    def display_info(self):
        return (
            f"IF_GPOS: {self.IF_GPOS}   IF_SPOS: {self.IF_SPOS}   "
            f"IF_EPOS: {self.IF_EPOS}   IF_GVAL: {self.IF_GVAL}   IF_SVAL: {self.IF_SVAL}\n"
            f"QU_IN_1({self.QU_IN_1.DWT}, {self.QU_IN_1.FRAC}, {self.QU_IN_1.isSigned()})\n"
            f"QU_IN_2({self.QU_IN_2.DWT}, {self.QU_IN_2.FRAC}, {self.QU_IN_2.isSigned()})\n"
            f"QU_OUT({self.QU_OUT.DWT}, {self.QU_OUT.FRAC}, {self.QU_OUT.isSigned()})\n"
            f"QU_MODE: {self.QU_MODE.cppType()}    OF_MODE: {self.OF_MODE.cppType()}\n"
            f"IF_RST_N: {self.IF_RST_N}    N_CLK: {self.N_CLK}\n"
        )


def generate_testcases():
    generator = PyTB.TestcaseGenerator(
        if_rst_n=[[False, False, True, False]],
        if_gpos=[True],
        if_spos=[True],
        if_epos=[True],
        if_gval=[True],
        if_sval=[True],
        dwt_in_1=[7, 8],
        dwt_in_2=[5, 6],
        dwt_out_1=[4, 8],
        frac_in_1=[4],
        frac_in_2=[7],
        frac_out_1=[3],
        if_signed_in_1=[True],
        if_signed_in_2=[True],
        if_signed_out_1=[True],
        qu_mode=[PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF,
                 PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF,
                 PyTU.QuMode.RND.INF],
        of_mode=[PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL,
                 PyTU.OfMode.SAT.SMGN],
        n_frames=[100],
        n_clk=[4],
    )
    return generator.generate_testcases(Testcase)


TESTCASES = generate_testcases()


@pytest.mark.parametrize("case", TESTCASES)
def test_comp(case: Testcase):
    input_dir = SIM_DIR / "Input_Files"
    comparison_dir = SIM_DIR / "Comparison_Files"
    output_dir = SIM_DIR / "Output_Files"
    log_dir = SIM_DIR / "Log_Files"
    cpp_dir = SIM_DIR / "CppModules"
    cpp_include_dir = cpp_dir / "include"
    rtl_dir = SIM_DIR / "RTL" / str(id(case))

    for directory in (input_dir, comparison_dir, output_dir, log_dir, cpp_dir, cpp_include_dir):
        directory.mkdir(parents=True, exist_ok=True)

    shutil.rmtree(rtl_dir, ignore_errors=True)
    rtl_dir.mkdir(parents=True)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")

    ModuleTbComp(
        QU_IN_1=case.QU_IN_1,
        QU_IN_2=case.QU_IN_2,
        QU_OUT=case.QU_OUT,
        N_CLK=case.N_CLK,
        IF_RST_N=case.IF_RST_N,
        QU_MODE=case.QU_MODE,
        OF_MODE=case.OF_MODE,
        N_FRAMES=case.N_FRAMES,
        IF_GIDX=case.IF_GPOS,
        IF_LIDX=case.IF_SPOS,
        IF_EIDX=case.IF_EPOS,
        IF_GVAL=case.IF_GVAL,
        IF_LVAL=case.IF_SVAL,
    )
    moduleloader.reset()

    moduleloader.set_root_dir(str(cpp_include_dir))
    moduleloader.set_language_mode("CPP_HEADER")
    ModuleCppConfigComp(
        QU_IN_1=case.QU_IN_1, QU_IN_2=case.QU_IN_2,
        QU_OUT=case.QU_OUT, QU_MODE=case.QU_MODE, OF_MODE=case.OF_MODE,
    )

    moduleloader.set_root_dir(str(cpp_dir))
    moduleloader.set_language_mode("CPP")
    ModuleCppRunComp(N_FRAMES=case.N_FRAMES)

    generated_config = (
        list(moduleloader.getParams(case.CPP_CONFIG_FILE_NAME_PREFIX)[-1].keys())[-1] + ".h"
    )
    generated_runner = (
        list(moduleloader.getParams(case.CPP_RUN_FILE_NAME_PREFIX)[-1].keys())[-1] + ".cpp"
    )
    os.replace(cpp_include_dir / generated_config, cpp_include_dir / case.CPP_CONFIG_FILE_NAME_DEST)
    os.replace(cpp_dir / generated_runner, cpp_dir / case.CPP_RUN_FILE_NAME_DEST)
    moduleloader.reset()

    run_subprocess(
        ["clang++", case.CPP_RUN_FILE_NAME_DEST, "-std=c++23", "-Iinclude", "-o", "fxp2.out"],
        cwd=cpp_dir,
    )
    run_subprocess(["./fxp2.out"], cwd=cpp_dir)

    verilog_files = sorted(p.name for p in rtl_dir.glob("*.v"))
    assert verilog_files, f"No Verilog files generated in {rtl_dir}"
    run_subprocess(["iverilog", "-o", "wave", *verilog_files], cwd=rtl_dir)
    run_subprocess(["vvp", "-n", "wave", "-lxt2"], cwd=rtl_dir)

    # Comparison
    in1_path = input_dir / "Comp_i_data_1.txt"
    in2_path = input_dir / "Comp_i_data_2.txt"
    expected_gidx = comparison_dir / "Comp_o_gidx.txt"
    expected_lidx = comparison_dir / "Comp_o_lidx.txt"
    expected_eidx = comparison_dir / "Comp_o_eidx.txt"
    expected_gval = comparison_dir / "Comp_o_gval.txt"
    expected_lval = comparison_dir / "Comp_o_lval.txt"
    actual_gidx = output_dir / "Comp_o_gidx.txt"
    actual_lidx = output_dir / "Comp_o_lidx.txt"
    actual_eidx = output_dir / "Comp_o_eidx.txt"
    actual_gval = output_dir / "Comp_o_gval.txt"
    actual_lval = output_dir / "Comp_o_lval.txt"

    inputs1 = in1_path.read_text(encoding="utf-8").splitlines()
    inputs2 = in2_path.read_text(encoding="utf-8").splitlines()
    exp_gidx = expected_gidx.read_text(encoding="utf-8").splitlines()
    exp_lidx = expected_lidx.read_text(encoding="utf-8").splitlines()
    exp_eidx = expected_eidx.read_text(encoding="utf-8").splitlines()
    exp_gval = expected_gval.read_text(encoding="utf-8").splitlines()
    exp_lval = expected_lval.read_text(encoding="utf-8").splitlines()
    act_gidx = actual_gidx.read_text(encoding="utf-8").splitlines()
    act_lidx = actual_lidx.read_text(encoding="utf-8").splitlines()
    act_eidx = actual_eidx.read_text(encoding="utf-8").splitlines()
    act_gval = actual_gval.read_text(encoding="utf-8").splitlines()
    act_lval = actual_lval.read_text(encoding="utf-8").splitlines()

    error_record = []
    for line_number, (i1, i2, eg, el, ee, egv, elv, ag, al, ae, agv, alv) in enumerate(
        itertools.zip_longest(
            inputs1, inputs2,
            exp_gidx, exp_lidx, exp_eidx, exp_gval, exp_lval,
            act_gidx, act_lidx, act_eidx, act_gval, act_lval,
        ), start=1,
    ):
        mismatches = []
        if eg is not None and ag is not None and eg.strip() != ag.strip():
            mismatches.append(f"gidx: exp={eg.strip()} act={ag.strip()}")
        if el is not None and al is not None and el.strip() != al.strip():
            mismatches.append(f"lidx: exp={el.strip()} act={al.strip()}")
        if ee is not None and ae is not None and ee.strip() != ae.strip():
            mismatches.append(f"eidx: exp={ee.strip()} act={ae.strip()}")
        if egv is not None and agv is not None and egv.strip() != agv.strip():
            mismatches.append(f"gval: exp={egv.strip()} act={agv.strip()}")
        if elv is not None and alv is not None and elv.strip() != alv.strip():
            mismatches.append(f"lval: exp={elv.strip()} act={alv.strip()}")
        if mismatches:
            d0 = decode_bits(i1, case.QU_IN_1.IF_SIGNED)
            d1 = decode_bits(i2, case.QU_IN_2.IF_SIGNED)
            error_record.append(
                f"line {line_number}: in1={i1}(d{d0}), in2={i2}(d{d1}), "
                + ", ".join(mismatches) + "\n"
            )

    if error_record:
        PyTB.Log.write_error_info(case, str(log_dir), error_record)

    assert not error_record, (
        f"{case.display_info()}\n" + "".join(error_record)
    )


def decode_bits(bits, is_signed):
    if bits is None:
        return "missing"
    value, _ = PyTB.binary_complement_to_decimal(bits.strip(), is_signed=is_signed)
    return value


def run_subprocess(command, cwd):
    try:
        return subprocess.run(
            command, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=True,
        )
    except subprocess.CalledProcessError as error:
        command_text = " ".join(str(c) for c in command)
        pytest.fail(
            f"Command failed in {cwd}: {command_text}\n"
            f"stdout:\n{error.stdout}\nstderr:\n{error.stderr}"
        )
