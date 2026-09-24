###################################################################################################
# Module Name: TIME_INTERP
# Description: Per-antenna-port time-domain interpolation wrapper.
#   Integrates:
#     1. PILOT_SRAM_BANK  — banked SRAM, stores freq-interp results per DMRS occasion
#     2. TI core array    — TI_RE_PARALLELISM × NN/Linear/LMMSE instances
#     3. FxMatch output   — optional truncation / rounding
#
#   Data flow:
#     SRAM bank read (selected by rd_bank_sel) → TI cores → stream out
#     Each clock produces TI_RE_PARALLELISM × num_pusch_symbols results.
#
# Author: LiPtP
# Date: 2026.3.6
# Version: V0.2.0
# Dependency Modules: PILOT_SRAM_BANK, CORE_TIME_{NN,LIN,LMMSE}_INTERP
###################################################################################################
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Dict, List, Literal, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from analyze_timing import ControlSignalGraph
from basic_modules import QuType, QuMode, OfMode, ModuleFxMatch, ModuleDelay
from v_pilot_sram_bank import ModulePILOT_SRAM_BANK
from v_core_time_nn_interp import ModuleCORE_TIME_NN_INTERP
from v_core_time_lin_interp import ModuleCORE_TIME_LIN_INTERP
from v_core_time_lmmse_interp import ModuleCORE_TIME_LMMSE_INTERP, time_lmmse_pipeline_depth


