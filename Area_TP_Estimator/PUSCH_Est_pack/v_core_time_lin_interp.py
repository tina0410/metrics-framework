###################################################################################################
# Module Name: CORE_TIME_LIN_INTERP
# Description: Linear time-domain interpolation core (per-RE instance).
#   For each target OFDM symbol, linearly interpolates between the two
#   bracketing DMRS occasions using a multiplier-free CSD shift-and-add
#   architecture.  Boundary symbols use nearest-neighbour fallback.
#
#   Reformulation -- eliminates all hardware multipliers:
#     h_out = h_R + alpha * diff,   diff = h_L - h_R   (diff shared per pair)
#
#   Architecture (3 layers):
#     Layer 1: Shared diff pool  -- 1 ModuleSub per unique occasion pair per component
#     Layer 2: CSD shift-and-add -- ModuleAdd/Sub chains, all N_CLK=0
#     Layer 3: Final add + ModuleDelay(N_CLK=1)  -- 1-clock output register
#
#   All complex planning is pre-computed in v_csd_helpers._build_csd_emission_plan(),
#   a pure-Python function with no pytv dependency.  The @convert body below is a
#   simple flat dispatcher (~50 lines) which avoids Pylance analysis lag.
#
#   Latency: 1 clock cycle.
#   Output ports: max(num_symbols_range) outputs (not hard-coded to 14).
#
# Author: Auto-generated
# Date: 2025
# Version: V0.3.0
# Dependency Modules: ModuleSub, ModuleAdd, ModuleDelay
###################################################################################################
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import List, Literal
from basic_modules import QuType, QuMode, OfMode, ModuleAdd, ModuleSub, ModuleDelay
from v_csd_helpers import (
    FRAC_BITS,
    _build_all_lin_tables,
    _build_csd_emission_plan,
)
from delay_budget import DelayBudget, cost_adder, DEFAULT_BUDGET
from helpers.config_space import expand_config_space


def time_lin_pipeline_depth() -> int:
    """Pipeline depth of the time linear interpolation core (always 1).

    Layer 1: shared diff pool (Sub, N_CLK=0)
    Layer 2: CSD shift-add chain (Add/Sub, N_CLK=0)
    Layer 3: output register (N_CLK=1)
    """
    # TODO: CSD shift-add chain needs timing analysis. When data widths are high, registers should be inserted.
    return 1


