###################################################################################################
# Module Name: TI_CTRL
# Description: Time-interpolation sweep controller (sub-FSM).
#   Post-FI mode (has_pre_fi_buf=False):
#     Sequences the read sweep during S_TIME_INTERP:
#       For each RB beat (SRAM address):
#         For each rb_within_beat (0 .. RB_PARALLELISM-1):
#           For each RE group (0 .. 12/P - 1):
#             Read selected SRAM bank, feed TI cores, stream output.
#     Produces ``ti_done`` handshake back to CE_FSM when sweep completes.
#
#   Pre-FI mode (has_pre_fi_buf=True):
#     During S_TI, drives BOTH FI and TI phases per window:
#       For each window (0 .. ceil(N_RB/FI_WINDOW_SIZE)-1):
#         FI phase: for each occasion (0 .. max_occasions-1):
#           Trigger FI core, wait FI_CYCLES_PER_OCC for output.
#         TI phase: sweep occasion registers (same counter as post-FI).
#       Final drain, then ti_done.
#
# Author: Auto-generated
# Date: 2025
# Version: V0.3.0
# Dependency Modules: None
###################################################################################################
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import List


@convert
def ModuleTI_CTRL(max_num_RBs: int, RB_PARALLELISM: int, TI_RE_PARALLELISM: int, TI_PIPELINE_DEPTH: int, has_pre_fi_buf: bool = False, max_occasions: int = 1, FI_WINDOW_SIZE: int = 1, FI_CYCLES_PER_OCC: int = 1, FI_CYCLES_PER_OCC_SINGLE: int = 1, FI_FILL_BEATS: int = 1, needs_rb_boundary: bool = True, runtime_n_additional: bool = False, runtime_double_dmrs: bool = False) -> None:
    """
    Time-interpolation sweep controller.

    A sub-FSM activated when ``enable_time_interp`` is asserted by CE_FSM.

    **Post-FI mode** (has_pre_fi_buf=False):
      3-state FSM: IDLE → SWEEP → DRAIN. Drives PILOT_SRAM_BANK reads.

    **Pre-FI mode** (has_pre_fi_buf=True):
      4-state FSM: IDLE → FI_PHASE → TI_SWEEP → DRAIN.
      FI_PHASE triggers the FI core per occasion per window.
      TI_SWEEP reads occasion registers per window.
      Loops windows until all RBs processed, then DRAIN → IDLE.

    :param max_num_RBs: 273
    :param RB_PARALLELISM: 1
    :param TI_RE_PARALLELISM: 3
    :param TI_PIPELINE_DEPTH: 2
    :param has_pre_fi_buf: False
    :param max_occasions: 1
    :param FI_WINDOW_SIZE: 1
        RBs per FI window (= LMMSE_P for LMMSE, 1 for NN/Linear).
    :param FI_CYCLES_PER_OCC: 1
        Cycles from FI trigger to last valid output per occasion.
        Includes the double-DMRS replay path when the build supports it.
    :param FI_CYCLES_PER_OCC_SINGLE: 1
        Corresponding latency for a single-symbol runtime in a Hybrid build.
    """
    if 12 % TI_RE_PARALLELISM != 0:
        raise ValueError(f"TI_RE_PARALLELISM={TI_RE_PARALLELISM} must divide 12")

    RE_GROUPS = 12 // TI_RE_PARALLELISM
    MAX_RB_BEATS = math.ceil(max_num_RBs / RB_PARALLELISM)
    RB_ADDR_WIDTH = max(math.ceil(math.log2(MAX_RB_BEATS)), 1) if MAX_RB_BEATS > 1 else 1
    RE_GROUP_WIDTH = max(math.ceil(math.log2(RE_GROUPS)), 1) if RE_GROUPS > 1 else 1
    RB_WITHIN_WIDTH = max(math.ceil(math.log2(RB_PARALLELISM)), 1) if RB_PARALLELISM > 1 else 1
    counter_width = max(math.ceil(math.log2(max_num_RBs)), 1)

    # Pre-FI constants
    if has_pre_fi_buf:
        if FI_CYCLES_PER_OCC_SINGLE > FI_CYCLES_PER_OCC:
            raise ValueError("single-DMRS FI latency cannot exceed double-DMRS latency")
        assert FI_WINDOW_SIZE >= RB_PARALLELISM, f"FI_WINDOW_SIZE={FI_WINDOW_SIZE} < RB_PARALLELISM={RB_PARALLELISM}"
        assert FI_WINDOW_SIZE % RB_PARALLELISM == 0, f"FI_WINDOW_SIZE={FI_WINDOW_SIZE} not divisible by RB_PARALLELISM={RB_PARALLELISM}"
        BEATS_PER_WINDOW = FI_WINDOW_SIZE // RB_PARALLELISM
        MAX_WINDOWS = math.ceil(max_num_RBs / FI_WINDOW_SIZE)
        WINDOW_CNT_WIDTH = max(math.ceil(math.log2(MAX_WINDOWS)), 1) if MAX_WINDOWS > 1 else 1
        OCC_SEL_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
        OCC_CNT_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
        FI_WAIT_WIDTH = max(math.ceil(math.log2(FI_CYCLES_PER_OCC)), 1)
        LOCAL_RB_WIDTH = max(math.ceil(math.log2(BEATS_PER_WINDOW)), 1) if BEATS_PER_WINDOW > 1 else 1
        STEPS_PER_WINDOW = BEATS_PER_WINDOW * RE_GROUPS
        if RB_PARALLELISM > 1:
            STEPS_PER_WINDOW = BEATS_PER_WINDOW * RB_PARALLELISM * RE_GROUPS
        FI_FILL_CNT_W = max(math.ceil(math.log2(FI_FILL_BEATS)), 1) if FI_FILL_BEATS > 1 else 1

    # Drain counter (shared)
    DRAIN_CYCLES = max(TI_PIPELINE_DEPTH + 1, 2)
    drain_cnt_w = max(math.ceil(math.log2(DRAIN_CYCLES + 1)), 1)

    # ---- Port declarations ----
    #/ `timescale 1ns / 1ps
    #/ module TI_CTRL (
    #/     input clk,
    #/     input rst_n,
    #/
    #/     // From CE_FSM
    #/     input                       ctrl_ti_en,
    #/     input [`counter_width`-1:0] num_RBs,
    #/
    #/     // To PILOT_SRAM_BANK or occasion registers
    #/     output                       ctrl_ti_sram_rd_en,
    #/     output [`RB_ADDR_WIDTH`-1:0] ctrl_ti_rb_addr,
    #/
    #/     // To TIME_INTERP data-path
    #/     output [`RE_GROUP_WIDTH`-1:0] ctrl_ti_re_group,
    if RB_PARALLELISM > 1:
        #/ output [`RB_WITHIN_WIDTH`-1:0] ti_rb_within_beat,
        pass

    if has_pre_fi_buf:
        #/     // Pre-FI: FI core trigger and occasion select
        #/     output fi_trigger,
        if runtime_double_dmrs:
            #/ input cfg_is_double_dmrs,
            pass
        if runtime_n_additional:
            _runtime_nadd_w = max(math.ceil(math.log2(max_occasions)), 1)
            #/ input [`_runtime_nadd_w`-1:0] cfg_n_additional_dmrs,
            pass
        if max_occasions > 1:
            #/ output [`OCC_SEL_WIDTH`-1:0] fi_occ_sel,
            pass
        #/ output [`RB_ADDR_WIDTH`-1:0] fi_window_base,
        # Window-boundary flags exist only for FI cores that consume them (NN,
        # Linear). LMMSE ignores them, so declaring them there leaves a driven
        # output that nothing reads all the way up through TOP.
        if needs_rb_boundary:
            #/ output fi_first_rb,
            #/ output fi_last_rb,
            if RB_PARALLELISM > 1:
                #/ output [`RB_PARALLELISM`-1:0] fi_lane_last,
                pass
            pass

    #/ output ctrl_ti_valid,
    #/// To CE_FSM
    #/ output ctrl_ti_done
    #/ );
    #/

    # ================================================================
    # POST-FI MODE (original behavior)
    # ================================================================
    if not has_pre_fi_buf:
        S_TI_IDLE  = 0
        S_TI_SWEEP = 1
        S_TI_DRAIN = 2
        STATE_W = 2

        #/ // ---- Internal registers ----
        #/ reg [`STATE_W`-1:0]        ti_state;
        #/ reg [`RB_ADDR_WIDTH`-1:0]  rb_beat_cnt;
        #/ reg [`RE_GROUP_WIDTH`-1:0] re_group_cnt;
        if RB_PARALLELISM > 1:
            #/ reg [`RB_WITHIN_WIDTH`-1:0] rb_within_cnt;
            pass
        #/ reg [`drain_cnt_w`-1:0] drain_cnt;
        #/

        if RB_PARALLELISM == 1:
            #/ wire [`RB_ADDR_WIDTH`-1:0] max_rb_beats = num_RBs;
            pass
        else:
            shift_bits = math.ceil(math.log2(RB_PARALLELISM))
            #/ wire [`RB_ADDR_WIDTH`-1:0] max_rb_beats = (num_RBs + `RB_PARALLELISM - 1`) >> `shift_bits`;
            pass

        #/
        #/ // ---- Valid pipeline: delay sram_rd_latency(1) + core_pipeline(`TI_PIPELINE_DEPTH`) ----
        VALID_DELAY = 1 + TI_PIPELINE_DEPTH
        #/ reg  [`VALID_DELAY`-1:0] valid_shift;
        #/ wire                     sweep_active = (ti_state == `STATE_W`'d`S_TI_SWEEP`);

        #/ wire valid_in = sweep_active;

        #/
        #/ always @(posedge clk or negedge rst_n) begin
        #/     if (!rst_n) begin
        #/         valid_shift <= `VALID_DELAY`'b0;
        #/     end else if (ti_state == `STATE_W`'d`S_TI_IDLE`) begin
        #/         valid_shift <= `VALID_DELAY`'b0;
        #/     end else begin
        #/         valid_shift <= {valid_shift[`VALID_DELAY - 2`:0], valid_in};
        #/     end
        #/ end
        #/
        #/ assign ctrl_ti_valid = valid_shift[`VALID_DELAY - 1`];
        #/

        #/ // ---- Sub-FSM ----
        #/ always @(posedge clk or negedge rst_n) begin
        #/     if (!rst_n) begin
        #/         ti_state     <= `STATE_W`'d`S_TI_IDLE`;
        #/         rb_beat_cnt  <= `RB_ADDR_WIDTH`'d0;
        #/         re_group_cnt <= `RE_GROUP_WIDTH`'d0;
        if RB_PARALLELISM > 1:
            #/ rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            pass
        #/ drain_cnt    <= `drain_cnt_w`'d0;
        #/ end else begin
        #/     case (ti_state)
        #/
        #/         `STATE_W`'d`S_TI_IDLE`: begin
        #/             rb_beat_cnt  <= `RB_ADDR_WIDTH`'d0;
        #/             re_group_cnt <= `RE_GROUP_WIDTH`'d0;
        if RB_PARALLELISM > 1:
            #/ rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            pass
        #/ drain_cnt    <= `drain_cnt_w`'d0;
        #/ if (ctrl_ti_en) begin
        #/     ti_state <= `STATE_W`'d`S_TI_SWEEP`;
        #/ end
        #/ end
        #/
        #/ `STATE_W`'d`S_TI_SWEEP`: begin

        _last_re_group = f"{RE_GROUP_WIDTH}'d{RE_GROUPS - 1}" if RE_GROUPS > 1 else f"{RE_GROUP_WIDTH}'d0"
        _last_rb_within = f"{RB_WITHIN_WIDTH}'d{RB_PARALLELISM - 1}" if RB_PARALLELISM > 1 else None

        if RB_PARALLELISM > 1 and RE_GROUPS > 1:
            #/ if (re_group_cnt == `_last_re_group`) begin
            #/     re_group_cnt <= `RE_GROUP_WIDTH`'d0;
            #/     if (rb_within_cnt == `_last_rb_within`) begin
            #/         if (rb_beat_cnt == max_rb_beats - 1'b1) begin
            #/             drain_cnt <= `drain_cnt_w`'d0;
            #/             ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/             rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            #/         end else begin
            #/             rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/             rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            #/         end
            #/     end else begin
            #/         rb_within_cnt <= rb_within_cnt + 1'b1;
            #/     end
            #/ end else begin
            #/     re_group_cnt <= re_group_cnt + 1'b1;
            #/ end
            pass
        elif RB_PARALLELISM > 1 and RE_GROUPS == 1:
            #/ if (rb_within_cnt == `_last_rb_within`) begin
            #/     rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            #/     if (rb_beat_cnt == max_rb_beats - 1'b1) begin
            #/         drain_cnt <= `drain_cnt_w`'d0;
            #/         ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/     end else begin
            #/         rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/     end
            #/ end else begin
            #/     rb_within_cnt <= rb_within_cnt + 1'b1;
            #/ end
            pass
        elif RB_PARALLELISM == 1 and RE_GROUPS > 1:
            #/ if (re_group_cnt == `_last_re_group`) begin
            #/     re_group_cnt <= `RE_GROUP_WIDTH`'d0;
            #/     if (rb_beat_cnt == max_rb_beats - 1'b1) begin
            #/         drain_cnt <= `drain_cnt_w`'d0;
            #/         ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/     end else begin
            #/         rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/     end
            #/ end else begin
            #/     re_group_cnt <= re_group_cnt + 1'b1;
            #/ end
            pass
        else:
            #/ if (rb_beat_cnt == max_rb_beats - 1'b1) begin
            #/     drain_cnt <= `drain_cnt_w`'d0;
            #/     ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/ end else begin
            #/     rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/ end
            pass

        #/ end
        #/
        #/ `STATE_W`'d`S_TI_DRAIN`: begin
        #/     drain_cnt <= drain_cnt + 1'b1;
        #/     if (drain_cnt == `drain_cnt_w`'d`DRAIN_CYCLES - 1`) begin
        #/         ti_state <= `STATE_W`'d`S_TI_IDLE`;
        #/     end
        #/ end
        #/
        #/ default: begin
        #/     ti_state <= `STATE_W`'d`S_TI_IDLE`;
        #/ end
        #/ endcase
        #/ end
        #/ end
        #/

        #/ assign ctrl_ti_rb_addr  = rb_beat_cnt;
        #/ assign ctrl_ti_re_group = re_group_cnt;
        if RB_PARALLELISM > 1:
            #/ assign ti_rb_within_beat = rb_within_cnt;
            pass

        #/ assign ctrl_ti_sram_rd_en = sweep_active;

        #/ assign ctrl_ti_done = (ti_state == `STATE_W`'d`S_TI_DRAIN`) & (drain_cnt == `drain_cnt_w`'d`DRAIN_CYCLES - 1`);
        #/

    # ================================================================
    # PRE-FI MODE: FI_PHASE → TI_SWEEP loop per window
    # ================================================================
    else:
        S_TI_IDLE     = 0
        S_TI_FI_PHASE = 1
        S_TI_SWEEP    = 2
        S_TI_DRAIN    = 3
        STATE_W = 2

        #/ // ---- Internal registers (pre-FI mode) ----
        #/ reg [`STATE_W`-1:0]         ti_state;
        #/ reg [`WINDOW_CNT_WIDTH`-1:0] window_cnt;
        #/ reg [`OCC_CNT_WIDTH`-1:0]   occ_cnt;
        #/ reg [`FI_WAIT_WIDTH`-1:0]   fi_wait_cnt;
        #/ reg [`LOCAL_RB_WIDTH`-1:0]   rb_beat_cnt;
        #/ reg [`RE_GROUP_WIDTH`-1:0]  re_group_cnt;
        if RB_PARALLELISM > 1:
            #/ reg [`RB_WITHIN_WIDTH`-1:0] rb_within_cnt;
            pass
        #/ reg [`drain_cnt_w`-1:0]     drain_cnt;
        #/ reg                         fi_trigger_r;
        if FI_FILL_BEATS > 1:
            #/ reg [`FI_FILL_CNT_W`-1:0]   fi_fill_cnt;
            pass
        #/

        # Runtime max_windows = ceil(num_RBs / _div)
        #
        # _div is how many RBs one window covers: FI_WINDOW_SIZE when the FI core
        # windows over several RBs, otherwise RB_PARALLELISM (one window per beat).
        _div = FI_WINDOW_SIZE if FI_WINDOW_SIZE > 1 else RB_PARALLELISM

        if _div == 1:
            # No divide -- just width-match num_RBs to the counter.
            if WINDOW_CNT_WIDTH == counter_width:
                #/ wire [`WINDOW_CNT_WIDTH`-1:0] max_windows = num_RBs;
                pass
            elif WINDOW_CNT_WIDTH > counter_width:
                _pad = WINDOW_CNT_WIDTH - counter_width
                #/ wire [`WINDOW_CNT_WIDTH`-1:0] max_windows = {`_pad`'d0, num_RBs};
                pass
            else:
                #/ wire [`WINDOW_CNT_WIDTH`-1:0] max_windows = num_RBs[`WINDOW_CNT_WIDTH`-1:0];
                pass
        else:
            # ceil(n / 2^s) == (n >> s) + |n[s-1:0]
            #
            # Written as quotient-plus-remainder-OR rather than (n + 2^s - 1) >> s
            # so that every bit of num_RBs is consumed: the low s bits feed the
            # OR-reduce, the rest form the quotient. The (n + K) >> s form leaves
            # the sum's low s bits and its carry bit unread, which lint reports as
            # dropped bits -- correct in the letter, since discarding them IS the
            # ceil, but it buries the signal in noise.
            _shift = math.ceil(math.log2(_div))
            _q_w = counter_width - _shift
            #/ wire max_windows_rem = |num_RBs[`_shift`-1:0];
            if WINDOW_CNT_WIDTH > 1:
                _rem_ext = f"{{{WINDOW_CNT_WIDTH - 1}'d0, max_windows_rem}}"
            else:
                _rem_ext = "max_windows_rem"
            if _q_w == WINDOW_CNT_WIDTH:
                #/ wire [`WINDOW_CNT_WIDTH`-1:0] max_windows = num_RBs[`counter_width`-1:`_shift`] + `_rem_ext`;
                pass
            elif _q_w < WINDOW_CNT_WIDTH:
                _qpad = WINDOW_CNT_WIDTH - _q_w
                #/ wire [`WINDOW_CNT_WIDTH`-1:0] max_windows = {`_qpad`'d0, num_RBs[`counter_width`-1:`_shift`]} + `_rem_ext`;
                pass
            else:
                # num_RBs has more headroom than the window counter needs. The
                # dropped high bits are zero for any num_RBs <= max_num_RBs, so
                # slice explicitly rather than let the adder truncate.
                #/ wire [`WINDOW_CNT_WIDTH`-1:0] max_windows = num_RBs[`_shift + WINDOW_CNT_WIDTH - 1`:`_shift`] + `_rem_ext`;
                pass

        # ---- Valid pipeline ----
        VALID_DELAY = 1 + TI_PIPELINE_DEPTH
        #/ reg [`VALID_DELAY`-1:0] valid_shift;
        #/ wire sweep_active = (ti_state == `STATE_W`'d`S_TI_SWEEP`);
        #/ wire valid_in = sweep_active;
        #/
        #/ always @(posedge clk or negedge rst_n) begin
        #/     if (!rst_n) begin
        #/         valid_shift <= `VALID_DELAY`'b0;
        #/     end else if (ti_state == `STATE_W`'d`S_TI_IDLE`) begin
        #/         valid_shift <= `VALID_DELAY`'b0;
        #/     end else begin
        #/         valid_shift <= {valid_shift[`VALID_DELAY - 2`:0], valid_in};
        #/     end
        #/ end
        #/ assign ctrl_ti_valid = valid_shift[`VALID_DELAY - 1`];
        #/

        # ---- Last-beat detection for TI sweep ----
        _last_re_group = f"{RE_GROUP_WIDTH}'d{RE_GROUPS - 1}" if RE_GROUPS > 1 else f"{RE_GROUP_WIDTH}'d0"
        _last_rb_beat = f"{LOCAL_RB_WIDTH}'d{BEATS_PER_WINDOW - 1}" if BEATS_PER_WINDOW > 1 else f"{LOCAL_RB_WIDTH}'d0"
        _last_occ = "cfg_n_additional_dmrs" if runtime_n_additional else (
            f"{OCC_CNT_WIDTH}'d{max_occasions - 1}"
            if max_occasions > 1 else f"{OCC_CNT_WIDTH}'d0"
        )
        _last_fi_wait = f"{FI_WAIT_WIDTH}'d{FI_CYCLES_PER_OCC - 1}"
        if runtime_double_dmrs:
            # Hybrid builds must not charge a single-symbol runtime for the
            # second replay pass that the window controller skips.
            #/ wire [`FI_WAIT_WIDTH`-1:0] fi_wait_limit = cfg_is_double_dmrs ? `FI_WAIT_WIDTH`'d`FI_CYCLES_PER_OCC - 1` : `FI_WAIT_WIDTH`'d`FI_CYCLES_PER_OCC_SINGLE - 1`;
            _last_fi_wait = "fi_wait_limit"
        if RB_PARALLELISM > 1:
            _last_rb_within = f"{RB_WITHIN_WIDTH}'d{RB_PARALLELISM - 1}"

        # ---- Sub-FSM ----
        #/ // ---- Pre-FI Sub-FSM ----
        #/ always @(posedge clk or negedge rst_n) begin
        #/     if (!rst_n) begin
        #/         ti_state     <= `STATE_W`'d`S_TI_IDLE`;
        #/         window_cnt   <= `WINDOW_CNT_WIDTH`'d0;
        #/         occ_cnt      <= `OCC_CNT_WIDTH`'d0;
        #/         fi_wait_cnt  <= `FI_WAIT_WIDTH`'d0;
        #/         rb_beat_cnt  <= `LOCAL_RB_WIDTH`'d0;
        #/         re_group_cnt <= `RE_GROUP_WIDTH`'d0;
        if RB_PARALLELISM > 1:
            #/     rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            pass
        #/         drain_cnt    <= `drain_cnt_w`'d0;
        #/         fi_trigger_r <= 1'b0;
        #/     end else begin
        #/         fi_trigger_r <= 1'b0;
        #/         case (ti_state)
        #/
        #/         `STATE_W`'d`S_TI_IDLE`: begin
        #/             window_cnt   <= `WINDOW_CNT_WIDTH`'d0;
        #/             occ_cnt      <= `OCC_CNT_WIDTH`'d0;
        #/             fi_wait_cnt  <= `FI_WAIT_WIDTH`'d0;
        #/             rb_beat_cnt  <= `LOCAL_RB_WIDTH`'d0;
        #/             re_group_cnt <= `RE_GROUP_WIDTH`'d0;
        if RB_PARALLELISM > 1:
            #/         rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            pass
        #/             drain_cnt    <= `drain_cnt_w`'d0;
        #/             if (ctrl_ti_en) begin
        #/                 ti_state     <= `STATE_W`'d`S_TI_FI_PHASE`;
        #/                 fi_trigger_r <= 1'b1;
        #/             end
        #/         end
        #/

        # ---- FI_PHASE: count FI_CYCLES_PER_OCC per occasion ----
        #/         `STATE_W`'d`S_TI_FI_PHASE`: begin
        #/             if (fi_wait_cnt == `_last_fi_wait`) begin
        #/                 fi_wait_cnt <= `FI_WAIT_WIDTH`'d0;
        if max_occasions > 1:
            #/             if (occ_cnt == `_last_occ`) begin
            #/                 occ_cnt  <= `OCC_CNT_WIDTH`'d0;
            #/                 ti_state <= `STATE_W`'d`S_TI_SWEEP`;
            #/             end else begin
            #/                 occ_cnt      <= occ_cnt + 1'b1;
            #/                 fi_trigger_r <= 1'b1;
            #/             end
            pass
        else:
            #/                 ti_state <= `STATE_W`'d`S_TI_SWEEP`;
            pass
        #/             end else begin
        #/                 fi_wait_cnt <= fi_wait_cnt + 1'b1;
        #/             end
        #/         end
        #/

        # ---- TI_SWEEP: nested counter (same structure as post-FI) ----
        #/         `STATE_W`'d`S_TI_SWEEP`: begin

        # Determine what happens when sweep finishes one window
        # If last window → DRAIN. Otherwise → FI_PHASE for next window.

        if RB_PARALLELISM == 1 and RE_GROUPS > 1:
            #/             if (re_group_cnt == `_last_re_group`) begin
            #/                 re_group_cnt <= `RE_GROUP_WIDTH`'d0;
            #/                 if (rb_beat_cnt == `_last_rb_beat`) begin
            #/                     rb_beat_cnt <= `LOCAL_RB_WIDTH`'d0;
            #/                     if (window_cnt == max_windows - 1'b1) begin
            #/                         drain_cnt <= `drain_cnt_w`'d0;
            #/                         ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/                     end else begin
            #/                         window_cnt   <= window_cnt + 1'b1;
            #/                         occ_cnt      <= `OCC_CNT_WIDTH`'d0;
            #/                         fi_wait_cnt  <= `FI_WAIT_WIDTH`'d0;
            #/                         ti_state     <= `STATE_W`'d`S_TI_FI_PHASE`;
            #/                         fi_trigger_r <= 1'b1;
            #/                     end
            #/                 end else begin
            #/                     rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/                 end
            #/             end else begin
            #/                 re_group_cnt <= re_group_cnt + 1'b1;
            #/             end
            pass
        elif RB_PARALLELISM > 1 and RE_GROUPS > 1:
            #/             if (re_group_cnt == `_last_re_group`) begin
            #/                 re_group_cnt <= `RE_GROUP_WIDTH`'d0;
            #/                 if (rb_within_cnt == `_last_rb_within`) begin
            #/                     rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            #/                     if (rb_beat_cnt == `_last_rb_beat`) begin
            #/                         rb_beat_cnt <= `LOCAL_RB_WIDTH`'d0;
            #/                         if (window_cnt == max_windows - 1'b1) begin
            #/                             drain_cnt <= `drain_cnt_w`'d0;
            #/                             ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/                         end else begin
            #/                             window_cnt   <= window_cnt + 1'b1;
            #/                             occ_cnt      <= `OCC_CNT_WIDTH`'d0;
            #/                             fi_wait_cnt  <= `FI_WAIT_WIDTH`'d0;
            #/                             ti_state     <= `STATE_W`'d`S_TI_FI_PHASE`;
            #/                             fi_trigger_r <= 1'b1;
            #/                         end
            #/                     end else begin
            #/                         rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/                     end
            #/                 end else begin
            #/                     rb_within_cnt <= rb_within_cnt + 1'b1;
            #/                 end
            #/             end else begin
            #/                 re_group_cnt <= re_group_cnt + 1'b1;
            #/             end
            pass
        elif RB_PARALLELISM > 1 and RE_GROUPS == 1:
            #/             if (rb_within_cnt == `_last_rb_within`) begin
            #/                 rb_within_cnt <= `RB_WITHIN_WIDTH`'d0;
            #/                 if (rb_beat_cnt == `_last_rb_beat`) begin
            #/                     rb_beat_cnt <= `LOCAL_RB_WIDTH`'d0;
            #/                     if (window_cnt == max_windows - 1'b1) begin
            #/                         drain_cnt <= `drain_cnt_w`'d0;
            #/                         ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/                     end else begin
            #/                         window_cnt   <= window_cnt + 1'b1;
            #/                         occ_cnt      <= `OCC_CNT_WIDTH`'d0;
            #/                         fi_wait_cnt  <= `FI_WAIT_WIDTH`'d0;
            #/                         ti_state     <= `STATE_W`'d`S_TI_FI_PHASE`;
            #/                         fi_trigger_r <= 1'b1;
            #/                     end
            #/                 end else begin
            #/                     rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/                 end
            #/             end else begin
            #/                 rb_within_cnt <= rb_within_cnt + 1'b1;
            #/             end
            pass
        else:
            # RB_PARALLELISM==1, RE_GROUPS==1
            #/             if (rb_beat_cnt == `_last_rb_beat`) begin
            #/                 rb_beat_cnt <= `LOCAL_RB_WIDTH`'d0;
            #/                 if (window_cnt == max_windows - 1'b1) begin
            #/                     drain_cnt <= `drain_cnt_w`'d0;
            #/                     ti_state  <= `STATE_W`'d`S_TI_DRAIN`;
            #/                 end else begin
            #/                     window_cnt   <= window_cnt + 1'b1;
            #/                     occ_cnt      <= `OCC_CNT_WIDTH`'d0;
            #/                     fi_wait_cnt  <= `FI_WAIT_WIDTH`'d0;
            #/                     ti_state     <= `STATE_W`'d`S_TI_FI_PHASE`;
            #/                     fi_trigger_r <= 1'b1;
            #/                 end
            #/             end else begin
            #/                 rb_beat_cnt <= rb_beat_cnt + 1'b1;
            #/             end
            pass

        #/         end
        #/

        # ---- DRAIN ----
        #/         `STATE_W`'d`S_TI_DRAIN`: begin
        #/             drain_cnt <= drain_cnt + 1'b1;
        #/             if (drain_cnt == `drain_cnt_w`'d`DRAIN_CYCLES - 1`) begin
        #/                 ti_state <= `STATE_W`'d`S_TI_IDLE`;
        #/             end
        #/         end
        #/
        #/         default: begin
        #/             ti_state <= `STATE_W`'d`S_TI_IDLE`;
        #/         end
        #/         endcase
        #/     end
        #/ end
        #/

        # ---- Output assignments (pre-FI) ----
        # In pre-FI mode the TI buffer holds one FI window, so the address is the
        # intra-window beat counter (LOCAL_RB_WIDTH bits). The port is sized for
        # the non-pre-FI case (RB_ADDR_WIDTH bits), so zero-extend explicitly
        # instead of relying on implicit widening.
        if LOCAL_RB_WIDTH == RB_ADDR_WIDTH:
            #/ assign ctrl_ti_rb_addr  = rb_beat_cnt;
            pass
        elif LOCAL_RB_WIDTH < RB_ADDR_WIDTH:
            _addr_pad = RB_ADDR_WIDTH - LOCAL_RB_WIDTH
            #/ assign ctrl_ti_rb_addr  = {`_addr_pad`'d0, rb_beat_cnt};
            pass
        else:
            #/ assign ctrl_ti_rb_addr  = rb_beat_cnt[`RB_ADDR_WIDTH`-1:0];
            pass
        #/ assign ctrl_ti_re_group = re_group_cnt;
        if RB_PARALLELISM > 1:
            #/ assign ti_rb_within_beat = rb_within_cnt;
            pass
        #/ assign ctrl_ti_sram_rd_en = sweep_active;
        if FI_FILL_BEATS > 1:
            #/ // Hold fi_trigger high for FI_FILL_BEATS cycles so the LMMSE core's
            #/ // internal fill_cnt can accumulate all pilot beats (non-pre-FI mode gets
            #/ // this for free because ctrl_freq_interp_en stays high; here fi_trigger_r
            #/ // is a single-cycle pulse).
            #/ assign fi_trigger = fi_trigger_r | (fi_fill_cnt != `FI_FILL_CNT_W`'d0);
            #/ always @(posedge clk or negedge rst_n) begin
            #/     if (!rst_n) begin
            #/         fi_fill_cnt <= `FI_FILL_CNT_W`'d0;
            #/     end else if (fi_trigger_r) begin
            #/         fi_fill_cnt <= `FI_FILL_CNT_W`'d`FI_FILL_BEATS - 1`;
            #/     end else if (fi_fill_cnt != `FI_FILL_CNT_W`'d0) begin
            #/         fi_fill_cnt <= fi_fill_cnt - 1'b1;
            #/     end
            #/ end
            pass
        else:
            #/ assign fi_trigger = fi_trigger_r;
            pass
        if max_occasions > 1:
            #/ assign fi_occ_sel = occ_cnt[`OCC_SEL_WIDTH`-1:0];
            pass
        #/ assign fi_window_base = window_cnt * `BEATS_PER_WINDOW`;
        if needs_rb_boundary:
            #/ assign fi_first_rb = (window_cnt == `WINDOW_CNT_WIDTH`'d0);
            #/ assign fi_last_rb  = (window_cnt == max_windows - 1'b1);
            if RB_PARALLELISM > 1:
                # Per-lane logical-last-RB flag.  FI_WINDOW_SIZE == RB_PARALLELISM for
                # the pre-FI NN/Linear path (one window == one RB beat), so the global
                # RB index of lane i is ``window_cnt * RB_PARALLELISM + i``; it is the
                # final RB iff that equals ``num_RBs - 1`` (correct on a partial last beat).
                for _lane in range(RB_PARALLELISM):
                    #/ wire fi_lane_last`_lane` = (window_cnt * `RB_PARALLELISM` + `_lane` == num_RBs - 1'b1);
                    pass
                #/ assign fi_lane_last = {`", ".join(f"fi_lane_last{RB_PARALLELISM-1-lane}" for lane in range(RB_PARALLELISM))`};
                pass
        #/ assign ctrl_ti_done = (ti_state == `STATE_W`'d`S_TI_DRAIN`) & (drain_cnt == `drain_cnt_w`'d`DRAIN_CYCLES - 1`);
        #/

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleTI_CTRL(
        max_num_RBs=273,
        RB_PARALLELISM=1,
        TI_RE_PARALLELISM=3,
        TI_PIPELINE_DEPTH=2,
    )

    ModuleTI_CTRL(
        max_num_RBs=273,
        RB_PARALLELISM=1,
        TI_RE_PARALLELISM=3,
        TI_PIPELINE_DEPTH=6,
    )

    ModuleTI_CTRL(
        max_num_RBs=273,
        RB_PARALLELISM=1,
        TI_RE_PARALLELISM=3,
        TI_PIPELINE_DEPTH=2,
        has_pre_fi_buf=True,
        max_occasions=3,
        FI_WINDOW_SIZE=4,
        FI_CYCLES_PER_OCC=21,
    )