@convert
def ModuleTIME_INTERP(antenna_port: int, max_occasions: int, max_num_RBs: int, RB_PARALLELISM: int, TI_RE_PARALLELISM: int, Qu_H_interp_f: QuType, Qu_H_interp_t: QuType, time_interp_method: str, dmrs_typeA_pos: str, is_double_dmrs: bool | Literal["Hybrid"], additional_DMRS_range: List[int], num_symbols_range: List[int], LMMSE_REAL_COEFF: bool, Qu_TI_LMMSE_COEFF: QuType, n_additional_dmrs_fixed: int, f_d_norm: float, W_coeffs: Optional[List[List[float]]], COEFF_SOURCE: Literal['ROM', 'SRAM'] = 'ROM', SRAM_MACRO_CONFIG: Optional[Dict] = None, has_pre_fi_buf: bool = False, FI_RE_PARALLELISM: int = 12, FI_WINDOW_SIZE: int = 1, ti_ctrl_graph: Optional['ControlSignalGraph'] = None) -> None:
    """
    Per-antenna-port time-domain interpolation wrapper.

    Instantiates PILOT_SRAM_BANK for pilot storage and TI_RE_PARALLELISM
    parallel time-interpolation cores.  Takes control signals from TI_CTRL
    (shared across all ports) and produces streaming output.

    **Data ordering** (Column input, Row output):
      For each RB beat (from TI_CTRL):
        For each RE group g = 0 .. 12/P − 1:
          Output P × max_pusch_symbols results  (all symbols, P REs in parallel).

    **Latency**:
      SRAM read (1 clk) + core pipeline → total visible in TI_CTRL ``TI_PIPELINE_DEPTH``.

    :param antenna_port: 0
    :param max_occasions: 3
    :param max_num_RBs: 273
    :param RB_PARALLELISM: 1
    :param TI_RE_PARALLELISM: 3
    :param Qu_H_interp_f: QuType(12, 4, True)
        Per-component QuType for freq-interpolated H. Complex width = 2 * DWT.
    :param Qu_H_interp_t: QuType(12, 4, True)
        Per-component QuType for time-interpolated H output. Complex width = 2 * DWT.
    :param time_interp_method: 'nn'
    :param dmrs_typeA_pos: 'pos2'
    :param is_double_dmrs: False
    :param additional_DMRS_range: [0, 2]
    :param num_symbols_range: [4, 14]
    :param LMMSE_REAL_COEFF: True
    :param Qu_TI_LMMSE_COEFF: QuType(12, 11, True)
        QuType for time-domain LMMSE coefficients.
    :param n_additional_dmrs_fixed: 2
    :param f_d_norm: 0.01
    :param W_coeffs: None
    :param has_pre_fi_buf: False
        When True, uses occasion registers instead of PILOT_SRAM_BANK.
    :param FI_RE_PARALLELISM: 12
    :param FI_WINDOW_SIZE: 1
        RBs per FI window (= LMMSE_P for LMMSE, 1 for NN/Linear).
    """
    # Derive complex wire widths from per-component QuType
    H_interp_f_DWT = 2 * Qu_H_interp_f.DWT
    H_interp_t_DWT = 2 * Qu_H_interp_t.DWT
    LMMSE_COEFF_DWT = Qu_TI_LMMSE_COEFF.DWT

    if 12 % TI_RE_PARALLELISM != 0:
        raise ValueError(f"TI_RE_PARALLELISM={TI_RE_PARALLELISM} must divide 12")

    RE_GROUPS = 12 // TI_RE_PARALLELISM
    SRAM_DEPTH = math.ceil(max_num_RBs / RB_PARALLELISM)
    SRAM_DATA_WIDTH = RB_PARALLELISM * 12 * H_interp_f_DWT  # full write-port width
    BANK_DATA_WIDTH = TI_RE_PARALLELISM * H_interp_f_DWT    # per-bank read width
    N_BANKS = RB_PARALLELISM * RE_GROUPS
    ADDR_WIDTH = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1
    OCC_SEL_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
    RE_GROUP_WIDTH = max(math.ceil(math.log2(RE_GROUPS)), 1) if RE_GROUPS > 1 else 1
    BANK_SEL_WIDTH = max(math.ceil(math.log2(N_BANKS)), 1) if N_BANKS > 1 else 1

    # Pre-FI occasion register geometry
    if has_pre_fi_buf:
        BEATS_PER_WINDOW = FI_WINDOW_SIZE // RB_PARALLELISM
        OCC_REG_DEPTH = BEATS_PER_WINDOW
        OCC_REG_ADDR_W = max(math.ceil(math.log2(OCC_REG_DEPTH)), 1) if OCC_REG_DEPTH > 1 else 1
        OCC_REG_DATA_W = SRAM_DATA_WIDTH
        FI_BEATS_PER_OCC = BEATS_PER_WINDOW
        FI_BEAT_CNT_W = max(math.ceil(math.log2(FI_BEATS_PER_OCC)), 1) if FI_BEATS_PER_OCC > 1 else 1
        LOCAL_RB_WIDTH = max(math.ceil(math.log2(BEATS_PER_WINDOW)), 1) if BEATS_PER_WINDOW > 1 else 1

    # Determine TI core pipeline depth
    if time_interp_method == 'nn':
        CORE_LATENCY = 1
    elif time_interp_method == 'linear':
        CORE_LATENCY = 1
    elif time_interp_method == 'lmmse':
        CORE_LATENCY = time_lmmse_pipeline_depth(max_occasions)
    else:
        raise ValueError(f"Invalid time_interp_method: {time_interp_method}")

    # Check runtime-config needs (for NN/Linear cores)
    needs_runtime_l0 = (dmrs_typeA_pos == 'Hybrid')
    needs_runtime_dbl = (is_double_dmrs == "Hybrid")
    needs_runtime_nadd = (len(additional_DMRS_range) > 1)
    min_sym = num_symbols_range[0]
    max_sym = num_symbols_range[-1]
    N_OUT_SYMS = max_sym
    sym_list = list(range(min_sym, max_sym + 1))
    needs_runtime_nsym = (len(sym_list) > 1)

    n_add_max = max(additional_DMRS_range)
    n_add_width = max(math.ceil(math.log2(n_add_max + 1)), 1) if n_add_max > 0 else 1
    counter_width = max(math.ceil(math.log2(max_num_RBs)), 1)

    #/ `timescale 1ns / 1ps
    #/ module TIME_INTERP (
    #/     input clk,
    #/     input rst_n,

    if not has_pre_fi_buf:
        #/ input wr_en,
        if max_occasions > 1:
            #/ input [`OCC_SEL_WIDTH`-1:0] wr_occasion_sel,
            pass
        #/ input [`ADDR_WIDTH`-1:0]      wr_addr,
        #/ input [`SRAM_DATA_WIDTH`-1:0] wr_data,
        pass
    else:
        #/ // ---- FI output capture -- pre-FI mode ----
        #/ input                        fi_out_valid,
        #/ input [`OCC_REG_DATA_W`-1:0] fi_out_data,
        if max_occasions > 1:
            #/ input [`OCC_SEL_WIDTH`-1:0] fi_occ_sel,
            pass

    #/
    #/ // ---- TI control -- from TI_CTRL, shared ----
    #/ input                        ti_sram_rd_en,
    if not has_pre_fi_buf:
        #/ input [`ADDR_WIDTH`-1:0]     ti_rb_addr,
        pass
    else:
        #/ input [`LOCAL_RB_WIDTH`-1:0] ti_rb_addr,
        pass
    #/ input [`RE_GROUP_WIDTH`-1:0] ti_re_group,
    if RB_PARALLELISM > 1:
        RB_WITHIN_WIDTH = max(math.ceil(math.log2(RB_PARALLELISM)), 1)
        #/ input [`RB_WITHIN_WIDTH`-1:0] ti_rb_within_beat,
        pass
    #/


    # ---- Runtime config inputs (when needed) ----
    if needs_runtime_l0:
        #/ input dmrs_typeA_pos_sel,
        pass
    if needs_runtime_dbl:
        #/ input is_double_dmrs,
        pass
    if needs_runtime_nadd:
        #/ input [`n_add_width`-1:0] n_additional_dmrs,
        pass
    if needs_runtime_nsym:
        #/ input [3:0] pusch_symbol_length,
        pass

    # ---- LMMSE coefficient write port (SRAM mode) ----
    if time_interp_method == 'lmmse' and COEFF_SOURCE == 'SRAM':
        _n_occ_fixed = 1 + n_additional_dmrs_fixed
        _total_coeff = max_sym * _n_occ_fixed
        _coeff_addr_w = max(math.ceil(math.log2(_total_coeff)), 1) if _total_coeff > 1 else 1
        #/ // LMMSE coefficient register write port -- shared across RE lanes
        #/ input                         ti_coeff_wr_en,
        #/ input [`_coeff_addr_w`-1:0]   ti_coeff_wr_addr,
        #/ input [`LMMSE_COEFF_DWT`-1:0] ti_coeff_wr_data,
        pass

    #/ // ---- Streaming output ----
    for re_lane in range(TI_RE_PARALLELISM):
        for sym in range(N_OUT_SYMS):
            last_port = (re_lane == TI_RE_PARALLELISM - 1) and (sym == N_OUT_SYMS - 1)
            comma = "" if last_port else ","
            #/ output [`H_interp_t_DWT`-1:0] `f"h_time_re{re_lane}_sym{sym}{comma}"`
            pass

    #/ );
    #/ 

    if not has_pre_fi_buf:
        # ===========================================================
        # 1. PILOT_SRAM_BANK instantiation (post-FI mode)
        # ===========================================================
        sram_ports = {'clk': 'clk', 'rst_n': 'rst_n', 'wr_en': 'wr_en', 'wr_addr': 'wr_addr', 'wr_data': 'wr_data', 'rd_en': 'ti_sram_rd_en', 'rd_addr': 'ti_rb_addr'}
        if max_occasions > 1:
            sram_ports['wr_occasion_sel'] = 'wr_occasion_sel'

        if N_BANKS > 1:
            if RB_PARALLELISM > 1 and RE_GROUPS > 1:
                #/ wire [`BANK_SEL_WIDTH`-1:0] rd_bank_sel_w = ti_rb_within_beat * `RE_GROUPS` + ti_re_group;
                sram_ports['rd_bank_sel'] = 'rd_bank_sel_w'
            elif RB_PARALLELISM > 1 and RE_GROUPS == 1:
                sram_ports['rd_bank_sel'] = 'ti_rb_within_beat'
            else:
                sram_ports['rd_bank_sel'] = 'ti_re_group'
        for occ in range(max_occasions):
            sram_ports[f'rd_data_occ{occ}'] = f'sram_rd_occ{occ}'

        for occ in range(max_occasions):
            #/ wire [`BANK_DATA_WIDTH`-1:0] `f"sram_rd_occ{occ}"`;
            pass
        #/

        ModulePILOT_SRAM_BANK(
            max_occasions=max_occasions,
            SRAM_DEPTH=SRAM_DEPTH,
            Qu_H_interp_f=Qu_H_interp_f,
            TI_RE_PARALLELISM=TI_RE_PARALLELISM,
            RB_PARALLELISM=RB_PARALLELISM,
            SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG,
            PORTS=sram_ports,  # type: ignore
        )

        # ===========================================================
        # 2. Unpack SRAM bank output (post-FI)
        # ===========================================================
        for re_lane in range(TI_RE_PARALLELISM):
            lo_bit = re_lane * H_interp_f_DWT
            hi_bit = lo_bit + H_interp_f_DWT - 1
            for occ in range(max_occasions):
                #/ wire [`H_interp_f_DWT`-1:0] `f"ti_in_re{re_lane}_occ{occ}"` = `f"sram_rd_occ{occ}"`[`hi_bit`:`lo_bit`];
                pass
        #/

    else:
        # ===========================================================
        # 1. Occasion register file (pre-FI mode)
        # ===========================================================
        # Per-occasion reg array, full-RB-width entries (SRAM_DATA_WIDTH per entry).
        # Write: sequential by fi_beat_cnt. Read: indexed by ti_rb_addr, bank-selected on output.
        #/ // ========== Occasion Register File (pre-FI) ==========
        for occ in range(max_occasions):
            #/ reg [`OCC_REG_DATA_W`-1:0] `f"occ_reg_{occ}"` [0:`OCC_REG_DEPTH`-1];
            pass
        #/

        if FI_BEATS_PER_OCC > 1:
            #/ reg [`FI_BEAT_CNT_W`-1:0] fi_beat_cnt;
            #/ always @(posedge clk or negedge rst_n) begin
            #/     if (!rst_n) begin
            #/         fi_beat_cnt <= `FI_BEAT_CNT_W`'d0;
            #/     end else if (fi_out_valid) begin
            #/         if (fi_beat_cnt == `FI_BEAT_CNT_W`'d`FI_BEATS_PER_OCC - 1`) begin
            #/             fi_beat_cnt <= `FI_BEAT_CNT_W`'d0;
            #/         end else begin
            #/             fi_beat_cnt <= fi_beat_cnt + 1'b1;
            #/         end
            #/     end
            #/ end
            #/
            #/ wire [`OCC_REG_ADDR_W`-1:0] fi_wr_addr = fi_beat_cnt;
            pass
        else:
            #/ wire [`OCC_REG_ADDR_W`-1:0] fi_wr_addr = `OCC_REG_ADDR_W`'d0;
            pass

        # Write logic: occasion-selected write
        for occ in range(max_occasions):
            #/ always @(posedge clk) begin
            if max_occasions > 1:
                #/     if (fi_out_valid && (fi_occ_sel == `OCC_SEL_WIDTH`'d`occ`)) begin
                pass
            else:
                #/     if (fi_out_valid) begin
                pass
            #/         `f"occ_reg_{occ}"`[fi_wr_addr] <= fi_out_data;
            #/     end
            #/ end
            pass
        #/

        # Read: address is RB beat within window (full-RB-width data)
        #/ wire [`OCC_REG_ADDR_W`-1:0] occ_rd_addr = ti_rb_addr;

        for occ in range(max_occasions):
            #/ reg [`OCC_REG_DATA_W`-1:0] `f"occ_rd_q_{occ}"`;
            pass

        #/ always @(posedge clk) begin
        #/     if (ti_sram_rd_en) begin
        for occ in range(max_occasions):
            #/     `f"occ_rd_q_{occ}"` <= `f"occ_reg_{occ}"`[occ_rd_addr];
            pass
        #/     end
        #/ end
        #/

        # ===========================================================
        # 2. Bank-select + unpack occasion register output (pre-FI)
        # ===========================================================
        N_BANKS_PRE_FI = RB_PARALLELISM * RE_GROUPS
        if N_BANKS_PRE_FI > 1:
            BANK_SEL_W_PRE_FI = max(math.ceil(math.log2(N_BANKS_PRE_FI)), 1)
            if RB_PARALLELISM > 1 and RE_GROUPS > 1:
                #/ wire [`BANK_SEL_W_PRE_FI`-1:0] occ_bank_sel_raw = ti_rb_within_beat * `RE_GROUPS` + ti_re_group;
                pass
            elif RB_PARALLELISM > 1:
                #/ wire [`BANK_SEL_W_PRE_FI`-1:0] occ_bank_sel_raw = ti_rb_within_beat;
                pass
            else:
                #/ wire [`BANK_SEL_W_PRE_FI`-1:0] occ_bank_sel_raw = ti_re_group;
                pass
            #/ wire [`BANK_SEL_W_PRE_FI`-1:0] occ_bank_sel;
            if ti_ctrl_graph is not None and 'occ_bank_sel' in ti_ctrl_graph.build_delay_table():
                _bs_delay = ti_ctrl_graph.build_delay_table()['occ_bank_sel']['delay']
            else:
                _bs_delay = 1
            ModuleDelay(DWT=BANK_SEL_W_PRE_FI, N_CLK=_bs_delay, IF_RST_N=False,
                        PORTS={'i_data': 'occ_bank_sel_raw', 'o_data': 'occ_bank_sel', 'i_clk': 'clk'})  # type: ignore
            for occ in range(max_occasions):
                #/ wire [`BANK_DATA_WIDTH`-1:0] `f"occ_rd_bank_{occ}"` = `f"occ_rd_q_{occ}"`[occ_bank_sel * `BANK_DATA_WIDTH` +: `BANK_DATA_WIDTH`];
                pass
        else:
            for occ in range(max_occasions):
                #/ wire [`BANK_DATA_WIDTH`-1:0] `f"occ_rd_bank_{occ}"` = `f"occ_rd_q_{occ}"`;
                pass

        for re_lane in range(TI_RE_PARALLELISM):
            lo_bit = re_lane * H_interp_f_DWT
            hi_bit = lo_bit + H_interp_f_DWT - 1
            for occ in range(max_occasions):
                #/ wire [`H_interp_f_DWT`-1:0] `f"ti_in_re{re_lane}_occ{occ}"` = `f"occ_rd_bank_{occ}"`[`hi_bit`:`lo_bit`];
                pass
        #/

    # ===========================================================
    # 3. TI core instances (TI_RE_PARALLELISM parallel lanes)
    # ===========================================================
    for re_lane in range(TI_RE_PARALLELISM):
        core_ports = {
            'clk': 'clk',
            'rst_n': 'rst_n',
        }

        # Connect occasion inputs
        for occ in range(max_occasions):
            core_ports[f'h_pilot_occ{occ}'] = f'ti_in_re{re_lane}_occ{occ}'

        # Runtime configuration selects the interpolation table/ROM bank.
        if needs_runtime_l0:
            core_ports['dmrs_typeA_pos_sel'] = 'dmrs_typeA_pos_sel'
        if needs_runtime_dbl:
            core_ports['is_double_dmrs'] = 'is_double_dmrs'
        if needs_runtime_nadd:
            core_ports['n_additional_dmrs'] = 'n_additional_dmrs'
        if needs_runtime_nsym:
            core_ports['pusch_symbol_length'] = 'pusch_symbol_length'

        # Connect outputs
        for sym in range(N_OUT_SYMS):
            core_out_name = f'ti_core_re{re_lane}_sym{sym}'
            core_ports[f'h_time_sym{sym}'] = core_out_name
            if time_interp_method == 'lmmse':
                #/ wire [`H_interp_f_DWT`-1:0] `core_out_name`;
                pass
            else:
                #/ wire [`H_interp_f_DWT`-1:0] `core_out_name`;
                pass

        if time_interp_method == 'nn':
            ModuleCORE_TIME_NN_INTERP(
                max_occasions=max_occasions,
                Qu_H=Qu_H_interp_f,
                dmrs_typeA_pos=dmrs_typeA_pos,
                is_double_dmrs=is_double_dmrs,
                additional_DMRS_range=additional_DMRS_range,
                num_symbols_range=num_symbols_range,
                PORTS=core_ports,  # type: ignore
            )
        elif time_interp_method == 'linear':
            ModuleCORE_TIME_LIN_INTERP(
                max_occasions=max_occasions,
                Qu_H=Qu_H_interp_f,
                dmrs_typeA_pos=dmrs_typeA_pos,
                is_double_dmrs=is_double_dmrs,
                additional_DMRS_range=additional_DMRS_range,
                num_symbols_range=num_symbols_range,
                PORTS=core_ports,  # type: ignore
            )
        elif time_interp_method == 'lmmse':
            if COEFF_SOURCE == 'SRAM':
                core_ports['coeff_wr_en'] = 'ti_coeff_wr_en'
                core_ports['coeff_wr_addr'] = 'ti_coeff_wr_addr'
                core_ports['coeff_wr_data'] = 'ti_coeff_wr_data'
            ModuleCORE_TIME_LMMSE_INTERP(
                max_occasions=max_occasions,
                Qu_H=Qu_H_interp_f,
                Qu_COEFF=Qu_TI_LMMSE_COEFF,
                LMMSE_REAL_COEFF=LMMSE_REAL_COEFF,
                dmrs_typeA_pos=dmrs_typeA_pos,
                is_double_dmrs=is_double_dmrs,
                additional_DMRS_range=additional_DMRS_range,
                num_symbols_range=num_symbols_range,
                W_coeffs=W_coeffs,
                f_d_norm=f_d_norm,
                COEFF_SOURCE=COEFF_SOURCE,
                PORTS=core_ports,  # type: ignore
            )
        else:
            raise ValueError(f"Invalid time_interp_method: {time_interp_method}")

    #/ 

    # ===========================================================
    # 4. Output: optional FxMatch truncation + renaming
    # ===========================================================
    # If H_interp_t_DWT < H_interp_f_DWT, we need truncation.
    # If equal, direct wire assignment.

    if H_interp_t_DWT == H_interp_f_DWT:
        for re_lane in range(TI_RE_PARALLELISM):
            for sym in range(N_OUT_SYMS):
                #/ assign `f"h_time_re{re_lane}_sym{sym}"` = `f"ti_core_re{re_lane}_sym{sym}"`;
                pass
    else:
        # FxMatch for output quantisation
        COMP_F = H_interp_f_DWT // 2
        COMP_T = H_interp_t_DWT // 2
        for re_lane in range(TI_RE_PARALLELISM):
            for sym in range(N_OUT_SYMS):
                # Truncate each component (real, imag) independently
                # Simple truncation: take MSBs
                #/ assign `f"h_time_re{re_lane}_sym{sym}"` = {`f"ti_core_re{re_lane}_sym{sym}"`[`H_interp_f_DWT - 1`:`H_interp_f_DWT - COMP_T`], `f"ti_core_re{re_lane}_sym{sym}"`[`COMP_F - 1`:`COMP_F - COMP_T`]};
                pass

    #/ 
    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleTIME_INTERP(
        antenna_port=0,
        max_occasions=3,
        max_num_RBs=273,
        RB_PARALLELISM=1,
        TI_RE_PARALLELISM=3,
        Qu_H_interp_f=QuType(12, 4, True),
        Qu_H_interp_t=QuType(12, 4, True),
        time_interp_method='nn',
        dmrs_typeA_pos='pos2',
        is_double_dmrs=False,
        additional_DMRS_range=[0, 2],
        num_symbols_range=[4, 14],
        LMMSE_REAL_COEFF=True,
        Qu_TI_LMMSE_COEFF=QuType(12, 11, True),
        n_additional_dmrs_fixed=2,
        f_d_norm=0.01,
        W_coeffs=None,
    )

    ModuleTIME_INTERP(
        antenna_port=0,
        max_occasions=3,
        max_num_RBs=273,
        RB_PARALLELISM=1,
        TI_RE_PARALLELISM=3,
        Qu_H_interp_f=QuType(12, 4, True),
        Qu_H_interp_t=QuType(12, 4, True),
        time_interp_method='nn',
        dmrs_typeA_pos='pos2',
        is_double_dmrs=False,
        additional_DMRS_range=[0, 2],
        num_symbols_range=[4, 14],
        LMMSE_REAL_COEFF=True,
        Qu_TI_LMMSE_COEFF=QuType(12, 11, True),
        n_additional_dmrs_fixed=2,
        f_d_norm=0.01,
        W_coeffs=None,
        has_pre_fi_buf=True,
        FI_RE_PARALLELISM=3,
        FI_WINDOW_SIZE=4,
    )
