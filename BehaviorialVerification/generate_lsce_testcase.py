#!/usr/bin/env python3
"""Regenerate one LSCE RTL/testbench/reference testcase using existing code."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LSCE_ROOT = ROOT.parent
SIM_ROOT = ROOT / "sim"


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def clean_case(case_id: int) -> None:
    """Preserve sim/TestcaseN while resetting only its generated workspace."""
    if isinstance(case_id, bool) or not isinstance(case_id, int) or case_id < 0:
        raise ValueError("case_id must be a non-negative integer")
    case_root = SIM_ROOT / f"Testcase{case_id}"
    workspace = case_root / "workspace"
    for parent in (SIM_ROOT, case_root, workspace):
        if parent.resolve() != parent.absolute():
            raise ValueError(f"Refusing cleanup through a redirected workspace: {parent}")
    generated_names = (
        "Generated_RTL", "RTL", "Input_Files", "Comparison_Files",
        "Output_Files", "Log_Files", "CppModules",
    )
    for name in generated_names:
        target = workspace / name
        if target.resolve() != target.absolute():
            raise ValueError(f"Refusing cleanup of a redirected generated directory: {target}")
    case_root.mkdir(parents=True, exist_ok=True)
    # Invalidate success only after checking every cleanup target.
    (case_root / "simulation_result.json").unlink(missing_ok=True)
    for generated_name in generated_names:
        _remove_path(workspace / generated_name)

def generate_testcase(config_path: Path, case_id: int, *, config: dict | None = None) -> dict[str, list[str]]:
    """Generate one RTL workspace and return its freshly bound C++ reference."""
    if __package__:
        from .lsce_binding import (build_reference, generator_context,
                                   generator_parameters, write_reference_files)
    else:
        from lsce_binding import (build_reference, generator_context,
                                  generator_parameters, write_reference_files)
    with generator_context():
        from evaluate_lsce import load_config, validate_config, _case_id
        config_path = config_path.resolve()
        config = load_config(config_path) if config is None else validate_config(config, config_path)
    if isinstance(case_id, bool) or not isinstance(case_id, int) or case_id < 0 or _case_id(config_path) != case_id:
        raise ValueError("case_id must match the non-negative config_caseN.json filename")
    if int(config["Parallelism R"]) != int(config["Number of Receiving Antennas"]):
        raise ValueError("Complete RTL simulation requires P_R == N_R")
    clean_case(case_id)
    case_name = f"Testcase{case_id}"
    case_root = SIM_ROOT / case_name
    workspace = case_root / "workspace"
    (case_root / "config_snapshot.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (case_root / "config_source.txt").write_text(str(config_path), encoding="utf-8")
    module = build_reference(config, workspace / "CppModules")
    rows = module.reference_frames(10)
    write_reference_files(rows, workspace, case_id)
    design_rtl = workspace / "Generated_RTL" / case_name
    rtl = workspace / "RTL" / case_name
    design_rtl.mkdir(parents=True, exist_ok=True)
    rtl.mkdir(parents=True, exist_ok=True)
    (workspace / "Output_Files" / case_name).mkdir(parents=True, exist_ok=True)
    with generator_context():
        from pytv.ModuleLoader import moduleloader
        from LSCE import GenLSCE
        from tb_LSCE import ModuleTbLSCE
        try:
            GenLSCE(ConfigFileName=str(config_path), GenRoot=str(design_rtl), config=config)
            if not list(design_rtl.glob("LSCE*.v")):
                raise RuntimeError("RTL generation did not produce an LSCE top module")
            moduleloader.reset()
            moduleloader.set_language_mode("VERILOG")
            moduleloader.set_root_dir(str(rtl))
            moduleloader.set_naming_mode("SEQUENTIAL")
            moduleloader.disEnableWarning()
            ModuleTbLSCE(**generator_parameters(config),
                         CLOCK_PERIOD_NS=float(config.get("clock", {}).get("period_ns", 10.0)),
                         input_file_dir=f"../../Input_Files/{case_name}",
                         output_file_dir=f"../../Output_Files/{case_name}", N_FRAMES=10)
            for path in rtl.glob("*.v"):
                if not path.name.startswith("TbLSCE"):
                    path.unlink()
            for path in design_rtl.glob("*.v"):
                shutil.copy2(path, rtl / path.name)
        finally:
            moduleloader.reset()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate one LSCE testcase")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--case", type=int, required=True)
    args = parser.parse_args()
    generate_testcase(args.config, args.case)


if __name__ == "__main__":
    main()
