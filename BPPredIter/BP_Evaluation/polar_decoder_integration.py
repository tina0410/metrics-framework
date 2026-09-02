"""Boundary between BPPredIter and the canonical PolarDecoder generator."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_POLAR_PROJECT = (
    ROOT.parent.parent / "Generator" / "PolarDecoder" / "BehaviorialVerification"
)


def simulate_bp_rtl(
    config_path: Path,
    case_dir: Path,
    project_dir: Path = DEFAULT_POLAR_PROJECT,
    *,
    label: str | None = None,
) -> dict[str, object]:
    """Run one isolated RTL simulation and publish its review artifacts.

    ``case_dir`` is persistent. The canonical simulator is only allowed to
    rebuild ``case_dir/workspace``; standard results are copied to the case
    root after all consistency checks pass.
    """
    simulator = project_dir / "bp_latency_simulation.py"
    if not simulator.exists():
        raise FileNotFoundError(f"PolarDecoder latency simulator not found: {simulator}")
    case_dir.mkdir(parents=True, exist_ok=True)
    workspace = case_dir / "workspace"
    result_path = case_dir / "simulation_result.json"
    raw_result_path = workspace / "simulation_result.json"
    for name in ("simulation_result.json", "latency_output.txt", "simulation.log", "wave.vcd"):
        previous = case_dir / name
        if previous.exists():
            previous.unlink()
    command = [
        sys.executable,
        str(simulator),
        "--config-path",
        str(config_path.resolve()),
        "--output-dir",
        str(workspace.resolve()),
        "--result-json",
        str(raw_result_path.resolve()),
    ]
    if label is not None:
        command.extend(["--label", label])
    completed = subprocess.run(
        command,
        cwd=project_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "PolarDecoder RTL simulation failed:\n" + completed.stdout
        )
    if not raw_result_path.exists():
        raise RuntimeError(f"Simulation result was not produced: {raw_result_path}")
    result = json.loads(raw_result_path.read_text(encoding="utf-8"))

    if result.get("stimulus_source") != "baseline_input_files":
        raise RuntimeError(
            "PolarDecoder did not use the approved baseline input files"
        )
    stimulus_files = result.get("stimulus_files")
    if not isinstance(stimulus_files, dict):
        raise RuntimeError("PolarDecoder baseline stimulus metadata is missing")
    for key in ("channel", "left_messages", "right_messages", "cpp_reference"):
        artifact = stimulus_files.get(key)
        if not isinstance(artifact, str) or not artifact:
            raise RuntimeError(f"PolarDecoder baseline stimulus path is missing: {key}")
        artifact_path = Path(artifact).resolve()
        if not artifact_path.is_relative_to(workspace.resolve()):
            raise RuntimeError(
                f"PolarDecoder stimulus escaped the isolated workspace: {artifact_path}"
            )
        if not artifact_path.exists() or artifact_path.stat().st_size == 0:
            raise RuntimeError(
                f"PolarDecoder baseline stimulus is missing or empty: {artifact_path}"
            )

    required_positive = {
        "sim_latency_cycles": "RTL latency",
        "cpp_iterations": "C++ iteration count",
    }
    for key, description in required_positive.items():
        value = result.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise RuntimeError(
                f"PolarDecoder {description} is missing or invalid: {value!r}"
            )
    required_times = {
        "rtl_simulation_time_ms": "RTL simulation time",
        "cpp_simulation_time_ms": "C++ simulation time",
    }
    for key, description in required_times.items():
        value = result.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise RuntimeError(
                f"PolarDecoder {description} is missing or invalid: {value!r}"
            )

    if result.get("waveform_verified") is not True:
        raise RuntimeError("PolarDecoder waveform was not verified")
    if result.get("decoding_verified") is not True:
        raise RuntimeError("PolarDecoder fixed-point decoding was not verified")

    waveform_text = result.get("waveform")
    if not isinstance(waveform_text, str) or not waveform_text:
        raise RuntimeError("PolarDecoder waveform path is missing")
    waveform = Path(waveform_text)
    if not waveform.exists() or waveform.stat().st_size == 0:
        raise RuntimeError(f"PolarDecoder waveform is missing or empty: {waveform}")

    latency_source = workspace / "latency_output.txt"
    if not latency_source.exists():
        raise RuntimeError(f"PolarDecoder latency evidence is missing: {latency_source}")
    try:
        latency_from_file = int(latency_source.read_text(encoding="utf-8").strip())
    except ValueError as error:
        raise RuntimeError(
            f"PolarDecoder latency evidence is invalid: {latency_source}"
        ) from error
    if latency_from_file != int(result["sim_latency_cycles"]):
        raise RuntimeError(
            "PolarDecoder latency evidence disagrees with simulation_result.json: "
            f"file={latency_from_file}, json={result['sim_latency_cycles']}"
        )

    artifact_sources = {
        "waveform": waveform,
        "latency_output": latency_source,
        "simulation_log": Path(str(result.get("simulation_log", ""))),
    }
    published_names = {
        "waveform": "wave.vcd",
        "latency_output": "latency_output.txt",
        "simulation_log": "simulation.log",
    }
    for key, source in artifact_sources.items():
        if not source.exists() or not source.is_file():
            raise RuntimeError(f"PolarDecoder {key} artifact is missing: {source}")
        published = case_dir / published_names[key]
        if source.resolve() != published.resolve():
            shutil.copy2(source, published)
        result[f"workspace_{key}"] = str(source.resolve())
        result[key] = str(published.resolve())

    result["artifact_dir"] = str(case_dir.resolve())
    result["workspace"] = str(workspace.resolve())
    result["console_log"] = completed.stdout
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
