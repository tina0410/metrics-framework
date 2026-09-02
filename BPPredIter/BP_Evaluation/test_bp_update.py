from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

area_stub = types.ModuleType("area_tp_integration")
area_stub.evaluate_bp_area = lambda *args: None
pred_stub = types.ModuleType("PredIter")
pred_stub.predict_iter = lambda *args: None
sys.modules.setdefault("area_tp_integration", area_stub)
sys.modules.setdefault("PredIter", pred_stub)

import evaluate_bp
from polar_decoder_integration import simulate_bp_rtl


class PolarIntegrationTests(unittest.TestCase):
    def make_fake_project(
        self,
        root: Path,
        *,
        waveform_verified: bool = True,
        stimulus_source: str = "baseline_input_files",
    ) -> Path:
        project = root / "polar"
        project.mkdir()
        simulator = project / "bp_latency_simulation.py"
        simulator.write_text(
            """from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--config-path')
p.add_argument('--output-dir', type=Path)
p.add_argument('--result-json', type=Path)
p.add_argument('--label')
a = p.parse_args()
if a.output_dir.exists():
    shutil.rmtree(a.output_dir)
a.output_dir.mkdir(parents=True)
wave = a.output_dir / 'wave.vcd'
wave.write_text('vcd', encoding='utf-8')
latency = a.output_dir / 'latency_output.txt'
latency.write_text('77', encoding='utf-8')
log = a.output_dir / 'simulation.log'
log.write_text('ok', encoding='utf-8')
input_dir = a.output_dir / 'input_files'
comparison_dir = a.output_dir / 'comparison_files'
input_dir.mkdir()
comparison_dir.mkdir()
stimulus = {
    'channel': input_dir / 'y1.txt',
    'left_messages': input_dir / 'L.txt',
    'right_messages': input_dir / 'R.txt',
    'cpp_reference': comparison_dir / 'u_route_log.txt',
}
for path in stimulus.values():
    path.write_text('0\\n', encoding='utf-8')
result = {
    'waveform': str(wave.resolve()),
    'simulation_log': str(log.resolve()),
    'sim_latency_cycles': 77,
    'cpp_iterations': 2.25,
    'cpp_simulation_time_ms': 8.5,
    'rtl_simulation_time_ms': 12.5,
    'waveform_verified': WAVEFORM_VERIFIED,
    'decoding_verified': True,
    'stimulus_source': STIMULUS_SOURCE,
    'stimulus_files': {key: str(path.resolve()) for key, path in stimulus.items()},
}
a.result_json.parent.mkdir(parents=True, exist_ok=True)
a.result_json.write_text(json.dumps(result), encoding='utf-8')
""".replace("WAVEFORM_VERIFIED", repr(waveform_verified)).replace(
                "STIMULUS_SOURCE", repr(stimulus_source)
            ),
            encoding="utf-8",
        )
        return project

    def test_publishes_checked_artifacts_and_preserves_case_extras(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_fake_project(root)
            config = root / "rtl_config.json"
            config.write_text("{}", encoding="utf-8")
            case = root / "sim" / "config1"
            case.mkdir(parents=True)
            extra = case / "keep.txt"
            extra.write_text("keep", encoding="utf-8")

            result = simulate_bp_rtl(config, case, project, label="config1")

            self.assertEqual(result["sim_latency_cycles"], 77)
            self.assertTrue(extra.exists())
            for name in ("simulation_result.json", "latency_output.txt", "simulation.log", "wave.vcd"):
                self.assertTrue((case / name).is_file(), name)
            saved = json.loads((case / "simulation_result.json").read_text(encoding="utf-8"))
            self.assertEqual(Path(saved["artifact_dir"]), case.resolve())
            self.assertEqual(Path(saved["workspace"]), (case / "workspace").resolve())

    def test_rejects_unverified_waveform_without_publishing_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_fake_project(root, waveform_verified=False)
            config = root / "rtl_config.json"
            config.write_text("{}", encoding="utf-8")
            case = root / "sim" / "config1"

            with self.assertRaisesRegex(RuntimeError, "waveform was not verified"):
                simulate_bp_rtl(config, case, project)
            self.assertFalse((case / "simulation_result.json").exists())


    def test_rejects_unapproved_stimulus_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_fake_project(root, stimulus_source="copied_archive")
            config = root / "rtl_config.json"
            config.write_text("{}", encoding="utf-8")
            case = root / "sim" / "config1"

            with self.assertRaisesRegex(RuntimeError, "approved baseline"):
                simulate_bp_rtl(config, case, project)
            self.assertFalse((case / "simulation_result.json").exists())



class EvaluationDataFlowTests(unittest.TestCase):
    def test_final_metrics_use_rtl_latency_and_rtl_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "external.json"
            config.write_text(json.dumps({
                "decoder": {
                    "hardware_architecture": "TypeI",
                    "decoding_algorithm": "MS",
                    "code_length": 1024,
                    "parallelism": 256,
                    "data_width": 5,
                    "code_rate": 0.5,
                    "ebn0_db": 10.0,
                },
                "clock": {"period_ns": 2.5},
                "flow": {"run_simulation": True, "output_dir": "out"},
            }), encoding="utf-8")
            simulation = {
                "sim_latency_cycles": 77,
                "rtl_simulation_time_ms": 12.5,
                "cpp_iterations": 2.25,
                "cpp_simulation_time_ms": 999.0,
            }
            area = {
                "predicted_area_um2": 112.0,
                "actual_area_um2": 224.0,
                "error_percent": 50.0,
                "prediction_time_ms": 1.0,
                "synthesis_time_ms": 10.0,
                "speedup": 10.0,
            }
            with mock.patch.object(evaluate_bp, "predict_iter", return_value=2.0), \
                 mock.patch.object(evaluate_bp, "evaluate_bp_area", return_value=area), \
                 mock.patch.object(evaluate_bp, "read_ge_area", return_value=1.12), \
                 mock.patch.object(evaluate_bp, "simulate_rtl", return_value=simulation):
                result = evaluate_bp.run_bp_evaluation(config)

            latency = result["\u5ef6\u8fdf"]
            self.assertEqual(latency["\u4eff\u771f\u7ed3\u679c (cycles)"], 77)
            self.assertEqual(latency["\u4eff\u771f\u65f6\u95f4 (ms)"], 12.5)
            self.assertEqual(result["Throughput"]["\u4eff\u771f\u7ed3\u679c (Gbps)"], 2.66)
            self.assertEqual(result["\u786c\u4ef6\u590d\u6742\u5ea6"]["\u4eff\u771f\u7ed3\u679c (GE\u00b7cycles)"], 15400.0)
            rtl_config = json.loads(
                (root / "out" / "sim" / "rtl_config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(rtl_config["Clock Period (ns)"], 2.5)


    def test_config_actual_area_bypasses_workbook_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "custom_area.json"
            config.write_text(json.dumps({
                "decoder": {
                    "hardware_architecture": "TypeI",
                    "decoding_algorithm": "MS",
                    "code_length": 1024,
                    "parallelism": 128,
                    "data_width": 5,
                    "code_rate": 0.5,
                    "ebn0_db": 10.0,
                },
                "clock": {"period_ns": 20.0},
                "area": {
                    "use_config_actual_area": True,
                    "actual_area_um2": 300.0,
                    "synthesis_time_ms": 2500.0,
                },
                "flow": {
                    "run_simulation": False,
                    "output_dir": "out",
                },
            }), encoding="utf-8")
            area = {
                "predicted_area_um2": 240.0,
                "actual_area_um2": 300.0,
                "error_percent": 20.0,
                "prediction_time_ms": 1.0,
                "synthesis_time_ms": 2500.0,
                "speedup": 2500.0,
                "report": "config.area.actual_area_um2",
            }
            with mock.patch.object(evaluate_bp, "predict_iter", return_value=2.0), \
                 mock.patch.object(evaluate_bp, "evaluate_bp_area", return_value=area) as area_mock, \
                 mock.patch.object(evaluate_bp, "read_ge_area", return_value=1.12):
                result = evaluate_bp.run_bp_evaluation(config)

            self.assertEqual(result["面积"]["真实结果 (μm²)"], 300.0)
            self.assertEqual(result["面积"]["误差 (%)"], 20.0)
            self.assertEqual(result["面积"]["综合时间 (ms)"], 2500.0)
            self.assertEqual(result["面积"]["速度提升倍数 (×)"], 2500.0)
            self.assertNotIn("真实值来源", result["面积"])
            self.assertNotIn("仿真证据 (simulation_result.json)", result["延迟"])
            self.assertEqual(area_mock.call_args.kwargs["actual_area_um2"], 300.0)
            self.assertEqual(area_mock.call_args.kwargs["synthesis_time_ms"], 2500.0)

class ConfigSelectionTests(unittest.TestCase):
    def test_positive_numeric_shorthand_resolves_config6(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_dir = Path(temporary)
            config6 = config_dir / "config6.json"
            config6.write_text("{}", encoding="utf-8")
            with mock.patch.object(evaluate_bp, "CONFIG_DIR", config_dir):
                selected = evaluate_bp.resolve_config_selection("6")
            self.assertEqual(selected, [config6.resolve()])

class CleanupTests(unittest.TestCase):
    def test_cleanup_removes_only_selected_metric(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "config1.json"
            selected.write_text("{}", encoding="utf-8")
            selected_dir = root / "evaluation_output" / "config1"
            other_dir = root / "evaluation_output" / "config2"
            selected_dir.mkdir(parents=True)
            other_dir.mkdir(parents=True)
            selected_metric = selected_dir / "bp_metrics.json"
            other_metric = other_dir / "bp_metrics.json"
            selected_metric.write_text("selected", encoding="utf-8")
            other_metric.write_text("other", encoding="utf-8")
            with mock.patch.object(evaluate_bp, "configured_output_dir", return_value=selected_dir):
                evaluate_bp.cleanup_previous_run([selected])
            self.assertFalse(selected_metric.exists())
            self.assertTrue(other_metric.exists())


if __name__ == "__main__":
    unittest.main()

