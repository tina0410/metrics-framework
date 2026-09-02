from __future__ import annotations

import json
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
from metrics_framework.adapters import ls as ls_adapter
from metrics_framework.adapters import mimo as mimo_adapter


ROOT = Path(__file__).resolve().parent


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
if action == "validate" and config.get("fail_validation"):
    print("validation unavailable", file=sys.stderr)
    raise SystemExit(2)
if action == "predict":
    metrics = {
        "latency": {"predicted_cycles": 8, "prediction_time_ms": 0.25},
        "area": {"predicted_um2": 100.0, "prediction_time_ms": 2.0},
        "throughput": {
            "predicted": 1.5,
            "unit": "Gbps",
            "precision": 2,
            "prediction_time_ms": 0.5
        },
        "hardware_complexity": {
            "predicted_ge_cycles": 800.0,
            "prediction_time_ms": 0.75,
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
    recorded_metric_ms = (
        result["延迟"]["预测时间 (ms)"]
        + result["延迟"]["仿真时间 (ms)"]
        + result["面积"]["预测时间 (ms)"]
        + result["面积"]["综合时间 (ms)"]
        + result["Throughput"]["预测时间 (ms)"]
        + result["硬件复杂度"]["预测时间 (ms)"]
    )
    assert abs(result["自动评估总时间 (ms)"] - recorded_metric_ms) <= 3.0
    saved = json.loads(
        (root / "evaluation_output" / "config1" / "evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved == result


def test_batch_evaluation_reports_total_time_per_case(tmp_path, monkeypatch):
    _root, registry = _fixture(tmp_path, monkeypatch, [{}, {}])
    result = evaluate("fake", registry=registry)

    assert list(result) == ["config1", "config2"]
    assert result["config1"]["自动评估总时间 (ms)"] > 0
    assert result["config2"]["自动评估总时间 (ms)"] > 0


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


def test_ls_validation_json_bypasses_reference_and_rtl(monkeypatch, tmp_path):
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
            pytest.fail("RTL must not run")

    monkeypatch.setattr(ls_adapter, "_module", lambda: Module)
    result = ls_adapter.validate(tmp_path / "config.json", config)
    assert result["area"]["actual_um2"] == 112.0
    assert result["latency"]["actual_cycles"] == 10
    assert result["throughput"]["actual"] == 12500.0
    assert result["hardware_complexity"]["actual_ge_cycles"] == pytest.approx(1000.0)


def test_mimo_validation_json_bypasses_reference_and_rtl(monkeypatch, tmp_path):
    config = _validation_config()

    class Evaluator:
        @staticmethod
        def load_config(_path):
            return config

        @staticmethod
        def simulate_rtl(_path):
            pytest.fail("RTL must not run")

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


def test_bp_validation_json_bypasses_reference_and_rtl(monkeypatch, tmp_path):
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
        def simulate_rtl(*_args, **_kwargs):
            pytest.fail("RTL must not run")

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
