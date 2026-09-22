"""PUSCH_CE metrics adapter scaffold and area-process boundary.

The module is intentionally kept in ``registered`` state until the four metric
implementations have been reviewed.  This file fixes the adapter boundary and
validates the shared case schema without claiming executable predictions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from metrics_framework.adapters.common import run_cli


MODULE_NAME = "pusch_ce"
REQUIRED_SECTIONS = (
    "protocol",
    "architecture",
    "quantization",
    "arithmetic",
    "implementation",
    "area",
)


def validate_scaffold_config(config: Mapping[str, Any]) -> None:
    """Validate fields shared by every future PUSCH_CE metric implementation."""

    missing = [name for name in REQUIRED_SECTIONS if not isinstance(config.get(name), dict)]
    if missing:
        raise ValueError("missing object sections: " + ", ".join(missing))

    area = config["area"]
    for key in ("use_config_actual_area", "use_config_actual_time"):
        if key in area and not isinstance(area[key], bool):
            raise ValueError(f"area.{key} must be boolean")


def _area(action: str, config_path: Path) -> dict[str, Any]:
    """Run the legacy estimator in isolation, matching the MIMO adapter."""

    interface = (
        Path(__file__).resolve().parents[2]
        / "Area_TP_Estimator"
        / "PUSCH_Est_pack"
        / "pusch_ce_area_interface.py"
    )
    process = subprocess.run(
        [sys.executable, str(interface), action, str(config_path)],
        cwd=interface.parent,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip())
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("PUSCH_CE area interface returned invalid JSON") from error
    if not isinstance(result, dict):
        raise RuntimeError("PUSCH_CE area interface returned a non-object")
    return result


def _pending(config: dict[str, Any]) -> None:
    validate_scaffold_config(config)
    raise RuntimeError(
        "PUSCH_CE area evaluation is available, but the unified module remains "
        "registered until latency, throughput, and hardware complexity are reviewed"
    )


def predict(_config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    _pending(config)
    raise AssertionError("unreachable")


def validate(_config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    _pending(config)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE_NAME, predict, validate))
