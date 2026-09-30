"""Area, throughput, and fixed-point complexity helpers for basic modules."""

from __future__ import annotations

import ast
import importlib.util
import math
import re
import sys
import time
import warnings
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree

from metrics_framework.adapters.common import positive_optional, validation_section


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AREA_ROOT = PROJECT_ROOT / "Area_TP_Estimator"
GE_REFERENCE_CELL = "LVT_NAND2HDV0"
STANDARD_CELL_AREA_FILE = AREA_ROOT / "65nm Standard Cells Area.txt"

MODULE_DIRECTORIES = {
    "abs": "Abs",
    "addertree": "AdderTree",
    "cadd": "CAdd",
    "cmul": "CMul",
    "cnorm": "CNorm",
    "comp": "Comp",
    "comptree": "CompTree",
    "counter": "Counter",
    "csub": "CSub",
    "delay": "Delay",
    "fxmatch": "FxMatch",
    "mux": "MUX",
    "neg": "Neg",
    "sub": "Sub",
    "sxmatch": "SxMatch",
}

MODEL_FILES = {
    "abs": ("ABS_area_model.pkl",),
    "addertree": ("ADDERTREE_area_model.pkl", "ADD_comb_area.pkl"),
    "cadd": ("ADD_comb_area.pkl",),
    "cmul": ("CMUL_area_model.pkl", "MUL_area_model.pkl", "ADD_comb_area.pkl"),
    "cnorm": ("CNORM_area_model.pkl", "ABS_area_model.pkl", "ADD_comb_area.pkl"),
    "comp": ("COMP_area_model.pkl",),
    "comptree": ("COMPTREE_area_model.pkl", "COMP_area_model.pkl"),
    "counter": ("COUNTER_area_model.pkl",),
    "csub": ("SUB_comb_area.pkl",),
    "mux": ("MUX_area_model.pkl",),
    "neg": ("NEG_area_model.pkl",),
    "sub": ("SUB_comb_area.pkl",),
}

ESTIMATOR_FUNCTIONS = {
    name: f"Est_{directory}" for name, directory in MODULE_DIRECTORIES.items()
}
ESTIMATOR_FUNCTIONS["sub"] = "Est_SUB"


