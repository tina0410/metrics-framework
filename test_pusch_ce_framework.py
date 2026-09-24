import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest

from metrics_framework.adapters import pusch_ce
from metrics_framework.adapters.pusch_ce import validate_scaffold_config
from metrics_framework.core import Registry, _evaluation_view, resolve_configs


ROOT = Path(__file__).resolve().parent


EXPECTED_SECTIONS = {
    "protocol",
    "architecture",
    "quantization",
    "arithmetic",
    "implementation",
    "area",
}


def test_pusch_ce_adapter_starts_from_module_working_directory() -> None:
    adapter = ROOT / "metrics_framework" / "adapters" / "pusch_ce.py"
    module_root = ROOT / "Generator" / "PUSCH_CE"
    process = subprocess.run(
        [sys.executable, str(adapter)],
        cwd=module_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert process.returncode == 1
    assert "usage: pusch_ce.py predict|validate CONFIG" in process.stdout
    assert "ModuleNotFoundError" not in process.stdout


def test_pusch_ce_rtl_generator_sources_are_versioned() -> None:
    module_root = ROOT / "Generator" / "PUSCH_CE"
    required = (
        "top_api.py",
        "v_top.py",
        "v_controller.py",
        "v_ls.py",
        "v_freq_interp.py",
        "v_time_interp.py",
        "basic_modules/PyTU.py",
        "helpers/config_space.py",
    )
    missing = [name for name in required if not (module_root / name).is_file()]
    assert not missing, f"missing PUSCH_CE RTL generator sources: {missing}"


def test_pusch_ce_requirements_include_area_model_runtime() -> None:
    requirements = (
        ROOT / "Generator" / "PUSCH_CE" / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert "scikit-learn==1.6.1" in requirements
    assert "joblib==1.4.2" in requirements


def test_complex_mul_uses_converter_safe_port_maps() -> None:
    source = (
        ROOT / "Generator" / "PUSCH_CE" / "basic_modules" / "ComplexMul.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_mul_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ModuleMul"
    ]
    assert len(module_mul_calls) == 7
    for call in module_mul_calls:
        ports = next(keyword.value for keyword in call.keywords if keyword.arg == "PORTS")
        assert isinstance(ports, ast.Name)

    submodule_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"ModuleMul", "ModuleAdd", "ModuleSub"}
    ]
    assert len(submodule_calls) == 14
    assert all(call.lineno == call.end_lineno for call in submodule_calls)


def test_pusch_ce_is_active_with_five_cases_and_ce_alias():
    spec = Registry().get("pusch_ce")
    assert spec.status == "active"
    assert Registry().get("ce") == spec
    assert spec.default_cases == (1, 2, 3, 4, 5)
    assert spec.config_pattern == "config{case}.json"
    assert spec.adapter is not None and spec.adapter.is_file()
    assert spec.capabilities == {
        "area",
        "latency",
        "throughput",
        "hardware_complexity",
    }

    configs = resolve_configs(spec, None)
    assert len(configs) == 5
    for path in configs:
        config = json.loads(path.read_text(encoding="utf-8"))
        validate_scaffold_config(config)
        assert set(config) == EXPECTED_SECTIONS
        assert config["area"] == {
            "use_config_actual_area": False,
            "actual_area_um2": None,
            "use_config_actual_time": False,
            "actual_time_ms": None,
        }


def test_pusch_ce_adapter_combines_all_prediction_metrics(monkeypatch):
    config_path = ROOT / "Generator" / "PUSCH_CE" / "cases" / "config1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    runtime_config = {**config, "latency": {"runtime": {}}}

    monkeypatch.setattr(pusch_ce, "_area", lambda action, path: {
        "predicted_area_um2": 112.0,
        "prediction_time_ms": 2.0,
    })
    monkeypatch.setattr(
        pusch_ce,
        "_modules",
        lambda: (
            "LVT_NAND2HDV0",
            lambda predicted_area, predicted_latency, **kwargs: {
                "predicted_ge_cycles": predicted_area / 1.12 * predicted_latency,
                "actual_ge_cycles": None,
                "ge_area_um2": 1.12,
            },
            lambda path: runtime_config,
            lambda value: {"predicted_cycles": 40, "prediction_time_ms": 1.0},
            lambda value, latency_prediction=None: {
                "predicted_gbps": 9.6,
                "prediction_time_ms": 0.5,
            },
        ),
    )
    result = pusch_ce.predict(config_path, config)
    assert result["latency"]["predicted_cycles"] == 40
    assert result["area"]["predicted_um2"] == 112.0
    assert result["throughput"]["predicted"] == 9.6
    assert result["hardware_complexity"]["predicted_ge_cycles"] == pytest.approx(4000.0)


def test_pusch_ce_adapter_uses_one_rtl_result_for_validation(monkeypatch):
    config_path = ROOT / "Generator" / "PUSCH_CE" / "cases" / "config1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        pusch_ce,
        "_area",
        lambda action, path: {"actual_area_um2": 123.2},
    )
    monkeypatch.setattr(
        pusch_ce,
        "_rtl",
        lambda path: {
            "latency": {"actual_cycles": 50, "simulation_time_ms": 200.0},
            "throughput": {"actual_gbps": 8.0, "actual_interval_cycles": 50},
            "rtl": {"throughput_interval_cycles": 50},
        },
    )
    monkeypatch.setattr(
        pusch_ce,
        "_modules",
        lambda: (
            "LVT_NAND2HDV0",
            lambda predicted_area, predicted_latency, **kwargs: {
                "predicted_ge_cycles": 5500.0,
                "actual_ge_cycles": 5500.0,
                "ge_area_um2": 1.12,
            },
            None,
            None,
            None,
        ),
    )
    result = pusch_ce.validate(config_path, config)
    assert result["latency"]["actual_cycles"] == 50
    assert result["area"]["synthesis_time_available"] is False
    assert result["throughput"] == {"actual": 8.0, "source": "rtl_measured"}
    assert result["hardware_complexity"]["actual_ge_cycles"] == 5500.0


def test_pusch_ce_evaluation_omits_unavailable_synthesis_time() -> None:
    prediction = {
        "module": "pusch_ce",
        "config_digest": "same",
        "metrics": {
            "latency": {"predicted_cycles": 40, "prediction_time_ms": 1.0},
            "area": {"predicted_um2": 112.0, "prediction_time_ms": 2.0},
            "throughput": {
                "predicted": 9.6,
                "unit": "Gbps",
                "precision": 9,
                "prediction_time_ms": 0.5,
            },
            "hardware_complexity": {
                "predicted_ge_cycles": 4000.0,
                "prediction_time_ms": 0.1,
                "ge_reference_cell": "LVT_NAND2HDV0",
                "ge_area_um2": 1.12,
            },
        },
    }
    validation = {
        "config_digest": "same",
        "metrics": {
            "latency": {"actual_cycles": 50, "simulation_time_ms": 200.0},
            "area": {
                "actual_um2": 123.2,
                "synthesis_time_ms": None,
                "reported_speedup": None,
                "synthesis_time_available": False,
            },
            "throughput": {"actual": 8.0},
            "hardware_complexity": {"actual_ge_cycles": 5500.0},
        },
    }
    result = _evaluation_view(prediction, validation)
    assert result["面积"]["真实结果 (μm²)"] == 123.2
    assert "综合时间 (ms)" not in result["面积"]
    assert "速度提升倍数 (×)" not in result["面积"]
