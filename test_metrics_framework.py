from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from metrics_framework import cli
from metrics_framework.core import (
    EvaluationUnavailable,
    Registry,
    _interpreter,
    evaluate,
    predict,
)
from metrics_framework.adapters import bp as bp_adapter
from metrics_framework.adapters import add as add_adapter
from metrics_framework.adapters import ls as ls_adapter
from metrics_framework.adapters import mimo as mimo_adapter
from metrics_framework.adapters import mul as mul_adapter


ROOT = Path(__file__).resolve().parent


def test_registered_add_uses_canonical_module_root():
    spec = Registry().get("add")
    expected = (ROOT / "Generator" / "Add" / "V0.2.1").resolve()
    assert spec.root == expected
    assert spec.config_dir == expected / "configs"
    assert spec.output_root == expected / "evaluation_output"


def test_registered_mul_uses_canonical_module_root():
    spec = Registry().get("mul")
    expected = (ROOT / "Generator" / "Mul" / "V0.2.1").resolve()
    assert spec.root == expected
    assert spec.config_dir == expected / "configs"
    assert spec.output_root == expected / "evaluation_output"


def test_registered_ls_uses_canonical_module_root():
    spec = Registry().get("ls")
    expected = (ROOT / "Generator" / "LSCE").resolve()
    assert spec.root == expected
    assert spec.config_dir == expected / "configs"
    assert spec.output_root == expected / "evaluation_output"
    assert Path(ls_adapter._module().__file__).resolve() == expected / "evaluate_lsce.py"


