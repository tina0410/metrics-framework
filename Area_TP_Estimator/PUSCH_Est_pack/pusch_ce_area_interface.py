"""Single-case area interface for the PUSCH channel estimator."""

from __future__ import annotations

import contextlib
import io
import json
import math
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
MODEL_DIR = ROOT / "model"
PARAM_WORKBOOK = ROOT / "param.xlsx"
PARAM_SHEET = "parameters"


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    with path.open("r", encoding="utf-8-sig") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError(f"{path}: expected a JSON object")
    required = ("protocol", "architecture", "quantization", "arithmetic", "implementation")
    missing = [name for name in required if not isinstance(config.get(name), dict)]
    if missing:
        raise ValueError(f"{path}: missing object sections: {', '.join(missing)}")
    if not isinstance(config.get("area", {}), dict):
        raise ValueError(f"{path}: area must be an object")
    return config


def _flat_parameters(config: Mapping[str, Any]) -> dict[str, Any]:
    protocol = config["protocol"]
    architecture = config["architecture"]
    quants = config["quantization"]
    arithmetic = config["arithmetic"]
    implementation = config["implementation"]
    return {
        "num_RB_min": protocol["num_RB_range"][0],
        "num_RB_max": protocol["num_RB_range"][1],
        "num_symbols_min": protocol["num_symbols_range"][0],
        "num_symbols_max": protocol["num_symbols_range"][1],
        "is_ECP": protocol["is_ECP"],
        "dmrs_Uplink": protocol["dmrs_Uplink"],
        "dmrs_Type": protocol["dmrs_Type"],
        "is_double_dmrs": protocol["is_double_dmrs"],
        "is_enhanced": protocol["is_enhanced"],
        "dmrs_typeA_pos": protocol["dmrs_typeA_pos"],
        # The legacy row parser expects list-valued spreadsheet cells as
        # literal strings and converts them with ast.literal_eval.
        "additional_DMRS_range": repr(list(protocol["additional_DMRS_range"])),
        "antenna_ports": repr(list(protocol["antenna_ports"])),
        "slot_index_format": protocol["slot_index_format"],
        **architecture,
        **quants,
        **arithmetic,
        **implementation,
    }


def _ensure_pytv_importable() -> None:
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        import pytv  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    finally:
        sys.argv = original_argv
    # The repository carries the same lightweight compatibility package used
    # by behavioral verification.  A normal generator environment with
    # Verithon installed never takes this fallback.
    fallback = PROJECT_ROOT / "Generator" / "LSCE" / "BehaviorialVerification"
    if fallback.is_dir():
        sys.path.insert(0, str(fallback))


@lru_cache(maxsize=1)
def _area_resources() -> tuple[Any, Any, Any, Any, Any, Any]:
    required = (
        MODEL_DIR / "SU_in.xlsx",
        MODEL_DIR / "ADD_area.pkl",
        MODEL_DIR / "pure_MUL_area.pkl",
        MODEL_DIR / "SU_out_FxP_area.pkl",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("PUSCH_CE area model files are missing: " + ", ".join(missing))
    _ensure_pytv_importable()
    root_text = str(ROOT)
    sys.path.insert(0, root_text)
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        import Est_PUSCH
    finally:
        sys.argv = original_argv
        sys.path.remove(root_text)
    su_book = MODEL_DIR / "SU_in.xlsx"
    return (
        Est_PUSCH,
        pd.read_excel(su_book, sheet_name="SU_in"),
        pd.read_excel(su_book, sheet_name="Sub"),
        joblib.load(MODEL_DIR / "ADD_area.pkl"),
        joblib.load(MODEL_DIR / "pure_MUL_area.pkl"),
        joblib.load(MODEL_DIR / "SU_out_FxP_area.pkl"),
    )


def predict_area(config_path: str | Path) -> dict[str, float]:
    config = load_config(config_path)
    estimator, su_in, sub, model_add, model_mul, model_su = _area_resources()
    row = pd.Series(_flat_parameters(config))
    inputs = estimator._top_inputs_from_row(row)
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        evaluated = estimator.Est_Top(model_add, sub, model_mul, model_su, su_in, *inputs)
    prediction_time_ms = (time.perf_counter() - started) * 1000.0
    predicted = float(np.asarray(evaluated).ravel()[0])
    if not math.isfinite(predicted) or predicted <= 0:
        raise ValueError(f"PUSCH_CE area estimator returned invalid area: {predicted}")
    return {"predicted_area_um2": predicted, "prediction_time_ms": prediction_time_ms}


def _configured_positive(config: Mapping[str, Any], switch: str, value: str) -> float | None:
    area = config.get("area", {})
    enabled = area.get(switch, False)
    if not isinstance(enabled, bool):
        raise ValueError(f"area.{switch} must be boolean")
    if not enabled:
        return None
    try:
        result = float(area[value])
    except (KeyError, TypeError, ValueError):
        result = math.nan
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"area.{value} must be greater than zero when area.{switch}=true")
    return result


def _normal(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        text = value.strip()
        if text in ("", "None", "None (Jakes model)"):
            return None
        try:
            import ast
            return ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return text
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, tuple):
        return list(value)
    return value


def _same(left: Any, right: Any) -> bool:
    left, right = _normal(left), _normal(right)
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    return left == right


def read_reference_area(config: Mapping[str, Any]) -> dict[str, Any]:
    flat = _flat_parameters(config)
    params = pd.read_excel(PARAM_WORKBOOK, sheet_name=PARAM_SHEET)
    matches = []
    for index, row in params.iterrows():
        if all(key in row and _same(row[key], expected) for key, expected in flat.items()):
            matches.append((index, row))
    if len(matches) != 1:
        raise LookupError(f"expected one PUSCH_CE parameter row, found {len(matches)}")
    param_index, row = matches[0]
    design_id = int(row["design_id"])

    if pd.isna(row.get("area")):
        raise LookupError(f"no actual TOP area found for design{design_id}")
    actual = float(row["area"])
    if not math.isfinite(actual) or actual <= 0:
        raise ValueError(f"invalid actual TOP area for design{design_id}: {actual}")
    return {
        "actual_area_um2": actual,
        "design_id": design_id,
        "reference_sources": ["param.xlsx"],
        "parameter_excel_row": int(param_index) + 2,
    }


def evaluate_area(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    prediction = predict_area(config_path)
    configured_area = _configured_positive(
        config, "use_config_actual_area", "actual_area_um2"
    )
    configured_time = _configured_positive(
        config, "use_config_actual_time", "actual_time_ms"
    )
    reference = {} if configured_area is not None else read_reference_area(config)
    actual = configured_area if configured_area is not None else float(reference["actual_area_um2"])
    predicted = float(prediction["predicted_area_um2"])
    elapsed = float(prediction["prediction_time_ms"])
    return {
        **prediction,
        **reference,
        "actual_area_um2": actual,
        "error_percent": abs(predicted - actual) / actual * 100.0,
        "synthesis_time_ms": configured_time,
        "speedup": configured_time / elapsed if configured_time is not None else None,
        "actual_value_kind": "configured_known_value" if configured_area is not None else "historical_dc_reference",
    }


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"predict", "validate", "evaluate"}:
        print("usage: pusch_ce_area_interface.py predict|validate|evaluate CONFIG", file=sys.stderr)
        return 1
    try:
        action, path = sys.argv[1], Path(sys.argv[2])
        result = predict_area(path) if action == "predict" else (
            read_reference_area(load_config(path)) if action == "validate" else evaluate_area(path)
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
        return 0
    except (FileNotFoundError, LookupError, RuntimeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
