#!/usr/bin/env python3
"""Generate evaluation data, aggregate acceptance metrics, and fill Result.docx.

The script intentionally uses only the Python standard library so it can run in
the VS Code remote environment without installing python-docx or openpyxl.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
S_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"


@dataclass(frozen=True)
class ModuleSpec:
    row_name: str
    registry_key: str
    evaluation_roots: tuple[str, ...]
    workbook_candidates: tuple[str, ...] = ()
    standalone_latency_validation: bool = False
    latency_cases: tuple[int, ...] | None = None


MODULES = (
    ModuleSpec("SxMatch", "sxmatch", ("Generator/BasicModules/SxMatch/evaluation_output",), ("Area_TP_Estimator/SxMatch/report/test.xlsx",)),
    ModuleSpec("Delay", "delay", ("Generator/BasicModules/Delay/evaluation_output",), ("Area_TP_Estimator/Delay/report/basic.xlsx", "Area_TP_Estimator/Delay/report/test.xlsx")),
    ModuleSpec("Counter", "counter", ("Generator/BasicModules/Counter/evaluation_output",), ("Area_TP_Estimator/Counter/report/test.xlsx",)),
    ModuleSpec("Add", "add", ("Generator/BasicModules/Add/evaluation_output",), ("Area_TP_Estimator/Add/report/test.xlsx", "Area_TP_Estimator/Est/ADD.xlsx")),
    ModuleSpec("Sub", "sub", ("Generator/BasicModules/Sub/evaluation_output",), ("Area_TP_Estimator/Sub/report/basic.xlsx", "Area_TP_Estimator/Sub/report/test.xlsx")),
    ModuleSpec("Mul", "mul", ("Generator/BasicModules/Mul/evaluation_output",), ("Area_TP_Estimator/Mul/report/test.xlsx", "Area_TP_Estimator/Est/MUL0912.xlsx", "Area_TP_Estimator/Est/MUL.xlsx")),
    ModuleSpec("Neg", "neg", ("Generator/BasicModules/Neg/evaluation_output",), ("Area_TP_Estimator/Neg/report/test.xlsx",)),
    ModuleSpec("Abs", "abs", ("Generator/BasicModules/Abs/evaluation_output",), ("Area_TP_Estimator/Abs/report/test.xlsx",)),
    ModuleSpec("Comp", "comp", ("Generator/BasicModules/Comp/evaluation_output",), ("Area_TP_Estimator/Comp/report/test.xlsx",)),
    ModuleSpec("CAdd", "cadd", ("Generator/BasicModules/CAdd/evaluation_output",), ("Area_TP_Estimator/CAdd/report/test.xlsx",)),
    ModuleSpec("CSub", "csub", ("Generator/BasicModules/CSub/evaluation_output",), ("Area_TP_Estimator/CSub/report/test.xlsx",)),
    ModuleSpec("CMul", "cmul", ("Generator/BasicModules/CMul/evaluation_output",), ("Area_TP_Estimator/CMul/report/test.xlsx",)),
    ModuleSpec("CNorm", "cnorm", ("Generator/BasicModules/CNorm/evaluation_output",), ("Area_TP_Estimator/CNorm/report/test.xlsx",)),
    ModuleSpec("Mux", "mux", ("Generator/BasicModules/MUX/evaluation_output",), ("Area_TP_Estimator/MUX/report/test.xlsx", "Area_TP_Estimator/Mux/report/test.xlsx")),
    ModuleSpec("AdderTree", "addertree", ("Generator/BasicModules/AdderTree/evaluation_output",), ("Area_TP_Estimator/AdderTree/report/test.xlsx",)),
    ModuleSpec("CompTree", "comptree", ("Generator/BasicModules/CompTree/evaluation_output",), ("Area_TP_Estimator/CompTree/report/test.xlsx",)),
    ModuleSpec("5G PUSCH Channel Estimator", "pusch_ce", ("Generator/PUSCH_CE/evaluation_output",), ("Area_TP_Estimator/PUSCH_Est_pack/param.xlsx",), True, (1,)),
    ModuleSpec("INSA -MMSE MIMO Detector", "mimo", ("Generator/MIMODetector/evaluation_output",), ("Area_TP_Estimator/Est_INSA_MMSE/INSA.xlsx",)),
    ModuleSpec("BP Polar-Decodere", "bp", ("BPPredIter/BP_Evaluation/evaluation_output",), ("Area_TP_Estimator/Est_Polar_BP_Decoder/area.xlsx",)),
)


@dataclass
class MetricSeries:
    errors: list[float] = field(default_factory=list)
    prediction_times_s: list[float] = field(default_factory=list)
    speedups: list[float] = field(default_factory=list)


@dataclass
class ModuleResult:
    module: str
    area_error_text: str = ""
    delay_error_percent: float | None = None
    complexity_error_text: str = ""
    area_prediction_time_s: float | None = None
    delay_prediction_time_s: float | None = None
    area_speedup: float | None = None
    delay_speedup: float | None = None
    delay_case_count: int = 0
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ResultError(RuntimeError):
    pass


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive(value: Any) -> float | None:
    number = _finite_number(value)
    return number if number is not None and number > 0 else None


def _first_number(mapping: dict[str, Any], keys: Iterable[str]) -> float | None:
    for key in keys:
        if key in mapping:
            value = _finite_number(mapping[key])
            if value is not None:
                return value
    return None


def _section(payload: dict[str, Any], chinese: str, english: str) -> dict[str, Any]:
    for key in (chinese, english, english.lower(), english.capitalize()):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _case_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root)
    return relative.parts[0] if len(relative.parts) > 1 else path.stem


def collect_json_metrics(root: Path, only_cases: set[str] | None = None) -> tuple[MetricSeries, MetricSeries, list[tuple[Path, float, float]], list[str]]:
    """Return area, delay, complexity comparisons, and source paths by case."""
    area = MetricSeries()
    delay = MetricSeries()
    comparisons: list[tuple[Path, float, float]] = []
    sources: list[str] = []
    if not root.is_dir():
        return area, delay, comparisons, sources

    candidates: dict[str, list[tuple[int, Path, dict[str, Any]]]] = {}
    name_priority = {
        "latency_evaluation.json": -1,
        "area_prediction.json": 0,
        "evaluation.json": 0,
        "mimo_metrics.json": 1,
        "bp_metrics.json": 1,
        "metrics.json": 2,
        "area_evaluation.json": 3,
        "prediction.json": 4,
    }
    for path in sorted(root.rglob("*.json")):
        priority = name_priority.get(path.name)
        if priority is None:
            continue
        payload = _read_json(path)
        if payload is None:
            continue
        candidates.setdefault(_case_name(root, path), []).append((priority, path, payload))

    for case in sorted(candidates, key=natural_key):
        if only_cases is not None and case not in only_cases:
            continue
        # A case may split area and latency into different JSON files. Consume
        # each metric once, preferring the standard evaluation snapshot.
        got_area = got_delay = False
        for _, path, payload in sorted(candidates[case], key=lambda item: (item[0], str(item[1]))):
            area_section = _section(payload, "面积", "area")
            delay_section = _section(payload, "延迟", "latency")
            complexity_section = _section(payload, "硬件复杂度", "hardware_complexity")

            if area_section and not got_area:
                error = _first_number(area_section, ("误差 (%)", "error_percent", "mape_percent", "MAPE"))
                time_ms = _first_number(area_section, ("预测时间 (ms)", "prediction_time_ms"))
                speedup = _first_number(area_section, ("速度提升倍数 (×)", "speedup"))
                if error is not None or time_ms is not None or speedup is not None:
                    if error is not None:
                        area.errors.append(abs(error))
                    if time_ms is not None and time_ms >= 0:
                        area.prediction_times_s.append(time_ms / 1000.0)
                    if speedup is not None and speedup > 0:
                        area.speedups.append(speedup)
                    got_area = True
                    sources.append(str(path))

            if delay_section and not got_delay:
                error = _first_number(delay_section, ("误差 (%)", "error_percent", "mape_percent", "MAPE"))
                time_ms = _first_number(delay_section, ("预测时间 (ms)", "prediction_time_ms"))
                speedup = _first_number(delay_section, ("速度提升倍数 (×)", "speedup"))
                # Delay acceptance requires an evaluated error, not prediction-only output.
                if error is not None:
                    delay.errors.append(abs(error))
                    if time_ms is not None and time_ms >= 0:
                        delay.prediction_times_s.append(time_ms / 1000.0)
                    if speedup is not None and speedup > 0:
                        delay.speedups.append(speedup)
                    got_delay = True
                    sources.append(str(path))

            area_error = _first_number(area_section, ("误差 (%)", "error_percent", "mape_percent", "MAPE"))
            complexity_error = _first_number(complexity_section, ("误差 (%)", "error_percent", "mape_percent", "MAPE"))
            if area_error is not None and complexity_error is not None:
                comparisons.append((path, abs(area_error), abs(complexity_error)))
    return area, delay, comparisons, sorted(set(sources))


def natural_key(value: Any) -> tuple[Any, ...]:
    return tuple(int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", str(value)))


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.text or "" for node in item.iter(f"{{{S_NS}}}t")) for item in root]


def _xlsx_sheet_paths(archive: zipfile.ZipFile) -> list[str]:
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except KeyError:
        return sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
    targets = {rel.attrib.get("Id"): rel.attrib.get("Target", "") for rel in relationships.findall(f"{{{P_NS}}}Relationship")}
    paths: list[str] = []
    for sheet in workbook.iter(f"{{{S_NS}}}sheet"):
        target = targets.get(sheet.attrib.get(f"{{{R_NS}}}id"), "")
        if target:
            target = target.lstrip("/")
            paths.append(target if target.startswith("xl/") else f"xl/{target}")
    return paths


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{S_NS}}}t"))
    value = cell.find(f"{{{S_NS}}}v")
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared[int(value.text)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "b":
        return "true" if value.text == "1" else "false"
    return value.text


def read_xlsx_sheets(path: Path) -> list[list[list[str]]]:
    sheets: list[list[list[str]]] = []
    with zipfile.ZipFile(path) as archive:
        shared = _xlsx_shared_strings(archive)
        for sheet_path in _xlsx_sheet_paths(archive):
            try:
                root = ET.fromstring(archive.read(sheet_path))
            except KeyError:
                continue
            sheet_rows: list[list[str]] = []
            for row in root.iter(f"{{{S_NS}}}row"):
                values: dict[int, str] = {}
                for cell in row.findall(f"{{{S_NS}}}c"):
                    reference = cell.attrib.get("r", "")
                    match = re.match(r"([A-Z]+)", reference)
                    if not match:
                        continue
                    column = 0
                    for char in match.group(1):
                        column = column * 26 + ord(char) - 64
                    values[column - 1] = _cell_value(cell, shared)
                if values:
                    width = max(values) + 1
                    sheet_rows.append([values.get(index, "") for index in range(width)])
            if sheet_rows:
                sheets.append(sheet_rows)
    return sheets


def read_xlsx_rows(path: Path) -> list[list[str]]:
    return [row for sheet in read_xlsx_sheets(path) for row in sheet]


def _normalized_header(value: str) -> str:
    return re.sub(r"[\s_（）()·×/%²μµ]", "", value).casefold()


def _find_column(headers: list[str], aliases: Iterable[str]) -> int | None:
    normalized = [_normalized_header(header) for header in headers]
    for alias in aliases:
        target = _normalized_header(alias)
        for index, header in enumerate(normalized):
            if header == target:
                return index
    return None


def _column_numbers(rows: list[list[str]], index: int | None) -> list[float]:
    if index is None:
        return []
    values: list[float] = []
    for row in rows:
        if index >= len(row):
            continue
        number = _finite_number(row[index])
        if number is not None:
            values.append(number)
    return values


def collect_workbook_metrics(path: Path) -> MetricSeries:
    for rows in read_xlsx_sheets(path):
        header_index = next(
            (index for index, row in enumerate(rows) if any(_normalized_header(cell) in {"mape", "评估时间s", "预测时间s", "综合时间s"} for cell in row)),
            None,
        )
        if header_index is None:
            continue
        result = MetricSeries()
        headers = rows[header_index]
        data = rows[header_index + 1 :]
        error_col = _find_column(headers, ("MAPE", "面积预测偏差", "误差 (%)", "error_percent"))
        prediction_col = _find_column(headers, ("评估时间(s)", "预测时间(s)", "area prediction time(s)", "prediction_time_s"))
        synthesis_col = _find_column(headers, ("综合时间(s)", "DC综合时间(s)", "synthesis_time_s", "time"))
        speedup_col = _find_column(headers, ("速度提升倍数", "速度提升", "speedup"))

        errors = [abs(value) for value in _column_numbers(data, error_col)]
        # Basic-area workbooks store MAPE as a fraction; already-percent columns do not.
        if errors and error_col is not None and headers[error_col].strip().casefold() == "mape" and max(errors) <= 1.0:
            errors = [value * 100.0 for value in errors]
        result.errors.extend(errors)

        times = [value for value in _column_numbers(data, prediction_col) if value >= 0]
        result.prediction_times_s.extend(times)
        direct_speedups = [value for value in _column_numbers(data, speedup_col) if value > 0]
        result.speedups.extend(direct_speedups)
        if not direct_speedups and prediction_col is not None and synthesis_col is not None:
            for row in data:
                if max(prediction_col, synthesis_col) >= len(row):
                    continue
                prediction = _positive(row[prediction_col])
                synthesis = _positive(row[synthesis_col])
                if prediction is not None and synthesis is not None:
                    result.speedups.append(synthesis / prediction)
        if result.errors or result.prediction_times_s or result.speedups:
            return result
    return MetricSeries()


def _minimum(values: Iterable[float]) -> float | None:
    materialized = [value for value in values if math.isfinite(value)]
    return min(materialized) if materialized else None


def _prefer(primary: float | None, fallback: float | None) -> float | None:
    return primary if primary is not None else fallback


def _mean(values: Iterable[float]) -> float | None:
    materialized = [value for value in values if math.isfinite(value)]
    return statistics.fmean(materialized) if materialized else None


def _docx_namespaces(xml_bytes: bytes) -> None:
    import io

    for _, pair in ET.iterparse(io.BytesIO(xml_bytes), events=("start-ns",)):
        prefix, uri = pair
        try:
            ET.register_namespace(prefix or "", uri)
        except ValueError:
            pass


def _word_cell_text(cell: ET.Element) -> str:
    return "".join(node.text or "" for node in cell.iter(f"{{{W_NS}}}t"))


def _set_word_cell_text(cell: ET.Element, value: str) -> None:
    texts = list(cell.iter(f"{{{W_NS}}}t"))
    if texts:
        texts[0].text = value
        texts[0].set(f"{{{XML_NS}}}space", "preserve")
        for node in texts[1:]:
            node.text = ""
        return
    paragraph = cell.find(f"{{{W_NS}}}p")
    if paragraph is None:
        paragraph = ET.SubElement(cell, f"{{{W_NS}}}p")
    run = ET.SubElement(paragraph, f"{{{W_NS}}}r")
    text = ET.SubElement(run, f"{{{W_NS}}}t")
    text.set(f"{{{XML_NS}}}space", "preserve")
    text.text = value


def read_docx_table(path: Path) -> tuple[bytes, ET.Element, dict[str, list[ET.Element]]]:
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    _docx_namespaces(xml_bytes)
    root = ET.fromstring(xml_bytes)
    tables = list(root.iter(f"{{{W_NS}}}tbl"))
    if not tables:
        raise ResultError(f"Word 文件没有表格: {path}")
    rows: dict[str, list[ET.Element]] = {}
    for table in tables:
        for row in table.findall(f"{{{W_NS}}}tr"):
            cells = row.findall(f"{{{W_NS}}}tc")
            if cells:
                name = _word_cell_text(cells[0]).strip()
                if name:
                    rows[name] = cells
    return xml_bytes, root, rows


def _copy_docx_with_xml(input_path: Path, output_path: Path, xml_bytes: bytes) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    with zipfile.ZipFile(input_path) as source, zipfile.ZipFile(temporary, "w") as target:
        for info in source.infolist():
            data = xml_bytes if info.filename == "word/document.xml" else source.read(info.filename)
            target.writestr(info, data)
    temporary.replace(output_path)


def _serialize_word_xml(root: ET.Element, original: bytes) -> bytes:
    """Serialize while retaining namespace declarations used by mc:Ignorable.

    ElementTree removes namespace declarations that only occur inside attribute
    values (for example ``mc:Ignorable=\"w15 w16\"``). Word treats the missing
    declarations as document corruption, so copy them from the original root.
    """
    serialized = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    original_root = re.search(br"<[^!?][^>]*>", original)
    new_root = re.search(br"<[^!?][^>]*>", serialized)
    if original_root is None or new_root is None:
        return serialized
    declarations = re.findall(br"\s+xmlns(?::[A-Za-z_][\w.-]*)?=\"[^\"]+\"", original_root.group(0))
    current = new_root.group(0)
    missing = [declaration for declaration in declarations if declaration.split(b"=", 1)[0] not in current]
    if not missing:
        return serialized
    replacement = current[:-1] + b"".join(missing) + b">"
    return serialized[: new_root.start()] + replacement + serialized[new_root.end() :]


def _format_error(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 1)
    return f"{rounded:.1f}".rstrip("0").rstrip(".")


def _format_time(value: float | None) -> str:
    if value is None:
        return "-"
    if value == 0:
        return "0"
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _format_speedup(value: float | None) -> str:
    if value is None:
        return "-"
    text = f"{value:.3g}" if abs(value) >= 10_000 else f"{value:.4g}"
    return re.sub(r"e\+?(-?)0*(\d+)$", r"e\1\2", text)


def _pair(first: float | None, second: float | None, formatter: Any) -> str:
    return f"{formatter(first)}/{formatter(second)}"


def _match_docx_row(rows: dict[str, list[ET.Element]], expected: str) -> tuple[str, list[ET.Element]] | None:
    normalized_expected = re.sub(r"[^a-z0-9]", "", expected.casefold())
    for name, cells in rows.items():
        normalized_name = re.sub(r"[^a-z0-9]", "", name.casefold())
        if normalized_name == normalized_expected:
            return name, cells
    return None


def aggregate_module(repo_root: Path, spec: ModuleSpec, area_error_text: str, expected_cases: int, allow_partial: bool, tolerance: float) -> ModuleResult:
    result = ModuleResult(module=spec.row_name, area_error_text=area_error_text, complexity_error_text=area_error_text)
    json_area = MetricSeries()
    json_delay = MetricSeries()
    comparisons: list[tuple[Path, float, float]] = []
    registry_path = repo_root / "metrics_framework" / "registry.json"
    registry_entry = json.loads(registry_path.read_text(encoding="utf-8"))["modules"][spec.registry_key]
    case_ids = spec.latency_cases if spec.latency_cases is not None else registry_entry["default_cases"]
    only_cases = {Path(registry_entry["config_pattern"].format(case=case)).stem for case in case_ids}
    for relative in spec.evaluation_roots:
        root = repo_root / relative
        area, delay, checks, sources = collect_json_metrics(root, only_cases)
        json_area.errors.extend(area.errors)
        json_area.prediction_times_s.extend(area.prediction_times_s)
        json_area.speedups.extend(area.speedups)
        json_delay.errors.extend(delay.errors)
        json_delay.prediction_times_s.extend(delay.prediction_times_s)
        json_delay.speedups.extend(delay.speedups)
        comparisons.extend(checks)
        result.sources.extend(str(Path(source).relative_to(repo_root)) if Path(source).is_relative_to(repo_root) else source for source in sources)

    result.delay_case_count = len(json_delay.errors)
    module_expected_cases = len(spec.latency_cases) if spec.latency_cases is not None else expected_cases
    if result.delay_case_count != module_expected_cases:
        message = f"延迟评估有效 case 数为 {result.delay_case_count}，期望 {module_expected_cases}"
        if not allow_partial:
            raise ResultError(f"{spec.row_name}: {message}")
        result.warnings.append(message)
    result.delay_error_percent = _mean(json_delay.errors)
    result.delay_prediction_time_s = _minimum(json_delay.prediction_times_s)
    result.delay_speedup = _minimum(json_delay.speedups)

    mismatches = [(path, area, complexity) for path, area, complexity in comparisons if abs(area - complexity) > tolerance]
    if mismatches:
        preview = ", ".join(f"{path.name}: {area:g}!={complexity:g}" for path, area, complexity in mismatches[:3])
        message = f"面积/复杂度逐 case 误差不一致 ({len(mismatches)}): {preview}"
        if not allow_partial:
            raise ResultError(f"{spec.row_name}: {message}")
        result.warnings.append(message)

    workbook_metrics = MetricSeries()
    workbook_path: Path | None = None
    for relative in spec.workbook_candidates:
        candidate = repo_root / relative
        if candidate.is_file():
            metrics = collect_workbook_metrics(candidate)
            if metrics.prediction_times_s or metrics.speedups or metrics.errors:
                workbook_metrics = metrics
                workbook_path = candidate
                break
    # Area performance comes from the workbook when present; JSON is the
    # fallback for application modules and newer all-metric adapters.
    result.area_prediction_time_s = _prefer(_minimum(workbook_metrics.prediction_times_s), _minimum(json_area.prediction_times_s))
    result.area_speedup = _prefer(_minimum(workbook_metrics.speedups), _minimum(json_area.speedups))
    if workbook_path is not None:
        result.sources.append(str(workbook_path.relative_to(repo_root)))
    if result.area_prediction_time_s is None and not spec.standalone_latency_validation:
        result.warnings.append("未找到面积预测时间")
    if result.area_speedup is None and not spec.standalone_latency_validation:
        result.warnings.append("未找到面积速度提升倍数")
    if result.delay_prediction_time_s is None:
        result.warnings.append("未找到延迟预测时间")
    if result.delay_speedup is None:
        result.warnings.append("未找到延迟速度提升倍数")
    if result.warnings and not allow_partial:
        raise ResultError(f"{spec.row_name}: {'；'.join(result.warnings)}")
    result.sources = sorted(set(result.sources))
    return result


def generate_evaluations(repo_root: Path, specs: Iterable[ModuleSpec], python: str) -> None:
    registry = repo_root / "metrics_framework" / "registry.json"
    if not registry.is_file():
        raise ResultError(f"找不到统一指标注册表: {registry}")
    registry_modules = json.loads(registry.read_text(encoding="utf-8"))["modules"]
    for spec in specs:
        if spec.standalone_latency_validation:
            entry = registry_modules[spec.registry_key]
            module_root = repo_root / entry["root"]
            script = module_root / "tests" / "validate_pusch_ce_latency.py"
            area_script = repo_root / "Area_TP_Estimator" / "PUSCH_Est_pack" / "pusch_ce_area_interface.py"
            for case in spec.latency_cases if spec.latency_cases is not None else entry["default_cases"]:
                case_name = entry["config_pattern"].format(case=case)
                config_path = module_root / entry["config_dir"] / case_name
                area_output = module_root / entry["output_root"] / f"config{case}" / "area_prediction.json"
                area_command = [python, str(area_script), "predict", str(config_path)]
                print(f"[generate] {spec.row_name} area predict {case}: {' '.join(area_command)}", flush=True)
                area_completed = subprocess.run(area_command, cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if area_completed.returncode != 0:
                    detail = area_completed.stderr.strip() or area_completed.stdout.strip() or f"exit={area_completed.returncode}"
                    raise ResultError(f"{spec.row_name} 面积预测 case {case} 失败: {detail}")
                try:
                    area_payload = json.loads(area_completed.stdout)
                except json.JSONDecodeError as error:
                    raise ResultError(f"{spec.row_name} 面积预测 case {case} 未返回有效 JSON") from error
                area_time_ms = _finite_number(area_payload.get("prediction_time_ms")) if isinstance(area_payload, dict) else None
                if area_time_ms is None or area_time_ms <= 0:
                    raise ResultError(f"{spec.row_name} 面积预测 case {case} 缺少有效预测时间")
                area_output.parent.mkdir(parents=True, exist_ok=True)
                area_temporary = area_output.with_name(f".{area_output.name}.tmp")
                area_temporary.write_text(json.dumps({"area": area_payload}, ensure_ascii=False, indent=2), encoding="utf-8")
                area_temporary.replace(area_output)
                output = module_root / entry["output_root"] / f"config{case}" / "latency_evaluation.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                temporary = output.with_name(f".{output.name}.tmp")
                temporary.unlink(missing_ok=True)
                command = [python, str(script), str(config_path), "--simulator", "verilator", "--output-json", str(temporary)]
                print(f"[generate] {spec.row_name} latency evaluate {case}: {' '.join(command)}", flush=True)
                completed = subprocess.run(command, cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if completed.returncode != 0:
                    detail = completed.stderr.strip() or completed.stdout.strip() or f"exit={completed.returncode}"
                    raise ResultError(f"{spec.row_name} 延迟验证 case {case} 失败: {detail}")
                try:
                    payload = json.loads(temporary.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    detail = (completed.stdout.strip() or completed.stderr.strip())[-1000:]
                    raise ResultError(f"{spec.row_name} 延迟验证 case {case} 未写入有效 JSON；输出末尾: {detail}") from error
                latency = payload.get("latency") if isinstance(payload, dict) else None
                if not isinstance(latency, dict) or any(
                    _finite_number(latency.get(key)) is None
                    for key in ("predicted_cycles", "actual_cycles", "error_percent", "prediction_time_ms", "speedup")
                ):
                    raise ResultError(f"{spec.row_name} 延迟验证 case {case} 缺少预测值、真实值、偏差或计时")
                temporary.replace(output)
            continue
        command = [python, "-m", "metrics_framework", spec.registry_key, "evaluate"]
        print(f"[generate] {spec.row_name}: {' '.join(command)}", flush=True)
        completed = subprocess.run(command, cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or f"exit={completed.returncode}"
            raise ResultError(f"{spec.row_name} 评估失败: {detail}")


def fill_document(
    repo_root: Path,
    input_docx: Path,
    output_docx: Path,
    expected_cases: int,
    allow_partial: bool,
    tolerance: float,
) -> list[ModuleResult]:
    _, root, rows = read_docx_table(input_docx)
    results: list[ModuleResult] = []
    for spec in MODULES:
        matched = _match_docx_row(rows, spec.row_name)
        if matched is None:
            raise ResultError(f"Result.docx 中找不到模块行: {spec.row_name}")
        actual_name, cells = matched
        if len(cells) < 6:
            raise ResultError(f"模块行列数不足 6: {actual_name}")
        area_error_text = _word_cell_text(cells[1]).strip()
        if not area_error_text:
            raise ResultError(f"{actual_name}: 面积预测偏差为空；本脚本默认保留已填写面积值")
        result = aggregate_module(repo_root, spec, area_error_text, expected_cases, allow_partial, tolerance)
        _set_word_cell_text(cells[2], _format_error(result.delay_error_percent))
        _set_word_cell_text(cells[3], result.complexity_error_text)
        _set_word_cell_text(cells[4], _pair(result.area_prediction_time_s, result.delay_prediction_time_s, _format_time))
        _set_word_cell_text(cells[5], _pair(result.area_speedup, result.delay_speedup, _format_speedup))
        results.append(result)

    with zipfile.ZipFile(input_docx) as archive:
        original_xml = archive.read("word/document.xml")
    xml_bytes = _serialize_word_xml(root, original_xml)
    _copy_docx_with_xml(input_docx, output_docx, xml_bytes)
    return results


def _markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _markdown_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def update_markdown_table(text: str, results: Iterable[ModuleResult]) -> str:
    by_name = {_markdown_name(result.module): result for result in results}
    output: list[str] = []
    updated: set[str] = set()
    for line in text.splitlines():
        cells = _markdown_row(line)
        if cells and len(cells) >= 6:
            key = _markdown_name(cells[0])
            result = by_name.get(key)
            if result is not None:
                cells[2] = _format_error(result.delay_error_percent)
                cells[3] = result.complexity_error_text
                cells[4] = _pair(result.area_prediction_time_s, result.delay_prediction_time_s, _format_time)
                cells[5] = _pair(result.area_speedup, result.delay_speedup, _format_speedup)
                line = "| " + " | ".join(cells) + " |"
                updated.add(key)
        output.append(line)
    missing = sorted(set(by_name) - updated)
    if missing:
        raise ResultError(f"Result.md 中找不到模块行: {', '.join(missing)}")
    return "\n".join(output) + "\n"


def fill_markdown(
    repo_root: Path,
    input_md: Path,
    output_md: Path,
    expected_cases: int,
    allow_partial: bool,
    tolerance: float,
) -> list[ModuleResult]:
    text = input_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    area_by_name: dict[str, str] = {}
    for line in lines:
        cells = _markdown_row(line)
        if cells and len(cells) >= 6:
            area_by_name[_markdown_name(cells[0])] = cells[1]
    results: list[ModuleResult] = []
    for spec in MODULES:
        area_error_text = area_by_name.get(_markdown_name(spec.row_name), "").strip()
        if not area_error_text:
            raise ResultError(f"{spec.row_name}: Result.md 中面积预测偏差为空")
        results.append(aggregate_module(repo_root, spec, area_error_text, expected_cases, allow_partial, tolerance))
    rendered = update_markdown_table(text, results)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_md.with_name(f".{output_md.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(output_md)
    return results


def _select_modules(names: list[str] | None) -> tuple[ModuleSpec, ...]:
    if not names:
        return MODULES
    wanted = {name.casefold() for name in names}
    selected = tuple(spec for spec in MODULES if spec.row_name.casefold() in wanted or spec.registry_key.casefold() in wanted)
    missing = wanted - {spec.row_name.casefold() for spec in selected} - {spec.registry_key.casefold() for spec in selected}
    if missing:
        raise ResultError(f"未知模块: {', '.join(sorted(missing))}")
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成评估数据并逐模块填写 Result.docx 或 Result.md")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="统一指标仓库根目录")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-docx", type=Path, help="待填写的 Result.docx")
    source.add_argument("--input-md", type=Path, help="待填写的 Result.md")
    parser.add_argument("--output-docx", type=Path, help="输出文件；默认与输入同目录的 Result_filled.docx")
    parser.add_argument("--output-md", type=Path, help="输出文件；默认与输入同目录的 Result_filled.md，可与输入相同")
    parser.add_argument("--report-json", type=Path, help="可选：保存逐模块汇总和核对告警")
    parser.add_argument("--generate", action="store_true", help="填表前调用统一指标框架，为表中全部模块重新运行 evaluate")
    parser.add_argument("--python", default=sys.executable, help="--generate 使用的远端 Python 解释器")
    parser.add_argument("--modules", nargs="+", help="仅用于 --generate；按表中名称或 registry key 选择模块")
    parser.add_argument("--expected-cases", type=int, default=5, help="普通模块延迟平均值要求的有效 case 数，默认 5；PUSCH_CE 仅使用 config1")
    parser.add_argument("--allow-partial", action="store_true", help="允许 case 不足时按现有数据填表，并在报告中告警")
    parser.add_argument("--complexity-tolerance", type=float, default=1e-6, help="逐 case 面积与复杂度误差核对容差")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo_root = args.repo_root.resolve()
        if args.generate:
            generate_evaluations(repo_root, _select_modules(args.modules), args.python)
        if args.input_docx:
            input_path = args.input_docx.resolve()
            output_path = (args.output_docx or input_path.with_name(f"{input_path.stem}_filled.docx")).resolve()
            if output_path == input_path:
                raise ResultError("DOCX 输出文件必须与输入文件不同，以保留原始表格")
            results = fill_document(repo_root, input_path, output_path, args.expected_cases, args.allow_partial, args.complexity_tolerance)
        else:
            input_path = args.input_md.resolve()
            output_path = (args.output_md or input_path.with_name(f"{input_path.stem}_filled.md")).resolve()
            results = fill_markdown(repo_root, input_path, output_path, args.expected_cases, args.allow_partial, args.complexity_tolerance)
        report = {
            "input": str(input_path),
            "output": str(output_path),
            "metric_order": {"预测时间": "面积秒/延迟秒", "速度提升": "面积倍数/延迟倍数"},
            "modules": [asdict(result) for result in results],
        }
        if args.report_json:
            report_path = args.report_json.resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ResultError, OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