@convert
def ModuleCORE_TIME_LIN_INTERP(max_occasions: int, Qu_H: QuType, dmrs_typeA_pos: str, is_double_dmrs: bool | Literal["Hybrid"], additional_DMRS_range: List[int], num_symbols_range: List[int]) -> None:
    """
    Linear Time-Domain Interpolation Core -- single RE lane.

    Multiplier-free shift-and-add architecture.  Output port count is
    ``max(num_symbols_range)``; no ``max_pusch_symbols`` parameter needed.

    Latency: 1 clock cycle.

    :param max_occasions: 3
    :param Qu_H: QuType(12, 4, True)
        Per-component QuType for H estimates. Complex wire width = 2 * Qu_H.DWT.
    :param dmrs_typeA_pos: 'pos2'
    :param is_double_dmrs: "Hybrid"
    :param additional_DMRS_range: [1]
    :param num_symbols_range: [8]
    """
    # Derive complex wire width from per-component QuType
    H_DWT = 2 * Qu_H.DWT
    # ---- Resolve config space ----
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

    all_tables = _build_all_lin_tables(
        dmrs_typeA_pos_options=l0_options,
        is_double_dmrs_options=dbl_options,
        additional_DMRS_range=additional_DMRS_range,
        num_symbols_range=sym_list,
        n_out_syms=N_OUT_SYMS,
    )

    # ---- Deduplicate tables ----
    unique_tables = []
    table_to_idx  = {}
    for key, tbl in all_tables.items():
        tbl_tuple = tuple((a, b, c) for a, b, c in tbl)
        if tbl_tuple not in table_to_idx:
            table_to_idx[tbl_tuple] = len(unique_tables)
            unique_tables.append(tbl_tuple)

    single_table = (len(unique_tables) == 1)
    NUM_TABLES   = len(unique_tables)
    TBL_IDX_W   = max(math.ceil(math.log2(NUM_TABLES)), 1) if NUM_TABLES > 1 else 1

    # ---- QuType definitions ----
    COMP_DWT = H_DWT // 2
    FRAC     = Qu_H.FRAC
    Qu_comp  = QuType(COMP_DWT,     FRAC, True)
    Qu_diff  = QuType(COMP_DWT + 1, FRAC, True)
    scale    = (1 << FRAC_BITS)

    # =========================================================================
    # DelayBudget analysis — time linear interpolation
    # =========================================================================
    # Worst-case: Sub(diff) + CSD shift-add chain (2-3 Add/Sub ops) + final Add
    # All N_CLK=0, then 1 output register.
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    budget.add_comb(cost_adder(Qu_diff.DWT), tag="sub_diff")
    budget.add_comb(cost_adder(Qu_diff.DWT + FRAC_BITS), tag="csd_shift_add")
    budget.add_comb(cost_adder(COMP_DWT), tag="final_add_hR_plus_scaled")
    budget.add_register(1, tag="output_reg")
    TIME_LIN_MIN_DEPTH = budget.pipeline_depth  # == 1

    # ================================================================
    # Module Port Declaration
    # ================================================================
    #/ `timescale 1ns / 1ps
    #/ module CORE_TIME_LIN_INTERP (
    #/     input clk,
    #/     input rst_n,

    for occ in range(max_occasions):
        #/ input  [`H_DWT`-1:0] `f"h_pilot_occ{occ}"`,
        pass

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

    for sym in range(N_OUT_SYMS):
        if sym < N_OUT_SYMS - 1:
            #/ output [`H_DWT`-1:0] `f"h_time_sym{sym}"`,
            pass
        else:
            #/ output [`H_DWT`-1:0] `f"h_time_sym{sym}"`
            pass

    #/ );
    #/ 

    # ================================================================
    # Table selection logic
    # ================================================================
    if not single_table:
        #/ reg [`TBL_IDX_W`-1:0] tbl_idx;
        #/ always @(*) begin
        #/     tbl_idx = `TBL_IDX_W`'d0;

        config_map = []
        for key, tbl in all_tables.items():
            tbl_tuple = tuple((a, b, c) for a, b, c in tbl)
            idx = table_to_idx[tbl_tuple]
            config_map.append((key, idx))

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
        #/ end else begin
        #/     tbl_idx = `TBL_IDX_W`'d0;
        #/ end
        #/ end
        pass

    # ================================================================
    # Split pilot inputs into real / imag components
    # ================================================================
    for occ in range(max_occasions):
        #/ wire [`COMP_DWT`-1:0] `f"occ{occ}_re"` = `f"h_pilot_occ{occ}"`[`COMP_DWT - 1`:0];
        #/ wire [`COMP_DWT`-1:0] `f"occ{occ}_im"` = `f"h_pilot_occ{occ}"`[`H_DWT - 1`:`COMP_DWT`];
        pass
    #/ 

    # ================================================================
    # Layer 1: Shared diff pool
    # ================================================================
    all_pairs = set()
    for t_idx in range(NUM_TABLES):
        for sym_idx in range(N_OUT_SYMS):
            occ_L, occ_R, alpha_fix = unique_tables[t_idx][sym_idx]
            if occ_L != occ_R:
                all_pairs.add((occ_L, occ_R))
    all_pairs = sorted(all_pairs)

    #/ // ---- Layer 1: shared diff pool ----
    for (oL, oR) in all_pairs:
        for part in ['re', 'im']:
            diff_w   = f"diff_{oL}_{oR}_{part}"
            h_l_name = f"occ{oL}_{part}"
            h_r_name = f"occ{oR}_{part}"
            #/ wire [`Qu_diff.DWT`-1:0] `diff_w`;
            ModuleSub(QU_IN_1=Qu_comp, QU_IN_2=Qu_comp, QU_OUT=Qu_diff, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': h_l_name, 'i_data_2': h_r_name, 'o_data': diff_w},)
    #/ 

    # ================================================================
    # Layers 2+3: dispatch pre-computed emission plan
    # ================================================================
    emission_plan = _build_csd_emission_plan(
        unique_tables=unique_tables,
        NUM_TABLES=NUM_TABLES,
        single_table=single_table,
        N_OUT_SYMS=N_OUT_SYMS,
        Qu_comp=Qu_comp,
        Qu_diff=Qu_diff,
        H_DWT=H_DWT,
        TBL_IDX_W=TBL_IDX_W,
        scale=scale,
    )

    #/ // ---- Layers 2+3: per-symbol interpolation ----
    for task in emission_plan:
        ttype = task[0]
        if ttype == 'vlines':
            _, vlines_list = task
            for line in vlines_list:
                #/ `line`
                pass
        elif ttype == 'mod_sub':
            _, Qu_in1, Qu_in2, Qu_out, i1, i2, out = task
            ModuleSub(QU_IN_1=Qu_in1, QU_IN_2=Qu_in2, QU_OUT=Qu_out, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': i1, 'i_data_2': i2, 'o_data': out},)
        elif ttype == 'mod_add':
            _, Qu_in1, Qu_in2, Qu_out, i1, i2, out = task
            ModuleAdd(QU_IN_1=Qu_in1, QU_IN_2=Qu_in2, QU_OUT=Qu_out, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': i1, 'i_data_2': i2, 'o_data': out},)
        elif ttype == 'mod_delay':
            _, DWT, data_in, data_out = task
            ModuleDelay(DWT=DWT, N_CLK=1, IF_RST_N=False, PORTS={'i_data': data_in, 'o_data': data_out, 'i_clk': 'clk'},)

    #/ 
    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleCORE_TIME_LIN_INTERP(
        max_occasions=3,
        Qu_H=QuType(12, 4, True),
        dmrs_typeA_pos='pos2',
        is_double_dmrs=False,
        additional_DMRS_range=[0, 2],
        num_symbols_range=[4, 14],
    )
