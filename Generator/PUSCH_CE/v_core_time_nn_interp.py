###################################################################################################
# Module Name: CORE_TIME_NN_INTERP
# Description: Nearest-neighbor time-domain interpolation core (per-RE instance).
#   Given channel estimates from ``max_occasions`` DMRS occasions, selects the
#   nearest occasion for each of ``max_pusch_symbols`` target OFDM symbols.
#
#   Compile-time:
#     For every supported (n_additional_dmrs, pusch_symbol_length) combination,
#     a ``nearest_occ[0..N_sym-1]`` LUT is pre-computed from DMRS_POSITION_MAP.
#     When only one config exists, the LUT is hardwired; otherwise a runtime MUX
#     selects between tables using ``n_additional_dmrs`` and ``pusch_symbol_length``.
#
#   Hardware:
#     max_pusch_symbols parallel MUXes, each selecting 1 of max_occasions inputs.
#     Latency: 1 clock cycle (registered output).
#
# Author: Auto-generated
# Date: 2025
# Version: V0.1.0
# Dependency Modules: None (leaf combinational + register)
###################################################################################################
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import List, Literal
from basic_modules import QuType, ModuleDelay
from v_pilot_symbol_detection import DMRS_POSITION_MAP
from delay_budget import DelayBudget, COST_MUX_2TO1, DEFAULT_BUDGET
from helpers.config_space import expand_config_space


# =============================================================================
# Python helper: build nearest-occasion table for all target symbols
# =============================================================================

def _build_nearest_occ_table(
    *,
    dmrs_typeA_pos: int,         # resolved l0 (2 or 3)
    is_double_dmrs: bool,
    n_additional_dmrs: int,
    pusch_symbol_length: int,
) -> list[int]:
    """
    For each target OFDM symbol index (0 .. pusch_symbol_length-1), determine
    which DMRS *occasion* index (0-based) has the nearest pilot symbol.

    For double-DMRS, each occasion spans 2 consecutive symbols; we use the
    midpoint ``(pos + pos+1) / 2 = pos + 0.5`` as the effective pilot position.

    Returns a list of length ``pusch_symbol_length`` with values in
    ``[0, num_occasions-1]``.
    """
    symbol_type = 'double' if is_double_dmrs else 'single'
    key = ('A', symbol_type, n_additional_dmrs)
    entries = DMRS_POSITION_MAP.get(key, [])

    # Find position list for this duration
    pos_raw = [0]  # fallback
    for dur_range, pos_list in entries:
        if pusch_symbol_length in dur_range:
            pos_raw = pos_list
            break

    # Resolve positions: 0 → l0
    l0 = dmrs_typeA_pos
    positions = [l0 if p == 0 else p for p in pos_raw]
    num_occasions = len(positions)

    # Effective pilot symbol position per occasion
    if is_double_dmrs:
        # Midpoint of the 2-symbol pair
        eff_pos = [p + 0.5 for p in positions]
    else:
        eff_pos = [float(p) for p in positions]

    # For each target symbol, find nearest occasion
    nearest = []
    for sym in range(pusch_symbol_length):
        best_occ = 0
        best_dist = abs(sym - eff_pos[0])
        for occ_idx in range(1, num_occasions):
            d = abs(sym - eff_pos[occ_idx])
            if d < best_dist:
                best_dist = d
                best_occ = occ_idx
        nearest.append(best_occ)

    return nearest


def _build_all_nn_tables(
    *,
    dmrs_typeA_pos_options: list[int],    # e.g. [2] or [2, 3]
    is_double_dmrs_options: list[bool],   # e.g. [False] or [False, True]
    additional_DMRS_range: list[int],     # e.g. [0, 2]
    num_symbols_range: list[int],         # e.g. [4, 14] or range(4, 15)
    n_out_syms: int,
) -> dict:
    """
    Build nearest-occ tables for all valid (l0, double, n_add, n_sym) combos.
    Returns dict keyed by (l0, double, n_add, n_sym) → list[int] of length n_sym.
    """
    tables = {}
    for l0 in dmrs_typeA_pos_options:
        for dbl in is_double_dmrs_options:
            for n_add in additional_DMRS_range:
                for n_sym in num_symbols_range:
                    tbl = _build_nearest_occ_table(
                        dmrs_typeA_pos=l0,
                        is_double_dmrs=dbl,
                        n_additional_dmrs=n_add,
                        pusch_symbol_length=n_sym,
                    )
                    # Pad to n_out_syms with last valid value
                    while len(tbl) < n_out_syms:
                        tbl.append(tbl[-1] if tbl else 0)
                    tables[(l0, dbl, n_add, n_sym)] = tbl
    return tables


def time_nn_pipeline_depth() -> int:
    """Pipeline depth of the time NN interpolation core (always 1)."""
    return 1


