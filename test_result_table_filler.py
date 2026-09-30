from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).parent / "tools" / "fill_result_table.py"
SPEC = importlib.util.spec_from_file_location("fill_result_table", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_xlsx(path: Path) -> None:
    workbook = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>"""
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>MAPE</t></is></c><c r="B1" t="inlineStr"><is><t>综合时间(s)</t></is></c><c r="C1" t="inlineStr"><is><t>评估时间(s)</t></is></c></row>
<row r="2"><c r="A2"><v>0.1</v></c><c r="B2"><v>10</v></c><c r="C2"><v>0.01</v></c></row>
<row r="3"><c r="A3"><v>0.2</v></c><c r="B3"><v>40</v></c><c r="C3"><v>0.02</v></c></row>
</sheetData></worksheet>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def _write_docx(path: Path) -> None:
    rows = [
        ("基础运算单元", "面积预测偏差（%）", "延迟预测偏差（%）", "定点计算复杂度预测偏差（%）", "预测时间（s）", "速度提升"),
        ("SxMatch", "0.3", "", "", "面积指标/延迟指标", "面积指标/延迟指标"),
    ]
    body = []
    for row in rows:
        cells = "".join(f"<w:tc><w:p><w:r><w:t>{value}</w:t></w:r></w:p></w:tc>" for value in row)
        body.append(f"<w:tr>{cells}</w:tr>")
    xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{MODULE.W_NS}"><w:body><w:tbl>{"".join(body)}</w:tbl></w:body></w:document>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def test_workbook_metrics(tmp_path: Path) -> None:
    workbook = tmp_path / "test.xlsx"
    _write_xlsx(workbook)
    metrics = MODULE.collect_workbook_metrics(workbook)
    assert metrics.errors == [10.0, 20.0]
    assert min(metrics.prediction_times_s) == 0.01
    assert min(metrics.speedups) == 1000.0


def test_json_metrics_and_complexity_check(tmp_path: Path) -> None:
    root = tmp_path / "evaluation_output"
    for case in range(1, 6):
        directory = root / f"config_case{case}"
        directory.mkdir(parents=True)
        payload = {
            "延迟": {"误差 (%)": case, "预测时间 (ms)": 10 + case, "速度提升倍数 (×)": 100 - case},
            "面积": {"误差 (%)": 2, "预测时间 (ms)": 20, "速度提升倍数 (×)": 1000},
            "硬件复杂度": {"误差 (%)": 2},
        }
        (directory / "evaluation.json").write_text(MODULE.json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    area, delay, comparisons, _ = MODULE.collect_json_metrics(root)
    assert MODULE._mean(delay.errors) == 3.0
    assert min(delay.prediction_times_s) == 0.011
    assert min(delay.speedups) == 95
    assert len(area.errors) == 5
    assert len(comparisons) == 5


def test_mimo_ignores_extra_evaluation_case(tmp_path: Path) -> None:
    registry = tmp_path / "metrics_framework" / "registry.json"
    registry.parent.mkdir()
    registry.write_text(json.dumps({"modules": {"mimo": {
        "config_pattern": "config_case{case}.json",
        "default_cases": [1, 2, 3, 4, 5],
    }}}), encoding="utf-8")
    root = tmp_path / "Generator" / "MIMODetector" / "evaluation_output"
    for case in range(1, 7):
        directory = root / f"config_case{case}"
        directory.mkdir(parents=True)
        (directory / "evaluation.json").write_text(json.dumps({
            "area": {"error_percent": 2, "prediction_time_ms": 20, "speedup": 100},
            "latency": {"error_percent": case, "prediction_time_ms": 10 + case, "speedup": 50 - case},
            "hardware_complexity": {"error_percent": 2},
        }), encoding="utf-8")
    spec = next(spec for spec in MODULE.MODULES if spec.registry_key == "mimo")
    result = MODULE.aggregate_module(tmp_path, spec, "2", 5, False, 1e-6)
    assert result.delay_case_count == 5
    assert result.delay_error_percent == 3
    assert result.delay_prediction_time_s == 0.011
    assert result.delay_speedup == 45
    assert all("config_case6" not in source for source in result.sources)


def test_docx_cell_update(tmp_path: Path) -> None:
    source = tmp_path / "Result.docx"
    output = tmp_path / "Result_filled.docx"
    _write_docx(source)
    _, root, rows = MODULE.read_docx_table(source)
    cells = rows["SxMatch"]
    MODULE._set_word_cell_text(cells[2], "0")
    MODULE._set_word_cell_text(cells[3], "0.3")
    with zipfile.ZipFile(source) as archive:
        original_xml = archive.read("word/document.xml")
    MODULE._copy_docx_with_xml(source, output, MODULE._serialize_word_xml(root, original_xml))
    _, _, updated = MODULE.read_docx_table(output)
    assert MODULE._word_cell_text(updated["SxMatch"][2]) == "0"
    assert MODULE._word_cell_text(updated["SxMatch"][3]) == "0.3"


def test_compact_pair_formatting() -> None:
    assert MODULE._pair(0.0000715, 0.0150666, MODULE._format_time) == "0.0000715/0.0150666"
    assert MODULE._pair(121957, 69.2, MODULE._format_speedup) == "1.22e5/69.2"


def test_markdown_table_update() -> None:
    text = "| 基础运算单元 | 面积 | 延迟 | 复杂度 | 时间 | 速度 |\n|---|---|---|---|---|---|\n| SxMatch | 0.3 | 0？ | | 面积/延迟 | 面积/延迟 |\n"
    result = MODULE.ModuleResult(
        module="SxMatch",
        area_error_text="0.3",
        delay_error_percent=0.0,
        complexity_error_text="0.3",
        area_prediction_time_s=0.0000715,
        delay_prediction_time_s=0.0150666,
        area_speedup=121957,
        delay_speedup=69.2,
    )
    updated = MODULE.update_markdown_table(text, [result])
    assert "| SxMatch | 0.3 | 0 | 0.3 | 0.0000715/0.0150666 | 1.22e5/69.2 |" in updated


def test_pusch_ce_uses_standalone_rtl_latency_validation(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "metrics_framework" / "registry.json"
    registry.parent.mkdir()
    registry.write_text(json.dumps({"modules": {"pusch_ce": {
        "root": "Generator/PUSCH_CE",
        "config_dir": "cases",
        "config_pattern": "config{case}.json",
        "default_cases": [1, 2, 3, 4, 5],
        "output_root": "evaluation_output",
    }}}), encoding="utf-8")
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        case = int(Path(command[2]).stem.removeprefix("config"))
        payload = {"latency": {
            "predicted_cycles": 100 + case,
            "actual_cycles": 100 + case,
            "error_percent": 0.0,
            "prediction_time_ms": 10 + case,
            "simulation_time_ms": 1000.0,
            "speedup": 1000.0 / (10 + case),
        }}
        Path(command[command.index("--output-json") + 1]).write_text(json.dumps(payload), encoding="utf-8")
        return MODULE.subprocess.CompletedProcess(
            command, 0,
            stdout="Verilator build log\ncocotb test log\n" + json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    spec = next(spec for spec in MODULE.MODULES if spec.registry_key == "pusch_ce")
    MODULE.generate_evaluations(tmp_path, [spec], "python")

    assert len(commands) == 1
    assert Path(commands[0][2]).name == "config1.json"
    assert all("validate_pusch_ce_latency.py" in command[1] for command in commands)
    stale_case = tmp_path / "Generator" / "PUSCH_CE" / "evaluation_output" / "config2"
    stale_case.mkdir(parents=True)
    (stale_case / "latency_evaluation.json").write_text(json.dumps({"latency": {
        "error_percent": 99.0,
        "prediction_time_ms": 1.0,
        "speedup": 1.0,
    }}), encoding="utf-8")
    result = MODULE.aggregate_module(tmp_path, spec, "6.9", 5, False, 1e-6)
    assert result.delay_case_count == 1
    assert result.delay_prediction_time_s == 0.011
    assert result.delay_error_percent == 0.0
    assert result.delay_speedup == 1000.0 / 11
    assert all("config2" not in source for source in result.sources)
    assert result.area_speedup is None
