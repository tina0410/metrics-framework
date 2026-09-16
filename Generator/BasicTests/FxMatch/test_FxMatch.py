# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Pytest verification for FxMatch

import itertools
import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest
from pytv.ModuleLoader import moduleloader

import PyTB
import PyTU
from BehavModel_FxMatch import (
    ModuleFxMatchCppConfig as ModuleCppConfig,
    ModuleFxMatchCppRun as ModuleCppRun,
)
from tb_FxMatch import ModuleTbFxMatch


TEST_DIR = Path(__file__).resolve().parent
SIM_DIR = TEST_DIR / "sim"


class Testcase:
    __test__ = False
    DUT_NAME = "FxMatch"
    TB_NAME_PREFIX = f"Tb{DUT_NAME}"
    CPP_CONFIG_FILE_NAME_PREFIX = "FxMatchCppConfig"
    CPP_RUN_FILE_NAME_PREFIX = "FxMatchCppRun"
    CPP_CONFIG_FILE_NAME_DEST = "config.h"
    CPP_RUN_FILE_NAME_DEST = f"{DUT_NAME}.cpp"

    def __init__(self, qu_type_in_1: PyTU.QuType, qu_type_out_1: PyTU.QuType,
                 qu_mode, of_mode, if_rst_n, n_clk, n_frames):
        self.QU_IN = qu_type_in_1
        self.QU_OUT = qu_type_out_1
        self.IF_RST_N = if_rst_n
        self.N_CLK = n_clk
        self.N_FRAMES = n_frames
        self.QU_MODE = qu_mode
        self.OF_MODE = of_mode

    def display_info(self):
        return (
            f"QU_IN({self.QU_IN.DWT}, {self.QU_IN.FRAC}, {self.QU_IN.isSigned()})\n"
            f"QU_OUT({self.QU_OUT.DWT}, {self.QU_OUT.FRAC}, {self.QU_OUT.isSigned()})\n"
            f"QU_MODE: {self.QU_MODE.cppType()}    OF_MODE: {self.OF_MODE.cppType()}\n"
            f"IF_RST_N: {self.IF_RST_N}    N_CLK: {self.N_CLK}\n"
        )


