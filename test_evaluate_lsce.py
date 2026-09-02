from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from evaluate_lsce import (
    _configured_area_root,
    _load_area_evaluator,
    PROJECT_ROOT,
    latency_cycles,
    load_config,
    resolve_config_selection,
    run_lsce_evaluation,
    select_actual_area,
    select_actual_time,
)


class LSCEEvaluationTests(unittest.TestCase):
    def test_default_collection_ignores_nested_checkout(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
            for relative in (".", "LSCE", "LSCE/Generator/LSCE"):
                target = project / relative
                target.mkdir(parents=True, exist_ok=True)
                for name in (
                    "test_evaluate_lsce.py",
                    "test_lsce_binding.py",
                    "test_metrics_framework.py",
                ):
                    (target / name).write_text(
                        "def test_contract(): pass\n", encoding="utf-8"
                    )
            collected = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q"],
                cwd=project,
                capture_output=True,
                text=True,
            )
            self.assertEqual(collected.returncode, 0, collected.stdout + collected.stderr)
            nodes = [
                line
                for line in collected.stdout.splitlines()
                if "::test_contract" in line
            ]
            self.assertEqual(
                nodes,
                [
                    "test_evaluate_lsce.py::test_contract",
                    "test_lsce_binding.py::test_contract",
                    "test_metrics_framework.py::test_contract",
                ],
            )

    def test_area_root_keeps_original_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                _configured_area_root(),
                PROJECT_ROOT / "Area_TP_Estimator" / "Est_LS_CE_M2V",
            )

    def test_area_root_accepts_external_model_directory(self) -> None:
        with TemporaryDirectory(prefix="lsce model ") as directory:
            with patch.dict(os.environ, {"LSCE_AREA_ROOT": directory}):
                self.assertEqual(_configured_area_root(), Path(directory).resolve())

    def test_empty_area_root_is_rejected(self) -> None:
        with patch.dict(os.environ, {"LSCE_AREA_ROOT": " "}):
            with self.assertRaisesRegex(ValueError, "LSCE_AREA_ROOT"):
                _configured_area_root()

    def test_incomplete_area_model_reports_path_and_missing_files(self) -> None:
        with TemporaryDirectory() as directory:
            model_root = Path(directory)
            (model_root / "EstLS.py").write_text(
                "raise AssertionError('Incomplete model must not be imported')\n",
                encoding="utf-8",
            )
            with patch("evaluate_lsce.AREA_ROOT", model_root):
                with self.assertRaises(FileNotFoundError) as caught:
                    _load_area_evaluator.__wrapped__()
            message = str(caught.exception)
            self.assertIn(str(model_root), message)
            self.assertIn("model/ADD_area.pkl", message)
            self.assertIn("EstModule.py", message)
            self.assertIn("LSCE_AREA_ROOT", message)

    def test_actual_area_falls_back_to_workbook(self) -> None:
        self.assertEqual(select_actual_area({}, 123.5), 123.5)

    def test_actual_area_uses_enabled_config_value(self) -> None:
        config = {
            "area": {
                "use_config_actual_area": True,
                "actual_area_um2": 456.75,
            }
        }
        self.assertEqual(select_actual_area(config, 123.5), 456.75)

    def test_enabled_config_area_requires_value(self) -> None:
        config = {
            "area": {
                "use_config_actual_area": True,
                "actual_area_um2": None,
            }
        }
        with self.assertRaises(ValueError):
            select_actual_area(config, 123.5)
    def test_actual_time_falls_back_to_workbook(self) -> None:
        self.assertEqual(select_actual_time({}, 103954.488), 103954.488)

    def test_actual_time_uses_enabled_config_value(self) -> None:
        config = {
            "area": {
                "use_config_actual_time": True,
                "actual_time_ms": 456.75,
            }
        }
        self.assertEqual(select_actual_time(config, 123.5), 456.75)

    def test_enabled_config_time_requires_value(self) -> None:
        config = {
            "area": {
                "use_config_actual_time": True,
                "actual_time_ms": None,
            }
        }
        with self.assertRaises(ValueError):
            select_actual_time(config, 123.5)
    def test_default_selection_includes_case1_through_case5(self) -> None:
        self.assertEqual(
            [path.stem for path in resolve_config_selection()],
            [f"config_case{i}" for i in range(1, 6)],
        )

    def test_latency_formula_for_standard_cases(self) -> None:
        expected = {1: 8, 2: 6, 3: 6, 4: 10, 5: 18}
        for case_id, cycles in expected.items():
            config = load_config(ROOT / "configs" / f"config_case{case_id}.json")
            self.assertEqual(latency_cycles(config), cycles)

    def test_invalid_parallelism_is_rejected(self) -> None:
        config_path = ROOT / "configs" / "config_case1.json"
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        config["Parallelism T"] = 3
        with TemporaryDirectory() as directory:
            temporary = Path(directory) / "config_case7.json"
            temporary.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must divide"):
                load_config(temporary)
    @patch("evaluate_lsce.simulate_lsce", return_value={"latency_cycles": 8, "output_interval_cycles": 4})
    @patch("evaluate_lsce.evaluate_lsce_area")
    def test_case1_uses_area_evaluator_and_bp_output_shape(self, area_mock, simulation_mock) -> None:
        area_mock.return_value = {
            "predicted_area_um2": 90258.32,
            "actual_area_um2": 91814.8,
            "error_percent": 1.695247,
            "prediction_time_ms": 0.1234567,
            "synthesis_time_ms": 103954.488,
            "speedup": 842030.269124,
        }
        with TemporaryDirectory() as directory, patch(
            "evaluate_lsce.configured_output_dir", return_value=Path(directory)
        ):
            result = run_lsce_evaluation(ROOT / "configs" / "config_case1.json")
            self.assertEqual(set(result), {"延迟", "面积", "Throughput", "硬件复杂度"})
            self.assertEqual(result["延迟"]["预测结果 (cycles)"], 8)
            self.assertEqual(result["面积"]["预测结果 (μm²)"], 90258.32)
            self.assertEqual(result["面积"]["真实结果 (μm²)"], 91814.8)
            self.assertEqual(result["面积"]["预测时间 (ms)"], 0.123457)
            self.assertEqual(result["面积"]["综合时间 (ms)"], 103954.488)
            self.assertEqual(result["面积"]["速度提升倍数 (×)"], 842030.27)
            area_mock.assert_called_once()
            output = Path(directory) / "lsce_metrics.json"
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)

if __name__ == "__main__":
    unittest.main()
