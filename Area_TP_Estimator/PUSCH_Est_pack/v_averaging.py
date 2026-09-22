from typing import Dict, Literal, List, Optional, Tuple
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
import math
from os.path import dirname
sys.path.append(dirname((__file__)))


from basic_modules import QuType, QuMode, OfMode, ModuleAdd, ModuleDelay, ModuleFxMatch, ModuleSub, ModuleSimpleSRAM, ModuleCounter
from helpers.port_helpers import delay_ports, arith_ports, fxmatch_ports
from delay_budget import DelayBudget, cost_adder, COST_MUX, DEFAULT_BUDGET
from dmrs_config import (
    PILOT_RE_TYPE1, PILOT_RE_TYPE2,
    compute_fdCDM_tdCDM,
    get_cdm_group_for_port,
)


def averaging_pipeline_depth(
    Qu_IN_DWT: int,
    dmrs_Type: int | str,
    cdm_group: int,
    fdCDM: int | str,
    tdCDM: int | str,
    RB_PARALLELISM: int,
) -> int:
    """Actual pipeline depth for AVERAGING module.

    Stage 1 (freq avg): All L1+L2 adders + output MUX are combinational.
    Output register: 1 clock.
    Stage 2 (time avg): SRAM read alignment delay (1 clock) if tdCDM >= 2 or Hybrid.
    """
    AVG_FREQ_CLK = 1  # Single output register after combinational freq averaging
    need_td_avg = (tdCDM == 2 or tdCDM == "Hybrid")
    AVG_TIME_CLK = 1 if need_td_avg else 0
    return AVG_FREQ_CLK + AVG_TIME_CLK


