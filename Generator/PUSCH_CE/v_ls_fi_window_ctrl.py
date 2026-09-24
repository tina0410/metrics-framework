import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Optional, Dict, Any


@convert
def ModuleLS_FI_WINDOW_CTRL(max_num_RBs: int, RB_PARALLELISM: int, LMMSE_P: int, FI_RE_PARALLELISM: int, max_occasions: int, symbols_per_occasion: int, LS_DRAIN_CYCLES: int, N_CDM_GROUPS: int = 1, is_double_dmrs: Any = None, runtime_n_additional: bool = False) -> None:
    """
    LS-FI Window Controller for rate-matched architecture.

    Orchestrates the producer (LS replay from Y_BUF) and consumer (LMMSE MAC)
    via a dual pilot-bank handshake protocol.

    :param max_num_RBs: Maximum RB allocation
    :param RB_PARALLELISM: RBs processed per clock in LS path
    :param LMMSE_P: LMMSE window size in RBs
    :param FI_RE_PARALLELISM: RE parallelism of LMMSE MAC
    :param max_occasions: 1 + max(additional_DMRS_range)
    :param symbols_per_occasion: 1 (single) or 2 (double DMRS)
    :param LS_DRAIN_CYCLES: LS pipeline drain latency
    :param N_CDM_GROUPS: Number of CDM groups (LFSR context instances)
    """
    if symbols_per_occasion not in (1, 2):
        raise ValueError("symbols_per_occasion must be 1 or 2")
    if is_double_dmrs not in (None, False, True, "Hybrid"):
        raise ValueError("is_double_dmrs must be False, True, 'Hybrid', or None")
    HAS_RUNTIME_DOUBLE = is_double_dmrs == "Hybrid"
    if LS_DRAIN_CYCLES < 2:
        raise ValueError("LS_DRAIN_CYCLES must be >= 2 for pilot write alignment")

    BEATS_PER_WINDOW = LMMSE_P // RB_PARALLELISM
    MAX_WINDOWS = math.ceil(max_num_RBs / LMMSE_P)
    WINDOW_CNT_W = max(math.ceil(math.log2(MAX_WINDOWS)), 1) if MAX_WINDOWS > 1 else 1
    OCC_CNT_W = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
    BEAT_CNT_W = max(math.ceil(math.log2(BEATS_PER_WINDOW)), 1) if BEATS_PER_WINDOW > 1 else 1
    DRAIN_CNT_W = max(math.ceil(math.log2(LS_DRAIN_CYCLES + 1)), 1)
    OUTPUT_GROUPS = 12 // FI_RE_PARALLELISM
    MAC_CYCLES = OUTPUT_GROUPS * BEATS_PER_WINDOW
    MAC_CNT_W = max(math.ceil(math.log2(MAC_CYCLES)), 1) if MAC_CYCLES > 1 else 1
    SRAM_DEPTH = math.ceil(max_num_RBs / RB_PARALLELISM)
    YBUF_ADDR_W = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1
    TOTAL_PLANES = max_occasions * symbols_per_occasion
    PLANE_SEL_W = max(math.ceil(math.log2(TOTAL_PLANES)), 1) if TOTAL_PLANES > 1 else 1
    REPLAY_TOKEN_DWT = PLANE_SEL_W + BEAT_CNT_W
    counter_width = max(math.ceil(math.log2(max_num_RBs)), 1)

    P_IDLE = 0; P_LOAD_CTX = 1; P_ISSUE = 2; P_DRAIN = 3
    P_SAVE_CTX = 4; P_PUBLISH = 5; P_STATE_W = 3
    C_IDLE = 0; C_WAIT_FULL = 1; C_MAC = 2; C_RELEASE = 3; C_STATE_W = 2

    _last_beat = f"{BEAT_CNT_W}'d{BEATS_PER_WINDOW - 1}" if BEATS_PER_WINDOW > 1 else f"{BEAT_CNT_W}'d0"
    _last_drain = f"{DRAIN_CNT_W}'d{LS_DRAIN_CYCLES - 1}"
    _last_occ = "cfg_n_additional_dmrs" if runtime_n_additional else (
        f"{OCC_CNT_W}'d{max_occasions - 1}" if max_occasions > 1 else None
    )
    _last_mac = f"{MAC_CNT_W}'d{MAC_CYCLES - 1}" if MAC_CYCLES > 1 else f"{MAC_CNT_W}'d0"
    _p_issue = f"{P_STATE_W}'d{P_ISSUE}"

    # =========================================================================
    # Port declarations
    # =========================================================================
    #/ `timescale 1ns / 1ps
    #/ module LS_FI_WINDOW_CTRL (
    #/     input                       clk,
    #/     input                       rst_n,
    #/     input                       ctrl_start,
    #/     input [`counter_width`-1:0] num_RBs,
    if runtime_n_additional:
        _runtime_nadd_w = max(math.ceil(math.log2(max_occasions)), 1)
        #/ input [`_runtime_nadd_w`-1:0] cfg_n_additional_dmrs,
        pass
    if HAS_RUNTIME_DOUBLE:
        #/ input cfg_is_double_dmrs,
        pass
    #/ output ybuf_rd_en,
    if TOTAL_PLANES > 1:
        #/ output [`PLANE_SEL_W`-1:0] ybuf_rd_plane_sel,
        pass
    #/ output [`YBUF_ADDR_W`-1:0] ybuf_rd_addr,
    #/ output                     ls_enable,
    if symbols_per_occasion > 1:
        #/ output replay_data_valid,
        pass
    #/ output                          replay_token_valid_in,
    #/ output [`REPLAY_TOKEN_DWT`-1:0] replay_token_in,
    #/ input                           replay_token_valid_out,
    #/ input  [`REPLAY_TOKEN_DWT`-1:0] replay_token_out,
    #/ output                          ls_sym_switch,
    #/ output                          lfsr_ctx_save_en,
    #/ output                          lfsr_ctx_restore_en,
    if symbols_per_occasion > 1:
        #/ output lfsr_ctx_sel,
        pass
    #/ output                    avg_sym_switch,
    #/ output                    pilot_bank_wr_done,
    #/ output                    pilot_bank_sel,
    #/ output                    replay_c_init_strb,
    #/ output                    fi_enable,
    #/ output                    pilot_wr_en,
    #/ output [`BEAT_CNT_W`-1:0] pilot_wr_addr,
    if TOTAL_PLANES > 1:
        #/ output [`PLANE_SEL_W`-1:0] pilot_wr_plane,
        pass
    #/ input fi_mac_done,
    if max_occasions > 1:
        #/ output [`OCC_CNT_W`-1:0] cur_occasion,
        pass
    #/ output [`WINDOW_CNT_W`-1:0] cur_window,
    #/ output                      all_done,
    #/ output                      ctrl_done
    #/ );
    #/

    # =========================================================================
    # Internal registers
    # =========================================================================

    # Runtime max_windows
    _shift = math.ceil(math.log2(LMMSE_P))
    _q_w = counter_width - _shift
    #/ wire max_windows_rem = |num_RBs[`_shift`-1:0];
    if WINDOW_CNT_W > 1:
        _rem_ext = f"{{{WINDOW_CNT_W - 1}'d0, max_windows_rem}}"
    else:
        _rem_ext = "max_windows_rem"
    if _q_w >= WINDOW_CNT_W:
        #/ wire [`WINDOW_CNT_W`-1:0] max_windows = num_RBs[`_shift + WINDOW_CNT_W - 1`:`_shift`] + `_rem_ext`;
        pass
    else:
        _qpad = WINDOW_CNT_W - _q_w
        #/ wire [`WINDOW_CNT_W`-1:0] max_windows = {`_qpad`'d0, num_RBs[`counter_width`-1:`_shift`]} + `_rem_ext`;
        pass

    #/ reg [`P_STATE_W`-1:0]    p_state;
    #/ reg [`WINDOW_CNT_W`-1:0] p_window_cnt;
    if max_occasions > 1:
        #/ reg [`OCC_CNT_W`-1:0] p_occ_cnt;
        pass
    if symbols_per_occasion > 1:
        #/ reg p_sym_cnt;
        pass
    #/ reg [`BEAT_CNT_W`-1:0]  p_beat_cnt;
    #/ reg [`DRAIN_CNT_W`-1:0] p_drain_cnt;
    #/ reg                     p_bank_sel;
    #/ reg [`C_STATE_W`-1:0]   c_state;
    #/ reg [`MAC_CNT_W`-1:0]   c_mac_cnt;
    #/ reg                     c_bank_sel;
    #/ reg [1:0]               bank_full;
    #/ reg                     done_r;
    #/ reg                     ctrl_start_seen;
    #/
    #/ wire p_bank_free = ~bank_full[p_bank_sel];
    #/ wire c_bank_ready = bank_full[c_bank_sel];
    if HAS_RUNTIME_DOUBLE:
        # Freeze the runtime mode with the replay descriptor.  A slot-level
        # configuration change must not alter an in-flight window.
        #/ reg  replay_double_dmrs_r;
        #/ wire replay_double_dmrs = replay_double_dmrs_r;
        pass
    elif symbols_per_occasion > 1:
        #/ wire replay_double_dmrs = 1'b1;
        pass
    else:
        #/ wire replay_double_dmrs = 1'b0;
        pass
    #/

    # Y_BUF has combinational plane/address lookup.  Single-symbol processing
    # presents RB0 during P_LOAD_CTX so it stays aligned with the restored Gold
    # state; double-symbol TD-CDM processing consumes beats in P_ISSUE.
    _win_base_expr = f"p_window_cnt * {BEATS_PER_WINDOW}" if BEATS_PER_WINDOW > 1 else "p_window_cnt"
    if BEATS_PER_WINDOW > 1:
        _last_addr = f"{_win_base_expr} + {BEATS_PER_WINDOW - 1}"
        #/ wire [`YBUF_ADDR_W`-1:0] ybuf_issue_addr_single = (p_beat_cnt == `_last_beat`) ? `_last_addr` : `_win_base_expr` + p_beat_cnt + 1'b1;
        #/ wire [`YBUF_ADDR_W`-1:0] ybuf_issue_addr_double = `_win_base_expr` + p_beat_cnt;
        #/ wire [`YBUF_ADDR_W`-1:0] ybuf_issue_addr = replay_double_dmrs ? ybuf_issue_addr_double : ybuf_issue_addr_single;
        pass
    else:
        #/ wire [`YBUF_ADDR_W`-1:0] ybuf_issue_addr = `_win_base_expr`;
        pass
    #/ assign ybuf_rd_en = (p_state == `P_STATE_W`'d`P_LOAD_CTX`) | (p_state == `P_STATE_W`'d`P_ISSUE`);
    #/ assign ybuf_rd_addr = (p_state == `P_STATE_W`'d`P_LOAD_CTX`) ? `_win_base_expr` : ybuf_issue_addr;
    if TOTAL_PLANES > 1:
        if symbols_per_occasion > 1:
            if max_occasions > 1:
                #/ assign ybuf_rd_plane_sel = {p_occ_cnt, p_sym_cnt};
                pass
            else:
                #/ assign ybuf_rd_plane_sel = {1'b0, p_sym_cnt};
                pass
        else:
            #/ assign ybuf_rd_plane_sel = p_occ_cnt[`PLANE_SEL_W`-1:0];
            pass
        #/ wire [`PLANE_SEL_W`-1:0] replay_token_plane_in = ybuf_rd_plane_sel;
    else:
        #/ wire [`PLANE_SEL_W`-1:0] replay_token_plane_in = `PLANE_SEL_W`'d0;
        pass
    # Descriptor valid/address is tied to the Y beat actually entering LS.
    # The last single-mode P_ISSUE cycle only holds RB(last) for drain and is
    # deliberately not a new token.
    #/ wire                    replay_single_data_valid = (p_state == `P_STATE_W`'d`P_LOAD_CTX`) |
    #/ ((p_state == `P_STATE_W`'d`P_ISSUE`) & (p_beat_cnt != `_last_beat`));
    #/ wire [`BEAT_CNT_W`-1:0] replay_single_local_rb =
    #/ (p_state == `P_STATE_W`'d`P_LOAD_CTX`) ? `BEAT_CNT_W`'d0 : p_beat_cnt + 1'b1;
    if symbols_per_occasion > 1:
        #/ assign replay_data_valid = replay_double_dmrs ? ls_enable : replay_single_data_valid;
        #/ assign replay_token_in   = {replay_token_plane_in,
        #/ replay_double_dmrs ? p_beat_cnt : replay_single_local_rb};
        # Only symbol 1 publishes in runtime/static double mode. Runtime
        # single mode publishes the prefetched symbol-0 beats.
        #/ assign replay_token_valid_in = replay_data_valid & (~replay_double_dmrs | p_sym_cnt);
        pass
    else:
        #/ assign replay_token_in       = {replay_token_plane_in, replay_single_local_rb};
        #/ assign replay_token_valid_in = replay_single_data_valid;
        pass
    #/

    # =========================================================================
    # Producer FSM
    # =========================================================================
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n) begin
    #/         p_state      <= `P_STATE_W`'d`P_IDLE`;
    #/         p_window_cnt <= `WINDOW_CNT_W`'d0;
    if max_occasions > 1:
        #/ p_occ_cnt    <= `OCC_CNT_W`'d0;
        pass
    if symbols_per_occasion > 1:
        #/ p_sym_cnt    <= 1'b0;
        pass
    #/ p_beat_cnt   <= `BEAT_CNT_W`'d0;
    #/ p_drain_cnt  <= `DRAIN_CNT_W`'d0;
    #/ p_bank_sel   <= 1'b0;
    #/ bank_full    <= 2'b0;
    #/ done_r       <= 1'b0;
    #/ ctrl_start_seen <= 1'b0;
    if HAS_RUNTIME_DOUBLE:
        #/ replay_double_dmrs_r <= 1'b0;
        pass
    #/ end else begin
    #/     if (!ctrl_start) begin
    #/         ctrl_start_seen <= 1'b0;
    #/     end
    #/
    #/     // Consumer bank release (higher priority than producer set)
    #/     if (c_state == `C_STATE_W`'d`C_RELEASE`)
    #/     bank_full[c_bank_sel] <= 1'b0;
    #/
    #/     case (p_state)
    #/
    #/         `P_STATE_W`'d`P_IDLE`: begin
    #/             p_beat_cnt  <= `BEAT_CNT_W`'d0;
    #/             p_drain_cnt <= `DRAIN_CNT_W`'d0;
    #/             done_r      <= 1'b0;
    #/             if (ctrl_start && !ctrl_start_seen && p_bank_free) begin
    #/                 p_state <= `P_STATE_W`'d`P_LOAD_CTX`;
    #/                 ctrl_start_seen <= 1'b1;
    if HAS_RUNTIME_DOUBLE:
        #/ replay_double_dmrs_r <= cfg_is_double_dmrs;
        pass
    if symbols_per_occasion > 1:
        #/ p_sym_cnt <= 1'b0;
        pass
    #/ end
    #/ end
    #/
    #/ `P_STATE_W`'d`P_LOAD_CTX`: begin
    #/     p_state    <= `P_STATE_W`'d`P_ISSUE`;
    #/     p_beat_cnt <= `BEAT_CNT_W`'d0;
    #/ end
    #/
    #/ `P_STATE_W`'d`P_ISSUE`: begin
    if BEATS_PER_WINDOW > 1:
        #/ if (p_beat_cnt == `_last_beat`) begin
        #/     p_beat_cnt  <= `BEAT_CNT_W`'d0;
        #/     p_drain_cnt <= `DRAIN_CNT_W`'d0;
        #/     p_state     <= `P_STATE_W`'d`P_DRAIN`;
        #/ end else begin
        #/     p_beat_cnt   <= p_beat_cnt + 1'b1;
        #/ end
        pass
    else:
        #/ p_drain_cnt <= `DRAIN_CNT_W`'d0;
        #/ p_state     <= `P_STATE_W`'d`P_DRAIN`;
        pass
    #/ end
    #/
    #/ `P_STATE_W`'d`P_DRAIN`: begin
    #/     if (p_drain_cnt == `_last_drain`) begin
    #/         p_state <= `P_STATE_W`'d`P_SAVE_CTX`;
    #/     end else begin
    #/         p_drain_cnt <= p_drain_cnt + 1'b1;
    #/     end
    #/ end
    #/
    #/ `P_STATE_W`'d`P_SAVE_CTX`: begin
    if symbols_per_occasion > 1:
        #/ if ((p_sym_cnt == 1'b0) && replay_double_dmrs) begin
        #/     p_sym_cnt <= 1'b1;
        #/     p_state   <= `P_STATE_W`'d`P_LOAD_CTX`;
        #/ end else begin
        #/     p_sym_cnt <= 1'b0;
        #/     p_state   <= `P_STATE_W`'d`P_PUBLISH`;
        #/ end
        pass
    else:
        #/ p_state <= `P_STATE_W`'d`P_PUBLISH`;
        pass
    #/ end
    #/
    #/ `P_STATE_W`'d`P_PUBLISH`: begin
    #/     bank_full[p_bank_sel] <= 1'b1;
    #/     p_bank_sel <= ~p_bank_sel;
    #/     p_state <= `P_STATE_W`'d`P_IDLE`;
    if max_occasions > 1:
        #/ if (p_occ_cnt == `_last_occ`) begin
        #/     p_occ_cnt <= `OCC_CNT_W`'d0;
        #/     if (p_window_cnt == max_windows - 1'b1) begin
        #/         done_r       <= 1'b1;
        #/         p_window_cnt <= `WINDOW_CNT_W`'d0;
        #/     end else begin
        #/         p_window_cnt <= p_window_cnt + 1'b1;
        #/     end
        #/ end else begin
        #/     p_occ_cnt <= p_occ_cnt + 1'b1;
        #/ end
        pass
    else:
        #/ if (p_window_cnt == max_windows - 1'b1) begin
        #/     done_r       <= 1'b1;
        #/     p_window_cnt <= `WINDOW_CNT_W`'d0;
        #/ end else begin
        #/     p_window_cnt <= p_window_cnt + 1'b1;
        #/ end
        pass
    #/ end
    #/
    #/ default: p_state <= `P_STATE_W`'d`P_IDLE`;
    #/ endcase
    #/ end
    #/ end
    #/

    # =========================================================================
    # Consumer FSM
    # =========================================================================
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n) begin
    #/         c_state    <= `C_STATE_W`'d`C_IDLE`;
    #/         c_mac_cnt  <= `MAC_CNT_W`'d0;
    #/         c_bank_sel <= 1'b0;
    #/     end else begin
    #/         case (c_state)
    #/             `C_STATE_W`'d`C_IDLE`: begin
    #/                 if (c_bank_ready) begin
    #/                     c_state   <= `C_STATE_W`'d`C_WAIT_FULL`;
    #/                 end
    #/             end
    #/             `C_STATE_W`'d`C_WAIT_FULL`: begin
    #/                 c_state   <= `C_STATE_W`'d`C_MAC`;
    #/                 c_mac_cnt <= `MAC_CNT_W`'d0;
    #/             end
    #/             `C_STATE_W`'d`C_MAC`: begin
    #/                 if (c_mac_cnt == `_last_mac`) begin
    #/                     c_state <= `C_STATE_W`'d`C_RELEASE`;
    #/                 end else begin
    #/                     c_mac_cnt <= c_mac_cnt + 1'b1;
    #/                 end
    #/             end
    #/             `C_STATE_W`'d`C_RELEASE`: begin
    #/                 c_bank_sel <= ~c_bank_sel;
    #/                 c_state    <= bank_full[~c_bank_sel] ? `C_STATE_W`'d`C_WAIT_FULL` : `C_STATE_W`'d`C_IDLE`;
    #/             end
    #/             default: c_state <= `C_STATE_W`'d`C_IDLE`;
    #/         endcase
    #/     end
    #/ end
    #/

    # =========================================================================
    # Pilot bank write logic (returned LS replay token)
    # =========================================================================
    # The LS module delays {valid, plane, local_rb} by its actual pre-FI data
    # latency.  Publication therefore cannot lose RB0 or retag a beat when a
    # Hybrid runtime branch changes averaging behavior.
    #/ assign pilot_wr_en   = replay_token_valid_out;
    #/ assign pilot_wr_addr = replay_token_out[`BEAT_CNT_W`-1:0];
    if TOTAL_PLANES > 1:
        #/ assign pilot_wr_plane = replay_token_out[`REPLAY_TOKEN_DWT`-1:`BEAT_CNT_W`];
        pass
    #/

    # =========================================================================
    # Output assignments
    # =========================================================================
    #/ assign ls_enable = (p_state == `P_STATE_W`'d`P_ISSUE`);
    #/ assign ls_sym_switch = (p_state == `P_STATE_W`'d`P_LOAD_CTX`);
    #/ assign lfsr_ctx_save_en = (p_state == `P_STATE_W`'d`P_SAVE_CTX`);
    #/ assign lfsr_ctx_restore_en = (p_state == `P_STATE_W`'d`P_LOAD_CTX`);
    if symbols_per_occasion > 1:
        #/ assign lfsr_ctx_sel = p_sym_cnt;
        pass
    #/ assign avg_sym_switch = (p_state == `P_STATE_W`'d`P_LOAD_CTX`);
    #/ assign pilot_bank_wr_done = (p_state == `P_STATE_W`'d`P_PUBLISH`);
    #/ assign pilot_bank_sel = c_bank_sel;
    if symbols_per_occasion > 1:
        #/ assign replay_c_init_strb = (p_window_cnt == `WINDOW_CNT_W`'d0) &
        #/ ((p_state == `P_STATE_W`'d`P_LOAD_CTX`) |
        #/     (replay_double_dmrs & (p_state == `_p_issue`) &
        #/         (p_beat_cnt == `BEAT_CNT_W`'d0)));
        pass
    else:
        #/ assign replay_c_init_strb = (p_state == `P_STATE_W`'d`P_LOAD_CTX`) & (p_window_cnt == `WINDOW_CNT_W`'d0);
        pass
    #/ assign cur_window = p_window_cnt;
    if max_occasions > 1:
        #/ assign cur_occasion = p_occ_cnt;
        pass
    #/ assign all_done  = done_r;
    #/ assign ctrl_done = done_r;
    #/ assign fi_enable = (c_state == `C_STATE_W`'d`C_MAC`);
    #/
    #/ endmodule
