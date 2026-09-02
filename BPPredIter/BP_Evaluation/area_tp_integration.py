"""Boundary between BP metrics and the canonical Area/TP estimator."""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parent
DEFAULT_AREA_PROJECT = (
    ROOT.parent.parent / "Area_TP_Estimator" / "Est_Polar_BP_Decoder"
)


@lru_cache(maxsize=1)
def _load_area_module(project_dir: Path = DEFAULT_AREA_PROJECT) -> ModuleType:
    module_path = project_dir / "area_evaluation.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Area/TP evaluation module not found: {module_path}")
    spec = importlib.util.spec_from_file_location("canonical_bp_area_evaluation", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Area/TP evaluation module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(project_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def evaluate_bp_area(
    architecture: str,
    algorithm: str,
    n: int,
    m: int,
    width: int,
    *,
    actual_area_um2: float | None = None,
    synthesis_time_ms: float | None = None,
) -> dict[str, float | str | None]:
    """Evaluate predicted area with a workbook or config actual-area reference."""
    module = _load_area_module()
    return module.evaluate_area(
        architecture,
        algorithm,
        n,
        m,
        width,
        actual_area_um2=actual_area_um2,
        synthesis_time_ms=synthesis_time_ms,
    )
