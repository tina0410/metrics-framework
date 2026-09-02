"""Contract tests and opt-in standalone C++/RTL regressions for LSCE."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch

import pytest

import evaluate_lsce as evaluation
from BehaviorialVerification import generate_lsce_testcase as generation
from BehaviorialVerification import lsce_reference as reference
from BehaviorialVerification import validate_lsce_latency as validation
from BehaviorialVerification.validate_lsce_latency import measure_rtl_timing, run_validation


ROOT = Path(__file__).resolve().parent


@pytest.fixture
def config():
    return evaluation.load_config(ROOT / "configs" / "config_case1.json")


def test_sim_root_is_module_local():
    expected = ROOT / "BehaviorialVerification" / "sim"
    assert generation.SIM_ROOT == expected
    assert validation.SIM_DIR == expected
    assert validation.VALIDATION_DIR == expected


def test_generator_context_isolates_area_model_pytu(config, monkeypatch):
    area_pytu = ModuleType("PyTU")
    monkeypatch.setitem(sys.modules, "PyTU", area_pytu)
    with reference.generator_context():
        parameters = reference.generator_parameters(config)
        first_generator_pytu = sys.modules["PyTU"]
    with reference.generator_context():
        assert sys.modules["PyTU"] is first_generator_pytu
    assert parameters["P_T"] == 4
    assert parameters["QU_Y"].intBits() == 5
    assert parameters["QU_Y"].fracBits() == 4
    assert sys.modules["PyTU"] is area_pytu


@pytest.mark.parametrize(
    "field,value",
    [
        ("Parallelism T", True),
        ("Parallelism T", 1.5),
        ("Parallelism T", 0),
        ("Parallelism T", 3),
        ("Pipeline Stages ([Multiplication, Adder Tree])", [1, -1]),
        ("Pipeline Stages ([Multiplication, Adder Tree])", [True, 1]),
        ("clock", {"period_ns": float("nan")}),
        ("clock", []),
        ("clock", {"period_ns": True}),
        ("Quantization Mode", "TRN.BAD"),
        ("Overflow Mode", "SAT.BAD"),
        ("Parallelism R", 8),
    ],
)
def test_invalid_config(config, tmp_path, field, value):
    config[field] = value
    path = tmp_path / "config_case7.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError):
        evaluation.load_config(path)


def test_bom_external_config_and_generator_parameters(config, tmp_path):
    path = tmp_path / "config_case7.json"
    path.write_text(json.dumps(config), encoding="utf-8-sig")
    loaded = evaluation.load_config(path)
    with reference.generator_context():
        original = reference.generator_parameters(loaded)
        loaded["Parallelism T"] = 8
        changed = reference.generator_parameters(loaded)
    assert original["P_T"] == 4
    assert changed["P_T"] == 8
    assert evaluation.resolve_config_selection(path) == [path.resolve()]


@pytest.mark.parametrize(
    "field,value",
    [
        ("bitwidth", 0),
        ("bitwidth", True),
        ("bitwidth", 10.5),
        ("fractional width", -1),
        ("fractional width", 11),
        ("signed", 1),
    ],
)
def test_invalid_quantization(config, tmp_path, field, value):
    config["Quantization format of Y"][field] = value
    with pytest.raises(ValueError):
        evaluation.validate_config(config, tmp_path / "config_case7.json")


def test_prediction_only_allows_receive_grouping(config, tmp_path):
    config["Parallelism R"] = 8
    config["flow"]["run_simulation"] = False
    assert evaluation.validate_config(config, tmp_path / "arbitrary.json") is config


def test_cleanup_preserves_other_cases_and_user_files(config, tmp_path):
    paths = [tmp_path / f"config_case{i}.json" for i in (1, 2)]
    for index, path in enumerate(paths, 1):
        value = copy.deepcopy(config)
        value["flow"]["output_dir"] = f"results{index}"
        path.write_text(json.dumps(value), encoding="utf-8")
        output = tmp_path / f"results{index}"
        output.mkdir()
        (output / "lsce_metrics.json").write_text("old")
        (output / "user.txt").write_text("keep")
    evaluation.cleanup_previous_run([paths[0]])
    assert not (tmp_path / "results1/lsce_metrics.json").exists()
    assert (tmp_path / "results2/lsce_metrics.json").read_text() == "old"
    assert (tmp_path / "results1/user.txt").read_text() == "keep"
    with patch.object(generation, "SIM_ROOT", tmp_path / "sim"):
        first = tmp_path / "sim/Testcase1"
        second = tmp_path / "sim/Testcase2/workspace/RTL"
        second.mkdir(parents=True)
        (second / "user.v").write_text("keep")
        (first / "workspace/RTL").mkdir(parents=True)
        (first / "user.txt").write_text("keep")
        generation.clean_case(1)
        assert not (first / "workspace/RTL").exists()
        assert (first / "user.txt").read_text() == "keep"
        assert (second / "user.v").read_text() == "keep"


def test_invalid_case_does_not_clean(tmp_path):
    with patch.object(generation, "SIM_ROOT", tmp_path):
        with pytest.raises(ValueError):
            generation.clean_case(-1)
    assert list(tmp_path.iterdir()) == []


def test_failed_reference_does_not_reuse_success(config, tmp_path):
    path = tmp_path / "config_case7.json"
    path.write_text(json.dumps(config))
    case_root = tmp_path / "sim/Testcase7"
    case_root.mkdir(parents=True)
    marker = case_root / "simulation_result.json"
    marker.write_text('{"sim_latency_cycles": 999}')
    with patch.object(generation, "SIM_ROOT", tmp_path / "sim"), patch.object(
        reference,
        "generate_reference_files",
        side_effect=RuntimeError("standalone reference failed"),
    ):
        with pytest.raises(RuntimeError, match="standalone reference failed"):
            generation.generate_testcase(path, 7)
    assert not marker.exists()


def test_complete_reference_is_required_by_probe(tmp_path):
    probe, expected = tmp_path / "probe.txt", tmp_path / "expected.txt"
    probe.write_text("0 xx\n1 aa\n2 bb\n3 cc\n4 dd\n")
    expected.write_text("aa\ncc\n")
    assert measure_rtl_timing(probe, expected)[:2] == (2, 2)
    with pytest.raises(RuntimeError, match="complete C\\+\\+"):
        measure_rtl_timing(probe, expected, expected_rows=["aa", "cc", "ff"])


def test_compiler_mismatch_fails_without_build(config, tmp_path):
    with patch.object(reference, "_run", return_value="clang version 22.1.8"), patch.dict(
        os.environ, {"CXX": "clang++"}
    ):
        with pytest.raises(RuntimeError, match="requires Clang 20"):
            reference.clang20()
    assert not (tmp_path / "CppModules").exists()


def test_generate_cpp_algorithm_and_runner_templates(config, tmp_path):
    workspace = tmp_path / "workspace"
    source, include = reference._generate_sources(config, workspace, 7, 10)
    assert source.name == "main.cpp"
    assert "int main()" in source.read_text()
    assert "inline void LSCE_ACC(" in (include / "config.h").read_text()
    assert (include / "QuBLAS.h").is_file()


native = pytest.mark.skipif(
    os.environ.get("LSCE_RUN_NATIVE") != "1",
    reason="set LSCE_RUN_NATIVE=1 with Clang 20",
)
rtl = pytest.mark.skipif(
    os.environ.get("LSCE_RUN_RTL") != "1",
    reason="set LSCE_RUN_RTL=1 with the complete RTL/model toolchain",
)


@pytest.mark.native
@native
@pytest.mark.parametrize("case_id", [1, 2, 3, 4, 5])
def test_native_standalone_reference(case_id, tmp_path):
    config = evaluation.load_config(ROOT / "configs" / f"config_case{case_id}.json")
    first = reference.generate_reference_files(config, tmp_path / "first", case_id)
    second = reference.generate_reference_files(config, tmp_path / "second", case_id)
    assert first == second
    manifest = json.loads(
        (tmp_path / "first/CppModules/reference_build.json").read_text()
    )
    assert manifest["backend"] == "standalone_cpp"
    assert manifest["status"] == "ready"


@pytest.mark.native
@native
@pytest.mark.parametrize("change", ["parallelism", "quantization", "single_stage"])
def test_native_configuration_change(config, tmp_path, change):
    if change == "parallelism":
        config["Parallelism T"] = 8
    elif change == "single_stage":
        config["Parallelism T"] = config["Number of Transmit Antennas"]
    else:
        config["Quantization format of H"]["fractional width"] = 3
        config["Overflow Mode"] = "SAT.TCPL"
    rows = reference.generate_reference_files(config, tmp_path / "workspace", 7)
    assert len(rows["o_H"]) == 10


@pytest.mark.rtl
@rtl
@pytest.mark.parametrize("case_id", [1, 2, 3, 4, 5])
def test_standard_rtl(case_id):
    path = ROOT / "configs" / f"config_case{case_id}.json"
    result = evaluation.run_lsce_evaluation(path)
    assert result["延迟"]["仿真结果 (cycles)"] is not None
    assert result["Throughput"]["仿真结果 (kChannels/s)"] is not None


@pytest.mark.rtl
@rtl
def test_external_rtl_config_change(config, tmp_path):
    path = tmp_path / "config_case7.json"
    config["Parallelism T"] = 8
    path.write_text(json.dumps(config), encoding="utf-8-sig")
    result = run_validation(path, 7)
    assert result["sim_output_interval_cycles"] == 2
    config["Parallelism T"] = 4
    path.write_text(json.dumps(config), encoding="utf-8-sig")
    result = run_validation(path, 7)
    assert result["sim_output_interval_cycles"] == 4
