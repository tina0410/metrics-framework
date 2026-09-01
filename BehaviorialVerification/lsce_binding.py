"""Build and call the nanobind C++ reference; never reuse a previous binary."""

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
import sysconfig
from types import ModuleType
import uuid

ROOT = Path(__file__).resolve().parent
LSCE_ROOT = ROOT.parent
BINDINGS = LSCE_ROOT / "bindings"
QUANTIZATION_MODES = ("TRN.TCPL", "TRN.SMGN", "RND.POS_INF", "RND.NEG_INF",
                      "RND.ZERO", "RND.INF", "RND.CONV")
OVERFLOW_MODES = ("WRP.TCPL", "SAT.TCPL", "SAT.SMGN", "SAT.ZERO")


@contextlib.contextmanager
def generator_context():
    """Scope legacy generator search paths and command-line parsing."""
    previous_path, previous_argv = sys.path[:], sys.argv[:]
    sys.path[:0] = [str(ROOT), str(LSCE_ROOT / "designs"), str(LSCE_ROOT)]
    sys.argv = [sys.argv[0]]
    try:
        yield
    finally:
        sys.path[:] = previous_path
        sys.argv[:] = previous_argv


def generator_parameters(config: dict) -> dict:
    """Convert validated JSON parameters to the existing generator types."""
    from PyTU import QuType, QuMode, OfMode

    parameters = dict(zip(("N_T", "N_R", "P_T", "P_R"),
                          (int(config[key]) for key in (
                              "Number of Transmit Antennas", "Number of Receiving Antennas",
                              "Parallelism T", "Parallelism R"))))
    for name in ("Y", "P", "H", "M_V"):
        value = config[f"Quantization format of {name}"]
        parameters[f"QU_{name}"] = QuType(
            int(value["bitwidth"]), int(value["fractional width"]), value["signed"])
    for key, target, cls, allowed, default in (
        ("Quantization Mode", "QU_MODE", QuMode, QUANTIZATION_MODES, "TRN.TCPL"),
        ("Overflow Mode", "OF_MODE", OfMode, OVERFLOW_MODES, "WRP.TCPL"),
    ):
        value = config.get(key, default)
        if value not in allowed:
            raise ValueError(f"Unsupported {key}: {value!r}")
        group, member = value.split(".")
        parameters[target] = getattr(getattr(cls, group), member)
    parameters["N_PIPELINES"] = [int(x) for x in config[
        "Pipeline Stages ([Multiplication, Adder Tree])"]]
    return parameters


def render_parameters(config: dict) -> str:
    """Render compile-time constants without exposing QuBLAS to Python."""
    with generator_context():
        p = generator_parameters(config)
    lines = ['#pragma once', '#include "QuBLAS.h"', 'namespace lsce_parameters {']
    lines += [f"constexpr size_t {name} = {p[name]};" for name in ("N_T", "N_R", "P_T", "P_R")]
    for name in ("QU_Y", "QU_P", "QU_H", "QU_M_V"):
        q = p[name]
        lines.append(f"using {name} = Qu<intBits<{q.intBits()}>, fracBits<{q.fracBits()}>, "
                     f"isSigned<{q.isSigned()}>, QuMode<{p['QU_MODE'].cppType()}>, "
                     f"OfMode<{p['OF_MODE'].cppType()}>>;")
    lines.append(f"constexpr std::array<int, 2> N_PIPELINES = {{{p['N_PIPELINES'][0]}, {p['N_PIPELINES'][1]}}};")
    lines += ['static_assert(N_T % P_T == 0 && N_R % P_R == 0);', '}']
    return "\n".join(lines) + "\n"


