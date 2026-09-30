from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from enum import IntEnum
from typing import Literal
import sys
from os.path import dirname
sys.path.append(dirname(__file__))
import math


class CEState(IntEnum):
    """
    Channel Estimation FSM States — 4-state streaming design.

    S_IDLE:       IDLE state after reset. Await external signal 'start' to switch to either running state.
    S_COEFF_LOAD: Coefficient SRAM loading phase (only when HAS_COEFF_SRAM).
                  External bus writes W matrix coefficients.  counter_enable=0.
                  ``coeff_load_done`` input → S_RUN.
    S_RUN:        Main streaming state.  Counters always running.
                  LS pipeline gated combinationally by ``is_pilot_symbol``.
                  LS drain runs as a background counter after the last DMRS
                  symbol's ``sym_switch``.  When drain completes → S_TI.
    S_TI:         Time-interpolation sweep active.  Counters still running.
                  TI_CTRL performs the sweep (including its own internal drain).
                  When ``ti_done`` → S_RUN (or S_COEFF_LOAD if reload requested).
    """
    S_IDLE       = 0
    S_COEFF_LOAD = 1
    S_RUN        = 2
    S_TI         = 3


@convert
def ModuleCE_FSM(max_pusch_symbols: int, is_double_dmrs: bool | Literal["Hybrid"], LS_DRAIN_CYCLES: int, HAS_COEFF_SRAM: bool = False) -> None:
    """
    Channel Estimation Moore FSM — SLOT-level design principle.

    4-state design (fixed encoding, always 2-bit):
      S_IDLE → [COEFF_LOAD →] RUN ⇄ TI → [COEFF_LOAD →] RUN → …

    Key design points:
      1. **counter_enable is always 1** except S_COEFF_LOAD.
         rb_counter and symbol_counter run continuously during streaming.
      2. **S_COEFF_LOAD** (optional): If HAS_COEFF_SRAM is True, the FSM
         enters this state after reset.  External logic loads W matrix
         coefficients into SRAM.  ``coeff_load_done`` input transitions
         to S_RUN.  Online reload is supported via ``coeff_reload_req``
         sampled at the S_TI → exit transition.
      3. **LS drain is a background timer**, not a blocking state.
      4. **slot_boundary** input resets per-slot tracking.

    Moore outputs:
      - ``ctrl_ctr_en``    : 1 in S_RUN / S_TI
      - ``ctrl_ls_en``     : S_RUN && is_pilot_symbol
      - ``ctrl_ti_en``     : S_TI
      - ``ctrl_slot_done`` : 1-cycle pulse when ti_done fires in S_TI
      - ``coeff_loading``  : 1 during S_COEFF_LOAD (only if HAS_COEFF_SRAM)

    :param max_pusch_symbols: 14
    :param is_double_dmrs: False
    :param LS_DRAIN_CYCLES: 12
    :param HAS_COEFF_SRAM: True
        True to enable S_COEFF_LOAD state and online reload path.
    """

    state_width = 2

    S_IDLE       = int(CEState.S_IDLE)
    S_COEFF_LOAD = int(CEState.S_COEFF_LOAD)
    S_RUN        = int(CEState.S_RUN)
    S_TI         = int(CEState.S_TI)

    # Counter widths
    ls_drain_cnt_w = max(math.ceil(math.log2(LS_DRAIN_CYCLES + 1)), 1)

    #/ `timescale 1ns / 1ps
    #/ module CE_FSM (
    #/     input clk,
    #/     input rst_n,
    #/     
    #/     // Start signal
    #/     input start,
    #/     // From PILOT_SYMBOL_DETECTION
    #/     input is_pilot_symbol,
    #/     input l_quote,
    #/     input is_last_dmrs,
    #/     
    #/     // From RB_COUNTER
    #/     input sym_switch,
    #/     
    #/     // Slot boundary -- sym_switch when symbol counter wraps
    #/     input slot_boundary,
    #/     
    #/     // From TI_CTRL
    #/     input ti_done,

    if HAS_COEFF_SRAM:
        #/ // Coefficient SRAM loading
        #/ input coeff_load_done,
        #/ input coeff_reload_req,
        pass

    if is_double_dmrs == "Hybrid":
        #/ input is_double_dmrs,
        pass

    #/ // Moore outputs
    #/ output reg [`state_width`-1:0] state,
    #/ output                         ctrl_ctr_en,
    #/ output                         ctrl_ls_en,
    #/ output                         ctrl_ti_en,
    if HAS_COEFF_SRAM:
        #/ output ctrl_slot_done,
        #/ output coeff_loading
        pass
    else:
        #/ output ctrl_slot_done
        pass
    #/ );


    # ---- Internal registers ----
    #/ reg [`ls_drain_cnt_w`-1:0] ls_drain_cnt;
    #/ reg                        last_dmrs_seen;
    #/ reg                        ls_drain_active;

    #/ 
    #/ // ===== Derived signals =====
    #/ wire ls_drain_done = ls_drain_active & (ls_drain_cnt == `ls_drain_cnt_w`'d`LS_DRAIN_CYCLES - 1`);
    #/ 
    #/ // ===== Moore output assignments =====
    #/ assign ctrl_ctr_en     = (state == `state_width`'d`S_RUN`) | (state == `state_width`'d`S_TI`);
    #/ assign ctrl_ls_en      = (state == `state_width`'d`S_RUN`) & is_pilot_symbol;
    #/ assign ctrl_ti_en      = (state == `state_width`'d`S_TI`);
    #/ assign ctrl_slot_done  = (state == `state_width`'d`S_TI`) & ti_done;
    if HAS_COEFF_SRAM:
        #/ assign coeff_loading  = (state == `state_width`'d`S_COEFF_LOAD`);
        pass
    #/ 

    # ===== LS drain: background timer =====
    #/ // LS drain: starts after last DMRS sym_switch, counts LS_DRAIN_CYCLES.
    #/ // This is NOT a blocking FSM state — counters keep running.
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n) begin
    #/         ls_drain_active <= 1'b0;
    #/         ls_drain_cnt    <= `ls_drain_cnt_w`'d0;
    #/     end else begin
    #/         // Clean up: drain flag is no longer needed once S_TI is entered.
    #/         // A last-DMRS sym_switch may coincide with slot_boundary (for
    #/         // example, single DMRS with addPos=3 and a 12-symbol duration).
    #/         // Starting that drain must take priority over boundary cleanup,
    #/         // otherwise the completed slot can never enter S_TI.
    #/         if (state == `state_width`'d`S_TI`) begin
    #/             // Reset when the TI phase starts.
    #/             ls_drain_active <= 1'b0;
    #/             ls_drain_cnt    <= `ls_drain_cnt_w`'d0;
    #/         end else if (!ls_drain_active && last_dmrs_seen && sym_switch && state == `state_width`'d`S_RUN`) begin
    #/             // Start drain: last DMRS symbol just ended
    #/             ls_drain_active <= 1'b1;
    #/             ls_drain_cnt    <= `ls_drain_cnt_w`'d0;
    #/         end else if (slot_boundary) begin
    #/             // No completed-slot work is pending at this boundary.
    #/             ls_drain_active <= 1'b0;
    #/             ls_drain_cnt    <= `ls_drain_cnt_w`'d0;
    #/         end else if (ls_drain_active && !ls_drain_done) begin
    #/             ls_drain_active <= ls_drain_active;
    #/             ls_drain_cnt <= ls_drain_cnt + 1'b1;
    #/         end else begin
    #/             ls_drain_active <= ls_drain_active;
    #/             ls_drain_cnt    <= ls_drain_cnt;
    #/         end
    #/     end
    #/ end
    #/ 

    # ===== Per-slot last_dmrs tracking =====
    #/ // Track when the last DMRS occasion has been seen in the current slot.
    #/ // Reset at slot boundary for the new slot.
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n) begin
    #/         last_dmrs_seen <= 1'b0;
    #/     end
    #/     else if (slot_boundary) begin
    #/         last_dmrs_seen <= 1'b0;
    #/     end
    #/     else if (is_last_dmrs && is_pilot_symbol && state == `state_width`'d`S_RUN`) begin
    #/         last_dmrs_seen <= 1'b1;
    #/     end
    #/     else begin
    #/         last_dmrs_seen <= last_dmrs_seen;
    #/     end
    #/ end
    #/ 

    # ===== State register + transition logic =====
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n) begin
    #/         state <= `state_width`'d`S_IDLE`;
    #/     end else begin
    #/         case (state)
    #/             // IDLE
    #/             `state_width`'d`S_IDLE`: begin
    #/                 if (start) begin
    if HAS_COEFF_SRAM:
        #/ state <= `state_width`'d`S_COEFF_LOAD`;
        pass
    else:
        #/ state <= `state_width`'d`S_RUN`;
        pass
    #/ end else begin
    #/     state <= state;
    #/ end
    #/ end
    if HAS_COEFF_SRAM:
        #/ // COEFF_LOAD
        #/ `state_width`'d`S_COEFF_LOAD`: begin
        #/     if (coeff_load_done) begin
        #/         state <= `state_width`'d`S_RUN`;
        #/     end
        #/ end
        pass
    #/ // RUN
    #/ `state_width`'d`S_RUN`: begin
    #/     // LS drain timer runs in background.
    #/     // When drain completes → start TI sweep.
    #/     if (ls_drain_done) begin
    #/         state <= `state_width`'d`S_TI`;
    #/     end else begin
    #/         state <= state;
    #/     end
    #/ end
    #/ // TIME INTERP
    #/ `state_width`'d`S_TI`: begin
    #/     // TI_CTRL sweeps all RBs then drains internally.
    #/     // ti_done fires when TI pipeline is fully flushed.
    #/     if (ti_done) begin
    if HAS_COEFF_SRAM:
        #/ state <= coeff_reload_req ? `state_width`'d`S_COEFF_LOAD` : `state_width`'d`S_RUN`;
        pass
    else:
        #/ state <= `state_width`'d`S_RUN`;
        pass
    #/ end
    #/ end
    #/ 
    #/ default: begin
    #/     state <= `state_width`'d`S_IDLE`;
    #/ end
    #/ endcase
    #/ end
    #/ end
    #/ 
    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleCE_FSM(
        max_pusch_symbols=14,
        is_double_dmrs="Hybrid",
        LS_DRAIN_CYCLES=12,
        HAS_COEFF_SRAM=True,
    )
