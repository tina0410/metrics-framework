"""Shared adapter protocol and validation-config helpers."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable, Mapping


PROTOCOL_VERSION = 1


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def digest(config: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        config, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def positive_optional(value: Any, name: str) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric or null") from error
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def validation_section(config: Mapping[str, Any], section: str) -> dict[str, Any]:
    validation = config.get("validation", {})
    if validation is None:
        return {}
    if not isinstance(validation, dict):
        raise ValueError("validation must be a JSON object")
    value = validation.get(section, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"validation.{section} must be a JSON object")
    return value


def configured_area(config: Mapping[str, Any]) -> tuple[float | None, float | None, float | None]:
    section = validation_section(config, "area")
    actual = positive_optional(section.get("actual_um2"), "validation.area.actual_um2")
    synthesis = positive_optional(
        section.get("synthesis_time_ms"), "validation.area.synthesis_time_ms"
    )
    speedup = positive_optional(
        section.get("reported_speedup"), "validation.area.reported_speedup"
    )
    legacy = config.get("area", {})
    if not isinstance(legacy, dict):
        raise ValueError("area must be a JSON object")
    if actual is None and legacy.get("use_config_actual_area") is True:
        actual = positive_optional(legacy.get("actual_area_um2"), "area.actual_area_um2")
    if synthesis is None and (
        legacy.get("use_config_actual_time") is True
        or legacy.get("use_config_actual_area") is True
    ):
        synthesis = positive_optional(
            legacy.get("actual_time_ms", legacy.get("synthesis_time_ms")),
            "area synthesis time",
        )
    return actual, synthesis, speedup


def configured_latency(
    config: Mapping[str, Any],
) -> tuple[int | None, float | None, int | None, float | None]:
    section = validation_section(config, "latency")
    cycles_value = positive_optional(
        section.get("actual_cycles"), "validation.latency.actual_cycles"
    )
    interval_value = positive_optional(
        section.get("output_interval_cycles"),
        "validation.latency.output_interval_cycles",
    )
    simulation_time = positive_optional(
        section.get("simulation_time_ms"),
        "validation.latency.simulation_time_ms",
    )
    speedup = positive_optional(
        section.get("reported_speedup"),
        "validation.latency.reported_speedup",
    )
    cycles = int(cycles_value) if cycles_value is not None else None
    interval = int(interval_value) if interval_value is not None else None
    if cycles_value is not None and cycles != cycles_value:
        raise ValueError("validation.latency.actual_cycles must be an integer")
    if interval_value is not None and interval != interval_value:
        raise ValueError("validation.latency.output_interval_cycles must be an integer")
    return cycles, simulation_time, interval, speedup


def response(
    module: str,
    action: str,
    config_path: Path,
    config: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "status": "ok",
        "module": module,
        "action": action,
        "config_path": str(config_path),
        "config_digest": digest(config),
        "evidence_paths": [str(config_path)],
        "metrics": metrics,
    }


def run_cli(
    module: str,
    predict: Callable[[Path, dict[str, Any]], Mapping[str, Any]],
    validate: Callable[[Path, dict[str, Any]], Mapping[str, Any]],
) -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"predict", "validate"}:
        print(f"usage: {Path(sys.argv[0]).name} predict|validate CONFIG", file=sys.stderr)
        return 1
    action = sys.argv[1]
    path = Path(sys.argv[2]).expanduser().resolve()
    try:
        config = load_config(path)
        operation = predict if action == "predict" else validate
        with contextlib.redirect_stdout(sys.stderr):
            metrics = operation(path, config)
        sys.stdout.write(
            json.dumps(
                response(module, action, path, config, metrics), ensure_ascii=False
            )
        )
        return 0
    except (FileNotFoundError, LookupError, RuntimeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"Unexpected {type(error).__name__}: {error}", file=sys.stderr)
        return 1