def generate_testcase_specific_value_case1(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [5],
        dwt_out_1 = [5],
        frac_in_1 = [9],
        frac_out_1 = [2,3,4],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case1(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_in_1 = [random.randint(2, 15)]
    dwt_out_1 = [random.randint(2, 15)]
    frac_in_1 = [random.randint(-15, -1)]
    frac_out_1 = [fi - di for fi in frac_in_1 for di in dwt_in_1] + [fi - di-random.randint(2, 15) for fi in frac_in_1 for di in dwt_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case2(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [5],
        dwt_out_1 = [3],
        frac_in_1 = [1,3],
        frac_out_1 = [6],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case2(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_in_1 = [random.randint(2, 15)]
    dwt_out_1 = [random.randint(2, 15)]
    frac_out_1 = [random.randint(-15, -1)]
    frac_in_1 = [fo - do for fo in frac_out_1 for do in dwt_out_1] + [fo - do-random.randint(2, 15) for fo in frac_out_1 for do in dwt_out_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case3(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [2],
        dwt_out_1 = [2],
        frac_in_1 = [5],
        frac_out_1 = [4],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case3(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_in_1 = [random.randint(1, 15)]
    frac_out_1 = [fi - 1 for fi in frac_in_1]
    dwt_in_1 = [fi - fo + 2 for fi in frac_in_1 for fo in frac_out_1]
    dwt_out_1 = [fo - fi + di + 3 for fi in frac_in_1 for fo in frac_out_1 for di in dwt_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case4(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [6],
        dwt_out_1 = [5],
        frac_in_1 = [5],
        frac_out_1 = [4],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase


def generate_testcase_random_value_case4(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_out_1 = [random.randint(2, 15)]
    frac_in_1 = [random.randint(-15, -1)]
    frac_out_1 = [fi - 1 for fi in frac_in_1]
    dwt_in_1 = [do- fo + fi for fi in frac_in_1 for fo in frac_out_1 for do in dwt_out_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case5(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [7],
        dwt_out_1 = [5],
        frac_in_1 = [5],
        frac_out_1 = [4],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case5(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_out_1 = [random.randint(2, 10)]
    frac_in_1 = [random.randint(-10, -1)]
    frac_out_1 = [fi - 1 for fi in frac_in_1]
    dwt_in_1 = [do- fo + fi + 1 for fi in frac_in_1 for fo in frac_out_1 for do in dwt_out_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase


def generate_testcase_specific_value_case6(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [10],
        dwt_out_1 = [10],
        frac_in_1 = [5],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case6(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_out_1 = [random.randint(2, 10)]
    frac_in_1 = [random.randint(-10, -1)]
    frac_out_1 = frac_in_1
    dwt_in_1 = dwt_out_1
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case7(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [5],
        dwt_out_1 = [6],
        frac_in_1 = [5],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case7(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_in_1 = [random.randint(2, 10)]
    frac_in_1 = [random.randint(-10, -1)]
    frac_out_1 = frac_in_1
    dwt_out_1 = [di + 1 for di in dwt_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case8(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [6],
        dwt_out_1 = [5],
        frac_in_1 = [5],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case8(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_out_1 = [random.randint(2, 10)]
    frac_in_1 = [random.randint(-10, -1)]
    frac_out_1 = frac_in_1
    dwt_in_1 = [do + 2 for do in dwt_out_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase


def generate_testcase_specific_value_case9(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [3],
        dwt_out_1 = [3],
        frac_in_1 = [4],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case9(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(1, 10)]
    frac_in_1 = [fo - 2 for fo in frac_out_1]
    dwt_out_1 = [fo - fi + 1 for fo in frac_out_1 for fi in frac_in_1]
    dwt_in_1 = [do +fi-fo+2 for do in dwt_out_1 for fo in frac_out_1 for fi in frac_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case10(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [5],
        dwt_out_1 = [7],
        frac_in_1 = [3],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case10(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(-10, -1)]
    frac_in_1 = [fo - 1 for fo in frac_out_1]
    dwt_in_1 = [random.randint(2, 10)]
    dwt_out_1 = [di + fo - fi for di in dwt_in_1 for fo in frac_out_1 for fi in frac_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case11(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [5],
        dwt_out_1 = [7],
        frac_in_1 = [4],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case11(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(1, 10)]
    frac_in_1 = [fo - 2 for fo in frac_out_1]
    dwt_in_1 = [random.randint(2, 10)]
    dwt_out_1 = [di + fo - fi + 1 for di in dwt_in_1 for fo in frac_out_1 for fi in frac_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case12(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [5],
        frac_in_1 = [9],
        frac_out_1 = [8],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case12(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_in_1 = [random.randint(1, 10)]
    frac_out_1 = [fi - 2 for fi in frac_in_1]
    dwt_in_1 = [1]
    dwt_out_1 = [random.randint(2, 10)]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case13(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [2],
        frac_in_1 = [3],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case13(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(1, 10)]
    dwt_out_1 = [random.randint(2, 10)]
    frac_in_1 = [fo - do for fo in frac_out_1 for do in dwt_out_1]
    dwt_in_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case14(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [2],
        frac_in_1 = [-5],
        frac_out_1 = [-5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case14(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(-10, -1)]
    dwt_out_1 = [2,3]
    frac_in_1 = frac_out_1
    dwt_in_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case15(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [3],
        frac_in_1 = [5],
        frac_out_1 = [6],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case15(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_in_1 = [random.randint(-10, -1)]
    frac_out_1 = [fi +1 for fi in frac_in_1]
    dwt_in_1 = [1]
    dwt_out_1 = [fo - fi + 1 for fo in frac_out_1 for fi in frac_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case16(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [4],
        frac_in_1 = [5],
        frac_out_1 = [7],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case16(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_in_1 = [random.randint(-10, -1)]
    frac_out_1 = [fi +1 for fi in frac_in_1]
    dwt_in_1 = [1]
    dwt_out_1 = [fo - fi + 3 for fo in frac_out_1 for fi in frac_in_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case17(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [5],
        dwt_out_1 = [1],
        frac_in_1 = [9],
        frac_out_1 = [4],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case17(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_in_1 = [random.randint(2, 10)]
    frac_in_1 = [random.randint(-10, -1)]
    frac_out_1 = [fi -di for fi in frac_in_1 for di in dwt_in_1]
    dwt_out_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case18(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [5],
        dwt_out_1 = [1],
        frac_in_1 = [7],
        frac_out_1 = [8],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case18(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_in_1 = [random.randint(2, 10)]
    frac_out_1 = [random.randint(0, 10)]
    frac_in_1 = [fo - 1 for fo in frac_out_1]
    dwt_out_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case19(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [2],
        dwt_out_1 = [1],
        frac_in_1 = [5],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case19(Testcase):

    if_rst_n = [[False, False, True, False]]
    dwt_in_1 = [2,3,4]
    frac_out_1 = [random.randint(0, 10)]
    frac_in_1 = frac_out_1
    dwt_out_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case20(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [3],
        dwt_out_1 = [1],
        frac_in_1 = [7],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case20(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(0, 10)]
    frac_in_1 = [fo+2 for fo in frac_out_1]
    dwt_out_1 = [1]
    dwt_in_1 = [fi - fo + 1 for fi in frac_in_1 for fo in frac_out_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case21(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [4],
        dwt_out_1 = [1],
        frac_in_1 = [7],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case21(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(0, 10)]
    frac_in_1 = [fo+2 for fo in frac_out_1]
    dwt_out_1 = [1]
    dwt_in_1 = [fi - fo + 3 for fi in frac_in_1 for fo in frac_out_1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case22(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [1],
        frac_in_1 = [5],
        frac_out_1 = [4],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case22(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_in_1 = [random.randint(0, 10)]
    frac_out_1 = [fi-1 for fi in frac_in_1]
    dwt_out_1 = [1]
    dwt_in_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_specific_value_case23(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [1],
        frac_in_1 = [7],
        frac_out_1 = [8],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case23(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(0, 10)]
    frac_in_1 = [fo-2 for fo in frac_out_1]
    dwt_out_1 = [1]
    dwt_in_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase


def generate_testcase_specific_value_case24(Testcase):

    generator = PyTB.TestcaseGenerator(
        if_rst_n = [[False, False, True, False]],
        dwt_in_1 = [1],
        dwt_out_1 = [1],
        frac_in_1 = [5],
        frac_out_1 = [5],
        if_signed_in_1 = [True],
        if_signed_out_1 = [True],
        qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF],
        of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN],
        n_frames = [100],
        n_clk = [4]
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase

def generate_testcase_random_value_case24(Testcase):

    if_rst_n = [[False, False, True, False]]
    frac_out_1 = [random.randint(0, 10)]
    frac_in_1 = [fo for fo in frac_out_1]
    dwt_out_1 = [1]
    dwt_in_1 = [1]
    if_signed_in_1 = [True]
    if_signed_out_1 = [True]
    qu_mode = [PyTU.QuMode.TRN.TCPL, PyTU.QuMode.TRN.SMGN, PyTU.QuMode.RND.POS_INF, PyTU.QuMode.RND.ZERO, PyTU.QuMode.RND.CONV, PyTU.QuMode.RND.NEG_INF, PyTU. QuMode.RND.INF]
    of_mode = [PyTU.OfMode.WRP.TCPL, PyTU.OfMode.SAT.ZERO, PyTU.OfMode.SAT.TCPL, PyTU.OfMode.SAT.SMGN]
    n_frames = [100]
    n_clk = [4]

    generator = PyTB.TestcaseGenerator(
        if_rst_n=if_rst_n,
        dwt_in_1=dwt_in_1,
        dwt_out_1=dwt_out_1,
        frac_in_1=frac_in_1,
        frac_out_1=frac_out_1,
        if_signed_in_1=if_signed_in_1,
        if_signed_out_1=if_signed_out_1,
        qu_mode=qu_mode,
        of_mode=of_mode,
        n_frames=n_frames,
        n_clk=n_clk
    )

    testcase = generator.generate_testcases(Testcase)

    return testcase


# -------------------------------User Settings------------------------------- #
TESTCASES = generate_testcase_random_value_case3(Testcase)


@pytest.mark.parametrize("case", TESTCASES)
def test_fxmatch(case: Testcase):
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

    ModuleTbFxMatch(
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
        QU_IN=case.QU_IN, QU_OUT=case.QU_OUT,
        QU_MODE=case.QU_MODE, OF_MODE=case.OF_MODE,
    )

    moduleloader.set_root_dir(str(cpp_dir))
    moduleloader.set_language_mode("CPP")
    ModuleCppRun(N_FRAMES=case.N_FRAMES, DWT_IN=case.QU_IN.DWT, FRAC_IN=case.QU_IN.FRAC)

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

    compare_file_list = [
        (input_dir / "fxmatch_i_data.txt",
         comparison_dir / "fxmatch_o_data.txt",
         output_dir / "fxmatch_o_data.txt"),
    ]

    error_record = []
    for in_path, expected_path, actual_path in compare_file_list:
        inputs = in_path.read_text(encoding="utf-8").splitlines()
        expected = expected_path.read_text(encoding="utf-8").splitlines()
        actual = actual_path.read_text(encoding="utf-8").splitlines()

        for line_number, (inp, exp, act) in enumerate(
            itertools.zip_longest(inputs, expected, actual), start=1
        ):
            if exp is not None and act is not None and exp.strip() == act.strip():
                continue
            d0 = decode_bits(inp, case.QU_IN.IF_SIGNED)
            d1 = decode_bits(exp, case.QU_OUT.IF_SIGNED)
            d2 = decode_bits(act, case.QU_OUT.IF_SIGNED)
            error_record.append(
                f"line {line_number}: in={inp}(d{d0}), "
                f"expected={exp}(d{d1}), actual={act}(d{d2})\n"
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
