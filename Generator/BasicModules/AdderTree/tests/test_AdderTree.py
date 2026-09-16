# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Pytest verification for AdderTree using the legacy module-test template.

import shutil
import subprocess
from pathlib import Path

import pytest
from pytv.ModuleLoader import moduleloader

import PyTU
from BehavModel_AdderTree import adder_tree_expected, pack_lanes
from tb_AdderTree import ModuleTbAdderTree


class Testcase:
    __test__ = False
    DUT_NAME = "AdderTree"

    def __init__(self, n_inputs, n_pipelines, if_rst_n):
        self.QU_IN = PyTU.QuType(8, 0, False)
        self.QU_OUT = PyTU.QuType(12, 0, False)
        self.N_INPUTS = n_inputs
        self.N_PIPELINES = n_pipelines
        self.IF_RST_N = if_rst_n
        self.QU_MODE = PyTU.QuMode.TRN.TCPL
        self.OF_MODE = PyTU.OfMode.WRP.TCPL

    def display_info(self):
        return (
            f"N_INPUTS: {self.N_INPUTS}  N_PIPELINES: {self.N_PIPELINES}\n"
            f"IF_RST_N: {self.IF_RST_N}\n"
        )


TEST_DIR = Path(__file__).resolve().parent
SIM_DIR = TEST_DIR / "sim"


def generate_testcases():
    return [
        Testcase(3, 0, False),
        Testcase(5, 3, True),
        Testcase(8, 2, False),
    ]


TESTCASES = generate_testcases()


@pytest.mark.parametrize(
    "case",
    TESTCASES,
    ids=lambda case: f"n{case.N_INPUTS}_p{case.N_PIPELINES}",
)
def test_adder_tree(case: Testcase):
    # Keep the Python oracle exercised independently of RTL generation.
    values = list(range(1, case.N_INPUTS + 1))
    assert pack_lanes(values, case.QU_IN.DWT) >= 0
    assert adder_tree_expected(values, case.QU_OUT.DWT) == sum(values)

    rtl_dir = SIM_DIR / "RTL" / f"n{case.N_INPUTS}_p{case.N_PIPELINES}"
    shutil.rmtree(rtl_dir, ignore_errors=True)
    rtl_dir.mkdir(parents=True)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")

    ModuleTbAdderTree(
        QU_IN=case.QU_IN,
        QU_OUT=case.QU_OUT,
        N_PIPELINES=case.N_PIPELINES,
        QU_MODE=case.QU_MODE,
        OF_MODE=case.OF_MODE,
        IF_RST_N=case.IF_RST_N,
        N_INPUTS=case.N_INPUTS,
    )
    run_subprocess(["iverilog", "-g2012", "-o", "wave", *sorted(path.name for path in rtl_dir.glob("*.v"))], rtl_dir)
    result = run_subprocess(["vvp", "wave"], rtl_dir)
    assert f"PASS AdderTree N_INPUTS={case.N_INPUTS}" in result.stdout


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
    except FileNotFoundError as error:
        pytest.skip(f"Required simulator is unavailable: {error.filename}")
    except subprocess.CalledProcessError as error:
        pytest.fail(
            f"Command failed: {' '.join(command)}\nstdout:\n{error.stdout}\nstderr:\n{error.stderr}"
        )
