#!/usr/bin/env python3
"""Generate one isolated ADD testcase with its original PyTB/QuBLAS chain."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
ADD_ROOT = ROOT.parent
REPOSITORY_ROOT = ADD_ROOT.parents[2]
TESTS_ROOT = ADD_ROOT / "tests"
DESIGNS_ROOT = ADD_ROOT / "designs"
PYTV_ROOT = REPOSITORY_ROOT / "Generator" / "LSCE" / "BehaviorialVerification"
SIM_ROOT = Path(os.environ.get("ADD_SIM_ROOT", ADD_ROOT / "sim")).resolve()
QUBLAS_SOURCE = TESTS_ROOT / "sim" / "CppModules" / "include" / "QuBLAS.h"


def _remove_workspace(path: Path) -> None:
    resolved = path.resolve()
    if resolved.parent.parent != SIM_ROOT or resolved.name != "workspace":
        raise ValueError(f"Refusing to clean unexpected ADD workspace: {resolved}")
    if path.exists():
        shutil.rmtree(path)


def _single(path: Path, pattern: str) -> Path:
    matches = list(path.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one {pattern} in {path}, found {len(matches)}")
    return matches[0]


def _run(command: list[str], cwd: Path) -> str:
    process = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Command failed in {cwd}: {' '.join(command)}\n{process.stdout}")
    return process.stdout


def _load_generators():
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    inserted = [str(TESTS_ROOT), str(ADD_ROOT), str(DESIGNS_ROOT), str(PYTV_ROOT)]
    sys.path[:0] = inserted
    try:
        import PyTU
        from BehavModel_Add import ModuleCppConfig, ModuleCppRun
        from tb_Add import ModuleTbAdd
        from pytv.ModuleLoader import moduleloader
    finally:
        sys.argv = original_argv
    return PyTU, ModuleCppConfig, ModuleCppRun, ModuleTbAdd, moduleloader


def _qu_type(py_tu: Any, config: dict[str, Any], name: str):
    value = config[name]
    return py_tu.QuType(
        int(value["bitwidth"]), int(value["fractional_width"]), bool(value["signed"])
    )


def generate_testcase(config_path: Path, case_label: str) -> Path:
    """Generate the C++ reference, ADD RTL and original testbench."""
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing ADD config file: {config_path}")
    if not case_label or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in case_label
    ):
        raise ValueError(f"Invalid ADD case label: {case_label!r}")

    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    frames = int(config.get("flow", {}).get("simulation_frames", 3))
    if frames < 3:
        raise ValueError("ADD timing validation requires at least three frames")

    case_root = SIM_ROOT / case_label
    workspace = case_root / "workspace"
    case_root.mkdir(parents=True, exist_ok=True)
    _remove_workspace(workspace)
    rtl_dir = workspace / "RTL"
    cpp_dir = workspace / "CppModules"
    include_dir = cpp_dir / "include"
    for directory in (
        rtl_dir,
        workspace / "Input_Files",
        workspace / "Comparison_Files",
        workspace / "Output_Files",
        include_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(QUBLAS_SOURCE, include_dir / "QuBLAS.h")
    shutil.copy2(config_path, case_root / "config_snapshot.json")

    py_tu, cpp_config, cpp_run, tb_add, moduleloader = _load_generators()
    qu_in1 = _qu_type(py_tu, config, "input_1")
    qu_in2 = _qu_type(py_tu, config, "input_2")
    qu_out = _qu_type(py_tu, config, "output")
    qu_mode = py_tu.QuMode.TRN.TCPL
    of_mode = py_tu.OfMode.WRP.TCPL

    moduleloader.reset()
    moduleloader.set_language_mode("CPP_HEADER")
    moduleloader.set_root_dir(str(include_dir))
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    with contextlib.redirect_stdout(sys.stderr):
        cpp_config(
            QU_IN_1=qu_in1,
            QU_IN_2=qu_in2,
            QU_OUT=qu_out,
            QU_MODE=qu_mode,
            OF_MODE=of_mode,
        )
    _single(include_dir, "CppConfig*.h").replace(include_dir / "config.h")

    moduleloader.set_language_mode("CPP")
    moduleloader.set_root_dir(str(cpp_dir))
    with contextlib.redirect_stdout(sys.stderr):
        cpp_run(N_FRAMES=frames)
    _single(cpp_dir, "CppRun*.cpp").replace(cpp_dir / "Add.cpp")
    compiler = shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        raise FileNotFoundError("ADD reference generation requires clang++ or g++ on PATH")
    executable = cpp_dir / ("add_reference.exe" if os.name == "nt" else "add_reference")
    _run([compiler, "Add.cpp", "-std=c++23", "-Iinclude", "-o", str(executable)], cpp_dir)
    _run([str(executable)], cpp_dir)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    with contextlib.redirect_stdout(sys.stderr):
        tb_add(
            QU_IN_1=qu_in1,
            QU_IN_2=qu_in2,
            QU_OUT=qu_out,
            N_CLK=int(config["n_pipeline"]),
            IF_RST_N=config.get("if_rst_n", False),
            QU_MODE=qu_mode,
            OF_MODE=of_mode,
            input_file_dir="../",
            N_FRAMES=frames,
            CLK_PERIOD=float(config["clock"]["period_ns"]),
        )
    _single(rtl_dir, "TbAdd*.v")
    return rtl_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one original ADD testcase")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--case-label", required=True)
    args = parser.parse_args()
    generate_testcase(args.config, args.case_label)


if __name__ == "__main__":
    main()
