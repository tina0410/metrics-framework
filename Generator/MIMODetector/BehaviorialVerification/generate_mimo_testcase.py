#!/usr/bin/env python3
"""Regenerate one isolated MIMO RTL/testbench/reference testcase."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MIMO_ROOT = ROOT.parent
REPOSITORY_ROOT = MIMO_ROOT.parents[1]
SIM_ROOT = ROOT / "sim"
CPP_REFERENCE = ROOT / "cpp_reference"
QUBLAS_SOURCE = ROOT / "include" / "QuBLAS.h"


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def clean_case(case_id: int) -> None:
    """Preserve sim/TestcaseN while resetting only its generated workspace."""
    case_root = SIM_ROOT / f"Testcase{case_id}"
    workspace = case_root / "workspace"
    case_root.mkdir(parents=True, exist_ok=True)
    for generated_name in (
        "Generated_RTL",
        "RTL",
        "Input_Files",
        "Comparison_Files",
        "Output_Files",
        "Log_Files",
        "CppModules",
    ):
        _remove_path(workspace / generated_name)


def _reference_qam_order() -> int:
    source = CPP_REFERENCE / "lNSA.cpp"
    if not source.is_file():
        raise FileNotFoundError(f"Missing canonical MIMO C++ source: {source}")
    match = re.search(r"const\s+uword\s+QAM\s*=\s*(\d+)\s*;", source.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Cannot determine QAM order from {source}")
    return int(match.group(1))


def generate_testcase(config_path: Path, case_id: int) -> None:
    """Reuse GenlNSA and test_PE.py in an isolated case workspace."""
    if case_id < 0:
        raise ValueError("MIMO case id must be non-negative")
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing MIMO config file: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    configured_qam = int(config.get("QAM Order", 0))
    reference_qam = _reference_qam_order()
    if configured_qam != reference_qam:
        raise ValueError(
            f"QAM mismatch: config={configured_qam}, canonical lNSA.cpp={reference_qam}"
        )

    clean_case(case_id)
    case_name = f"Testcase{case_id}"
    case_root = SIM_ROOT / case_name
    workspace = case_root / "workspace"
    shutil.copy2(config_path, case_root / "config_snapshot.json")

    design_rtl_root = workspace / "Generated_RTL"
    design_rtl = design_rtl_root / case_name
    design_rtl.mkdir(parents=True, exist_ok=True)
    cpp_root = workspace / "CppModules"
    cpp_include = cpp_root / "include"
    cpp_include.mkdir(parents=True, exist_ok=True)
    for source_name in ("lNSA.cpp", "PE.h"):
        source = CPP_REFERENCE / source_name
        if not source.is_file():
            raise FileNotFoundError(f"Missing canonical MIMO C++ source: {source}")
        shutil.copy2(source, cpp_root / source_name)
    if not QUBLAS_SOURCE.is_file():
        raise FileNotFoundError(f"Missing canonical QuBLAS header: {QUBLAS_SOURCE}")
    shutil.copy2(QUBLAS_SOURCE, cpp_include / "QuBLAS.h")

    designs_root = MIMO_ROOT / "designs"
    generator_source = designs_root / "lNSA_MMSE.py"
    if not generator_source.exists():
        raise FileNotFoundError(f"MIMO RTL generator source is missing: {generator_source}")
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    sys.path.insert(0, str(REPOSITORY_ROOT))
    sys.path.insert(0, str(designs_root))
    sys.path.insert(0, str(MIMO_ROOT))
    try:
        from lNSA_MMSE import GenlNSA

        GenlNSA(ConfigFileName=str(config_path), GenRoot=str(design_rtl))
        if not list(design_rtl.glob("lNSA*.v")):
            raise RuntimeError(f"RTL generation did not produce an lNSA top module in {design_rtl}")
    finally:
        sys.argv = original_argv
        sys.path.remove(str(MIMO_ROOT))
        sys.path.remove(str(designs_root))
        sys.path.remove(str(REPOSITORY_ROOT))

    env_names = (
        "MIMO_CONFIG_PATH",
        "MIMO_CASE_ID",
        "MIMO_SIM_ROOT",
        "MIMO_DESIGN_RTL_ROOT",
    )
    previous = {name: os.environ.get(name) for name in env_names}
    old_cwd = Path.cwd()
    original_argv = sys.argv[:]
    os.environ.update(
        {
            "MIMO_CONFIG_PATH": str(config_path),
            "MIMO_CASE_ID": str(case_id),
            "MIMO_SIM_ROOT": str(workspace),
            "MIMO_DESIGN_RTL_ROOT": str(design_rtl_root),
        }
    )
    sys.argv = [sys.argv[0]]
    sys.path.insert(0, str(REPOSITORY_ROOT))
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(MIMO_ROOT))
    try:
        os.chdir(ROOT)
        importlib.invalidate_caches()
        test_pe = importlib.import_module("test_PE")
        if len(test_pe.testcase) != 1:
            raise RuntimeError(f"Expected one generated testcase, got {len(test_pe.testcase)}")
        test_pe.test_my_module(None, test_pe.testcase[0])
    finally:
        os.chdir(old_cwd)
        sys.argv = original_argv
        sys.path.remove(str(MIMO_ROOT))
        sys.path.remove(str(ROOT))
        sys.path.remove(str(REPOSITORY_ROOT))
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate one isolated MIMO testcase")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--case", type=int, required=True)
    args = parser.parse_args()
    generate_testcase(args.config, args.case)


if __name__ == "__main__":
    main()