@convert
def ModuleAVERAGING(Qu_IN: QuType, Qu_OUT: QuType, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool, RB_PARALLELISM: int, dmrs_Type: int | Literal["Hybrid"], cdm_group: int, fdCDM: int | Literal["Hybrid"], tdCDM: int | Literal["Hybrid"], max_num_RBs: int, SRAM_MACRO_CONFIG: Optional[Dict] = None, HAS_ENABLE: bool = False) -> None:
    """
    De-OCC Part 2 — Frequency + Time Averaging of LS Estimates.

    Per-component instance for one CDM group.

    Pipeline: Stage 1 (freq avg, 1 clk) → Stage 2 (time avg / SRAM, 1 clk).
    Total latency: 2 clocks (1 if tdCDM=1).

    :param Qu_IN: QuType(12, 4, True)
    :param Qu_OUT: QuType(12, 4, True)
    :param QU_MODE: QuMode.TRN.TCPL
    :param OF_MODE: OfMode.SAT.TCPL
    :param IF_RST_N: True
    :param RB_PARALLELISM: 1
    :param dmrs_Type: 1
        DMRS type (1, 2, or "Hybrid").
    :param cdm_group: 0
    :param fdCDM: 2
        Frequency-domain CDM window size (1, 2, 4, or "Hybrid").
    :param tdCDM: 1
        Time-domain CDM window size (1, 2, or "Hybrid").
    :param max_num_RBs: 273
        Maximum number of RBs (determines SRAM depth).

    Key Signal Timing (fdCDM=4, dmrs_Type=1, RB_PARALLELISM=1, tdCDM=2):
    sym_switch pulses 1 clk BEFORE the first RB data arrives at the module input.

    | clk            | T=0 | T=1 | T=2  | T=3  | T=4  | T=5  | T=6  | ... |
    |----------------|-----|-----|------|------|------|------|------|-----|
    | sym_switch     |  0  |  1  |  0   |  0   |  0   |  0   |  0   | ... |
    | input data     |  -  |  -  | RB0  | RB1  | RB2  | RB3  | RB0* | ... |
    | has_partial    |  ?  |  0  |  0   |  1   |  0   |  1   |  0   | ... |
    |                |     |  ^init on sym_switch                          |
    | prev_tail      |  ?  |  ?  | L1_2(RB0)| L1_2(RB1)| L1_2(RB2)| ... |
    | favg_q (Stage1)|  -  |  -  |  -   | RB0  | RB1  | RB2  | RB3  | ... |
    | l_quote        |  0  |  0  |  0   |  0   |  0   |  0   |  0   |  1  |
    | l_quote_q      |  0  |  0  |  0   |  0   |  0   |  0   |  0   |  0  |
    | sram_wr_en     |  0  |  0  |  0   |  1   |  1   |  1   |  1   | ... |
    | sram_rd_en     |  0  |  0  |  0   |  0   |  0   |  0   |  0   | ... |

    Averaging window assignment for each RB with fdCDM=4, need_cross_rb_t1=True:

    | RB parity   | has_partial | P0,P1         | P2,P3         | P4,P5         |
    |-------------|-------------|---------------|---------------|---------------|
    | Even (0,2,…)|     0       | l2_0 /4 avg   | l2_0 /4 avg   | l1_2 /2 avg   |
    | Odd  (1,3,…)|     1       | cross_l2 /4avg| l2_1 /4 avg   | l2_1 /4 avg   |

    where:
      l2_0    = (L1_0 + L1_1)   = pilot avg of P0+P1+P2+P3  in same RB
      l2_1    = (L1_1 + L1_2)   = pilot avg of P2+P3+P4+P5  in same RB
      cross_l2= (prev_L1_2+L1_0)= pilot avg of prevRB.P4,P5 + curRB.P0,P1

    This ensures exactly 3 non-overlapping 4-pilot windows across every
    consecutive RB pair (12 pilots total), matching 3GPP TS 38.211.
    """

    # =========================================================================
    # Step 0: Elaborate-time analysis
    # =========================================================================

    # Determine the pilot RE count per type
    if dmrs_Type == 1 or dmrs_Type == "Hybrid":
        pilot_re_t1 = PILOT_RE_TYPE1[cdm_group]
        n_pilots_t1 = len(pilot_re_t1)  # 6
    if dmrs_Type == 2 or dmrs_Type == "Hybrid":
        pilot_re_t2 = PILOT_RE_TYPE2[cdm_group]
        n_pilots_t2 = len(pilot_re_t2)  # 4
    if dmrs_Type == 3:
        from dmrs_config import PILOT_RE_TYPE3
        pilot_re_t3 = PILOT_RE_TYPE3[cdm_group]
        n_pilots_t3 = len(pilot_re_t3)  # 2

    # Hardware sizing: use the maximum pilot count across supported types
    if dmrs_Type == 1:
        N_PILOTS = n_pilots_t1  # 6
    elif dmrs_Type == 2:
        N_PILOTS = n_pilots_t2  # 4
    elif dmrs_Type == 3:
        N_PILOTS = n_pilots_t3  # 2
    else:  # Hybrid
        N_PILOTS = max(n_pilots_t1, n_pilots_t2)  # 6

    # Maximum fdCDM value for hardware sizing
    if fdCDM == "Hybrid":
        MAX_FDCDM = 4
    else:
        MAX_FDCDM = fdCDM

    # Whether we need cross-RB accumulation (Type 1, fdCDM=4: 6 mod 4 = 2)
    need_cross_rb_t1 = (MAX_FDCDM == 4) and (dmrs_Type == 1 or dmrs_Type == "Hybrid") and (RB_PARALLELISM % 2 != 0)

    # SRAM depth for tdCDM storage (one entry per RB clock beat, × N_PORTS for TDM)
    base_sram_depth = math.ceil(max_num_RBs / RB_PARALLELISM)
    SRAM_DEPTH = base_sram_depth
    SRAM_ADDR_WIDTH = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1

    # SRAM macro config extraction
    USE_MACRO = SRAM_MACRO_CONFIG is not None
    if USE_MACRO:
        if 'roles' not in SRAM_MACRO_CONFIG:
            raise ValueError("SRAM_MACRO_CONFIG requires candidate-derived memory roles")
        _ROLE = SRAM_MACRO_CONFIG['roles']['averaging_single_port']
        _TILES = _ROLE['tiles']
        _SP_TIEOFFS = SRAM_MACRO_CONFIG.get('sp_tieoff_ports', [("RET1N", "1'b1")])
        _SP_IS_DP_MACRO = SRAM_MACRO_CONFIG.get('sp_uses_dp_macro', False)
        _DP_TIEOFFS = SRAM_MACRO_CONFIG.get('dp_tieoff_ports', [("RET1N", "1'b1")])
        MACRO_DEPTH = _ROLE['macro_depth']
        MACRO_ADDR_WIDTH = max(math.ceil(math.log2(MACRO_DEPTH)), 1)
        if _ROLE['logical_width'] != N_PILOTS * Qu_IN.DWT:
            raise ValueError("averaging memory role width mismatch")
        if MACRO_DEPTH < SRAM_DEPTH:
            raise ValueError(f"SRAM macro depth={MACRO_DEPTH} < SRAM_DEPTH={SRAM_DEPTH}")


    n_l1 = N_PILOTS // 2  # Level-1 adder count: 3 for Type1(6), 2 for Type2(4)
    DWT_L1 = Qu_IN.DWT + 1
    DWT_L2 = Qu_IN.DWT + 2
    DWT_TD = Qu_IN.DWT + 1

    need_td_avg = (tdCDM == 2 or tdCDM == "Hybrid")

    # =========================================================================
    # Pipeline depth — single source of truth via averaging_pipeline_depth()
    # =========================================================================
    AVG_MIN_PIPELINE_DEPTH = averaging_pipeline_depth(Qu_IN_DWT=Qu_IN.DWT, dmrs_Type=dmrs_Type, cdm_group=cdm_group, fdCDM=fdCDM, tdCDM=tdCDM, RB_PARALLELISM=RB_PARALLELISM,)

    # =========================================================================
    # Step 1: Module Port Declaration
    # =========================================================================

    #/ `timescale 1ns / 1ps
    #/ module AVERAGING(
    #/     input clk,
    if IF_RST_N:
        #/ input rst_n,
        pass

    # Control signals
    if fdCDM == "Hybrid":
        #/ // 2'b00 = 1, 2'b01=2, 2'b10=4
        #/ input [1:0] fdCDM_ctrl,
        pass
    if tdCDM == "Hybrid":
        #/ // 1'b0 = 1, 1'b1=2
        #/ input tdCDM_ctrl,
        pass
    if need_td_avg:
        #/ // 0 = first DMRS symbol, 1=second
        #/ input l_quote,
        pass
    if need_td_avg or need_cross_rb_t1:
        #/ input sym_switch,
        pass
    if HAS_ENABLE:
        #/ input enable,
        pass

    # Per RB x per pilot: input (single component -- real or imag)
    for rb in range(RB_PARALLELISM):
        for k in range(N_PILOTS):
            in_name = f"h_ls_rb{rb}_pilot{k}"
            #/ input [`Qu_IN.DWT`-1:0] `in_name`,
            pass

    # Per RB x per pilot: output (single component)
    out_ports_list: List[str] = []
    for rb in range(RB_PARALLELISM):
        for k in range(N_PILOTS):
            out_ports_list.append(f"h_avg_rb{rb}_pilot{k}")

    for idx, op in enumerate(out_ports_list):
        comma = "" if idx == len(out_ports_list) - 1 else ","
        #/ output [`Qu_OUT.DWT`-1:0] `op + comma`
        pass
    #/ );

    # =========================================================================
    # Step 2: Frequency Averaging (Stage 1) -- Combinational Adder Tree
    # =========================================================================

    #/ // ========== Stage 1: Frequency Averaging ==========

    # Cross-RB partial window control (shared across RBs)
    # 1clk after sym_switch = first RBG included
    # Edge cases (all safe by design):
    #   - sym_switch during has_partial=1: resets to 0, fresh start for new symbol
    #   - Odd num_RBs with fdCDM=4: last odd RB uses cross_l2 (prev_tail + l1_0),
    #     its own l1_2 in prev_tail is harmlessly discarded at next sym_switch
    #   - SRAM address: 1 beat per RB regardless of has_partial state (no bubbles)
    if need_cross_rb_t1:
        #/ reg has_partial;
        if IF_RST_N:
            #/ always @(posedge clk or negedge rst_n) begin
            #/     if (!rst_n) begin
            #/         has_partial <= 1'b0;
            #/     end
            #/     else begin
            #/         if (sym_switch) begin
            #/             has_partial <= 1'b0;
            #/         end else `"if (enable) begin" if HAS_ENABLE else "begin"`
            #/             has_partial <= ~has_partial;
            #/         end
            #/     end
            #/ end
            pass
        else:
            #/ always @(posedge clk) begin
            #/     if (sym_switch) begin
            #/         has_partial <= 1'b0;
            #/     end else `"if (enable) begin" if HAS_ENABLE else "begin"`
            #/         has_partial <= ~has_partial;
            #/     end
            #/ end
            pass

    for rb in range(RB_PARALLELISM):
        #/ // --- RB `rb` ---

        # Alias input wires for readability
        for k in range(N_PILOTS):
            in_name = f"h_ls_rb{rb}_pilot{k}"
            alias = f"rb{rb}_in{k}"
            #/ wire [`Qu_IN.DWT`-1:0] `alias` = `in_name`;
            pass

        # ---- Level-1 adders: pairwise sums ----
        for j in range(n_l1):
            a_name = f"rb{rb}_in{2*j}"
            b_name = f"rb{rb}_in{2*j+1}"
            sum_name = f"rb{rb}_l1_{j}"
            #/ wire [`DWT_L1`-1:0] `sum_name`;

            Qu_L1 = QuType(DWT=Qu_IN.DWT, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L1_O = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            ModuleAdd(QU_IN_1=Qu_L1, QU_IN_2=Qu_L1, QU_OUT=Qu_L1_O, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS=arith_ports(a_name, b_name, sum_name))  # type: ignore

        # ---- Level-2 adder: l1_0 + l1_1 → l2_0 (for fdCDM=4) ----
        if MAX_FDCDM >= 4 and n_l1 >= 2:
            a2 = f"rb{rb}_l1_0"
            b2 = f"rb{rb}_l1_1"
            s2 = f"rb{rb}_l2_0"
            #/ wire [`DWT_L2`-1:0] `s2`;

            Qu_L2 = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L2_O = QuType(DWT=DWT_L2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            ModuleAdd(QU_IN_1=Qu_L2, QU_IN_2=Qu_L2, QU_OUT=Qu_L2_O, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS=arith_ports(a2, b2, s2))  # type: ignore

        # ---- Level-2 adder: l1_1 + l1_2 → l2_1 (fdCDM=4, Type1: 6 pilots, odd-RB tail group) ----
        # Required so that odd-RB pilots 2-5 form a clean 4-pilot window (l1_1+l1_2),
        # independent of the cross-RB window that consumed l1_0.
        if MAX_FDCDM >= 4 and n_l1 == 3:
            a2_1 = f"rb{rb}_l1_1"
            b2_1 = f"rb{rb}_l1_2"
            s2_1 = f"rb{rb}_l2_1"
            #/ wire [`DWT_L2`-1:0] `s2_1`;

            Qu_L2_1 = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L2_1_O = QuType(DWT=DWT_L2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            ModuleAdd(QU_IN_1=Qu_L2_1, QU_IN_2=Qu_L2_1, QU_OUT=Qu_L2_1_O, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS=arith_ports(a2_1, b2_1, s2_1))  # type: ignore

        # ---- Cross-RB partial window accumulation (fdCDM=4, Type 1: 6 mod 4 = 2) ----
        if need_cross_rb_t1:
            tail_idx = 2  # last L1 pair (tail of partial window)
            tail_l1 = f"rb{rb}_l1_{tail_idx}"  # e.g., rb0_l1_2 for 6 pilots
            head_l1 = f"rb{rb}_l1_0"           # first L1 pair

            prev_tail = f"prev_l1_tail_rb{rb}"
            prev_tail_cur = f"prev_l1_tail_cur_rb{rb}"
            cross_l2 = f"cross_l2_rb{rb}"

            if HAS_ENABLE:
                #/ reg [`DWT_L1`-1:0] `prev_tail`;
                if IF_RST_N:
                    #/ always @(posedge clk or negedge rst_n) begin
                    #/     if (!rst_n) `prev_tail` <= `DWT_L1`'d0;
                    #/     else if (enable) `prev_tail` <= `tail_l1`;
                    #/ end
                    pass
                else:
                    #/ always @(posedge clk) begin
                    #/     if (enable) `prev_tail` <= `tail_l1`;
                    #/ end
                    pass
            else:
                #/ wire [`DWT_L1`-1:0] `prev_tail`;
                ModuleDelay(DWT=DWT_L1, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports(tail_l1, prev_tail, if_rst_n=IF_RST_N))  # type: ignore
            #/ wire [`DWT_L1`-1:0] `prev_tail_cur` = `prev_tail`;
            pass

            # Cross-RB L2 adder: prev_tail_cur + current head
            #/ wire [`DWT_L2`-1:0] `cross_l2`;
            Qu_L2 = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L2_O = QuType(DWT=DWT_L2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            ModuleAdd(QU_IN_1=Qu_L2, QU_IN_2=Qu_L2, QU_OUT=Qu_L2_O, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS=arith_ports(prev_tail_cur, head_l1, cross_l2))  # type: ignore

        # ---- Output MUX: select per-pilot averaged value ----
        for k in range(N_PILOTS):
            out_favg = f"rb{rb}_favg{k}"

            if fdCDM == 1:
                in_name = f"rb{rb}_in{k}"
                #/ wire [`Qu_IN.DWT`-1:0] `out_favg` = `in_name`;
            elif fdCDM == 2:
                pair_idx = k // 2
                l1 = f"rb{rb}_l1_{pair_idx}"
                #/ wire [`Qu_IN.DWT`-1:0] `out_favg` = `l1`[`DWT_L1`-1:1];
            elif fdCDM == 4:
                group_start = (k // 4) * 4
                group_size = min(4, N_PILOTS - group_start)
                if group_size == 4:
                    if need_cross_rb_t1:
                        cross_l2 = f"cross_l2_rb{rb}"
                        l2 = f"rb{rb}_l2_0"
                        l2_1 = f"rb{rb}_l2_1"
                        #/ wire [`Qu_IN.DWT`-1:0] `out_favg`;
                        if k < 2:
                            # P0,P1: even-RB → l2_0 (pilots 0-3), odd-RB → cross_l2 (prevRB.P4,P5 + curRB.P0,P1)
                            #/ assign `out_favg` = has_partial ? `cross_l2`[`DWT_L2`-1:2] : `l2`[`DWT_L2`-1:2];
                            pass
                        else:
                            # P2,P3: even-RB → l2_0 (pilots 0-3), odd-RB → l2_1 (pilots 2-5)
                            #/ assign `out_favg` = has_partial ? `l2_1`[`DWT_L2`-1:2] : `l2`[`DWT_L2`-1:2];
                            pass
                    else:
                        l2 = f"rb{rb}_l2_0"
                        #/ wire [`Qu_IN.DWT`-1:0] `out_favg` = `l2`[`DWT_L2`-1:2];
                else:
                    # Partial window (Type 1 tail: pilots 4,5)
                    if need_cross_rb_t1:
                        l1 = f"rb{rb}_l1_2"
                        l2_1 = f"rb{rb}_l2_1"
                        #/ wire [`Qu_IN.DWT`-1:0] `out_favg`;
                        # even-RB: only 2-pilot avg (l1_2), odd-RB: 4-pilot avg (l2_1 = l1_1+l1_2)
                        #/ assign `out_favg` = has_partial ? `l2_1`[`DWT_L2`-1:2] : `l1`[`DWT_L1`-1:1];
                    else:
                        pair_idx = group_start // 2
                        l1 = f"rb{rb}_l1_{pair_idx}"
                        #/ wire [`Qu_IN.DWT`-1:0] `out_favg` = `l1`[`DWT_L1`-1:1];
            elif fdCDM == "Hybrid":
                in_pass = f"rb{rb}_in{k}"
                pair_idx = k // 2
                l1 = f"rb{rb}_l1_{pair_idx}"
                group_start = (k // 4) * 4
                group_size = min(4, N_PILOTS - group_start)

                if group_size == 4 and n_l1 >= 2:
                    l2 = f"rb{rb}_l2_0"
                    l2_1 = f"rb{rb}_l2_1"
                    if need_cross_rb_t1:
                        cross_l2 = f"cross_l2_rb{rb}"
                        if k < 2:
                            # P0,P1: even-RB → l2_0, odd-RB → cross_l2
                            fd4_expr = f"has_partial ? {cross_l2}[{DWT_L2}-1:2] : {l2}[{DWT_L2}-1:2]"
                        else:
                            # P2,P3: even-RB → l2_0, odd-RB → l2_1
                            fd4_expr = f"has_partial ? {l2_1}[{DWT_L2}-1:2] : {l2}[{DWT_L2}-1:2]"
                    else:
                        fd4_expr = f"{l2}[{DWT_L2}-1:2]"
                else:
                    # Partial window (pilots 4,5)
                    if need_cross_rb_t1:
                        l1_tail = f"rb{rb}_l1_2"
                        l2_1 = f"rb{rb}_l2_1"
                        # even-RB: 2-pilot (l1_2), odd-RB: 4-pilot (l2_1)
                        fd4_expr = f"has_partial ? {l2_1}[{DWT_L2}-1:2] : {l1_tail}[{DWT_L1}-1:1]"
                    else:
                        fd4_expr = f"{l1}[{DWT_L1}-1:1]"

                #/ wire [`Qu_IN.DWT`-1:0] `out_favg`;
                #/ assign `out_favg` = (fdCDM_ctrl == 2'b10) ? `fd4_expr` :
                #/ (fdCDM_ctrl == 2'b01) ? `l1`[`DWT_L1`-1:1] :
                #/ `in_pass`;

        # ---- Register freq-avg outputs (pipeline cut) ----
        for k in range(N_PILOTS):
            favg_in = f"rb{rb}_favg{k}"
            favg_q = f"rb{rb}_favg{k}_q"
            if HAS_ENABLE:
                #/ reg [`Qu_IN.DWT`-1:0] `favg_q`;
                if IF_RST_N:
                    #/ always @(posedge clk or negedge rst_n) begin
                    #/     if (!rst_n) `favg_q` <= `Qu_IN.DWT`'d0;
                    #/     else if (enable) `favg_q` <= `favg_in`;
                    #/ end
                    pass
                else:
                    #/ always @(posedge clk) begin
                    #/     if (enable) `favg_q` <= `favg_in`;
                    #/ end
                    pass
            else:
                #/ wire [`Qu_IN.DWT`-1:0] `favg_q`;
                ModuleDelay(DWT=Qu_IN.DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports(favg_in, favg_q, if_rst_n=IF_RST_N))  # type: ignore

    # =========================================================================
    # Step 3: Time Averaging (Stage 2) -- SRAM + Adder
    # =========================================================================

    #/ // ========== Stage 2: Time Averaging (tdCDM) ==========

    if need_td_avg:
        # SRAM address counter (shared)
        #/ wire [`SRAM_ADDR_WIDTH`-1:0] sram_addr;
        #/ wire                         sram_wr_en;
        #/ wire                         sram_rd_en;

        # l_quote delayed by 1 clk to align with Stage 1 output
        #/ wire l_quote_q;
        ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports('l_quote', 'l_quote_q', if_rst_n=IF_RST_N))  # type: ignore

        if HAS_ENABLE:
            # Valid follows the Stage-1 register just like l_quote_q.
            #/ wire enable_q;
            ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports('enable', 'enable_q', if_rst_n=IF_RST_N))  # type: ignore

        # sym_switch delayed by 1 clk to match pipeline stage
        #/ wire sym_switch_q;
        ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports('sym_switch', 'sym_switch_q', if_rst_n=IF_RST_N))  # type: ignore

        # l_quote delayed by 2 clk total to align with time-avg output
        # (1 clk for Stage 1 register + 1 clk for SRAM read latency)
        #/ wire l_quote_qq;
        ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports('l_quote_q', 'l_quote_qq', if_rst_n=IF_RST_N))  # type: ignore

        # SRAM write/read enable (all signals now at T+1). Windowed replay
        # gates bubbles; without an enable port every beat is valid.
        if tdCDM == "Hybrid":
            _avg_valid = "enable_q & " if HAS_ENABLE else ""
            #/ assign sram_wr_en = `_avg_valid`tdCDM_ctrl & ~l_quote_q;
            #/ assign sram_rd_en = `_avg_valid`tdCDM_ctrl &  l_quote_q;
            pass
        else:  # tdCDM == 2
            _avg_valid = "enable_q & " if HAS_ENABLE else ""
            #/ assign sram_wr_en = `_avg_valid`~l_quote_q;
            #/ assign sram_rd_en = `_avg_valid`l_quote_q;
            pass

        # SRAM address counter (uses delayed sym_switch to match pipeline)
        #/ wire sram_counter_en = sram_wr_en | sram_rd_en;
        counter_ports = {
            'clk': 'clk',
            'enable': 'sram_counter_en',
            'clear': 'sym_switch_q',
            'count': 'sram_addr',
        }
        if IF_RST_N:
            counter_ports['rst_n'] = 'rst_n'
        ModuleCounter(DWT=SRAM_ADDR_WIDTH, STEP=1, IF_RST_N=IF_RST_N, HAS_CLEAR=True, HAS_WRAP=False, PORTS=counter_ports)  # type: ignore

        # Per RB x pilot: SRAM + time-domain adder
        if USE_MACRO:
            # Macro mode: bundle N_PILOTS into one SP SRAM macro per RB
            PACKED_DWT = N_PILOTS * Qu_IN.DWT
            ADDR_PAD = MACRO_ADDR_WIDTH - SRAM_ADDR_WIDTH
            addr_ext = f"{{{ADDR_PAD}'b0, sram_addr}}" if ADDR_PAD > 0 else "sram_addr"
            if not _SP_IS_DP_MACRO:
                #/ wire sram_cen = ~(sram_wr_en | sram_rd_en);
                #/ wire sram_wen = ~sram_wr_en;
                pass

        for rb in range(RB_PARALLELISM):
            if USE_MACRO:
                # Pack all N_PILOTS write-data signals into one wide bus
                wr_parts = [f"rb{rb}_favg{k}_q" for k in range(N_PILOTS - 1, -1, -1)]
                wr_concat = "{" + ", ".join(wr_parts) + "}"
                wr_bus = f"sram_d_rb{rb}"
                macro_q = f"sram_q_rb{rb}"
                #/ wire [`PACKED_DWT`-1:0] `wr_bus` = `wr_concat`;
                #/ wire [`PACKED_DWT`-1:0] `macro_q`;
                _tile_offset = 0
                for _tile_idx, _tile in enumerate(_TILES):
                    _tile_width = _tile['width']
                    _tile_module = _tile['module']
                    _tile_q = f"{macro_q}_tile{_tile_idx}"
                    _tile_inst = f"u_sram_rb{rb}_tile{_tile_idx}"
                    _tile_hi = _tile_offset + _tile_width - 1
                    #/ wire [`_tile_width`-1:0] `_tile_q`;
                    if _SP_IS_DP_MACRO:
                        _tieoffs = _DP_TIEOFFS
                        #/ `_tile_module` `_tile_inst` (
                        #/     .CLKA   (clk),
                        #/     .CENA   (~sram_rd_en),
                        #/     .AA     (`addr_ext`),
                        #/     .QA     (`_tile_q`),
                        #/     .CLKB   (clk),
                        #/     .CENB   (~sram_wr_en),
                        #/     .AB     (`addr_ext`),
                        #/     .DB     (`wr_bus`[`_tile_hi`:`_tile_offset`])`"," if _tieoffs else ""`
                        for _ti, (_port, _val) in enumerate(_tieoffs):
                            _comma = "," if _ti < len(_tieoffs) - 1 else ""
                            #/     .`_port`  (`_val`)`_comma`
                            pass
                        #/ );
                    else:
                        _tieoffs = _SP_TIEOFFS
                        #/ `_tile_module` `_tile_inst` (
                        #/     .CLK    (clk),
                        #/     .CEN    (sram_cen),
                        #/     .WEN    (sram_wen),
                        #/     .A      (`addr_ext`),
                        #/     .D      (`wr_bus`[`_tile_hi`:`_tile_offset`]),
                        #/     .Q      (`_tile_q`)`"," if _tieoffs else ""`
                        for _ti, (_port, _val) in enumerate(_tieoffs):
                            _comma = "," if _ti < len(_tieoffs) - 1 else ""
                            #/     .`_port`  (`_val`)`_comma`
                            pass
                        #/ );
                    #/ assign `macro_q`[`_tile_hi`:`_tile_offset`] = `_tile_q`;
                    _tile_offset = _tile_hi + 1

                # Extract individual sram_rd signals from packed Q
                for k in range(N_PILOTS):
                    sram_rd = f"sram_rd_rb{rb}_k{k}"
                    lo = k * Qu_IN.DWT
                    hi = lo + Qu_IN.DWT - 1
                    #/ wire [`Qu_IN.DWT`-1:0] `sram_rd` = `macro_q`[`hi`:`lo`];
                    pass

            for k in range(N_PILOTS):
                favg_q = f"rb{rb}_favg{k}_q"
                sram_rd = f"sram_rd_rb{rb}_k{k}"
                td_sum = f"td_sum_rb{rb}_k{k}"
                td_avg = f"td_avg_rb{rb}_k{k}"

                if not USE_MACRO:
                    #/ wire [`Qu_IN.DWT`-1:0] `sram_rd`;
                    ModuleSimpleSRAM(DWT=Qu_IN.DWT, DEPTH=SRAM_DEPTH, MODE='SP', IF_RST_N=False, PORTS={'clk': 'clk', 'addr': 'sram_addr', 'wr_en': 'sram_wr_en', 'wr_data': favg_q, 'rd_en': 'sram_rd_en', 'rd_data': sram_rd,})  # type: ignore

                # Delay favg_q by 1 clock to align with sram_rd
                favg_q_d = f"rb{rb}_favg{k}_q_d"
                #/ wire [`Qu_IN.DWT`-1:0] `favg_q_d`;
                ModuleDelay(DWT=Qu_IN.DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports(favg_q, favg_q_d, if_rst_n=IF_RST_N))  # type: ignore

                # Time-domain adder (both inputs now at T+2)
                #/ wire [`DWT_TD`-1:0] `td_sum`;
                Qu_TD = QuType(DWT=Qu_IN.DWT, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
                Qu_TD_O = QuType(DWT=DWT_TD, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
                ModuleAdd(QU_IN_1=Qu_TD, QU_IN_2=Qu_TD, QU_OUT=Qu_TD_O, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS=arith_ports(favg_q_d, sram_rd, td_sum))  # type: ignore

                # Divide by 2
                #/ wire [`Qu_IN.DWT`-1:0] `td_avg` = `td_sum`[`DWT_TD`-1:1];

    # =========================================================================
    # Step 4: Output Selection + Quantization
    # =========================================================================

    #/ // ========== Output Stage ==========

    for rb in range(RB_PARALLELISM):
        for k in range(N_PILOTS):
            favg_q = f"rb{rb}_favg{k}_q"
            out_name = f"h_avg_rb{rb}_pilot{k}"

            if not need_td_avg:
                out_pre_quant = favg_q
            elif tdCDM == 2:
                td_avg = f"td_avg_rb{rb}_k{k}"
                favg_q_d = f"rb{rb}_favg{k}_q_d"
                out_pre = f"out_pre_rb{rb}_k{k}"
                #/ wire [`Qu_IN.DWT`-1:0] `out_pre`;
                #/ assign `out_pre` = l_quote_qq ? `td_avg` : `favg_q_d`;
                out_pre_quant = out_pre
            else:  # tdCDM == "Hybrid"
                td_avg = f"td_avg_rb{rb}_k{k}"
                favg_q_d = f"rb{rb}_favg{k}_q_d"
                out_pre = f"out_pre_rb{rb}_k{k}"
                #/ wire [`Qu_IN.DWT`-1:0] `out_pre`;
                #/ assign `out_pre` = (tdCDM_ctrl & l_quote_qq) ? `td_avg` : `favg_q_d`;
                out_pre_quant = out_pre

            # Output quantization
            ModuleFxMatch(QU_IN=QuType(DWT=Qu_IN.DWT, FRAC=Qu_IN.FRAC, IF_SIGNED=True), QU_OUT=Qu_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS=fxmatch_ports(out_pre_quant, out_name))  # type: ignore

    _min_depth = averaging_pipeline_depth(
        Qu_IN.DWT, dmrs_Type, cdm_group, fdCDM, tdCDM, RB_PARALLELISM,
    )
    #/ // Timing budget: auto-min=`_min_depth` (fdCDM=`fdCDM`, tdCDM=`tdCDM`)
    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Example: Type 1 CDM Group 0, fdCDM=2, tdCDM=1 (single port, single component)
    ModuleAVERAGING(
        Qu_IN=QuType(12, 4, True),
        Qu_OUT=QuType(12, 4, True),
        QU_MODE=QuMode.TRN.TCPL,
        OF_MODE=OfMode.SAT.TCPL,
        IF_RST_N=True,
        RB_PARALLELISM=1,
        dmrs_Type=1,
        cdm_group=0,
        fdCDM=2,
        tdCDM=1,
        max_num_RBs=273,
    )
