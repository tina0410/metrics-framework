# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Pytest verification for Delay using the legacy module-test template.

import shutil
import subprocess
from pathlib import Path

import pytest
from pytv.ModuleLoader import moduleloader

from BehavModel_Delay import delay_expected
from tb_Delay import ModuleTbDelay


class Testcase:
    __test__ = False
    DUT_NAME = "Delay"

    def __init__(self, dwt, n_clk, if_rst_n):
        self.DWT = dwt
        self.N_CLK = n_clk
        self.IF_RST_N = if_rst_n

    def display_info(self):
        return f"DWT: {self.DWT}  N_CLK: {self.N_CLK}  IF_RST_N: {self.IF_RST_N}\n"


TEST_DIR = Path(__file__).resolve().parent
SIM_DIR = TEST_DIR / "sim"


def generate_testcases():
    return [
        Testcase(1, 0, False),
        Testcase(8, 1, True),
        Testcase(13, 3, [True, False, True]),
    ]


TESTCASES = generate_testcases()


@pytest.mark.parametrize(
    "case",
    TESTCASES,
    ids=lambda case: f"dwt{case.DWT}_n{case.N_CLK}",
)
def test_delay(case: Testcase):
    assert delay_expected([1, 2, 3], 0) == [1, 2, 3]

    rtl_dir = SIM_DIR / "RTL" / f"dwt{case.DWT}_n{case.N_CLK}"
    shutil.rmtree(rtl_dir, ignore_errors=True)
    rtl_dir.mkdir(parents=True)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.disEnableWarning()
    moduleloader.set_naming_mode("SEQUENTIAL")
    ModuleTbDelay(DWT=case.DWT, N_CLK=case.N_CLK, IF_RST_N=case.IF_RST_N)

    verilog_files = sorted(path.name for path in rtl_dir.glob("*.v"))
    assert verilog_files
    run_subprocess(["iverilog", "-g2012", "-o", "wave", *verilog_files], rtl_dir)
    result = run_subprocess(["vvp", "wave"], rtl_dir)
    assert f"PASS Delay DWT={case.DWT} N_CLK={case.N_CLK}" in result.stdout


def test_delay_rejects_invalid_parameters(tmp_path):
    moduleloader.reset()
    moduleloader.set_root_dir(str(tmp_path))
    with pytest.raises(ValueError):
        ModuleTbDelay(DWT=0, N_CLK=1, IF_RST_N=False)
    with pytest.raises(ValueError):
        ModuleTbDelay(DWT=8, N_CLK=-1, IF_RST_N=False)


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
