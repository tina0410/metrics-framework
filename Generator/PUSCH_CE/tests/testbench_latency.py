"""Cocotb probe which measures accepted-start through ``slot_ce_done``."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

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

    measured: dict[str, int | None] = {"cycles": None}

    async def watch_done() -> None:
        timeout = num_symbols * math.ceil(num_rbs / rb_parallelism) + 16384
        for cycle in range(1, timeout + 1):
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            if int(dut.slot_ce_done.value):
                measured["cycles"] = cycle
                return
        raise AssertionError("slot_ce_done was not observed before the timeout")

    monitor = cocotb.start_soon(watch_done())
    beats = math.ceil(num_rbs / rb_parallelism)
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
    cycles = measured["cycles"]
    assert cycles is not None
    result = {
        "actual_cycles": cycles,
        "actual_time_ns": cycles * period_ns,
        "clock_period_ns": period_ns,
        "measurement_start": "accepted_start",
        "measurement_end": "slot_ce_done_rising",
        "coefficient_load_included": False,
    }
    Path(os.environ["PUSCH_CE_LATENCY_RESULT"]).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
