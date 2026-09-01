"""Contract tests and opt-in native/RTL regressions; no simulated native results."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest.mock import patch

import pytest

import evaluate_lsce as evaluation
from BehaviorialVerification import generate_lsce_testcase as generation
from BehaviorialVerification import lsce_binding as binding
from BehaviorialVerification.validate_lsce_latency import measure_rtl_timing, run_validation

ROOT = Path(__file__).resolve().parent


@pytest.fixture
def config():
    return evaluation.load_config(ROOT / "configs/config_case1.json")


def test_generator_context_isolates_area_model_pytu(config, monkeypatch):
    area_pytu = ModuleType("PyTU")
    monkeypatch.setitem(sys.modules, "PyTU", area_pytu)

    rendered = binding.render_parameters(config)

    assert "using QU_Y = Qu<" in rendered
    assert sys.modules["PyTU"] is area_pytu


@pytest.mark.parametrize("field,value", [
    ("Parallelism T", True), ("Parallelism T", 1.5),
    ("Parallelism T", 0), ("Parallelism T", 3),
    ("Pipeline Stages ([Multiplication, Adder Tree])", [1, -1]),
    ("Pipeline Stages ([Multiplication, Adder Tree])", [True, 1]),
    ("clock", {"period_ns": float("nan")}), ("clock", []),
    ("clock", {"period_ns": True}),
    ("Quantization Mode", "TRN.BAD"), ("Overflow Mode", "SAT.BAD"),
    ("Parallelism R", 8),
])
def test_invalid_config(config, tmp_path, field, value):
    config[field] = value
    path = tmp_path / "config_case7.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError):
        evaluation.load_config(path)


def test_bom_external_config_and_compile_parameters(config, tmp_path):
    path = tmp_path / "config_case7.json"
    path.write_text(json.dumps(config), encoding="utf-8-sig")
    loaded = evaluation.load_config(path)
    original = binding.render_parameters(loaded)
    loaded["Parallelism T"] = 8
    changed = binding.render_parameters(loaded)
    assert "P_T = 4;" in original and "P_T = 8;" in changed
    assert loaded == {**config, "Parallelism T": 8}
    assert evaluation.resolve_config_selection(path) == [path.resolve()]


@pytest.mark.parametrize("field,value", [
    ("bitwidth", 0), ("bitwidth", True), ("bitwidth", 10.5),
    ("fractional width", -1), ("fractional width", 11), ("signed", 1),
])
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


def test_failed_binding_does_not_reuse_success(config, tmp_path):
    path = tmp_path / "config_case7.json"
    path.write_text(json.dumps(config))
    case_root = tmp_path / "sim/Testcase7"
    case_root.mkdir(parents=True)
    marker = case_root / "simulation_result.json"
    marker.write_text('{"sim_latency_cycles": 999}')
    with patch.object(generation, "SIM_ROOT", tmp_path / "sim"), \
         patch.object(binding, "build_reference", side_effect=RuntimeError("binding failed")):
        with pytest.raises(RuntimeError, match="binding failed"):
            generation.generate_testcase(path, 7)
    assert not marker.exists()


def test_complete_reference_is_required_by_probe(tmp_path):
    probe, expected = tmp_path / "probe.txt", tmp_path / "expected.txt"
    probe.write_text("0 xx\n1 aa\n2 bb\n3 cc\n4 dd\n")
    expected.write_text("aa\ncc\n")
    assert measure_rtl_timing(probe, expected)[:2] == (2, 2)
    with pytest.raises(RuntimeError, match="complete C\\+\\+"):
        measure_rtl_timing(probe, expected, expected_rows=["aa", "cc", "ff"])


def test_compiler_mismatch_fails_without_artifacts(config, tmp_path):
    with patch.object(binding, "_run", return_value="clang version 22.1.8"), \
         patch.dict(os.environ, {"CXX": "clang++"}):
        with pytest.raises(RuntimeError, match="requires Clang 20"):
            binding.build_reference(config, tmp_path / "artifacts")
    assert not (tmp_path / "artifacts").exists()


def test_single_batch_and_cli_share_configuration_once(config, tmp_path):
    path = tmp_path / "config_case7.json"
    config["flow"]["run_simulation"] = False
    path.write_text(json.dumps(config))
    marker = {"contract": "shared"}
    with patch.object(evaluation, "load_config", wraps=evaluation.load_config) as loader, \
         patch.object(evaluation, "_evaluate_config", return_value=marker) as core:
        assert evaluation.run_lsce_evaluation(path) == marker
        assert evaluation.run_lsce_evaluations(path) == {path.stem: marker}
        with patch.object(sys, "argv", ["evaluate_lsce.py", str(path)]):
            evaluation.main()
        assert loader.call_count == 3
        assert core.call_count == 3
        assert all(call.args[0] == path.resolve() for call in core.call_args_list)


def test_generate_cpp_algorithm_template(tmp_path):
    with binding.generator_context():
        from pytv.ModuleLoader import moduleloader
        from BehavModel_LSCE import ModuleCppConfig
        moduleloader.reset()
        moduleloader.set_root_dir(str(tmp_path))
        moduleloader.set_language_mode("CPP_HEADER")
        moduleloader.set_naming_mode("SEQUENTIAL")
        ModuleCppConfig()
        headers = list(tmp_path.glob("CppConfig*.h"))
        assert len(headers) == 1
        assert "inline void LSCE_ACC(" in headers[0].read_text()
        moduleloader.reset()


native = pytest.mark.skipif(os.environ.get("LSCE_RUN_NATIVE") != "1",
                            reason="set LSCE_RUN_NATIVE=1 with Clang 20 and nanobind")
rtl = pytest.mark.skipif(os.environ.get("LSCE_RUN_RTL") != "1",
                         reason="set LSCE_RUN_RTL=1 with the complete RTL/model toolchain")


@pytest.mark.native
@native
@pytest.mark.parametrize("case_id", [1, 2, 3, 4, 5])
def test_native_matches_legacy_cpp(case_id, tmp_path):
    config = evaluation.load_config(ROOT / "configs" / f"config_case{case_id}.json")
    _compare_native_and_legacy(config, tmp_path)


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
    path = tmp_path / "config_case7.json"
    path.write_text(json.dumps(config), encoding="utf-8-sig")
    _compare_native_and_legacy(evaluation.load_config(path), tmp_path)


def _compare_native_and_legacy(config, tmp_path):
    module = binding.build_reference(config, tmp_path / "artifacts")
    rows = module.reference_frames(10)
    assert rows == module.reference_frames(10)
    with pytest.raises(ValueError):
        module.reference_frames(0)
    with pytest.raises(ValueError):
        module.reference_frames(-1)
    with pytest.raises(TypeError):
        module.reference_frames(1.5)
    manifest = json.loads((tmp_path / "artifacts/binding_build.json").read_text())
    assert manifest["binding_backend"] == "nanobind"
    assert manifest["nanobind_version"]
    generated = Path(manifest["build_root"]) / "sources"
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    for name in ("inputs", "outputs"):
        (legacy / name).mkdir()
    with binding.generator_context():
        from pytv.ModuleLoader import moduleloader
        from BehavModel_LSCE import ModuleCppRun
        moduleloader.reset()
        moduleloader.set_root_dir(str(legacy))
        moduleloader.set_language_mode("CPP")
        moduleloader.set_naming_mode("SEQUENTIAL")
        ModuleCppRun(**binding.generator_parameters(config), N_FRAMES=10,
                     input_file_dir="inputs", comparison_file_dir="outputs")
        source, = legacy.glob("CppRun*.cpp")
        moduleloader.reset()
    executable = legacy / ("reference.exe" if os.name == "nt" else "reference")
    subprocess.run([binding.clang20(), "-std=c++23", str(source), "-I", str(generated),
                    "-I", str(binding.ROOT / "include"), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], cwd=legacy, check=True)
    for name, values in rows.items():
        folder = "outputs" if name in ("o_H", "Decimal_o_H") else "inputs"
        assert (legacy / folder / f"{name}.txt").read_text().splitlines() == values, name


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