@convert
def ModuleCORE_TIME_NN_INTERP(max_occasions: int, Qu_H: QuType, dmrs_typeA_pos: str, is_double_dmrs: bool | Literal["Hybrid"], additional_DMRS_range: List[int], num_symbols_range: List[int]) -> None:
    """
    Nearest-Neighbor Time-Domain Interpolation Core (single RE lane).

    For each of ``max_pusch_symbols`` target symbols, selects the channel
    estimate from the nearest DMRS occasion via a compile-time LUT + MUX.

    **Input**: ``max_occasions`` pilot values (complex, ``2*Qu_H.DWT`` bits each).
    **Output**: ``max_pusch_symbols`` interpolated values (complex, same width).
    **Latency**: 1 clock cycle (registered output).

    :param max_occasions: 3
    :type max_occasions: int
    :param Qu_H: QuType(12, 4, True)
        Per-component QuType for H estimates. Complex wire width = 2 * Qu_H.DWT.
    :type Qu_H: QuType
    :param dmrs_typeA_pos: 'pos2'
    :type dmrs_typeA_pos: str
    :param is_double_dmrs: False
    :type is_double_dmrs: bool | Literal["Hybrid"]
    :param additional_DMRS_range: [0, 2]
    :type additional_DMRS_range: List[int]
    :param num_symbols_range: [4, 14]
    :type num_symbols_range: List[int]
    """
    # Derive complex wire width from per-component QuType
    H_DWT = 2 * Qu_H.DWT
    # Resolve compile-time config space
    cs = expand_config_space(dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range)
    l0_options = cs.l0_options
    dbl_options = cs.dbl_options
    N_OUT_SYMS = cs.N_OUT_SYMS
    sym_list = cs.sym_list
    n_add_max = cs.n_add_max
    n_add_width = cs.n_add_width
    needs_runtime_l0 = cs.needs_runtime_l0
    needs_runtime_dbl = cs.needs_runtime_dbl
    needs_runtime_nadd = cs.needs_runtime_nadd
    needs_runtime_nsym = cs.needs_runtime_nsym

    OCC_SEL_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
    sym_width = max(math.ceil(math.log2(N_OUT_SYMS + 1)), 1)

    # Build all possible NN tables
    all_tables = _build_all_nn_tables(
        dmrs_typeA_pos_options=l0_options,
        is_double_dmrs_options=dbl_options,
        additional_DMRS_range=additional_DMRS_range,
        num_symbols_range=sym_list,
        n_out_syms=N_OUT_SYMS,
    )

    # Deduplicate tables: find unique tables and assign indices
    unique_tables = []
    table_to_idx = {}
    for key, tbl in all_tables.items():
        tbl_tuple = tuple(tbl)
        if tbl_tuple not in table_to_idx:
            table_to_idx[tbl_tuple] = len(unique_tables)
            unique_tables.append(tbl_tuple)

    single_table = (len(unique_tables) == 1)

    # =========================================================================
    # DelayBudget analysis — time NN interpolation
    # =========================================================================
    # MUX-only combinational path + 1 registered output → fixed depth = 1.
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    budget.add_comb(COST_MUX_2TO1, tag="nn_occasion_mux")
    budget.add_register(1, tag="output_reg")
    TIME_NN_DEPTH = budget.pipeline_depth  # == 1

    #/ `timescale 1ns / 1ps
    #/ module CORE_TIME_NN_INTERP (
    #/     input clk,
    #/     input rst_n,
    #/     

    # Pilot occasion inputs
    for occ in range(max_occasions):
        #/ input  [`H_DWT`-1:0]    `f"h_pilot_occ{occ}"`,
        pass

    # Runtime config inputs (only when needed)
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

    # Outputs: one per target symbol
    for sym in range(N_OUT_SYMS):
        if sym < N_OUT_SYMS - 1:
            #/ output [`H_DWT`-1:0] `f"h_time_sym{sym}"`,
            pass
        else:
            #/ output [`H_DWT`-1:0] `f"h_time_sym{sym}"`
            pass

    #/ );
    #/ 

    if single_table:
        # ---- Hardwired single table: no runtime mux needed ----
        the_table = unique_tables[0]
        #/ // Single NN table (no runtime selection needed)
        # Build concatenated input from selected occasions
        sel_parts = []
        for sym in reversed(range(N_OUT_SYMS)):
            occ_idx = the_table[sym]
            sel_parts.append(f"h_pilot_occ{occ_idx}")
        concat_in = "{" + ", ".join(sel_parts) + "}"
        TOTAL_W = N_OUT_SYMS * H_DWT
        #/ wire [`TOTAL_W`-1:0] nn_concat_in = `concat_in`;
        #/ wire [`TOTAL_W`-1:0] nn_concat_out;
        ModuleDelay(
            DWT=TOTAL_W, N_CLK=1, IF_RST_N=False,
            PORTS={'i_data': 'nn_concat_in', 'o_data': 'nn_concat_out', 'i_clk': 'clk'}  # type: ignore
        )
        for sym in range(N_OUT_SYMS):
            lo = sym * H_DWT
            hi = lo + H_DWT - 1
            #/ assign `f"h_time_sym{sym}"` = nn_concat_out[`hi`:`lo`];
            pass
        pass
    else:
        # ---- Multiple tables: encode as ROM + runtime case/mux ----
        # Assign a config index for each (l0, dbl, n_add, n_sym) combo
        # and generate a casez block.

        # We generate per-symbol nearest-occasion wires selected at runtime
        # Strategy: for each symbol, emit a combinational mux on the config
        # that selects the occasion index, then register the selected pilot.

        # Encode unique tables into per-symbol ROM
        # For each symbol position, create a table-select → occasion wire
        NUM_TABLES = len(unique_tables)
        TBL_IDX_W = max(math.ceil(math.log2(NUM_TABLES + 1)), 1) if NUM_TABLES > 1 else 1

        #/ // ---- NN table select logic (combinational) ----
        #/ reg [`TBL_IDX_W`-1:0] tbl_idx;

        # Build mapping from runtime config → table index
        # We use a case statement covering all (l0, dbl, n_add, n_sym) combos
        config_map = []
        for key, tbl in all_tables.items():
            tbl_tuple = tuple(tbl)
            idx = table_to_idx[tbl_tuple]
            config_map.append((key, idx))

        #/ always @(*) begin
        #/     tbl_idx = `TBL_IDX_W`'d0;

        first = True
        for (l0, dbl, n_add, n_sym), idx in config_map:
            conditions = []
            if needs_runtime_l0:
                sel_val = 0 if l0 == 2 else 1
                conditions.append(f"dmrs_typeA_pos_sel == 1'b{sel_val}")
            if needs_runtime_dbl:
                conditions.append(f"is_double_dmrs == 1'b{1 if dbl else 0}")
            if needs_runtime_nadd:
                conditions.append(f"n_additional_dmrs == {n_add_width}'d{n_add}")
            if needs_runtime_nsym:
                conditions.append(f"pusch_symbol_length == 4'd{n_sym}")

            if conditions:
                cond_str = " && ".join(conditions)
                if first:
                    #/ if (`cond_str`) begin
                    first = False
                else:
                    #/ end else if (`cond_str`) begin
                    pass
                #/ tbl_idx = `TBL_IDX_W`'d`idx`;
                pass

        #/ end
        #/ end
        #/ 

        #/ // ---- Per-symbol MUX: occasion selection ----
        for sym in range(N_OUT_SYMS):
            # Build per-table occasion index for this symbol
            occ_per_table = [unique_tables[t][sym] for t in range(NUM_TABLES)]
            # Check if all the same → simplify
            if len(set(occ_per_table)) == 1:
                occ = occ_per_table[0]
                #/ wire [`H_DWT`-1:0] `f"nn_sel_sym{sym}"` = `f"h_pilot_occ{occ}"`;
                pass
            else:
                #/ reg [`H_DWT`-1:0] `f"nn_sel_sym{sym}"`;
                #/ always @(*) begin
                #/     case (tbl_idx)
                for t_idx in range(NUM_TABLES):
                    occ = occ_per_table[t_idx]
                    #/ `TBL_IDX_W`'d`t_idx`: `f"nn_sel_sym{sym}"` = `f"h_pilot_occ{occ}"`;
                    pass
                #/ default: `f"nn_sel_sym{sym}"` = `f"h_pilot_occ0"`;
                #/ endcase
                #/ end
                pass

        #/ // ---- Registered output (1-clk latency) ----
        # Concatenate all selected symbols into wide bus for single ModuleDelay
        sel_parts_mt = []
        for sym in reversed(range(N_OUT_SYMS)):
            sel_parts_mt.append(f"nn_sel_sym{sym}")
        concat_mt_in = "{" + ", ".join(sel_parts_mt) + "}"
        TOTAL_W_MT = N_OUT_SYMS * H_DWT
        #/ wire [`TOTAL_W_MT`-1:0] nn_mt_concat_in = `concat_mt_in`;
        #/ wire [`TOTAL_W_MT`-1:0] nn_mt_concat_out;
        ModuleDelay(
            DWT=TOTAL_W_MT, N_CLK=1, IF_RST_N=False,
            PORTS={'i_data': 'nn_mt_concat_in', 'o_data': 'nn_mt_concat_out', 'i_clk': 'clk'}  # type: ignore
        )
        for sym in range(N_OUT_SYMS):
            lo = sym * H_DWT
            hi = lo + H_DWT - 1
            #/ assign `f"h_time_sym{sym}"` = nn_mt_concat_out[`hi`:`lo`];
            pass
        pass

    #/ 
    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleCORE_TIME_NN_INTERP(
        max_occasions=3,
        Qu_H=QuType(12, 4, True),
        dmrs_typeA_pos='pos2',
        is_double_dmrs=False,
        additional_DMRS_range=[0, 2],
        num_symbols_range=[4, 14],
    )
