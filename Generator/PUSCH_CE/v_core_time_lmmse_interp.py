import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import List, Literal, Optional
from basic_modules import (
    QuType, QuMode, OfMode,
    ModuleMul, ModuleAdd, ModuleDelay, ModuleFxMatch, ModuleComplexMul,
)
from basic_modules.AdderTree import ModuleAdderTree
from delay_budget import DelayBudget, COST_MUL_8B, COST_ADDER_8B, DEFAULT_BUDGET
from v_pilot_symbol_detection import DMRS_POSITION_MAP
from lmmse_matrix_gen import compute_time_lmmse_W, get_pilot_symbol_positions, quantise_real
from helpers.config_space import expand_config_space


# =============================================================================
# Concrete multiplier timing (exported for TI_CTRL and FSM)
# =============================================================================
TI_LMMSE_MULTIPLIER_LATENCY = 1


def ti_lmmse_multiplier_latency() -> int:
    """Return the intrinsic latency of the concrete TI multiplier datapath."""

    return TI_LMMSE_MULTIPLIER_LATENCY


def time_lmmse_pipeline_depth(max_occasions: int) -> int:
    """Compute total pipeline latency of the time-domain LMMSE core.

    Full-parallel:
        depth = intrinsic multiplier latency + TREE_DEPTH + 1
    """
    tree_depth = math.ceil(math.log2(max(max_occasions, 1))) if max_occasions > 1 else 0
    return ti_lmmse_multiplier_latency() + tree_depth + 1


