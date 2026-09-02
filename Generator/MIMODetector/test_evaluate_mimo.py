from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import evaluate_mimo as mimo_evaluator
import BehaviorialVerification.generate_mimo_testcase as mimo_generator
from BehaviorialVerification.generate_mimo_testcase import _reference_qam_order
from BehaviorialVerification.cpp_validation import validate_generated_cpp_inputs
from BehaviorialVerification.validate_mimo_timing import (
    measure_rtl_timing,
    parse_testbench_clock_period_ns,
)

from evaluate_mimo import (
    evaluate_area,
    load_config,
    predict_latency,
    predicted_output_interval_cycles,
    run_mimo_evaluation,
    throughput_gbps,
    valid_bits_per_output,
)


ROOT = Path(__file__).resolve().parent


def test_latency_formula_for_standard_cases() -> None:
    expected = {0: 64, 1: 40, 2: 28, 3: 34, 4: 28, 5: 39}
    for case_id, cycles in expected.items():
        config = load_config(ROOT / "configs" / f"config_case{case_id}.json")
        assert predict_latency(config) == cycles


def test_throughput_formula_for_16qam_at_10ns() -> None:
    config = load_config(ROOT / "configs" / "config_case5.json")
    assert valid_bits_per_output(config) == 16
    assert predicted_output_interval_cycles(config) == 4
    assert throughput_gbps(config, 4) == 0.4
    assert throughput_gbps(config, 4) == 0.4
    assert throughput_gbps(config, None) is None


def test_standard_configs_expose_ls_compatible_area_selection() -> None:
    for case_id in range(7):
        area = load_config(ROOT / "configs" / f"config_case{case_id}.json")["area"]
        assert area == {
            "use_config_actual_area": False,
            "actual_area_um2": None,
            "use_config_actual_time": False,
            "actual_time_ms": None,
        }


def test_area_selection_switches_must_be_boolean(tmp_path: Path) -> None:
    source = load_config(ROOT / "configs" / "config_case1.json")
    source["area"]["use_config_actual_area"] = "true"
    config_path = tmp_path / "bad_area_switch.json"
    config_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="use_config_actual_area must be boolean"):
        load_config(config_path)


def test_area_interface_matches_case1_reference() -> None:
    area = evaluate_area(ROOT / "configs" / "config_case1.json")
    assert area["predicted_area_um2"] == pytest.approx(197803.708761683)
    assert area["actual_area_um2"] == pytest.approx(202393.237954)
    assert area["reference_excel_rows"] == [3, 181]


@pytest.mark.parametrize(
    ("case_id", "predicted_area", "actual_area", "reference_rows"),
    [
        (1, 197803.7087616831, 202393.237954, [3, 181]),
        (2, 384110.52316521644, 392780.356185, [4]),
        (3, 197430.74876168315, 203216.437919, [5]),
        (4, 197182.90104890027, 201719.557992, [8]),
        (5, 276720.50152007974, 282972.477154, [24]),
    ],
)
def test_area_interface_matches_all_standard_cases(
    case_id: int,
    predicted_area: float,
    actual_area: float,
    reference_rows: list[int],
) -> None:
    area = evaluate_area(ROOT / "configs" / f"config_case{case_id}.json")
    assert area["predicted_area_um2"] == pytest.approx(predicted_area)
    assert area["actual_area_um2"] == pytest.approx(actual_area)
    assert area["reference_excel_rows"] == reference_rows


def test_area_and_predicted_complexity_without_rtl(tmp_path: Path) -> None:
    source = load_config(ROOT / "configs" / "config_case1.json")
    source["flow"]["run_simulation"] = False
    source["flow"]["output_dir"] = str(tmp_path / "output")
    config_path = tmp_path / "config_case1.json"
    config_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    result = run_mimo_evaluation(config_path, clean_previous=False)
    assert result["面积"]["预测结果 (μm²)"] == 197803.71
    assert result["面积"]["真实结果 (μm²)"] == 202393.24
    assert "真实结果类型" not in result["面积"]
    assert "参考表行" not in result["面积"]
    assert result["硬件复杂度"]["预测结果 (GE·cycles)"] == pytest.approx(
        197803.708761683 / 1.12 * 40, abs=0.01
    )
    assert result["硬件复杂度"]["真实结果 (GE·cycles)"] is None


