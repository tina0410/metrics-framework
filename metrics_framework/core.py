"""Framework orchestration, subprocess isolation, persistence, and rendering."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = Path(__file__).with_name("registry.json")
PROTOCOL_VERSION = 1


class MetricsFrameworkError(RuntimeError):
    """Base error for framework failures."""


class EvaluationUnavailable(MetricsFrameworkError):
    """Raised when validation cannot produce a complete evaluation."""


class AdapterFailure(MetricsFrameworkError):
    """Raised when an adapter process fails or violates the protocol."""

    def __init__(self, message: str, *, returncode: int | None = None) -> None:
        super().__init__(message)
        self.returncode = returncode


class ConfigDigestMismatch(AdapterFailure):
    """A validation result cannot be paired with this config revision."""

    def __init__(self, message: str) -> None:
        super().__init__(message, returncode=2)


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    root: Path
    adapter: Path
    command: tuple[str, ...]
    config_dir: Path
    config_pattern: str
    default_cases: tuple[int, ...]
    python_env: str
    output_root: Path
    capabilities: frozenset[str]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def config_digest(path: Path) -> str:
    """Return a stable digest of parsed JSON, independent of formatting."""
    encoded = json.dumps(
        _read_json(path), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Registry:
    def __init__(self, path: str | Path = DEFAULT_REGISTRY) -> None:
        self.path = Path(path).resolve()
        raw = _read_json(self.path)
        if raw.get("schema_version") != 1:
            raise ValueError(f"Unsupported registry schema: {raw.get('schema_version')!r}")
        modules = raw.get("modules")
        if not isinstance(modules, dict) or not modules:
            raise ValueError("Registry must define at least one module")
        self._specs: dict[str, ModuleSpec] = {}
        for name, item in modules.items():
            if not isinstance(item, dict):
                raise ValueError(f"Registry module {name!r} must be an object")
            module_root = (ROOT / str(item["root"])).resolve()
            adapter = (ROOT / str(item["adapter"])).resolve()
            spec = ModuleSpec(
                name=name,
                root=module_root,
                adapter=adapter,
                command=tuple(
                    str(value)
                    for value in item.get("command", ["{python}", "{adapter}"])
                ),
                config_dir=(module_root / str(item["config_dir"])).resolve(),
                config_pattern=str(item["config_pattern"]),
                default_cases=tuple(int(case) for case in item["default_cases"]),
                python_env=str(item["python_env"]),
                output_root=(module_root / str(item["output_root"])).resolve(),
                capabilities=frozenset(str(value) for value in item["capabilities"]),
            )
            required = {"area", "latency", "throughput", "hardware_complexity"}
            if not spec.command:
                raise ValueError(f"Registry module {name!r} has an empty command")
            missing_capabilities = sorted(required - spec.capabilities)
            if missing_capabilities:
                raise ValueError(
                    f"Registry module {name!r} lacks required capabilities: "
                    + ", ".join(missing_capabilities)
                )
            if name in self._specs:
                raise ValueError(f"Duplicate module name: {name}")
            self._specs[name] = spec

    def get(self, name: str) -> ModuleSpec:
        try:
            spec = self._specs[name.lower()]
        except KeyError as error:
            supported = ", ".join(sorted(self._specs))
            raise ValueError(f"Unknown module {name!r}; supported modules: {supported}") from error
        if not spec.adapter.is_file():
            raise FileNotFoundError(f"Adapter not found for {name}: {spec.adapter}")
        return spec


def _candidate_interpreters(spec: ModuleSpec) -> Iterable[Path]:
    configured = os.environ.get(spec.python_env)
    if configured:
        yield Path(configured).expanduser()
    if os.name == "nt":
        yield spec.root / ".venv" / "Scripts" / "python.exe"
    else:
        yield spec.root / ".venv" / "bin" / "python"
    yield Path(sys.executable)


def _interpreter(spec: ModuleSpec) -> Path:
    for candidate in _candidate_interpreters(spec):
        if candidate.is_file():
            # Keep a POSIX virtualenv's python symlink intact. Resolving it to
            # /usr/bin/python discards the virtualenv prefix and site-packages.
            return candidate.absolute()
    raise FileNotFoundError(
        f"No Python interpreter found for {spec.name}; set {spec.python_env}"
    )


def resolve_configs(spec: ModuleSpec, selection: str | Path | None) -> list[Path]:
    if selection is None:
        paths = [
            spec.config_dir / spec.config_pattern.format(case=case)
            for case in spec.default_cases
        ]
    else:
        text = str(selection)
        if text.isdecimal():
            paths = [spec.config_dir / spec.config_pattern.format(case=int(text))]
        else:
            candidate = Path(selection).expanduser()
            paths = [candidate if candidate.is_absolute() else (Path.cwd() / candidate)]
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Config file not found: " + ", ".join(map(str, missing)))
    return [path.resolve() for path in paths]


def _output_dir(spec: ModuleSpec, config_path: Path) -> Path:
    if config_path.is_relative_to(spec.root):
        return spec.output_root / config_path.stem
    config = _read_json(config_path)
    configured = config.get("flow", {}).get("output_dir", "evaluation_output")
    return (config_path.parent / str(configured)).resolve()


def _run_adapter(spec: ModuleSpec, action: str, config_path: Path) -> dict[str, Any]:
    interpreter = (
        str(_interpreter(spec))
        if any("{python}" in token for token in spec.command)
        else ""
    )
    replacements = {
        "python": interpreter,
        "adapter": str(spec.adapter),
        "action": action,
        "config": str(config_path),
    }
    command = [token.format_map(replacements) for token in spec.command]
    if not any("{action}" in token for token in spec.command):
        command.append(action)
    if not any("{config}" in token for token in spec.command):
        command.append(str(config_path))
    process = subprocess.run(
        command,
        cwd=spec.root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        details = process.stdout.strip() or process.stderr.strip()
        raise AdapterFailure(
            details or f"{spec.name} {action} adapter exited with {process.returncode}",
            returncode=process.returncode,
        )
    if process.stderr:
        print(process.stderr, end="" if process.stderr.endswith("\n") else "\n", file=sys.stderr)
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise AdapterFailure(
            f"{spec.name} {action} adapter returned invalid JSON"
        ) from error
    if not isinstance(result, dict):
        raise AdapterFailure(f"{spec.name} {action} adapter returned a non-object")
    if result.get("protocol_version") != PROTOCOL_VERSION:
        raise AdapterFailure(
            f"{spec.name} adapter protocol mismatch: {result.get('protocol_version')!r}"
        )
    if result.get("status") != "ok":
        raise AdapterFailure(f"{spec.name} adapter returned non-success status")
    if result.get("module") != spec.name or result.get("action") != action:
        raise AdapterFailure(f"{spec.name} adapter returned mismatched identity")
    expected_digest = config_digest(config_path)
    if result.get("config_digest") != expected_digest:
        raise ConfigDigestMismatch(
            f"{spec.name} prediction and validation config digests differ"
        )
    return result


def _prediction_view(result: Mapping[str, Any]) -> dict[str, Any]:
    module = str(result["module"])
    metrics = result["metrics"]
    latency = metrics["latency"]
    area = metrics["area"]
    throughput = metrics["throughput"]
    complexity = metrics["hardware_complexity"]
    view: dict[str, Any] = {
        "延迟": {
            "预测结果 (cycles)": latency["predicted_cycles"],
            "预测时间 (ms)": round(float(latency["prediction_time_ms"]), 6),
        }
    }
    if module == "bp":
        view["round前迭代次数 (iter)"] = {
            "模型原始输出 (iter)": round(float(metrics["iterations"]["predicted"]), 6)
        }
    view.update(
        {
            "面积": {
                "预测结果 (μm²)": round(float(area["predicted_um2"]), 2),
                "预测时间 (ms)": round(float(area["prediction_time_ms"]), 6),
            },
            "Throughput": {
                f"预测结果 ({throughput['unit']})": round(
                    float(throughput["predicted"]), int(throughput["precision"])
                )
            },
            "硬件复杂度": {
                "预测结果 (GE·cycles)": round(float(complexity["predicted_ge_cycles"]), 2),
                "GE基准单元": complexity["ge_reference_cell"],
                "1 GE面积 (μm²)": complexity["ge_area_um2"],
            },
        }
    )
    return view


def _positive(value: Any, name: str) -> float:
    if value is None:
        raise EvaluationUnavailable(f"Validation did not provide {name}")
    number = float(value)
    if number <= 0:
        raise EvaluationUnavailable(f"Validation provided invalid {name}: {value!r}")
    return number


def _evaluation_view(
    prediction: Mapping[str, Any], validation: Mapping[str, Any]
) -> dict[str, Any]:
    if prediction["config_digest"] != validation["config_digest"]:
        raise EvaluationUnavailable("Prediction and validation config digests differ")
    module = str(prediction["module"])
    predicted = prediction["metrics"]
    actual = validation["metrics"]

    predicted_latency = _positive(predicted["latency"]["predicted_cycles"], "predicted latency")
    actual_latency = _positive(actual["latency"].get("actual_cycles"), "actual latency")
    latency_prediction_time = _positive(
        predicted["latency"]["prediction_time_ms"], "latency prediction time"
    )
    latency_validation_time = actual["latency"].get("simulation_time_ms")
    latency_reported_speedup = actual["latency"].get("reported_speedup")
    if latency_validation_time is None:
        speedup = _positive(latency_reported_speedup, "latency speedup")
        latency_validation_time = speedup * latency_prediction_time
    latency_validation_time = _positive(latency_validation_time, "latency simulation time")
    latency_speedup = latency_validation_time / latency_prediction_time

    predicted_area = _positive(predicted["area"]["predicted_um2"], "predicted area")
    actual_area = _positive(actual["area"].get("actual_um2"), "actual area")
    area_prediction_time = _positive(
        predicted["area"]["prediction_time_ms"], "area prediction time"
    )
    synthesis_time = actual["area"].get("synthesis_time_ms")
    area_reported_speedup = actual["area"].get("reported_speedup")
    if synthesis_time is None:
        speedup = _positive(area_reported_speedup, "area speedup")
        synthesis_time = speedup * area_prediction_time
    synthesis_time = _positive(synthesis_time, "synthesis time")
    area_speedup = synthesis_time / area_prediction_time

    predicted_throughput = _positive(
        predicted["throughput"]["predicted"], "predicted throughput"
    )
    actual_throughput = _positive(actual["throughput"].get("actual"), "actual throughput")
    predicted_complexity = _positive(
        predicted["hardware_complexity"]["predicted_ge_cycles"],
        "predicted hardware complexity",
    )
    actual_complexity = _positive(
        actual["hardware_complexity"].get("actual_ge_cycles"),
        "actual hardware complexity",
    )

    latency_error = (actual_latency - predicted_latency) / predicted_latency * 100.0
    area_error = abs(predicted_area - actual_area) / actual_area * 100.0
    complexity_error = abs(predicted_complexity - actual_complexity) / actual_complexity * 100.0
    throughput = predicted["throughput"]
    view: dict[str, Any] = {
        "延迟": {
            "预测结果 (cycles)": int(predicted_latency),
            "仿真结果 (cycles)": int(actual_latency),
            "误差 (%)": round(latency_error, 2),
            "预测时间 (ms)": round(latency_prediction_time, 6),
            "仿真时间 (ms)": round(latency_validation_time, 3),
            "速度提升倍数 (×)": round(latency_speedup, 2),
        }
    }
    if module == "bp":
        predicted_iterations = _positive(predicted["iterations"]["predicted"], "predicted iterations")
        actual_iterations = _positive(actual["iterations"].get("actual"), "actual iterations")
        view["round前迭代次数 (iter)"] = {
            "模型原始输出 (iter)": round(predicted_iterations, 6),
            "C++仿真值 (iter)": round(actual_iterations, 6),
            "误差 (%)": round(
                (actual_iterations - predicted_iterations) / predicted_iterations * 100.0,
                2,
            ),
        }
    view.update(
        {
            "面积": {
                "预测结果 (μm²)": round(predicted_area, 2),
                "真实结果 (μm²)": round(actual_area, 2),
                "误差 (%)": round(area_error, 2),
                "预测时间 (ms)": round(area_prediction_time, 6),
                "综合时间 (ms)": round(synthesis_time, 3),
                "速度提升倍数 (×)": round(area_speedup, 2),
            },
            "Throughput": {
                f"预测结果 ({throughput['unit']})": round(
                    predicted_throughput, int(throughput["precision"])
                ),
                f"仿真结果 ({throughput['unit']})": round(
                    actual_throughput, int(throughput["precision"])
                ),
            },
            "硬件复杂度": {
                "预测结果 (GE·cycles)": round(predicted_complexity, 2),
                ("仿真结果 (GE·cycles)" if module == "bp" else "真实结果 (GE·cycles)"): round(
                    actual_complexity, 2
                ),
                "误差 (%)": round(complexity_error, 2),
                "GE基准单元": predicted["hardware_complexity"]["ge_reference_cell"],
                "1 GE面积 (μm²)": predicted["hardware_complexity"]["ge_area_um2"],
            },
        }
    )
    return view


def _prepare_paths(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("prediction.json", "evaluation.json"):
        (output_dir / name).unlink(missing_ok=True)
    for name in ("prediction.json", "evaluation_error.json"):
        (output_dir / "diagnostics" / name).unlink(missing_ok=True)


def _save_diagnostic(output_dir: Path, name: str, value: Mapping[str, Any]) -> None:
    _write_json(output_dir / "diagnostics" / name, value)


def _shape_results(results: list[tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    if len(results) == 1:
        return results[0][1]
    return {path.stem: result for path, result in results}


def predict(
    module: str,
    config: str | Path | None = None,
    *,
    registry: str | Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    spec = Registry(registry).get(module)
    rendered: list[tuple[Path, dict[str, Any]]] = []
    for path in resolve_configs(spec, config):
        output_dir = _output_dir(spec, path)
        _prepare_paths(output_dir)
        raw = _run_adapter(spec, "predict", path)
        view = _prediction_view(raw)
        _write_json(output_dir / "prediction.json", view)
        rendered.append((path, view))
    return _shape_results(rendered)


def evaluate(
    module: str,
    config: str | Path | None = None,
    *,
    registry: str | Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    spec = Registry(registry).get(module)
    rendered: list[tuple[Path, dict[str, Any]]] = []
    failures: list[str] = []
    for path in resolve_configs(spec, config):
        output_dir = _output_dir(spec, path)
        _prepare_paths(output_dir)
        evaluation_started = time.perf_counter()
        prediction_raw: dict[str, Any] | None = None
        try:
            prediction_raw = _run_adapter(spec, "predict", path)
        except (AdapterFailure, OSError, ValueError) as error:
            diagnostic = {
                "module": spec.name,
                "config": str(path),
                "error_type": type(error).__name__,
                "message": str(error),
            }
            _save_diagnostic(output_dir, "evaluation_error.json", diagnostic)
            raise
        try:
            validation_raw = _run_adapter(spec, "validate", path)
            view = _evaluation_view(prediction_raw, validation_raw)
            view["评估总时间 (s)"] = round(
                time.perf_counter() - evaluation_started,
                3,
            )
            _write_json(output_dir / "evaluation.json", view)
            rendered.append((path, view))
        except AdapterFailure as error:
            if error.returncode != 2:
                _save_diagnostic(
                    output_dir,
                    "evaluation_error.json",
                    {
                        "module": spec.name,
                        "config": str(path),
                        "error_type": type(error).__name__,
                        "message": str(error),
                    },
                )
                raise
            unavailable = EvaluationUnavailable(str(error))
            _save_diagnostic(output_dir, "prediction.json", prediction_raw)
            _save_diagnostic(
                output_dir,
                "evaluation_error.json",
                {
                    "module": spec.name,
                    "config": str(path),
                    "error_type": type(unavailable).__name__,
                    "message": str(unavailable),
                },
            )
            failures.append(f"{path.stem}: {unavailable}")
        except (EvaluationUnavailable, OSError, ValueError) as error:
            if prediction_raw is not None:
                _save_diagnostic(output_dir, "prediction.json", prediction_raw)
            diagnostic = {
                "module": spec.name,
                "config": str(path),
                "error_type": type(error).__name__,
                "message": str(error),
            }
            _save_diagnostic(output_dir, "evaluation_error.json", diagnostic)
            failures.append(f"{path.stem}: {error}")
    if failures:
        raise EvaluationUnavailable("; ".join(failures))
    return _shape_results(rendered)
