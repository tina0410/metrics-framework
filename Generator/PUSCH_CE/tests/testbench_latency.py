"""Cocotb probe for PUSCH CE latency and steady-state bit throughput."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


def _set_if_present(dut, name: str, value: int) -> None:
    signal = getattr(dut, name, None)
    if signal is not None:
        signal.value = value


@cocotb.test()
async def measure_pusch_ce_latency(dut):
    config = json.loads(os.environ["PUSCH_CE_LATENCY_CONFIG_JSON"])
    runtime = config["latency"]["runtime"]
    protocol = config["protocol"]
    architecture = config["architecture"]
    period_ns = float(config["latency"].get("clock_period_ns", 10.0))
    rb_parallelism = int(architecture["rb_parallelism"])
    num_rbs = int(runtime["num_RBs"])
    num_symbols = int(runtime["num_symbols"])

    cocotb.start_soon(Clock(dut.clk, period_ns, unit="ns").start())
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.N_ID.value = 0
    dut.n_scid.value = 0
    dut.current_slot_idx.value = 0
    dut.pusch_symbol_length.value = num_symbols
    dut.num_RBs.value = num_rbs
    _set_if_present(dut, "protocol_switch", 0)
    _set_if_present(dut, "num_cdm_groups_without_data", 0)
    _set_if_present(dut, "dmrs_type", 1 if int(runtime["dmrs_type"]) == 2 else 0)
    _set_if_present(
        dut, "n_additional_dmrs", int(runtime["n_additional_dmrs"])
    )
    _set_if_present(
        dut, "is_double_dmrs", 1 if runtime["is_double_dmrs"] else 0
    )
    _set_if_present(
        dut, "dmrs_typeA_pos_sel", 1 if runtime["dmrs_typeA_pos"] == "pos3" else 0
    )
    _set_if_present(dut, "is_ECP", 1 if protocol["is_ECP"] else 0)
    _set_if_present(dut, "is_enhanced", 1 if protocol["is_enhanced"] else 0)
    _set_if_present(dut, "coeff_load_done", 1)
    for port in protocol["antenna_ports"]:
        _set_if_present(dut, f"port_enable_p{port}", 1)

    input_mode = architecture["input_mode"]
    if input_mode == "A":
        dut.Y.value = 0
    else:
        for lane in range(rb_parallelism):
            _set_if_present(dut, f"Y_rb{lane}", 0)
            _set_if_present(dut, f"Y_valid_rb{lane}", 0)

    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 1
    await RisingEdge(dut.clk)  # latency cycle 0: start accepted
    dut.start.value = 0

    ti_re_parallelism = int(architecture["ti_re_parallelism"])
    re_groups = 12 // ti_re_parallelism
    component_width_match = re.fullmatch(
        r"\s*QuType\(\s*(\d+)\s*,.*", config["quantization"]["H_TI"]
    )
    assert component_width_match is not None
    bits_per_valid_pulse = (
        ti_re_parallelism
        * num_symbols
        * len(protocol["antenna_ports"])
        * 2
        * int(component_width_match.group(1))
    )
    expected_output_bits = (
        num_rbs * 12 * num_symbols * len(protocol["antenna_ports"])
        * 2 * int(component_width_match.group(1))
    )
    measured: dict[str, list[int]] = {"done_cycles": [], "output_bits": []}

    async def watch_metrics() -> None:
        timeout = 2 * (num_symbols * math.ceil(num_rbs / rb_parallelism) + 16384)
        pulse_count = 0
        slot_bits = 0
        for cycle in range(1, timeout + 1):
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            if int(dut.ti_data_valid.value):
                rb_beat = pulse_count // (rb_parallelism * re_groups)
                remainder = pulse_count % (rb_parallelism * re_groups)
                rb_within = remainder // re_groups
                rb_index = rb_beat * rb_parallelism + rb_within
                if rb_index < num_rbs:
                    slot_bits += bits_per_valid_pulse
                pulse_count += 1
            if int(dut.slot_ce_done.value):
                measured["done_cycles"].append(cycle)
                measured["output_bits"].append(slot_bits)
                pulse_count = 0
                slot_bits = 0
                if len(measured["done_cycles"]) == 2:
                    return
        raise AssertionError("two slot_ce_done pulses were not observed before the timeout")

    monitor = cocotb.start_soon(watch_metrics())
    beats = math.ceil(num_rbs / rb_parallelism)
    for _slot in range(2):
        for _symbol in range(num_symbols):
            for beat in range(beats):
                if input_mode == "A":
                    dut.Y.value = 0
                    await RisingEdge(dut.clk)
                    continue
                active_lanes = min(rb_parallelism, num_rbs - beat * rb_parallelism)
                for lane in range(rb_parallelism):
                    _set_if_present(dut, f"Y_valid_rb{lane}", int(lane < active_lanes))
                while True:
                    await RisingEdge(dut.clk)
                    await Timer(1, unit="ns")
                    if all(
                        int(getattr(dut, f"Y_ready_rb{lane}").value)
                        for lane in range(active_lanes)
                    ):
                        break

    if input_mode == "B":
        for lane in range(rb_parallelism):
            _set_if_present(dut, f"Y_valid_rb{lane}", 0)
    await monitor
    first_done, second_done = measured["done_cycles"]
    first_bits, second_bits = measured["output_bits"]
    assert first_bits == expected_output_bits
    assert second_bits == expected_output_bits
    interval_cycles = second_done - first_done
    result = {
        "actual_cycles": first_done,
        "actual_time_ns": first_done * period_ns,
        "clock_period_ns": period_ns,
        "measurement_start": "accepted_start",
        "measurement_end": "slot_ce_done_rising",
        "coefficient_load_included": False,
        "throughput_interval_cycles": interval_cycles,
        "throughput_output_bits": second_bits,
        "throughput_gbps": second_bits / (interval_cycles * period_ns),
        "throughput_measurement_boundary": "adjacent_slot_ce_done_rising_edges",
        "rtl_output_valid_derived": True,
    }
    Path(os.environ["PUSCH_CE_LATENCY_RESULT"]).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
