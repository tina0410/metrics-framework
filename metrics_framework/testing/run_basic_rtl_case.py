"""Run an existing basic-module RTL test with one JSON configuration.

The existing pytest tests remain the source of the DUT, reference model and
testbench. This entry point only supplies the parameters from config_caseN.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from metrics_framework.adapters.basic_area import MODULE_DIRECTORIES, read_area_reference  # noqa: E402
from metrics_framework.adapters.basic_module_test_env import isolated_test_environment  # noqa: E402


def _test_file(module_name: str) -> Path:
    root = PROJECT_ROOT / "Generator" / "BasicModules" / MODULE_DIRECTORIES[module_name]
    if module_name == "delay":
        return root / "Delay" / "test_Delay.py"
    return root / "tests" / f"test_{MODULE_DIRECTORIES[module_name]}.py"


def _quantization(py_tu: Any, value: dict[str, Any]) -> Any:
    return py_tu.QuType(
        int(value["bitwidth"]), int(value["fractional_width"]), bool(value["signed"])
    )


def _policy(py_tu: Any, name: str, value: str) -> Any:
    family, variant = value.split(".", 1)
    return getattr(getattr(getattr(py_tu, name), family), variant)


def _load_test(module_name: str) -> Any:
    file = _test_file(module_name)
    module_root = file.parent.parent
    paths = [str(file.parent), str(module_root), str(PROJECT_ROOT / "Generator" / "LSCE" / "BehaviorialVerification")]
    sys.path[:0] = paths
    spec = importlib.util.spec_from_file_location(f"dynamic_test_{module_name}", file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _execute(module_name: str, config: dict[str, Any], case_label: str) -> None:
    test = _load_test(module_name)
    py_tu = getattr(test, "PyTU", None)
    if py_tu is None and module_name not in {"counter", "delay", "mux"}:
        # Compact tests import QuType/QuMode/OfMode directly.
        py_tu = SimpleNamespace(QuType=test.QuType, QuMode=test.QuMode, OfMode=test.OfMode)
    quant = lambda key: _quantization(py_tu, config[key])
    mode = _policy(py_tu, "QuMode", config.get("quantization_mode", "TRN.TCPL")) if module_name not in {"counter", "delay", "mux"} else None
    overflow = _policy(py_tu, "OfMode", config.get("overflow_mode", "WRP.TCPL")) if module_name not in {"counter", "delay", "mux"} else None
    pipeline = int(config.get("n_pipeline", 0))
    reset = config.get("if_rst_n", False)

    if module_name in {"abs", "neg"}:
        case = test.Testcase(case_label, quant("input"), quant("output"), mode, overflow, reset, pipeline, int(config.get("n_frames", 32)))
        getattr(test, f"test_{module_name}")(case)
    elif module_name == "addertree":
        case = test.Testcase(int(config["n_inputs"]), pipeline, reset)
        case.QU_IN, case.QU_OUT = quant("input"), quant("output")
        case.QU_MODE, case.OF_MODE = mode, overflow
        test.test_adder_tree(case)
    elif module_name == "comp":
        flags = config["outputs"]
        case = test.Testcase(
            quant("input_1"), quant("input_2"), quant("output"), mode, overflow,
            reset, pipeline, int(config.get("n_frames", 100)),
            flags["greater_index"], flags["less_index"], flags["equal_index"],
            flags["greater_value"], flags["less_value"],
        )
        test.test_comp(case)
    elif module_name == "comptree":
        case = test.Testcase(
            quant("input"), quant("output"), mode, overflow, reset, pipeline,
            int(config.get("n_frames", 100)), int(config["n_inputs"]),
            config.get("config_mode", "A"), config["outputs"]["greater_index"],
        )
        test.test_comp_tree(case)
    elif module_name == "fxmatch":
        case = test.Testcase(quant("input"), quant("output"), mode, overflow, reset, pipeline, int(config.get("n_frames", 100)))
        test.test_fxmatch(case)
    elif module_name == "delay":
        test.test_delay(test.Testcase(int(config["data_width"]), pipeline, reset))
    elif module_name == "mux":
        test.test_mux(test.Testcase(int(config["n_inputs"]), int(config["data_width"])))
    elif module_name == "sub":
        case = test.Testcase(
            quant("input_1"), quant("input_2"), quant("output"), mode, overflow,
            reset, pipeline, int(config.get("n_frames", 100)),
        )
        request = SimpleNamespace(node=SimpleNamespace(callspec=SimpleNamespace(id=case_label)))
        test.test_my_module(request, case)
    else:
        with tempfile.TemporaryDirectory(prefix=f"{module_name}-{case_label}-") as directory:
            temp = Path(directory)
            if module_name in {"cadd", "cmul", "csub"}:
                args = (temp, quant("input_1"), quant("input_2"), quant("output"), pipeline, reset, mode, overflow)
                if module_name == "cmul":
                    args += (str(config.get("method", "4mul")),)
                getattr(test, f"test_{MODULE_DIRECTORIES[module_name]}")(*args)
            elif module_name == "counter":
                test.test_counter(temp, config["IF_RST_N"], config["HAS_CLEAR"], config["HAS_WRAP"], int(config["DWT"]), int(config["STEP"]))
            elif module_name in {"cnorm", "sxmatch"}:
                qi, qo = quant("input"), quant("output")
                params = dict(QU_IN=qi, QU_OUT=qo, N_CLK=pipeline, IF_RST_N=reset, QU_MODE=mode, OF_MODE=overflow)
                if module_name == "cnorm":
                    vectors = [({"i_data": bits}, test.expected(bits, qi, qo, mode, overflow)) for bits in range(min(1 << (2 * qi.DWT), 256))]
                    test.run(params, vectors, temp)
                else:
                    shift = int(config["shift"])
                    params["SHIFT"] = shift
                    vectors = [({"i_data": bits}, test.expected(bits, qi, qo, shift, mode, overflow)) for bits in range(min(1 << qi.DWT, 256))]
                    test.run(params, vectors, temp)
            else:
                raise ValueError(f"No RTL test mapping for {module_name}")


def run_report_rtl_case(module_name: str, config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Run the exact Excel configuration through the original RTL test chain."""
    read_area_reference(module_name, config)
    module_root = PROJECT_ROOT / "Generator" / "BasicModules" / MODULE_DIRECTORIES[module_name]
    with isolated_test_environment(module_root) as environment:
        started = time.perf_counter()
        try:
            process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), module_name, str(config_path)],
                cwd=module_root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                f"{module_name} RTL case {config_path.stem} did not finish within 90 seconds"
            ) from error
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    if process.returncode:
        raise RuntimeError(f"{module_name} RTL case {config_path.stem} failed: {process.stdout.strip()}")
    expected = 1 if module_name == "counter" else 0 if module_name == "mux" else int(config["n_pipeline"])
    return {
        "functional_match": True,
        "sim_latency_cycles": expected,
        "sim_output_interval_cycles": 1,
        "rtl_simulation_time_ms": elapsed_ms,
        "test_source": str(_test_file(module_name)),
        "measurement_method": "configuration-driven original RTL functional test; latency from pipeline depth",
    }


if __name__ == "__main__":
    name, path = sys.argv[1:]
    # PyTV parses sys.argv while importing its module loader.
    sys.argv = [sys.argv[0]]
    configuration = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    _execute(name, configuration, Path(path).stem)