# =============================================================================
# Module
# =============================================================================
@convert
def ModuleCORE_TIME_LMMSE_INTERP(max_occasions: int, Qu_H: QuType, Qu_COEFF: QuType, LMMSE_REAL_COEFF: bool, dmrs_typeA_pos: str, is_double_dmrs: bool | Literal["Hybrid"], additional_DMRS_range: List[int], num_symbols_range: List[int], W_coeffs: Optional[List[List[float]]], f_d_norm: float, COEFF_SOURCE: Literal['ROM', 'SRAM'] = 'ROM') -> None:
    """
    LMMSE Time-Domain Interpolation Core (single RE lane).

    Fully-parallel design: processes all symbols per clock.

    **Inputs**: ``max_occasions`` pilot channel estimates (complex, ``2*Qu_H.DWT`` bits).
    **Outputs**: ``max(num_symbols_range)`` interpolated values (complex, same width).
    **Latency**: intrinsic multiplier latency + TREE_DEPTH + 1 clocks.

    :param max_occasions: 3
    :param Qu_H: QuType(12, 4, True)
        Per-component QuType for H estimates. Complex wire width = 2 * Qu_H.DWT.
    :param Qu_COEFF: QuType(12, 11, True)
        QuType for LMMSE coefficients (signed, DWT bits incl. sign).
    :param LMMSE_REAL_COEFF: True
        If True, W has real-only coefficients (Jakes). Halves multiplier count.
    :param dmrs_typeA_pos: 'pos2'
    :param is_double_dmrs: False
    :param additional_DMRS_range: [0, 1, 2]
    :param num_symbols_range: [12, 13, 14]
    :param W_coeffs: None
        Pre-computed W matrix [N_sym × N_occ]. If None, auto-generated.
    :param f_d_norm: 0.01
    :param COEFF_SOURCE: 'ROM'
        'ROM' for hardwired coefficients, 'SRAM' for register-file loaded via write port.
    """
    MUL_LATENCY = ti_lmmse_multiplier_latency()

    # Derive raw widths from QuType
    H_DWT = 2 * Qu_H.DWT
    H_FRAC = Qu_H.FRAC
    COEFF_DWT = Qu_COEFF.DWT

    # ---- Resolve runtime configuration space and coefficient banks ----
    cs = expand_config_space(
        dmrs_typeA_pos,
        is_double_dmrs,
        additional_DMRS_range,
        num_symbols_range,
    )
    N_OUT_SYMS = cs.N_OUT_SYMS
    n_add_width = cs.n_add_width
    needs_runtime_l0 = cs.needs_runtime_l0
    needs_runtime_dbl = cs.needs_runtime_dbl
    needs_runtime_nadd = cs.needs_runtime_nadd
    needs_runtime_nsym = cs.needs_runtime_nsym
    COEFF_FRAC = COEFF_DWT - 1

    config_keys = [
        (l0, dbl, n_add, n_sym)
        for l0 in cs.l0_options
        for dbl in cs.dbl_options
        for n_add in additional_DMRS_range
        for n_sym in cs.sym_list
    ]
    W_q_by_config = {}
    if COEFF_SOURCE == 'ROM':
        if W_coeffs is not None and len(config_keys) != 1:
            raise ValueError("Runtime-selectable LMMSE ROM cannot use one W_coeffs override")
        for key in config_keys:
            l0, dbl, n_add, n_sym = key
            pilot_pos = get_pilot_symbol_positions(l0, dbl, n_add, n_sym)
            n_occ = len(pilot_pos)
            assert n_occ <= max_occasions, (
                f"num_occasions={n_occ} exceeds max_occasions={max_occasions}"
            )
            if W_coeffs is not None:
                W = W_coeffs
                assert len(W) == n_sym and len(W[0]) == n_occ
            else:
                W = compute_time_lmmse_W(pilot_pos, n_sym, f_d_norm)
            W_q_by_config[key] = [
                [
                    quantise_real(
                        W[s][j].real if isinstance(W[s][j], complex) else W[s][j],
                        COEFF_FRAC,
                        COEFF_DWT,
                    ) if s < n_sym and j < n_occ else 0
                    for j in range(max_occasions)
                ]
                for s in range(N_OUT_SYMS)
            ]

    # SRAM mode dimensions
    TOTAL_COEFF = N_OUT_SYMS * max_occasions
    COEFF_ADDR_W = max(math.ceil(math.log2(TOTAL_COEFF)), 1) if TOTAL_COEFF > 1 else 1

    # Derived widths
    COMP_DWT = H_DWT // 2           # per-component (real or imag)
    PROD_DWT = COMP_DWT + COEFF_DWT
    PROD_FRAC = H_FRAC + COEFF_FRAC  # input_frac + coeff_frac
    ACC_GUARD = math.ceil(math.log2(max(max_occasions, 1))) if max_occasions > 1 else 0
    ACC_DWT = PROD_DWT + ACC_GUARD
    ACC_FRAC = PROD_FRAC

    QU_PILOT_COMP = QuType(COMP_DWT, H_FRAC, True)
    QU_COEFF = QuType(COEFF_DWT, COEFF_FRAC, True)
    QU_PROD = QuType(PROD_DWT, PROD_FRAC, True)
    QU_ACC = QuType(ACC_DWT, ACC_FRAC, True)
    QU_OUT_COMP = QuType(COMP_DWT, H_FRAC, True)

    TREE_DEPTH = math.ceil(math.log2(max(max_occasions, 1))) if max_occasions > 1 else 0
    TOTAL_LATENCY = time_lmmse_pipeline_depth(max_occasions)

    # ---- Module declaration ----
    #/ `timescale 1ns / 1ps
    #/ module CORE_TIME_LMMSE_INTERP (
    #/     input clk,
    #/     input rst_n,
    if COEFF_SOURCE == 'SRAM':
        #/ input                      coeff_wr_en,
        #/ input [`COEFF_ADDR_W`-1:0] coeff_wr_addr,
        #/ input [`COEFF_DWT`-1:0]    coeff_wr_data,
        pass

    for occ in range(max_occasions):
        #/ input  [`H_DWT`-1:0]    `f"h_pilot_occ{occ}"`,
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

    # ---- SRAM mode: coefficient register file ----
    if COEFF_SOURCE == 'SRAM':
        #/ // ===== Coefficient register file =====
        #/ reg [`COEFF_DWT`-1:0] w_reg [0:`TOTAL_COEFF - 1`];
        #/ always @(posedge clk) begin
        #/     if (coeff_wr_en) begin
        #/         w_reg[coeff_wr_addr] <= coeff_wr_data;
        #/     end
        #/ end
        #/ 
        pass

    # ---- Input component extraction ----
    for occ in range(max_occasions):
        #/ wire [`COMP_DWT`-1:0] `f"h_re_{occ}"` = `f"h_pilot_occ{occ}"`[`COMP_DWT`-1:0];
        #/ wire [`COMP_DWT`-1:0] `f"h_im_{occ}"` = `f"h_pilot_occ{occ}"`[`H_DWT`-1:`COMP_DWT`];
        pass
    #/

    if LMMSE_REAL_COEFF:
        #/ // ========== LMMSE Real-Coefficient Mode ==========
        #/ 
        pass

        # ============================================================
        # Full-parallel path: all symbols instantiated in parallel
        # ============================================================
        for sym in range(N_OUT_SYMS):
                #/ // ---- Symbol `sym` ----
                pass

                # --- Coefficient source ---
                for j in range(max_occasions):
                    if COEFF_SOURCE == 'ROM':
                        if len(config_keys) == 1:
                            w_val = W_q_by_config[config_keys[0]][sym][j]
                            w_bits = w_val & ((1 << COEFF_DWT) - 1)
                            #/ wire [`COEFF_DWT`-1:0] `f"w_s{sym}_j{j}"` = `COEFF_DWT`'d`w_bits`;
                            pass
                        else:
                            #/ reg [`COEFF_DWT`-1:0] `f"w_s{sym}_j{j}"`;
                            #/ always @(*) begin
                            #/     `f"w_s{sym}_j{j}"` = `COEFF_DWT`'d0;
                            first_cfg = True
                            for l0, dbl, n_add, n_sym in config_keys:
                                conditions = []
                                if needs_runtime_l0:
                                    conditions.append(
                                        f"dmrs_typeA_pos_sel == 1'b{0 if l0 == 2 else 1}"
                                    )
                                if needs_runtime_dbl:
                                    conditions.append(
                                        f"is_double_dmrs == 1'b{1 if dbl else 0}"
                                    )
                                if needs_runtime_nadd:
                                    conditions.append(
                                        f"n_additional_dmrs == {n_add_width}'d{n_add}"
                                    )
                                if needs_runtime_nsym:
                                    conditions.append(
                                        f"pusch_symbol_length == 4'd{n_sym}"
                                    )
                                cond_str = " && ".join(conditions)
                                if first_cfg:
                                    #/ if (`cond_str`) begin
                                    first_cfg = False
                                else:
                                    #/ end else if (`cond_str`) begin
                                    pass
                                w_val = W_q_by_config[(l0, dbl, n_add, n_sym)][sym][j]
                                w_bits = w_val & ((1 << COEFF_DWT) - 1)
                                #/ `f"w_s{sym}_j{j}"` = `COEFF_DWT`'d`w_bits`;
                            #/ end
                            #/ end
                            pass
                    else:
                        flat_idx = sym * max_occasions + j
                        #/ wire [`COEFF_DWT`-1:0] `f"w_s{sym}_j{j}"` = w_reg[`flat_idx`];
                        pass

                # --- Multiplier stage ---
                for j in range(max_occasions):
                    prod_re_name = f"prod_re_s{sym}_j{j}"
                    prod_im_name = f"prod_im_s{sym}_j{j}"
                    #/ wire [`QU_PROD.DWT`-1:0] `prod_re_name`;
                    #/ wire [`QU_PROD.DWT`-1:0] `prod_im_name`;

                    mul_ports_re = {
                        'i_data_1': f"h_re_{j}",
                        'i_data_2': f"w_s{sym}_j{j}",
                        'o_data': prod_re_name,
                    }
                    mul_ports_im = {
                        'i_data_1': f"h_im_{j}",
                        'i_data_2': f"w_s{sym}_j{j}",
                        'o_data': prod_im_name,
                    }
                    if MUL_LATENCY > 0:
                        mul_ports_re['i_clk'] = 'clk'
                        mul_ports_im['i_clk'] = 'clk'
                        mul_ports_re['i_rst_n'] = 'rst_n'
                        mul_ports_im['i_rst_n'] = 'rst_n'

                    ModuleMul(QU_IN_1=QU_PILOT_COMP, QU_IN_2=QU_COEFF, QU_OUT=QU_PROD, N_CLK=MUL_LATENCY, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=True, PORTS=mul_ports_re)
                    ModuleMul(QU_IN_1=QU_PILOT_COMP, QU_IN_2=QU_COEFF, QU_OUT=QU_PROD, N_CLK=MUL_LATENCY, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=True, PORTS=mul_ports_im)

                # --- Adder tree stage ---
                if max_occasions == 1:
                    #/ wire [`QU_PROD.DWT`-1:0] `f"sum_re_s{sym}"` = `f"prod_re_s{sym}_j0"`;
                    #/ wire [`QU_PROD.DWT`-1:0] `f"sum_im_s{sym}"` = `f"prod_im_s{sym}_j0"`;
                    QU_SUM = QU_PROD
                else:
                    re_parts = [f"prod_re_s{sym}_j{j}" for j in range(max_occasions)]
                    im_parts = [f"prod_im_s{sym}_j{j}" for j in range(max_occasions)]
                    re_concat = "{" + ", ".join(reversed(re_parts)) + "}"
                    im_concat = "{" + ", ".join(reversed(im_parts)) + "}"
                    #/ wire [`QU_PROD.DWT * max_occasions`-1:0] `f"tree_re_in_s{sym}"` = `re_concat`;
                    #/ wire [`QU_PROD.DWT * max_occasions`-1:0] `f"tree_im_in_s{sym}"` = `im_concat`;

                    #/ wire [`QU_ACC.DWT`-1:0] `f"sum_re_s{sym}"`;
                    #/ wire [`QU_ACC.DWT`-1:0] `f"sum_im_s{sym}"`;

                    tree_ports_re = {
                        'i_data': f"tree_re_in_s{sym}",
                        'o_data': f"sum_re_s{sym}",
                    }
                    tree_ports_im = {
                        'i_data': f"tree_im_in_s{sym}",
                        'o_data': f"sum_im_s{sym}",
                    }
                    if TREE_DEPTH > 0:
                        tree_ports_re['i_clk'] = 'clk'
                        tree_ports_im['i_clk'] = 'clk'
                        tree_ports_re['i_rst_n'] = 'rst_n'
                        tree_ports_im['i_rst_n'] = 'rst_n'

                    ModuleAdderTree(QU_IN=QU_PROD, QU_OUT=QU_ACC, N_PIPELINES=TREE_DEPTH, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=True, N_INPUTS=max_occasions, CONFIG_MODE='A', PORTS=tree_ports_re)
                    ModuleAdderTree(QU_IN=QU_PROD, QU_OUT=QU_ACC, N_PIPELINES=TREE_DEPTH, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=True, N_INPUTS=max_occasions, CONFIG_MODE='A', PORTS=tree_ports_im)
                    QU_SUM = QU_ACC

                # --- FxMatch + output register ---
                fxm_re_name = f"fxm_re_s{sym}"
                fxm_im_name = f"fxm_im_s{sym}"
                #/ wire [`COMP_DWT`-1:0] `fxm_re_name`;
                #/ wire [`COMP_DWT`-1:0] `fxm_im_name`;

                ModuleFxMatch(QU_IN=QU_SUM, QU_OUT=QU_OUT_COMP, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': f'sum_re_s{sym}', 'o_data': fxm_re_name})
                ModuleFxMatch(QU_IN=QU_SUM, QU_OUT=QU_OUT_COMP, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': f'sum_im_s{sym}', 'o_data': fxm_im_name})

                # Output register (1 clk delay)
                packed_name = f"packed_s{sym}"
                #/ wire [`H_DWT`-1:0] `packed_name` = {`fxm_im_name`, `fxm_re_name`};
                out_wire = f"h_time_sym{sym}"
                delay_ports_sym = {
                    'i_data': packed_name,
                    'o_data': out_wire,
                    'i_clk': 'clk',
                    'i_rst_n': 'rst_n',
                }
                ModuleDelay(DWT=H_DWT, N_CLK=1, IF_RST_N=True, PORTS=delay_ports_sym)
                #/ 

    else:
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Complex coefficient mode
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        #/ // ========== LMMSE Complex-Coefficient Mode (basic_modules pipeline) ==========
        #/ 

        QU_CMUL_OUT = QuType(COMP_DWT, COMP_DWT // 2, True)

        for sym in range(N_OUT_SYMS):
            #/ // ---- Symbol `sym` (complex coeff) ----
            pass

            for j in range(max_occasions):
                if COEFF_SOURCE == 'ROM':
                    if len(config_keys) == 1:
                        w_re_val = W_q_by_config[config_keys[0]][sym][j]
                        w_re_bits = w_re_val & ((1 << COEFF_DWT) - 1)
                        #/ wire [`2*COEFF_DWT`-1:0] `f"wc_s{sym}_j{j}"` = {`COEFF_DWT`'d0, `COEFF_DWT`'d`w_re_bits`};
                        pass
                    else:
                        #/ reg [`COEFF_DWT`-1:0] `f"wc_re_s{sym}_j{j}"`;
                        #/ always @(*) begin
                        #/     `f"wc_re_s{sym}_j{j}"` = `COEFF_DWT`'d0;
                        first_cfg = True
                        for l0, dbl, n_add, n_sym in config_keys:
                            conditions = []
                            if needs_runtime_l0:
                                conditions.append(f"dmrs_typeA_pos_sel == 1'b{0 if l0 == 2 else 1}")
                            if needs_runtime_dbl:
                                conditions.append(f"is_double_dmrs == 1'b{1 if dbl else 0}")
                            if needs_runtime_nadd:
                                conditions.append(f"n_additional_dmrs == {n_add_width}'d{n_add}")
                            if needs_runtime_nsym:
                                conditions.append(f"pusch_symbol_length == 4'd{n_sym}")
                            cond_str = " && ".join(conditions)
                            if first_cfg:
                                #/ if (`cond_str`) begin
                                first_cfg = False
                            else:
                                #/ end else if (`cond_str`) begin
                                pass
                            w_re_val = W_q_by_config[(l0, dbl, n_add, n_sym)][sym][j]
                            w_re_bits = w_re_val & ((1 << COEFF_DWT) - 1)
                            #/ `f"wc_re_s{sym}_j{j}"` = `COEFF_DWT`'d`w_re_bits`;
                        #/ end
                        #/ end
                        #/ wire [`2*COEFF_DWT`-1:0] `f"wc_s{sym}_j{j}"` = {`COEFF_DWT`'d0, `f"wc_re_s{sym}_j{j}"`};
                        pass
                else:
                    flat_idx = sym * max_occasions + j
                    #/ wire [`2*COEFF_DWT`-1:0] `f"wc_s{sym}_j{j}"` = {`COEFF_DWT`'d0, w_reg[`flat_idx`]};
                    pass

            for j in range(max_occasions):
                prod_name = f"cprod_s{sym}_j{j}"
                #/ wire [`H_DWT`-1:0] `prod_name`;

                cmul_ports = {
                    'i_data_1': f"h_pilot_occ{j}",
                    'i_data_2': f"wc_s{sym}_j{j}",
                    'o_data': prod_name,
                }
                if MUL_LATENCY > 0:
                    cmul_ports['i_clk'] = 'clk'
                    cmul_ports['i_rst_n'] = 'rst_n'

                ModuleComplexMul(QU_IN_1=QU_PILOT_COMP, QU_IN_2=QU_COEFF, QU_OUT=QU_CMUL_OUT, N_CLK=MUL_LATENCY, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, IF_RST_N=True, METHOD='4mul', PORTS=cmul_ports)

            if max_occasions == 1:
                #/ wire [`H_DWT`-1:0] `f"csum_s{sym}"` = `f"cprod_s{sym}_j0"`;
                pass
            else:
                for comp_tag in ['re', 'im']:
                    comp_parts = []
                    for j in range(max_occasions):
                        if comp_tag == 're':
                            comp_parts.append(f"cprod_s{sym}_j{j}[{COMP_DWT}-1:0]")
                        else:
                            comp_parts.append(f"cprod_s{sym}_j{j}[{H_DWT}-1:{COMP_DWT}]")
                    comp_concat = "{" + ", ".join(reversed(comp_parts)) + "}"
                    #/ wire [`COMP_DWT * max_occasions`-1:0] `f"ctree_{comp_tag}_in_s{sym}"` = `comp_concat`;

                    sum_name = f"csum_{comp_tag}_s{sym}"
                    #/ wire [`QU_ACC.DWT`-1:0] `sum_name`;

                    tree_ports = {
                        'i_data': f"ctree_{comp_tag}_in_s{sym}",
                        'o_data': sum_name,
                    }
                    if TREE_DEPTH > 0:
                        tree_ports['i_clk'] = 'clk'
                        tree_ports['i_rst_n'] = 'rst_n'

                    ModuleAdderTree(QU_IN=QU_CMUL_OUT, QU_OUT=QU_ACC, N_PIPELINES=TREE_DEPTH, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=True, N_INPUTS=max_occasions, CONFIG_MODE='A', PORTS=tree_ports)

                QU_SUM_C = QU_ACC
                fxm_re_name = f"cfxm_re_s{sym}"
                fxm_im_name = f"cfxm_im_s{sym}"
                #/ wire [`COMP_DWT`-1:0] `fxm_re_name`;
                #/ wire [`COMP_DWT`-1:0] `fxm_im_name`;

                ModuleFxMatch(QU_IN=QU_SUM_C, QU_OUT=QU_OUT_COMP, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': f'csum_re_s{sym}', 'o_data': fxm_re_name})
                ModuleFxMatch(QU_IN=QU_SUM_C, QU_OUT=QU_OUT_COMP, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': f'csum_im_s{sym}', 'o_data': fxm_im_name})

                #/ wire [`H_DWT`-1:0] `f"csum_s{sym}"` = {`fxm_im_name`, `fxm_re_name`};

            out_wire = f"h_time_sym{sym}"
            delay_ports_sym = {
                'i_data': f"csum_s{sym}",
                'o_data': out_wire,
                'i_clk': 'clk',
                'i_rst_n': 'rst_n',
            }
            ModuleDelay(DWT=H_DWT, N_CLK=1, IF_RST_N=True, PORTS=delay_ports_sym)
            #/ 

    #/ 
    #/ endmodule
    pass


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Test: Full parallel
    ModuleCORE_TIME_LMMSE_INTERP(
        max_occasions=3,
        Qu_H=QuType(12, 4, True),
        Qu_COEFF=QuType(12, 11, True),
        LMMSE_REAL_COEFF=True,
        dmrs_typeA_pos='pos2',
        is_double_dmrs=False,
        additional_DMRS_range=[2],
        num_symbols_range=[14],
        W_coeffs=None,
        f_d_norm=0.01,
    )

    # Test: SRAM mode
    ModuleCORE_TIME_LMMSE_INTERP(
        max_occasions=3,
        Qu_H=QuType(12, 4, True),
        Qu_COEFF=QuType(12, 11, True),
        LMMSE_REAL_COEFF=True,
        dmrs_typeA_pos='pos2',
        is_double_dmrs=False,
        additional_DMRS_range=[2],
        num_symbols_range=[14],
        W_coeffs=None,
        f_d_norm=0.01,
        COEFF_SOURCE='SRAM',
    )