def test_actual_metrics_use_rtl_latency_and_output_interval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = load_config(ROOT / "configs" / "config_case5.json")
    source["flow"]["run_simulation"] = True
    source["flow"]["output_dir"] = str(tmp_path / "output")
    config_path = tmp_path / "config_case5.json"
    config_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        mimo_evaluator,
        "evaluate_area",
        lambda _: {
            "predicted_area_um2": 112.0,
            "actual_area_um2": 224.0,
            "error_percent": 50.0,
            "prediction_time_ms": 1.0,
            "synthesis_time_ms": 10.0,
            "speedup": 10.0,
            "reference_excel_rows": [1],
        },
    )
    monkeypatch.setattr(
        mimo_evaluator,
        "simulate_rtl",
        lambda _: {
            "sim_latency_cycles": 40,
            "sim_output_interval_cycles": 5,
        },
    )

    result = run_mimo_evaluation(config_path, clean_previous=False)

    assert result["延迟"]["预测结果 (cycles)"] == 39
    assert result["延迟"]["仿真结果 (cycles)"] == 40
    assert result["延迟"]["误差 (%)"] == 2.56
    assert result["Throughput"]["预测结果 (Gbps)"] == 0.4
    assert result["Throughput"]["仿真结果 (Gbps)"] == 0.32
    assert result["硬件复杂度"]["预测结果 (GE·cycles)"] == 3900.0
    assert result["硬件复杂度"]["真实结果 (GE·cycles)"] == 8000.0
    assert result["硬件复杂度"]["误差 (%)"] == 51.25

def test_reference_qam_matches_standard_configs() -> None:
    assert _reference_qam_order() == 16
    for case_id in range(6):
        config = load_config(ROOT / "configs" / f"config_case{case_id}.json")
        assert config["QAM Order"] == 16
        assert config["flow"]["simulation_frames"] == 3


def test_generated_cpp_input_declaration_check() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
        cpp_path = Path(temporary) / "PE.cpp"
        cpp_path.write_text(
            "fxp::QU_H1 i_data_H1;\n"
            "i_data_H1.fill();\n",
            encoding="utf-8",
        )
        validate_generated_cpp_inputs(cpp_path)

        cpp_path.write_text(
            "fxp::QU_H1 i_data_H1;\n"
            "i_data_H2[0,0] = i_data_H1[0,0];\n",
            encoding="utf-8",
        )
        try:
            validate_generated_cpp_inputs(cpp_path)
        except ValueError as error:
            assert "i_data_H2" in str(error)
        else:
            raise AssertionError("undeclared generated C++ input was not rejected")


def test_case_cleanup_preserves_case_root_files() -> None:
    original_sim_root = mimo_generator.SIM_ROOT
    with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
        mimo_generator.SIM_ROOT = Path(temporary)
        try:
            case_root = mimo_generator.SIM_ROOT / "Testcase7"
            generated = case_root / "workspace" / "RTL"
            generated.mkdir(parents=True)
            (generated / "generated.v").write_text("generated", encoding="utf-8")
            marker = case_root / "user-analysis.keep"
            marker.write_text("preserve", encoding="utf-8")
            mimo_generator.clean_case(7)
            assert marker.read_text(encoding="utf-8") == "preserve"
            assert not generated.exists()
        finally:
            mimo_generator.SIM_ROOT = original_sim_root

def test_existing_case5_clock_and_multiframe_measurement() -> None:
    case_root = ROOT / "BehaviorialVerification" / "sim" / "Testcase5"
    rtl_dir = case_root / "workspace" / "RTL" / "Testcase5"
    testbench = next(rtl_dir.glob("TbPE*.v"))
    assert parse_testbench_clock_period_ns(testbench) == 10.0
    measured = measure_rtl_timing(
        rtl_dir / "wave.vcd",
        case_root / "workspace" / "Comparison_Files" / "PE_o_data.txt",
        tx=4,
        output_width=9,
    )
    assert measured["sim_latency_cycles"] == 39
    assert measured["matched_output_frames"] == 3
    assert measured["sim_output_interval_cycle_list"] == [4, 4]
    assert measured["sim_output_interval_cycles"] == 4

def test_case5_rtl_latency_evaluation() -> None:
    config_path = ROOT / "configs" / "config_case5.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("clock", {})["period_ns"] = 10.0
    config.setdefault("flow", {})["run_simulation"] = True
    temporary = ROOT / "config_case5_latency_test.json"
    temporary.write_text(json.dumps(config, indent=2), encoding="utf-8")
    try:
        result = run_mimo_evaluation(temporary)
    finally:
        temporary.unlink(missing_ok=True)
    assert result["延迟"]["预测结果 (cycles)"] == 39
    assert result["延迟"]["仿真结果 (cycles)"] == 39
    assert result["延迟"]["误差 (%)"] == 0.0
    assert result["面积"]["预测结果 (μm²)"] == 276720.5
    assert result["面积"]["真实结果 (μm²)"] == 282972.48
    assert result["硬件复杂度"]["真实结果 (GE·cycles)"] == pytest.approx(
        282972.477154 / 1.12 * 39, abs=0.01
    )
    assert result["硬件复杂度"]["误差 (%)"] == 2.21

