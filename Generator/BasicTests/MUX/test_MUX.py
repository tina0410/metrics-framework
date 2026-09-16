# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Pytest verification for MUX using the legacy module-test template.

import shutil
import subprocess
from pathlib import Path

import pytest
from pytv.ModuleLoader import moduleloader

from Generator.BasicModules.MUX import ModuleMUX, ModuleMux, mux_select_width

from BehavModel_MUX import mux_expected, pack_lanes
from tb_MUX import ModuleTbMUX


class Testcase:
    __test__ = False
    DUT_NAME = "MUX"

    def __init__(self, n_inputs, dwt):
        self.N_INPUTS = n_inputs
        self.DWT = dwt

    def display_info(self):
        return f"N_INPUTS: {self.N_INPUTS}  DWT: {self.DWT}\n"


TEST_DIR = Path(__file__).resolve().parent
SIM_DIR = TEST_DIR / "sim"


def generate_testcases():
    return [
        Testcase(1, 1),
        Testcase(2, 7),
        Testcase(3, 1),
        Testcase(4, 8),
        Testcase(5, 13),
        Testcase(9, 16),
        Testcase(17, 31),
    ]


TESTCASES = generate_testcases()


@pytest.mark.parametrize(
    "case",
    TESTCASES,
    ids=lambda case: f"n{case.N_INPUTS}_m{case.DWT}",
)
def test_mux(case: Testcase):
    values = [index * 3 + 1 for index in range(case.N_INPUTS)]
    packed = pack_lanes(values, case.DWT)
    for select in range(case.N_INPUTS):
        assert mux_expected(packed, select, case.N_INPUTS, case.DWT) == (
            values[select] & ((1 << case.DWT) - 1)
        )

    rtl_dir = SIM_DIR / "RTL" / f"n{case.N_INPUTS}_m{case.DWT}"
    shutil.rmtree(rtl_dir, ignore_errors=True)
    rtl_dir.mkdir(parents=True)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")
    ModuleTbMUX(N_INPUTS=case.N_INPUTS, DWT=case.DWT)

    verilog_files = sorted(path.name for path in rtl_dir.glob("*.v"))
    assert verilog_files
    run_subprocess(["iverilog", "-g2012", "-o", "wave", *verilog_files], rtl_dir)
    result = run_subprocess(["vvp", "wave"], rtl_dir)
    assert f"PASS MUX N={case.N_INPUTS} M={case.DWT}" in result.stdout


@pytest.mark.parametrize(
    ("n_inputs", "expected"),
    [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (9, 4), (17, 5)],
)
def test_mux_select_width(n_inputs, expected):
    assert mux_select_width(n_inputs) == expected


def test_mux_aliases_and_validation(tmp_path):
    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(tmp_path))
    moduleloader.disEnableWarning()
    ModuleMux(N=5, M=13)
    assert list(tmp_path.glob("MUX*.v"))

    with pytest.raises(ValueError):
        ModuleMUX(N_INPUTS=0, DWT=8)
    with pytest.raises(ValueError):
        ModuleMUX(N_INPUTS=2, DWT=0)
    with pytest.raises(ValueError):
        ModuleMUX(N_INPUTS=4, DWT=8, N=3)


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