def _quantization(config: Mapping[str, Any], key: str) -> tuple[int, int, int]:
    value = config.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a JSON object")
    try:
        return (
            int(value["bitwidth"]),
            int(value["fractional_width"]),
            int(bool(value["signed"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{key} must define bitwidth, fractional_width, and signed") from error


def _pipeline(config: Mapping[str, Any]) -> int:
    return int(config.get("n_pipeline", 0))


def _reset(config: Mapping[str, Any]) -> Any:
    return config.get("if_rst_n", config.get("IF_RST_N", False))


def _nonnegative_optional(value: Any, name: str) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric or null") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be greater than or equal to zero")
    return number


def _configured_area(
    config: Mapping[str, Any],
) -> tuple[float | None, float | None, float | None]:
    section = validation_section(config, "area")
    actual = _nonnegative_optional(section.get("actual_um2"), "validation.area.actual_um2")
    synthesis = positive_optional(
        section.get("synthesis_time_ms"), "validation.area.synthesis_time_ms"
    )
    speedup = positive_optional(
        section.get("reported_speedup"), "validation.area.reported_speedup"
    )
    legacy = config.get("area", {})
    if not isinstance(legacy, Mapping):
        raise ValueError("area must be a JSON object")
    if actual is None and legacy.get("use_config_actual_area") is True:
        actual = _nonnegative_optional(legacy.get("actual_area_um2"), "area.actual_area_um2")
    if synthesis is None and (
        legacy.get("use_config_actual_time") is True
        or legacy.get("use_config_actual_area") is True
    ):
        synthesis = positive_optional(
            legacy.get("actual_time_ms", legacy.get("synthesis_time_ms")),
            "area synthesis time",
        )
    return actual, synthesis, speedup


@lru_cache(maxsize=None)
def _load_estimator(module_name: str) -> Any:
    directory = MODULE_DIRECTORIES[module_name]
    estimator_root = AREA_ROOT / directory / "est"
    path = estimator_root / f"Est_{directory}.py"
    if not path.is_file():
        raise FileNotFoundError(f"Area estimator not found: {path}")
    sys.path.insert(0, str(estimator_root))
    spec = importlib.util.spec_from_file_location(f"area_estimator_{module_name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load area estimator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def _load_models(module_name: str) -> tuple[Any, ...]:
    filenames = MODEL_FILES.get(module_name, ())
    if not filenames:
        return ()
    try:
        import joblib
    except ImportError as error:
        raise RuntimeError(
            "Basic-module area models require joblib, numpy, and scikit-learn"
        ) from error
    model_root = AREA_ROOT / MODULE_DIRECTORIES[module_name] / "est" / "model"
    try:
        from sklearn.exceptions import InconsistentVersionWarning
    except ImportError:
        warning_types: tuple[type[Warning], ...] = ()
    else:
        warning_types = (InconsistentVersionWarning,)
    with warnings.catch_warnings():
        for warning_type in warning_types:
            warnings.simplefilter("ignore", warning_type)
        return tuple(joblib.load(model_root / filename) for filename in filenames)


def _estimator_arguments(
    module_name: str, config: Mapping[str, Any], models: tuple[Any, ...]
) -> tuple[Any, ...]:
    unary = {"abs", "cnorm", "fxmatch", "neg", "sxmatch"}
    binary = {"cadd", "cmul", "csub", "comp", "sub"}
    if module_name in unary:
        base: tuple[Any, ...] = (*_quantization(config, "input"), *_quantization(config, "output"))
        if module_name == "sxmatch":
            base += (int(config["shift"]),)
        base += (_pipeline(config), _reset(config))
    elif module_name in binary:
        base = (
            *_quantization(config, "input_1"),
            *_quantization(config, "input_2"),
            *_quantization(config, "output"),
            _pipeline(config),
            _reset(config),
        )
        if module_name == "sub":
            base = base[:8] + base[9:]
        if module_name == "cmul":
            base += (str(config.get("method", "4mul")),)
        if module_name == "comp":
            outputs = config.get("outputs", {})
            if not isinstance(outputs, Mapping):
                raise ValueError("outputs must be a JSON object")
            base += tuple(
                bool(outputs.get(key, False))
                for key in (
                    "greater_index",
                    "less_index",
                    "equal_index",
                    "greater_value",
                    "less_value",
                )
            )
    elif module_name in {"addertree", "comptree"}:
        base = (
            *_quantization(config, "input"),
            *_quantization(config, "output"),
            int(config["n_inputs"]),
            _pipeline(config),
            str(config.get("config_mode", "A")),
            _reset(config),
        )
        if module_name == "comptree":
            outputs = config.get("outputs", {})
            if not isinstance(outputs, Mapping):
                raise ValueError("outputs must be a JSON object")
            base += tuple(
                bool(outputs.get(key, False))
                for key in ("greater_index", "less_index", "greater_value", "less_value")
            )
    elif module_name == "counter":
        base = tuple(
            config[key] for key in ("DWT", "STEP", "IF_RST_N", "HAS_CLEAR", "HAS_WRAP")
        )
    elif module_name == "delay":
        base = (int(config["data_width"]), _pipeline(config), _reset(config))
    elif module_name == "mux":
        base = (int(config["n_inputs"]), int(config["data_width"]))
    else:
        raise ValueError(f"Unsupported basic-module area estimator: {module_name}")
    return (*models, *base)


def predict_area(module_name: str, config: Mapping[str, Any]) -> tuple[float, float]:
    estimator = _load_estimator(module_name)
    models = _load_models(module_name)
    operation = getattr(estimator, ESTIMATOR_FUNCTIONS[module_name])
    arguments = _estimator_arguments(module_name, config, models)
    started = time.perf_counter()
    area = float(operation(*arguments))
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if not math.isfinite(area) or area < 0:
        raise ValueError(f"{module_name} area estimator returned invalid area: {area!r}")
    return area, elapsed_ms


def _output_width(config: Mapping[str, Any], module_name: str) -> int:
    if module_name == "counter":
        return int(config["DWT"])
    if module_name in {"delay", "mux"}:
        return int(config["data_width"])
    output = config.get("output")
    if not isinstance(output, Mapping):
        raise ValueError("output must be a JSON object")
    return int(output["bitwidth"])


def throughput_gbps(
    module_name: str, config: Mapping[str, Any], *, interval_cycles: int = 1
) -> float:
    clock = config.get("clock")
    if not isinstance(clock, Mapping):
        raise ValueError("clock must be a JSON object")
    period_ns = float(clock["period_ns"])
    if period_ns <= 0 or interval_cycles < 1:
        raise ValueError("clock period and output interval must be positive")
    return _output_width(config, module_name) / (period_ns * interval_cycles)


@lru_cache(maxsize=1)
def read_ge_area() -> float:
    pattern = re.compile(
        rf"^Cell:\s+[^,]*/{re.escape(GE_REFERENCE_CELL)},\s*Area:\s*([0-9]+(?:\.[0-9]+)?)\s*$"
    )
    matches = [
        float(match.group(1))
        for line in STANDARD_CELL_AREA_FILE.read_text(encoding="utf-8").splitlines()
        if (match := pattern.match(line.strip()))
    ]
    if len(matches) != 1 or matches[0] <= 0:
        raise LookupError(f"Expected one positive {GE_REFERENCE_CELL} area entry")
    return matches[0]


def prediction_metrics(
    module_name: str, config: Mapping[str, Any], latency_cycles: int
) -> dict[str, Any]:
    area, area_time_ms = predict_area(module_name, config)
    started = time.perf_counter()
    throughput = throughput_gbps(module_name, config)
    throughput_time_ms = (time.perf_counter() - started) * 1000.0
    ge_area = read_ge_area()
    started = time.perf_counter()
    complexity = area / ge_area * max(1, int(latency_cycles))
    complexity_time_ms = (time.perf_counter() - started) * 1000.0
    return {
        "area": {
            "predicted_um2": area,
            "prediction_time_ms": area_time_ms,
            "source": "Area_TP_Estimator/est",
        },
        "throughput": {
            "predicted": throughput,
            "unit": "Gbps",
            "precision": 3,
            "prediction_time_ms": throughput_time_ms,
            "source": "effective_output_bits",
        },
        "hardware_complexity": {
            "predicted_ge_cycles": complexity,
            "prediction_time_ms": complexity_time_ms,
            "ge_reference_cell": GE_REFERENCE_CELL,
            "ge_area_um2": ge_area,
            "source": "derived",
        },
    }


def _column_number(reference: str) -> int:
    result = 0
    for character in reference:
        if character.isalpha():
            result = result * 26 + ord(character.upper()) - ord("A") + 1
    return result


@lru_cache(maxsize=None)
def _xlsx_rows(path: Path, sheet_name: str) -> tuple[dict[str, Any], ...]:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{{{main_ns}}}si"):
                shared.append("".join(node.text or "" for node in item.iter(f"{{{main_ns}}}t")))
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relation_id = None
        for sheet in workbook.findall(f".//{{{main_ns}}}sheet"):
            if sheet.get("name") == sheet_name:
                relation_id = sheet.get(f"{{{rel_ns}}}id")
                break
        if relation_id is None:
            raise LookupError(f"Workbook {path.name} has no sheet {sheet_name!r}")
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = None
        for relation in relationships.findall(f"{{{package_ns}}}Relationship"):
            if relation.get("Id") == relation_id:
                target = relation.get("Target")
                break
        if target is None:
            raise LookupError(f"Workbook relation {relation_id!r} is missing")
        worksheet_path = target.lstrip("/")
        if not worksheet_path.startswith("xl/"):
            worksheet_path = "xl/" + worksheet_path
        worksheet = ElementTree.fromstring(archive.read(worksheet_path))
        raw_rows: list[list[Any]] = []
        for row in worksheet.findall(f".//{{{main_ns}}}sheetData/{{{main_ns}}}row"):
            values: list[Any] = []
            for cell in row.findall(f"{{{main_ns}}}c"):
                column = _column_number(cell.get("r", ""))
                while len(values) < column:
                    values.append(None)
                data_type = cell.get("t")
                value_node = cell.find(f"{{{main_ns}}}v")
                if data_type == "inlineStr":
                    inline = cell.find(f"{{{main_ns}}}is")
                    value: Any = "" if inline is None else "".join(
                        node.text or "" for node in inline.iter(f"{{{main_ns}}}t")
                    )
                elif value_node is None or value_node.text is None:
                    value = None
                elif data_type == "s":
                    value = shared[int(value_node.text)]
                elif data_type == "b":
                    value = value_node.text == "1"
                elif data_type in {"str", "e"}:
                    value = value_node.text
                else:
                    number = float(value_node.text)
                    value = int(number) if number.is_integer() else number
                values[column - 1] = value
            raw_rows.append(values)
    if not raw_rows:
        return ()
    headers = [str(value) if value is not None else f"column_{index}" for index, value in enumerate(raw_rows[0])]
    return tuple(
        {header: row[index] if index < len(row) else None for index, header in enumerate(headers)}
        for row in raw_rows[1:]
    )


def _report_expected(module_name: str, config: Mapping[str, Any]) -> dict[str, Any]:
    quantization = config.get("quantization_mode", "TRN.TCPL")
    overflow = config.get("overflow_mode", "WRP.TCPL")
    reset = _reset(config)
    common = {"QU_MODE": quantization, "OF_MODE": overflow, "IF_RST_N": reset}
    if module_name in {"abs", "cnorm", "fxmatch", "neg", "sxmatch"}:
        source = _quantization(config, "input")
        output = _quantization(config, "output")
        expected = {
            "QU_IN_DWT": source[0], "QU_IN_FRAC": source[1], "QU_IN_IF_SIGNED": bool(source[2]),
            "QU_OUT_DWT": output[0], "QU_OUT_FRAC": output[1], "QU_OUT_IF_SIGNED": bool(output[2]),
            "N_CLK": _pipeline(config), **common,
        }
        if module_name == "sxmatch":
            expected["SHIFT"] = int(config["shift"])
        return expected
    if module_name in {"cadd", "cmul", "csub", "comp", "sub"}:
        first = _quantization(config, "input_1")
        second = _quantization(config, "input_2")
        output = _quantization(config, "output")
        expected = {
            "QU_IN_1_DWT": first[0], "QU_IN_1_FRAC": first[1], "QU_IN_1_IF_SIGNED": bool(first[2]),
            "QU_IN_2_DWT": second[0], "QU_IN_2_FRAC": second[1], "QU_IN_2_IF_SIGNED": bool(second[2]),
            "QU_OUT_DWT": output[0], "QU_OUT_FRAC": output[1], "QU_OUT_IF_SIGNED": bool(output[2]),
            "N_PIPELINES" if module_name == "comp" else "N_CLK": _pipeline(config), **common,
        }
        if module_name == "cmul":
            expected["METHOD"] = str(config.get("method", "4mul"))
        if module_name == "comp":
            outputs = config.get("outputs", {})
            flag_columns = {
                "IF_GIDX": "greater_index", "IF_LIDX": "less_index", "IF_EIDX": "equal_index",
                "IF_GVAL": "greater_value", "IF_LVAL": "less_value",
            }
            expected.update({column: bool(outputs.get(key, False)) for column, key in flag_columns.items()})
        return expected
    if module_name in {"addertree", "comptree"}:
        source = _quantization(config, "input")
        output = _quantization(config, "output")
        expected = {
            "QU_IN": f"QuType({source[0]},{source[1]},{'T' if source[2] else 'F'})",
            "QU_OUT_DWT": output[0], "QU_OUT_FRAC": output[1], "QU_OUT_IF_SIGNED": bool(output[2]),
            "N_PIPELINES": _pipeline(config), "N_INPUTS": int(config["n_inputs"]),
            "CONFIG_MODE": str(config.get("config_mode", "A")), **common,
        }
        if module_name == "comptree":
            outputs = config.get("outputs", {})
            flag_columns = {
                "IF_GIDX": "greater_index", "IF_LIDX": "less_index", "IF_EIDX": "equal_index",
                "IF_GVAL": "greater_value", "IF_LVAL": "less_value",
            }
            expected.update({column: bool(outputs.get(key, False)) for column, key in flag_columns.items()})
        return expected
    if module_name == "counter":
        return {key: config[key] for key in ("DWT", "STEP", "IF_RST_N", "HAS_CLEAR", "HAS_WRAP")}
    if module_name == "delay":
        return {"DWT": int(config["data_width"]), "N_CLK": _pipeline(config), "IF_RST_N": reset}
    if module_name == "mux":
        return {"N_INPUTS": int(config["n_inputs"]), "DWT": int(config["data_width"])}
    raise ValueError(f"Unsupported report mapping: {module_name}")


def _normalized(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_normalized(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        if "|" in text:
            return tuple(_normalized(part) for part in text.split("|"))
        if text.lower() == "true":
            return True
        if text.lower() == "false":
            return False
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            try:
                number = float(text)
            except ValueError:
                return text
            return int(number) if number.is_integer() else number
        return _normalized(parsed)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def read_area_reference(module_name: str, config: Mapping[str, Any]) -> dict[str, float]:
    directory = MODULE_DIRECTORIES[module_name]
    report_root = AREA_ROOT / directory / "report"
    workbook = report_root / ("test.xlsx" if (report_root / "test.xlsx").is_file() else "basic.xlsx")
    expected = _report_expected(module_name, config)
    matches = [
        row for row in _xlsx_rows(workbook, directory)
        if all(_normalized(row.get(key)) == _normalized(value) for key, value in expected.items())
    ]
    if len(matches) != 1:
        raise LookupError(
            f"{workbook.name}/{directory} expected one DC row for the configured parameters, "
            f"found {len(matches)}; provide validation.area.actual_um2 and either "
            "synthesis_time_ms or reported_speedup"
        )
    row = matches[0]
    values = list(row.values())
    actual_area = float(row["area"])
    synthesis_time_ms = float(values[-2]) * 1000.0
    if actual_area <= 0 or synthesis_time_ms <= 0:
        raise ValueError(f"{workbook.name}/{directory} contains non-positive DC data")
    return {
        "actual_area_um2": actual_area,
        "synthesis_time_ms": synthesis_time_ms,
        "source": f"Area_TP_Estimator/{directory}/report/{workbook.name}",
    }


def validation_metrics(
    module_name: str,
    config: Mapping[str, Any],
    actual_cycles: int,
    *,
    interval_cycles: int = 1,
) -> dict[str, Any]:
    actual_area, synthesis_time, area_speedup = _configured_area(config)
    configured = any(value is not None for value in (actual_area, synthesis_time, area_speedup))
    source = "config"
    if actual_area is None or (synthesis_time is None and area_speedup is None):
        reference = read_area_reference(module_name, config)
        actual_area = actual_area or reference["actual_area_um2"]
        synthesis_time = synthesis_time or reference["synthesis_time_ms"]
        source = f"config+{reference['source']}" if configured else reference["source"]
    ge_area = read_ge_area()
    return {
        "area": {
            "actual_um2": actual_area,
            "synthesis_time_ms": synthesis_time,
            "reported_speedup": area_speedup,
            "source": source,
        },
        "throughput": {
            "actual": throughput_gbps(module_name, config, interval_cycles=interval_cycles),
            "source": "rtl_output_interval",
        },
        "hardware_complexity": {
            "actual_ge_cycles": float(actual_area) / ge_area * max(1, int(actual_cycles)),
            "source": "derived",
        },
    }
