"""Unified full-metric adapter for CSub."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = PROJECT_ROOT / "Generator" / "BasicModules" / "CSub"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MODULE_ROOT))

from metrics_framework.adapters.basic_full import predict as predict_full, validate as validate_full  # noqa: E402
from metrics_framework.adapters.common import run_cli  # noqa: E402


def _module():
    import csub_metrics

    return csub_metrics


def predict(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    return predict_full("csub", _module(), config)


def validate(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    return validate_full("csub", "CSub", _module(), config_path, config)


if __name__ == "__main__":
    raise SystemExit(run_cli("csub", predict, validate))