FAKE_ADAPTER = r'''
import hashlib
import json
import sys
from pathlib import Path

action = sys.argv[1]
path = Path(sys.argv[2])
config = json.loads(path.read_text(encoding="utf-8"))
digest = hashlib.sha256(json.dumps(
    config, ensure_ascii=False, sort_keys=True, separators=(",", ":")
).encode("utf-8")).hexdigest()
prediction_run = 1
if action == "predict" and config.get("count_prediction_runs"):
    counter_path = path.with_suffix(".prediction_runs")
    if counter_path.exists():
        prediction_run = int(counter_path.read_text(encoding="utf-8")) + 1
    counter_path.write_text(str(prediction_run), encoding="utf-8")
if action == "validate" and config.get("fail_validation"):
    print("validation unavailable", file=sys.stderr)
    raise SystemExit(2)
if action == "predict":
    metrics = {
        "latency": {"predicted_cycles": 8, "prediction_time_ms": 0.25 * prediction_run},
        "area": {"predicted_um2": 100.0, "prediction_time_ms": 2.0 * prediction_run},
        "throughput": {
            "predicted": 1.5,
            "unit": "Gbps",
            "precision": 2,
            "prediction_time_ms": 0.5 * prediction_run
        },
        "hardware_complexity": {
            "predicted_ge_cycles": 800.0,
            "prediction_time_ms": 0.75 * prediction_run,
            "ge_reference_cell": "NAND2",
            "ge_area_um2": 1.0
        }
    }
else:
    metrics = {
        "latency": {
            "actual_cycles": None if config.get("null_latency") else 10,
            "simulation_time_ms": None if config.get("null_latency_time") else 5.0,
            "reported_speedup": config.get("latency_speedup")
        },
        "area": {
            "actual_um2": None if config.get("null_area") else 125.0,
            "synthesis_time_ms": None if config.get("null_area_time") else 20.0,
            "reported_speedup": config.get("area_speedup")
        },
        "throughput": {"actual": None if config.get("null_throughput") else 1.25},
        "hardware_complexity": {
            "actual_ge_cycles": None if config.get("null_complexity") else 1250.0
        }
    }
if action == "validate" and config.get("mismatch_digest"):
    digest = "0" * 64
print(json.dumps({
    "protocol_version": 1,
    "status": "ok",
    "module": "fake",
    "action": action,
    "config_path": str(path.resolve()),
    "config_digest": digest,
    "evidence_paths": [str(path.resolve())],
    "metrics": metrics
}, ensure_ascii=False))
'''


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configs: list[dict]):
    root = tmp_path / "fake"
    config_dir = root / "configs"
    config_dir.mkdir(parents=True)
    adapter = tmp_path / "adapter.py"
    adapter.write_text(FAKE_ADAPTER, encoding="utf-8")
    for index, value in enumerate(configs, 1):
        (config_dir / f"config{index}.json").write_text(
            json.dumps(value), encoding="utf-8"
        )
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "modules": {
                    "fake": {
                        "adapter": str(adapter),
                        "root": str(root),
                        "config_dir": "configs",
                        "config_pattern": "config{case}.json",
                        "default_cases": list(range(1, len(configs) + 1)),
                        "python_env": "FAKE_METRICS_PYTHON",
                        "output_root": "evaluation_output",
                        "capabilities": [
                            "area",
                            "latency",
                            "throughput",
                            "hardware_complexity",
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FAKE_METRICS_PYTHON", sys.executable)
    return root, registry


def test_predict_uses_compact_chinese_shape(tmp_path, monkeypatch):
    root, registry = _fixture(tmp_path, monkeypatch, [{}])
    result = predict("fake", "1", registry=registry)

    assert result == {
        "延迟": {"预测结果 (cycles)": 8, "预测时间 (ms)": 0.25},
        "面积": {"预测结果 (μm²)": 100.0, "预测时间 (ms)": 2.0},
        "Throughput": {"预测结果 (Gbps)": 1.5, "预测时间 (ms)": 0.5},
        "硬件复杂度": {
            "预测结果 (GE·cycles)": 800.0,
            "预测时间 (ms)": 0.75,
            "GE基准单元": "NAND2",
            "1 GE面积 (μm²)": 1.0,
        },
        "自动评估总时间 (ms)": 3.5,
    }
    serialized = json.dumps(result, ensure_ascii=False)
    assert "null" not in serialized
    saved = json.loads(
        (root / "evaluation_output" / "config1" / "prediction.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved == result


def test_predict_never_runs_validation(tmp_path, monkeypatch):
    _root, registry = _fixture(tmp_path, monkeypatch, [{"fail_validation": True}])
    result = predict("fake", "1", registry=registry)
    assert result["面积"]["预测结果 (μm²)"] == 100.0


def test_predict_recomputes_times_and_ignores_previous_output(tmp_path, monkeypatch):
    root, registry = _fixture(
        tmp_path, monkeypatch, [{"count_prediction_runs": True}]
    )
    first = predict("fake", "1", registry=registry)
    output = root / "evaluation_output" / "config1" / "prediction.json"
    output.write_text('{"自动评估总时间 (ms)": 999}', encoding="utf-8")

    second = predict("fake", "1", registry=registry)

    assert first["自动评估总时间 (ms)"] == 3.5
    assert second["自动评估总时间 (ms)"] == 7.0
    assert json.loads(output.read_text(encoding="utf-8")) == second


def test_evaluate_builds_reference_display_shape(tmp_path, monkeypatch):
    root, registry = _fixture(tmp_path, monkeypatch, [{}])
    result = evaluate("fake", "1", registry=registry)

    assert result["延迟"] == {
        "预测结果 (cycles)": 8,
        "仿真结果 (cycles)": 10,
        "误差 (%)": 25.0,
        "预测时间 (ms)": 0.25,
        "仿真时间 (ms)": 5.0,
        "速度提升倍数 (×)": 20.0,
    }
    assert result["面积"]["速度提升倍数 (×)"] == 10.0
    assert result["Throughput"] == {
        "预测结果 (Gbps)": 1.5,
        "仿真结果 (Gbps)": 1.25,
        "预测时间 (ms)": 0.5,
    }
    assert "自动评估总时间 (ms)" not in result
    saved = json.loads(
        (root / "evaluation_output" / "config1" / "evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved == result


def test_batch_evaluation_omits_total_time_per_case(tmp_path, monkeypatch):
    _root, registry = _fixture(tmp_path, monkeypatch, [{}, {}])
    result = evaluate("fake", registry=registry)

    assert list(result) == ["config1", "config2"]
    assert "自动评估总时间 (ms)" not in result["config1"]
    assert "自动评估总时间 (ms)" not in result["config2"]


def test_bp_prediction_loads_iteration_model_before_timing(monkeypatch, tmp_path):
    events: list[str] = []
    clocks = iter((1.0, 1.001, 2.0, 2.002, 3.0, 3.0005, 4.0, 4.00075))
    expected_model_bundle = object()

    class AreaModule:
        @staticmethod
        def Esttop(**_kwargs):
            return 112.0

    class AreaIntegration:
        @staticmethod
        def _load_area_module():
            return AreaModule

    def load_iter_model():
        events.append("model_load")
        return expected_model_bundle

    def predict_iter(*_args, model_bundle):
        events.append("model_predict")
        assert model_bundle is expected_model_bundle
        return 2.0

    monkeypatch.setattr(
        bp_adapter.time,
        "perf_counter",
        lambda: (events.append("clock"), next(clocks))[1],
    )
    monkeypatch.setattr(
        bp_adapter,
        "_modules",
        lambda: (
            AreaIntegration,
            object(),
            lambda iterations, _terms: int(iterations * 10),
            lambda *_args: object(),
            lambda *_args: 2.0,
            "NAND2",
            lambda area, ge: area / ge,
            lambda: 1.12,
            load_iter_model,
            predict_iter,
        ),
    )
    config = {
        "decoder": {
            "hardware_architecture": "TypeI",
            "decoding_algorithm": "MS",
            "code_length": 64,
            "parallelism": 16,
            "data_width": 5,
            "code_rate": 0.5,
            "ebn0_db": 10.0,
        },
        "clock": {"period_ns": 20.0},
    }

    result = bp_adapter.predict(tmp_path / "config1.json", config)
    assert events[:3] == ["model_load", "clock", "model_predict"]
    assert result["latency"]["prediction_time_ms"] == pytest.approx(1.0)
    assert result["throughput"]["prediction_time_ms"] == pytest.approx(0.5)
    assert result["hardware_complexity"]["prediction_time_ms"] == pytest.approx(0.75)


def _add_config(n_pipeline=4):
    return {
        "input_1": {"bitwidth": 8, "fractional_width": 4, "signed": True},
        "input_2": {"bitwidth": 6, "fractional_width": 2, "signed": False},
        "output": {"bitwidth": 9, "fractional_width": 4, "signed": True},
        "n_pipeline": n_pipeline,
        "if_rst_n": False,
        "clock": {"period_ns": 5.0},
    }


def _mul_config(n_pipeline=4):
    return {
        "input_1": {"bitwidth": 4, "fractional_width": 2, "signed": True},
        "input_2": {"bitwidth": 4, "fractional_width": 2, "signed": True},
        "output": {"bitwidth": 7, "fractional_width": 3, "signed": True},
        "n_pipeline": n_pipeline,
        "if_rst_n": False,
        "clock": {"period_ns": 5.0},
    }


def test_mul_prediction_units_latency_throughput_and_complexity(monkeypatch, tmp_path):
    models = object()

    class Module:
        GE_REFERENCE_CELL = "NAND2"

        @staticmethod
        def parameters(config):
            return (4, 2, 1, 4, 2, 1, 7, 3, config["n_pipeline"], False, 5.0)

        @staticmethod
        def latency_cycles(params):
            return params[8]

        @staticmethod
        def load_area_models():
            return models

        @staticmethod
        def predict_area(value, _params):
            assert value is models
            return 112.0

        @staticmethod
        def throughput_gframes_s(params, *, interval_cycles=1):
            return 1.0 / (params[10] * interval_cycles)

        @staticmethod
        def read_ge_area():
            return 1.12

    monkeypatch.setattr(mul_adapter, "_module", lambda: Module)
    result = mul_adapter.predict(tmp_path / "config.json", _mul_config())
    assert result["latency"]["predicted_cycles"] == 4
    assert result["throughput"]["predicted"] == pytest.approx(0.2)
    assert result["throughput"]["unit"] == "Gframes/s"
    assert result["hardware_complexity"]["predicted_ge_cycles"] == pytest.approx(400.0)


def test_mul_validation_requires_fresh_pipeline_simulation(monkeypatch, tmp_path):
    config = _mul_config(n_pipeline=3)
    config["validation"] = {
        "area": {"actual_um2": 224.0, "synthesis_time_ms": 10.0},
        "latency": {
            "actual_cycles": 3,
            "simulation_time_ms": 1.0,
            "output_interval_cycles": 1,
        },
    }

    class Module:
        GE_REFERENCE_CELL = "NAND2"
        simulation_calls = 0

        @staticmethod
        def parameters(value):
            return (4, 2, 1, 4, 2, 1, 7, 3, value["n_pipeline"], False, 5.0)

        @staticmethod
        def latency_cycles(params):
            return params[8]

        @staticmethod
        def throughput_gframes_s(params, *, interval_cycles=1):
            return 1.0 / (params[10] * interval_cycles)

        @staticmethod
        def read_ge_area():
            return 1.12

        @classmethod
        def simulate_latency(cls, _path, _config, params):
            cls.simulation_calls += 1
            return {
                "sim_latency_cycles": params[8],
                "sim_output_interval_cycles": 1,
                "functional_match": True,
            }

        @staticmethod
        def read_area_reference(_params):
            pytest.fail("configured area must bypass the DC workbook")

    monkeypatch.setattr(mul_adapter, "_module", lambda: Module)
    result = mul_adapter.validate(tmp_path / "config.json", config)
    assert Module.simulation_calls == 1
    assert result["latency"]["actual_cycles"] == 3
    assert result["latency"]["simulation_time_ms"] > 0
    assert result["latency"]["simulation_time_ms"] != 1.0
    assert result["latency"]["output_interval_cycles"] == 1
    assert result["throughput"]["actual"] == pytest.approx(0.2)
    assert result["hardware_complexity"]["actual_ge_cycles"] == pytest.approx(600.0)

    mul_adapter.validate(tmp_path / "config.json", config)
    assert Module.simulation_calls == 2

    config["validation"]["latency"]["actual_cycles"] = 4
    with pytest.raises(ValueError, match="must equal n_pipeline"):
        mul_adapter.validate(tmp_path / "config.json", config)


def test_mul_area_reference_converts_seconds_to_milliseconds():
    module = mul_adapter._module()
    params = module.parameters(_mul_config(n_pipeline=1))
    reference = module.read_area_reference(params)
    assert reference["actual_area_um2"] == pytest.approx(271.879996)
    assert reference["synthesis_time_ms"] == pytest.approx(20306.021)


def test_mul_area_prediction_matches_workbook_automatic_result():
    module = mul_adapter._module()
    params = module.parameters(_mul_config(n_pipeline=1))
    area = module.predict_area(module.load_area_models(), params)
    assert area == pytest.approx(201.781030, abs=1e-5)


def test_mul_simulation_never_accepts_stale_result(monkeypatch, tmp_path):
    module = mul_adapter._module()
    simulation_root = tmp_path / "sim"
    stale_result = simulation_root / "config" / "simulation_result.json"
    stale_result.parent.mkdir(parents=True)
    stale_result.write_text('{"sim_latency_cycles": 999}', encoding="utf-8")
    monkeypatch.setattr(module, "SIMULATION_ROOT", simulation_root)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )

    config = _mul_config(n_pipeline=3)
    with pytest.raises(FileNotFoundError, match="was not generated"):
        module.simulate_latency(tmp_path / "config.json", config, module.parameters(config))
    assert not stale_result.exists()


def test_mul_runtime_generator_import_does_not_require_pytest():
    script = r'''
import builtins
import sys
from pathlib import Path

root = Path.cwd() / "Generator" / "Mul" / "V0.2.1"
sys.path.insert(0, str(root))
real_import = builtins.__import__

def reject_pytest(name, *args, **kwargs):
    if name == "pytest" or name.startswith("pytest."):
        raise ModuleNotFoundError("pytest intentionally unavailable")
    return real_import(name, *args, **kwargs)

builtins.__import__ = reject_pytest
from validate_mul_timing import _load_generators
_load_generators()
'''
    process = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert process.returncode == 0, process.stdout


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="Icarus Verilog is not installed",
)
def test_mul_rtl_simulator_measures_pipeline_depth(monkeypatch, tmp_path):
    module = mul_adapter._module()
    monkeypatch.setattr(module, "SIMULATION_ROOT", tmp_path / "sim")
    config = _mul_config(n_pipeline=3)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    params = module.parameters(config)
    result = module.simulate_latency(config_path, config, params)

    assert result["sim_latency_cycles"] == 3
    assert result["sim_output_interval_cycles"] == 1
    assert result["functional_match"] is True
    assert result["measurement_method"].startswith("canonical MUL PyTB + QuBLAS")
    assert result["matched_output_frames"] == 8


def test_mul_unsigned_default_case_runs_full_unified_evaluation():
    result = evaluate("mul", "2")
    assert result["延迟"]["预测结果 (cycles)"] == 1
    assert result["延迟"]["仿真结果 (cycles)"] == 1
    assert result["面积"]["真实结果 (μm²)"] == 220.64
    assert result["Throughput"]["预测结果 (Gframes/s)"] == 0.2
    assert result["Throughput"]["仿真结果 (Gframes/s)"] == 0.2


def test_add_prediction_uses_pipeline_latency_and_one_op_per_cycle(monkeypatch, tmp_path):
    model = object()

    class Module:
        GE_REFERENCE_CELL = "NAND2"

        @staticmethod
        def parameters(config):
            return (8, 4, 1, 6, 2, 0, 9, 4, config["n_pipeline"], False, 5.0)

        @staticmethod
        def latency_cycles(params):
            return params[8]

        @staticmethod
        def load_area_model():
            return model

        @staticmethod
        def predict_area(value, _params):
            assert value is model
            return 112.0

        @staticmethod
        def throughput_gframes_s(params):
            return 1.0 / params[10]

        @staticmethod
        def read_ge_area():
            return 1.12

    monkeypatch.setattr(add_adapter, "_module", lambda: Module)
    result = add_adapter.predict(tmp_path / "config.json", _add_config())
    assert result["latency"]["predicted_cycles"] == 4
    assert result["throughput"]["predicted"] == pytest.approx(0.2)
    assert result["throughput"]["unit"] == "Gframes/s"
    assert result["hardware_complexity"]["predicted_ge_cycles"] == pytest.approx(400.0)


def test_add_validation_real_latency_is_n_pipeline(monkeypatch, tmp_path):
    config = _add_config(n_pipeline=3)
    config["validation"] = {
        "area": {"actual_um2": 224.0, "synthesis_time_ms": 10.0},
        "latency": {
            "actual_cycles": 3,
            "simulation_time_ms": 1.0,
            "output_interval_cycles": 1,
        },
    }

    class Module:
        GE_REFERENCE_CELL = "NAND2"
        simulation_calls = 0

        @staticmethod
        def parameters(value):
            return (8, 4, 1, 6, 2, 0, 9, 4, value["n_pipeline"], False, 5.0)

        @staticmethod
        def latency_cycles(params):
            return params[8]

        @staticmethod
        def throughput_gframes_s(params):
            return 1.0 / params[10]

        @staticmethod
        def read_ge_area():
            return 1.12

        @classmethod
        def simulate_latency(cls, _path, _config, params):
            cls.simulation_calls += 1
            return {
                "sim_latency_cycles": params[8],
                "sim_output_interval_cycles": 1,
                "simulated_throughput_gframes_s": 0.2,
                "functional_match": True,
            }

        @staticmethod
        def read_area_reference(_params):
            pytest.fail("configured area must bypass the DC workbook")

    monkeypatch.setattr(add_adapter, "_module", lambda: Module)
    result = add_adapter.validate(tmp_path / "config.json", config)
    assert Module.simulation_calls == 1
    assert result["latency"]["actual_cycles"] == 3
    assert result["latency"]["simulation_time_ms"] > 0
    assert result["latency"]["simulation_time_ms"] != 1.0
    assert result["latency"]["output_interval_cycles"] == 1
    assert result["throughput"]["actual"] == pytest.approx(0.2)
    assert result["hardware_complexity"]["actual_ge_cycles"] == pytest.approx(600.0)

    add_adapter.validate(tmp_path / "config.json", config)
    assert Module.simulation_calls == 2


def test_add_rejects_actual_latency_different_from_n_pipeline(monkeypatch, tmp_path):
    config = _add_config(n_pipeline=3)
    config["validation"] = {
        "area": {"actual_um2": 224.0, "synthesis_time_ms": 10.0},
        "latency": {"actual_cycles": 4, "simulation_time_ms": 1.0},
    }

    class Module:
        @staticmethod
        def parameters(value):
            return (8, 4, 1, 6, 2, 0, 9, 4, value["n_pipeline"], False, 5.0)

        @staticmethod
        def latency_cycles(params):
            return params[8]

    monkeypatch.setattr(add_adapter, "_module", lambda: Module)
    with pytest.raises(ValueError, match="must equal n_pipeline"):
        add_adapter.validate(tmp_path / "config.json", config)


def test_add_validation_uses_rtl_latency_and_interval(monkeypatch, tmp_path):
    config = _add_config(n_pipeline=3)
    config["validation"] = {
        "area": {"actual_um2": 224.0, "synthesis_time_ms": 10.0}
    }

    class Module:
        GE_REFERENCE_CELL = "NAND2"

        @staticmethod
        def parameters(value):
            return (8, 4, 1, 6, 2, 0, 9, 4, value["n_pipeline"], False, 5.0)

        @staticmethod
        def latency_cycles(params):
            return params[8]

        @staticmethod
        def simulate_latency(path, _config, params):
            assert path == tmp_path / "config.json"
            assert params[8] == 3
            return {
                "sim_latency_cycles": 3,
                "sim_output_interval_cycles": 1,
                "simulated_throughput_gframes_s": 0.125,
                "rtl_simulation_time_ms": 25.0,
                "functional_match": True,
            }

        @staticmethod
        def read_ge_area():
            return 1.12

        @staticmethod
        def read_area_reference(_params):
            pytest.fail("configured area must bypass the DC workbook")

    monkeypatch.setattr(add_adapter, "_module", lambda: Module)
    result = add_adapter.validate(tmp_path / "config.json", config)
    assert result["latency"]["actual_cycles"] == 3
    assert result["latency"]["simulation_time_ms"] > 0
    assert result["latency"]["output_interval_cycles"] == 1
    assert result["latency"]["reported_speedup"] is None
    assert result["latency"]["source"] == "rtl"
    assert result["throughput"] == {"actual": pytest.approx(0.125), "source": "rtl_measured"}


def test_add_simulation_never_accepts_stale_result(monkeypatch, tmp_path):
    module = add_adapter._module()
    simulation_root = tmp_path / "sim"
    stale_result = simulation_root / "config" / "simulation_result.json"
    stale_result.parent.mkdir(parents=True)
    stale_result.write_text('{"sim_latency_cycles": 999}', encoding="utf-8")
    monkeypatch.setattr(module, "SIMULATION_ROOT", simulation_root)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )

    config = _add_config(n_pipeline=3)
    with pytest.raises(FileNotFoundError, match="was not generated"):
        module.simulate_latency(tmp_path / "config.json", config, module.parameters(config))
    assert not stale_result.exists()


@pytest.mark.skipif(
    shutil.which("iverilog") is None
    or shutil.which("vvp") is None
    or (shutil.which("clang++") is None and shutil.which("g++") is None),
    reason="ADD simulation toolchain is not installed",
)
def test_add_rtl_simulator_measures_pipeline_depth(monkeypatch, tmp_path):
    module = add_adapter._module()
    monkeypatch.setattr(module, "SIMULATION_ROOT", tmp_path / "sim")
    config = _add_config(n_pipeline=3)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    params = module.parameters(config)
    result = module.simulate_latency(config_path, config, params)

    assert result["sim_latency_cycles"] == 3
    assert result["sim_output_interval_cycles"] == 1
    assert result["simulated_throughput_gframes_s"] == pytest.approx(0.2)
    assert (
        result["output_ready_times_ns"][2] - result["output_ready_times_ns"][0]
    ) == pytest.approx(10.0)
    assert result["functional_match"] is True
    assert result["matched_output_frames"] == 3
    assert result["testbench_source"].endswith("tests\\tb_Add.py") or result[
        "testbench_source"
    ].endswith("tests/tb_Add.py")
    assert result["reference_source"] == "original ModuleCppConfig/ModuleCppRun with QuBLAS"


def test_add_default_case_runs_full_unified_evaluation():
    result = evaluate("add", "2")
    assert result["延迟"]["预测结果 (cycles)"] == 1
    assert result["延迟"]["仿真结果 (cycles)"] == 1
    assert result["面积"]["真实结果 (μm²)"] == 11.48
    assert result["Throughput"]["预测结果 (Gframes/s)"] == 0.1
    assert result["Throughput"]["仿真结果 (Gframes/s)"] == 0.1


def test_incomplete_validation_does_not_write_evaluation(tmp_path, monkeypatch):
    root, registry = _fixture(tmp_path, monkeypatch, [{"null_latency": True}])
    with pytest.raises(EvaluationUnavailable, match="actual latency"):
        evaluate("fake", "1", registry=registry)
    output = root / "evaluation_output" / "config1"
    assert not (output / "evaluation.json").exists()
    assert (output / "diagnostics" / "prediction.json").is_file()
    assert (output / "diagnostics" / "evaluation_error.json").is_file()


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"null_area": True}, "actual area"),
        ({"null_latency_time": True}, "latency speedup"),
        ({"null_area_time": True}, "area speedup"),
        ({"null_throughput": True}, "actual throughput"),
        ({"null_complexity": True}, "actual hardware complexity"),
        ({"mismatch_digest": True}, "config digests differ"),
    ],
)
def test_evaluate_rejects_each_incomplete_contract(
    tmp_path, monkeypatch, config, message
):
    root, registry = _fixture(tmp_path, monkeypatch, [config])
    with pytest.raises(EvaluationUnavailable, match=message):
        evaluate("fake", "1", registry=registry)
    assert not (
        root / "evaluation_output" / "config1" / "evaluation.json"
    ).exists()