def _run(command: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        output = getattr(error, "stdout", "") or str(error)
        raise RuntimeError(f"LSCE binding command failed: {command!r}\n{output}") from error
    return result.stdout


def clang20() -> str:
    compiler = os.environ.get("CXX") or shutil.which("clang++-20") or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("LSCE binding requires Clang 20. Set CXX to clang++-20.")
    version = _run([compiler, "--version"], LSCE_ROOT)
    if not re.search(r"\bclang version 20\.", version):
        raise RuntimeError(f"LSCE binding requires Clang 20, not: {version.strip() or 'unknown compiler'}")
    return compiler


def build_reference(config: dict, artifact_dir: Path) -> ModuleType:
    """Generate, compile and import a fresh module for this validated config."""
    compiler = clang20()
    cmake = shutil.which("cmake")
    if not cmake:
        raise RuntimeError("LSCE binding requires CMake on PATH (install the bindings extra).")
    name = "_lsce_" + uuid.uuid4().hex
    # Loaded Windows extensions cannot be deleted. Keep builds outside case cleanup.
    build_root = LSCE_ROOT / ".binding_builds" / name
    generated = build_root / "sources"
    generated.mkdir(parents=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (generated / "parameters.hpp").write_text(render_parameters(config), encoding="utf-8")
    with generator_context():
        from pytv.ModuleLoader import moduleloader
        from BehavModel_LSCE import ModuleCppConfig
        moduleloader.reset()
        try:
            moduleloader.set_root_dir(str(generated))
            moduleloader.set_language_mode("CPP_HEADER")
            moduleloader.set_naming_mode("SEQUENTIAL")
            moduleloader.disEnableWarning()
            ModuleCppConfig()
            candidates = list(generated.glob("CppConfig*.h"))
            if len(candidates) != 1:
                raise RuntimeError(f"Expected one generated C++ algorithm header in {generated}")
            candidates[0].rename(generated / "config.h")
        finally:
            moduleloader.reset()
    sources = [BINDINGS / name for name in (
        "reference.hpp", "reference.cpp", "module.cpp.in", "CMakeLists.txt")]
    sources += [ROOT / "BehavModel_LSCE.py", ROOT / "include" / "QuBLAS.h", Path(__file__)]
    manifest = {"module": name, "build_root": str(build_root), "config": config,
                "compiler": compiler, "compiler_version": _run([compiler, "--version"], LSCE_ROOT),
                "python": sys.version, "extension_suffix": sysconfig.get_config_var("EXT_SUFFIX"),
                "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                "status": "building"}
    manifest_path = artifact_dir / "binding_build.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    try:
        manifest["binding_backend"] = "nanobind"
        manifest["nanobind_version"] = _run(
            [sys.executable, "-c", "import nanobind; print(nanobind.__version__)"], LSCE_ROOT).strip()
        configure = _run([cmake, "-S", str(BINDINGS), "-B", str(build_root / "build"),
                          "-G", "Ninja", f"-DCMAKE_CXX_COMPILER={compiler}",
                          "-DCMAKE_BUILD_TYPE=Release", f"-DPython_EXECUTABLE={sys.executable}",
                          f"-DLSCE_MODULE={name}", f"-DLSCE_GENERATED={generated}"], LSCE_ROOT)
        (artifact_dir / "binding_configure.log").write_text(configure, encoding="utf-8")
        output = _run([cmake, "--build", str(build_root / "build")], LSCE_ROOT)
        (artifact_dir / "binding_compile.log").write_text(output, encoding="utf-8")
        suffix = sysconfig.get_config_var("EXT_SUFFIX")
        binary = build_root / "build" / "module" / (name + suffix)
        if not binary.is_file():
            raise RuntimeError(f"LSCE binding binary was not produced: {binary}")
        spec = importlib.util.spec_from_file_location(name, binary)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load LSCE binding: {binary}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not callable(getattr(module, "reference_frames", None)):
            raise RuntimeError("Generated binding has no reference_frames API")
        manifest.update(status="ready", binary=str(binary),
                        binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
        return module
    except Exception as error:
        manifest.update(status="failed", error=str(error))
        raise RuntimeError(f"LSCE binding failed; no fallback is permitted. {error}") from error
    finally:
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_reference_files(rows: dict[str, list[str]], workspace: Path, case_id: int) -> None:
    """Write only files consumed by RTL or retained for reference tracing."""
    for name, values in rows.items():
        directory = "Comparison_Files" if name in ("o_H", "Decimal_o_H") else "Input_Files"
        destination = workspace / directory / f"Testcase{case_id}" / f"{name}.txt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("".join(value + "\n" for value in values), encoding="utf-8")
