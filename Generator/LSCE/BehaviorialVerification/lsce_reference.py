"""Generate and run the original standalone LSCE C++ reference program."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from types import ModuleType


ROOT = Path(__file__).resolve().parent
LSCE_ROOT = ROOT.parent
QUANTIZATION_MODES = (
    "TRN.TCPL",
    "TRN.SMGN",
    "RND.POS_INF",
    "RND.NEG_INF",
    "RND.ZERO",
    "RND.INF",
    "RND.CONV",
)
OVERFLOW_MODES = ("WRP.TCPL", "SAT.TCPL", "SAT.SMGN", "SAT.ZERO")
_GENERATOR_IMPORT_LOCK = threading.RLock()
_GENERATOR_PYTU: ModuleType | None = None


def _load_generator_pytu() -> ModuleType:
    global _GENERATOR_PYTU
    if _GENERATOR_PYTU is not None:
        sys.modules["PyTU"] = _GENERATOR_PYTU
        return _GENERATOR_PYTU
    path = ROOT / "PyTU.py"
    spec = importlib.util.spec_from_file_location("PyTU", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load LSCE generator types from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["PyTU"] = module
    spec.loader.exec_module(module)
    _GENERATOR_PYTU = module
    return module


@contextlib.contextmanager
def generator_context():
    """Scope the legacy generator imports and command-line parsing."""
    with _GENERATOR_IMPORT_LOCK:
        previous_path, previous_argv = sys.path[:], sys.argv[:]
        previous_pytu = sys.modules.get("PyTU")
        sys.path[:0] = [str(ROOT), str(LSCE_ROOT / "designs"), str(LSCE_ROOT)]
        sys.argv = [sys.argv[0]]
        try:
            _load_generator_pytu()
            yield
        finally:
            if previous_pytu is None:
                sys.modules.pop("PyTU", None)
            else:
                sys.modules["PyTU"] = previous_pytu
            sys.path[:] = previous_path
            sys.argv[:] = previous_argv


def generator_parameters(config: dict) -> dict:
    """Convert validated JSON parameters to the existing generator types."""
    from PyTU import OfMode, QuMode, QuType

    parameters = dict(
        zip(
            ("N_T", "N_R", "P_T", "P_R"),
            (
                int(config[key])
                for key in (
                    "Number of Transmit Antennas",
                    "Number of Receiving Antennas",
                    "Parallelism T",
                    "Parallelism R",
                )
            ),
        )
    )
    for name in ("Y", "P", "H", "M_V"):
        value = config[f"Quantization format of {name}"]
        parameters[f"QU_{name}"] = QuType(
            int(value["bitwidth"]),
            int(value["fractional width"]),
            value["signed"],
        )
    for key, target, cls, allowed, default in (
        ("Quantization Mode", "QU_MODE", QuMode, QUANTIZATION_MODES, "TRN.TCPL"),
        ("Overflow Mode", "OF_MODE", OfMode, OVERFLOW_MODES, "WRP.TCPL"),
    ):
        value = config.get(key, default)
        if value not in allowed:
            raise ValueError(f"Unsupported {key}: {value!r}")
        group, member = value.split(".")
        parameters[target] = getattr(getattr(cls, group), member)
    parameters["N_PIPELINES"] = [
        int(value)
        for value in config["Pipeline Stages ([Multiplication, Adder Tree])"]
    ]
    return parameters


def _run(command: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        output = getattr(error, "stdout", "") or str(error)
        raise RuntimeError(
            f"LSCE standalone C++ command failed: {command!r}\n{output}"
        ) from error
    return result.stdout


def clang20() -> str:
    compiler = os.environ.get("CXX") or shutil.which("clang++-20") or shutil.which("clang++")
    if not compiler:
        raise RuntimeError(
            "LSCE standalone C++ reference requires Clang 20; set CXX to clang++-20"
        )
    version = _run([compiler, "--version"], LSCE_ROOT)
    if not re.search(r"\bclang version 20\.", version):
        raise RuntimeError(
            "LSCE standalone C++ reference requires Clang 20, not: "
            f"{version.strip() or 'unknown compiler'}"
        )
    return compiler


def _single_generated(directory: Path, pattern: str) -> Path:
    candidates = list(directory.glob(pattern))
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected one generated {pattern} file in {directory}, found {len(candidates)}"
        )
    return candidates[0]


def _portable_cpp_path(path: Path) -> str:
    return path.resolve().as_posix()


def _generate_sources(
    config: dict,
    workspace: Path,
    case_id: int,
    n_frames: int,
) -> tuple[Path, Path]:
    cpp_root = workspace / "CppModules"
    include_root = cpp_root / "include"
    input_root = workspace / "Input_Files" / f"Testcase{case_id}"
    comparison_root = workspace / "Comparison_Files" / f"Testcase{case_id}"
    for directory in (include_root, input_root, comparison_root):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "include" / "QuBLAS.h", include_root / "QuBLAS.h")

    with generator_context():
        from BehavModel_LSCE import ModuleCppConfig, ModuleCppRun
        from pytv.ModuleLoader import moduleloader

        parameters = generator_parameters(config)
        moduleloader.reset()
        try:
            moduleloader.set_naming_mode("SEQUENTIAL")
            moduleloader.disEnableWarning()
            moduleloader.set_root_dir(str(include_root))
            moduleloader.set_language_mode("CPP_HEADER")
            ModuleCppConfig()
            generated_header = _single_generated(include_root, "CppConfig*.h")
            generated_header.replace(include_root / "config.h")

            moduleloader.set_root_dir(str(cpp_root))
            moduleloader.set_language_mode("CPP")
            ModuleCppRun(
                **parameters,
                input_file_dir=_portable_cpp_path(input_root),
                comparison_file_dir=_portable_cpp_path(comparison_root),
                N_FRAMES=n_frames,
            )
            generated_source = _single_generated(cpp_root, "CppRun*.cpp")
            generated_source.replace(cpp_root / "main.cpp")
        finally:
            moduleloader.reset()
    return cpp_root / "main.cpp", include_root


def _read_rows(workspace: Path, case_id: int) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for name in (
        "i_Y",
        "Decimal_i_Y",
        "i_P",
        "Decimal_i_P",
        "i_ctrl_stg",
        "Decimal_i_ctrl_stg",
        "o_H",
        "Decimal_o_H",
    ):
        parent = "Comparison_Files" if name in ("o_H", "Decimal_o_H") else "Input_Files"
        path = workspace / parent / f"Testcase{case_id}" / f"{name}.txt"
        if not path.is_file():
            raise FileNotFoundError(f"Standalone LSCE reference did not produce {path}")
        rows[name] = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    return rows


def _validate_row_counts(config: dict, rows: dict[str, list[str]], n_frames: int) -> None:
    stages = int(config["Number of Transmit Antennas"]) // int(config["Parallelism T"])
    expected_inputs = n_frames * stages
    for name in ("i_Y", "Decimal_i_Y", "i_P", "Decimal_i_P"):
        if len(rows[name]) != expected_inputs:
            raise RuntimeError(
                f"Standalone LSCE reference produced {len(rows[name])} {name} rows; "
                f"expected {expected_inputs}"
            )
    for name in ("o_H", "Decimal_o_H"):
        if len(rows[name]) != n_frames:
            raise RuntimeError(
                f"Standalone LSCE reference produced {len(rows[name])} {name} rows; "
                f"expected {n_frames}"
            )
    expected_control = 0
    if stages > 1:
        expected_control = expected_inputs + sum(
            int(value)
            for value in config["Pipeline Stages ([Multiplication, Adder Tree])"]
        )
    for name in ("i_ctrl_stg", "Decimal_i_ctrl_stg"):
        if len(rows[name]) != expected_control:
            raise RuntimeError(
                f"Standalone LSCE reference produced {len(rows[name])} {name} rows; "
                f"expected {expected_control}"
            )


def generate_reference_files(
    config: dict,
    workspace: Path,
    case_id: int,
    *,
    n_frames: int = 10,
) -> dict[str, list[str]]:
    """Generate, compile, and run a fresh standalone C++ reference executable."""
    if isinstance(n_frames, bool) or not isinstance(n_frames, int) or n_frames <= 0:
        raise ValueError("n_frames must be a positive integer")
    source, include_root = _generate_sources(config, workspace, case_id, n_frames)
    cpp_root = source.parent
    compiler = clang20()
    executable = cpp_root / ("LSCE.exe" if os.name == "nt" else "LSCE.out")
    manifest_path = cpp_root / "reference_build.json"
    sources = (source, include_root / "config.h", include_root / "QuBLAS.h", Path(__file__))
    manifest = {
        "backend": "standalone_cpp",
        "status": "building",
        "config_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "compiler": compiler,
        "compiler_version": _run([compiler, "--version"], LSCE_ROOT).strip(),
        "source_sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    try:
        compile_output = _run(
            [
                compiler,
                "-std=c++23",
                str(source),
                "-I",
                str(include_root),
                "-O3",
                "-o",
                str(executable),
            ],
            cpp_root,
        )
        (cpp_root / "reference_compile.log").write_text(compile_output, encoding="utf-8")
        run_output = _run([str(executable)], cpp_root)
        (cpp_root / "reference_run.log").write_text(run_output, encoding="utf-8")
        rows = _read_rows(workspace, case_id)
        _validate_row_counts(config, rows, n_frames)
        manifest.update(
            status="ready",
            executable=str(executable),
            executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
        )
        return rows
    except Exception as error:
        manifest.update(status="failed", error=str(error))
        raise
    finally:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