def test_reported_speedups_fill_missing_validation_times(tmp_path, monkeypatch):
    _root, registry = _fixture(
        tmp_path,
        monkeypatch,
        [
            {
                "null_latency_time": True,
                "latency_speedup": 20.0,
                "null_area_time": True,
                "area_speedup": 10.0,
            }
        ],
    )
    result = evaluate("fake", "1", registry=registry)
    assert result["延迟"]["速度提升倍数 (×)"] == 20.0
    assert result["面积"]["速度提升倍数 (×)"] == 10.0


def test_batch_evaluation_is_atomic_at_api_boundary(tmp_path, monkeypatch):
    root, registry = _fixture(tmp_path, monkeypatch, [{}, {"fail_validation": True}])
    with pytest.raises(EvaluationUnavailable, match="config2"):
        evaluate("fake", registry=registry)
    assert (root / "evaluation_output" / "config1" / "evaluation.json").is_file()
    assert not (root / "evaluation_output" / "config2" / "evaluation.json").exists()


def test_cli_evaluation_failure_has_empty_stdout(monkeypatch, capsys):
    def unavailable(*_args, **_kwargs):
        raise EvaluationUnavailable("RTL unavailable")

    monkeypatch.setattr(cli, "evaluate", unavailable)
    exit_code = cli.main(["ls", "evaluate", "1"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "RTL unavailable" in captured.err


def test_cli_prints_adapter_validation_failure_once(tmp_path, monkeypatch, capsys):
    _root, registry = _fixture(
        tmp_path, monkeypatch, [{"fail_validation": True}]
    )

    def run_fixture(_module, config):
        return evaluate("fake", config, registry=registry)

    monkeypatch.setattr(cli, "evaluate", run_fixture)
    exit_code = cli.main(["fake", "evaluate", "1"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.count("validation unavailable") == 1


def test_cli_success_prints_exactly_one_json(monkeypatch, capsys):
    expected = {"延迟": {"预测结果 (cycles)": 8}}
    monkeypatch.setattr(cli, "predict", lambda *_args, **_kwargs: expected)
    assert cli.main(["ls", "predict", "1"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert captured.err == ""


def test_interpreter_preserves_virtualenv_symlink(monkeypatch):
    expected = Path("/workspace/.venv/bin/python")

    class VirtualenvPython:
        def is_file(self):
            return True

        def absolute(self):
            return expected

        def resolve(self):
            pytest.fail("virtualenv interpreter symlink must not be resolved")

    monkeypatch.setattr(
        "metrics_framework.core._candidate_interpreters",
        lambda _spec: [VirtualenvPython()],
    )
    assert _interpreter(object()) == expected


def _validation_config():
    return {
        "validation": {
            "area": {
                "actual_um2": 112.0,
                "synthesis_time_ms": 20.0,
                "reported_speedup": None,
            },
            "latency": {
                "actual_cycles": 10,
                "simulation_time_ms": 5.0,
                "output_interval_cycles": 4,
                "reported_speedup": None,
            },
        }
    }


def test_ls_validation_json_still_runs_fresh_rtl(monkeypatch, tmp_path):
    config = _validation_config()
    config.update({"clock": {"period_ns": 10.0}, "Number of Receiving Antennas": 2})

    class Module:
        @staticmethod
        def validate_config(value, _path):
            return value

        @staticmethod
        def read_workbook_area_reference(_value):
            pytest.fail("area reference must not be read")

        @staticmethod
        def simulate_lsce(*_args, **_kwargs):
            return {"latency_cycles": 10, "output_interval_cycles": 4}

    monkeypatch.setattr(ls_adapter, "_module", lambda: Module)
    result = ls_adapter.validate(tmp_path / "config.json", config)
    assert result["area"]["actual_um2"] == 112.0
    assert result["latency"]["actual_cycles"] == 10
    assert result["latency"]["source"] == "rtl"
    assert result["latency"]["simulation_time_ms"] > 0
    assert result["throughput"]["actual"] == 12500.0
    assert result["hardware_complexity"]["actual_ge_cycles"] == pytest.approx(1000.0)


def test_mimo_validation_json_still_runs_fresh_rtl(monkeypatch, tmp_path):
    config = _validation_config()

    class Evaluator:
        @staticmethod
        def load_config(_path):
            return config

        @staticmethod
        def simulate_rtl(_path):
            return {
                "sim_latency_cycles": 10,
                "sim_output_interval_cycles": 4,
                "functional_match": True,
            }

    def throughput(_config, *, simulated_output_interval_cycles):
        assert simulated_output_interval_cycles == 4
        return {"simulated_gbps": 0.5}

    monkeypatch.setattr(
        mimo_adapter,
        "_modules",
        lambda: (
            Evaluator,
            "NAND2",
            lambda area, ge: area / ge,
            lambda: 1.12,
            lambda _config: 8,
            throughput,
        ),
    )
    monkeypatch.setattr(
        mimo_adapter,
        "_area",
        lambda *_args: pytest.fail("area reference must not be read"),
    )
    result = mimo_adapter.validate(tmp_path / "config.json", config)
    assert result["throughput"]["actual"] == 0.5
    assert result["latency"]["source"] == "rtl"
    assert result["latency"]["simulation_time_ms"] > 0
    assert result["hardware_complexity"]["actual_ge_cycles"] == pytest.approx(1000.0)


def test_ls_rtl_validation_reports_measured_latency(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "config_case7.json"
    config = {
        "clock": {"period_ns": 10.0},
        "Number of Receiving Antennas": 2,
        "validation": {
            "area": {
                "actual_um2": 112.0,
                "synthesis_time_ms": 20.0,
                "reported_speedup": None,
            }
        },
    }

    class Module:
        @staticmethod
        def validate_config(value, path):
            assert path == config_path
            return value

        @staticmethod
        def read_workbook_area_reference(_value):
            pytest.fail("area reference must not be read")

        @staticmethod
        def simulate_lsce(path, *, config):
            assert path == config_path
            return {"latency_cycles": 12, "output_interval_cycles": 4}

    monkeypatch.setattr(ls_adapter, "_module", lambda: Module)
    result = ls_adapter.validate(config_path, config)
    assert result["latency"]["actual_cycles"] == 12
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "Success. The RTL latency of config_case7 is 12 cycles\n"
    )


def test_mimo_rtl_validation_reports_measured_latency(
    monkeypatch, tmp_path, capsys
):
    config_path = tmp_path / "config_case8.json"
    config = {
        "validation": {
            "area": {
                "actual_um2": 112.0,
                "synthesis_time_ms": 20.0,
                "reported_speedup": None,
            }
        }
    }

    class Evaluator:
        @staticmethod
        def load_config(path):
            assert path == config_path
            return config

        @staticmethod
        def simulate_rtl(path):
            assert path == config_path
            return {
                "sim_latency_cycles": 14,
                "sim_output_interval_cycles": 2,
                "functional_match": True,
            }

    monkeypatch.setattr(
        mimo_adapter,
        "_modules",
        lambda: (
            Evaluator,
            "NAND2",
            lambda area, ge: area / ge,
            lambda: 1.12,
            lambda _config: 8,
            lambda _config, *, simulated_output_interval_cycles: {
                "simulated_gbps": 0.5
            },
        ),
    )
    monkeypatch.setattr(
        mimo_adapter,
        "_area",
        lambda *_args: pytest.fail("area reference must not be read"),
    )
    result = mimo_adapter.validate(config_path, config)
    assert result["latency"]["actual_cycles"] == 14
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "Success. The RTL latency of config_case8 is 14 cycles\n"
    )


def test_bp_validation_json_still_runs_fresh_rtl(monkeypatch, tmp_path):
    config = _validation_config()
    config["decoder"] = {
        "hardware_architecture": "TypeI",
        "decoding_algorithm": "MS",
        "code_length": 64,
        "parallelism": 16,
        "data_width": 5,
        "code_rate": 0.5,
        "ebn0_db": 10.0,
    }
    config["clock"] = {"period_ns": 20.0}

    class AreaIntegration:
        @staticmethod
        def _load_area_module():
            pytest.fail("area reference must not be read")

    class Evaluator:
        @staticmethod
        def configured_simulation_dir(_path):
            return tmp_path / "sim" / "config"

        @staticmethod
        def simulate_rtl(*_args, **_kwargs):
            return {
                "sim_latency_cycles": 10,
                "cpp_iterations": 2.0,
                "waveform_verified": True,
                "decoding_verified": True,
            }

    class Terms:
        decision_cycles = 4
        cycles_per_iteration = 44

    monkeypatch.setattr(
        bp_adapter,
        "_modules",
        lambda: (
            AreaIntegration,
            Evaluator,
            lambda *_args: 8,
            lambda *_args: Terms(),
            lambda latency, terms: (latency - terms.decision_cycles)
            / terms.cycles_per_iteration,
            "NAND2",
            lambda area, ge: area / ge,
            lambda: 1.12,
            lambda: object(),
            lambda *_args: 2.0,
        ),
    )
    result = bp_adapter.validate(tmp_path / "config.json", config)
    assert result["latency"]["actual_cycles"] == 10
    assert result["latency"]["source"] == "rtl"
    assert result["latency"]["simulation_time_ms"] > 0
    assert result["throughput"]["actual"] == pytest.approx(0.16)
    assert result["hardware_complexity"]["actual_ge_cycles"] == pytest.approx(1000.0)


def test_bp_rtl_validation_uses_canonical_sim_directory(
    monkeypatch, tmp_path, capsys
):
    config_path = tmp_path / "config6.json"
    simulation_dir = tmp_path / "sim" / "config6"
    config = {
        "decoder": {
            "hardware_architecture": "TypeI",
            "decoding_algorithm": "MS",
            "code_length": 64,
            "parallelism": 16,
            "data_width": 5,
            "code_rate": 0.5,
            "ebn0_db": 10.0,
        },
        "clock": {"period_ns": 20.0},
        "validation": {
            "area": {
                "actual_um2": 112.0,
                "synthesis_time_ms": 20.0,
                "reported_speedup": None,
            }
        },
    }
    observed: dict[str, Path] = {}

    class AreaIntegration:
        @staticmethod
        def _load_area_module():
            pytest.fail("area reference must not be read")

    class Evaluator:
        @staticmethod
        def configured_simulation_dir(path):
            assert path == config_path
            return simulation_dir

        @staticmethod
        def simulate_rtl(rtl_config, case_dir, *, label):
            observed["rtl_config"] = rtl_config
            observed["case_dir"] = case_dir
            assert label == "config6"
            return {
                "sim_latency_cycles": 10,
                "rtl_simulation_time_ms": 5.0,
                "cpp_iterations": 2.0,
                "waveform_verified": True,
                "decoding_verified": True,
            }

    class Terms:
        decision_cycles = 4
        cycles_per_iteration = 44

    monkeypatch.setattr(
        bp_adapter,
        "_modules",
        lambda: (
            AreaIntegration,
            Evaluator,
            lambda *_args: 8,
            lambda *_args: Terms(),
            lambda latency, terms: (latency - terms.decision_cycles)
            / terms.cycles_per_iteration,
            "NAND2",
            lambda area, ge: area / ge,
            lambda: 1.12,
            lambda: object(),
            lambda *_args: 2.0,
        ),
    )

    result = bp_adapter.validate(config_path, config)
    assert observed["case_dir"] == simulation_dir
    assert observed["rtl_config"] == simulation_dir / "rtl_config.json"
    assert observed["rtl_config"].is_file()
    assert result["latency"]["source"] == "rtl"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Success. The RTL latency of config6 is 10 cycles\n"
