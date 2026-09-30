from numpy import append
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname

sys.path.append(dirname(__file__))

from basic_modules import QuMode, QuType, OfMode, ModuleAdd, ModuleFxMatch, ModuleSub, ModuleDelay
from delay_budget import DelayBudget, cost_adder, COST_MUL_8B, COST_MUX, DEFAULT_BUDGET
from typing import Any
import math


def y_pre_pipeline_depth(Qu_Y: QuType, Qu_OUT: QuType, MAX_CDM_GROUPS: int) -> int:
    """Minimum pipeline depth for Y_PRE (callable without instantiation).

    Worst-case combinational chain: Add(4Y+Y) → Add(64T+8T) → Add(72T+2Y).
    If MAX_CDM_GROUPS >= 2, an output MUX adds COST_MUX.
    """
    Qu_T = QuType(Qu_Y.DWT + 3, Qu_Y.FRAC, True)
    Qu_72T = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)
    Qu_362Y = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    budget.add_comb(cost_adder(Qu_T.DWT), tag="add_4Y_plus_Y")
    budget.add_comb(cost_adder(Qu_72T.DWT), tag="add_64T_plus_8T")
    budget.add_comb(cost_adder(Qu_362Y.DWT), tag="add_72T_plus_2Y")
    if MAX_CDM_GROUPS >= 2:
        budget.add_comb(COST_MUX, tag="cdm_output_mux")
    return budget.pipeline_depth + 1  # +1 for output register


@convert
def ModuleY_PRE(N_CLK: int, Y_parallelism: int, Qu_Y: QuType, Qu_OUT: QuType, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, MAX_CDM_GROUPS: int) -> None:
    '''
    Docstring for ModuleY_PRE
    Pre-scales the Y input signal based on the number of CDM groups without data (Power Boosting).

    Scaling factors (÷512 to absorb |φ|²=2 from LS_ROT conjugate multiply):
    - num_cdm_groups_without_data = 0: Factor 362/512 (~1/sqrt(2))
    - num_cdm_groups_without_data = 1: Factor 1/2
    - num_cdm_groups_without_data = 2: Factor 209/512 (~1/sqrt(6))

    :param N_CLK: 1
    Number of clock cycles for sequential processing. Must be larger than 0.
    :type N_CLK: int
    :param Y_parallelism: 1
    Number of parallel resource elements (REs) to process.
    :type Y_parallelism: int
    :param Qu_Y: QuType(10, 8, True)
    Quantization type of the input Y.
    :type Qu_Y: QuType
    :param Qu_OUT: QuType(10, 8, True)
    Quantization type of the output.
    :type Qu_OUT: QuType
    :param QU_MODE: QuMode.TRN.TCPL
    Quantization rounding mode (e.g., TRN, RND).
    :type QU_MODE: QuMode
    :param OF_MODE: OfMode.WRP.TCPL
    Overflow handling mode (e.g., WRP, SAT).
    :type OF_MODE: OfMode
    :param MAX_CDM_GROUPS: 1
    Maximum supported CDM group modes.
    :type MAX_CDM_GROUPS: int
    '''

    if N_CLK <= 0:
        raise ValueError("N_CLK must be larger than 0.")
    if MAX_CDM_GROUPS not in (1, 2, 3, 4, 5, 6):
        raise ValueError("MAX_CDM_GROUPS must be between 1 and 6.")

    if MAX_CDM_GROUPS >= 5:
        sel_bits = 3
    elif MAX_CDM_GROUPS >= 3:
        sel_bits = 2
    elif MAX_CDM_GROUPS == 2:
        sel_bits = 1
    else:
        sel_bits = 0

    #/ `timescale 1ns / 1ps
    #/ module Y_PRE (

    for i in range(Y_parallelism):
        name = f"Y_in_complex_{i}"
        #/ input [`2*Qu_Y.DWT`-1:0] `name`,
        pass

    for i in range(Y_parallelism):
        name = f"Y_out_complex_{i}"
        #/ output [`2*Qu_OUT.DWT`-1:0] `name`,
        pass

    if MAX_CDM_GROUPS >= 2:
        #/ input [`sel_bits`-1:0] num_cdm_groups_without_data,
        #/ input                  clk
        pass
    else:
        #/ input clk
        pass
    #/ );

    Qu_2Y = QuType(Qu_Y.DWT + 1, Qu_Y.FRAC, True)
    Qu_4Y = QuType(Qu_Y.DWT + 2, Qu_Y.FRAC, True)

    Qu_Y_half = QuType(Qu_Y.DWT, Qu_Y.FRAC + 1, True)  # ÷2 via FxMatch FRAC shift

    Qu_T    = QuType(Qu_Y.DWT + 3, Qu_Y.FRAC, True)
    Qu_8T   = QuType(Qu_Y.DWT + 6, Qu_Y.FRAC, True)
    Qu_64T  = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)
    Qu_72T  = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)
    Qu_362Y = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)

    Qu_3Y   = QuType(Qu_Y.DWT + 2, Qu_Y.FRAC, True)
    Qu_48Y  = QuType(Qu_Y.DWT + 6, Qu_Y.FRAC, True)
    Qu_256Y = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC, True)
    Qu_208Y = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC, True)
    Qu_209Y = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC, True)

    Qu_362Y_temp = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC + 9, True)
    Qu_209Y_temp = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC + 9, True)

    # =========================================================================
    # DelayBudget analysis — compute minimum pipeline depth for Y_PRE
    # =========================================================================
    # 362Y path (worst-case: longest combinational chain):
    #   Add(4Y+Y→T): width Qu_T.DWT       → cost_adder(Qu_T.DWT)
    #   shift (free) → Add(64T+8T→72T): width Qu_72T.DWT → cost_adder(Qu_72T.DWT)
    #   Add(72T+2Y→362Y): width Qu_362Y.DWT → cost_adder(Qu_362Y.DWT)
    #   FxMatch (bit-select, free) + MUX (free)
    #
    # 209Y path (parallel, similar depth):
    #   Add(2Y+Y→3Y): cost_adder(Qu_3Y.DWT)
    #   shift → Sub(256Y-48Y→208Y): cost_adder(Qu_208Y.DWT)
    #   Add(208Y+Y→209Y): cost_adder(Qu_209Y.DWT)
    #   FxMatch + MUX
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)

    # Stage: Add(4Y + Y → T), width = Qu_T.DWT
    budget.add_comb(cost_adder(Qu_T.DWT), tag="add_4Y_plus_Y")
    # Stage: shift is free → Add(64T + 8T → 72T), width = Qu_72T.DWT
    budget.add_comb(cost_adder(Qu_72T.DWT), tag="add_64T_plus_8T")
    # Stage: Add(72T + 2Y → 362Y), width = Qu_362Y.DWT
    budget.add_comb(cost_adder(Qu_362Y.DWT), tag="add_72T_plus_2Y")
    # Final: FxMatch + MUX → free

    Y_PRE_MIN_PIPELINE_DEPTH = budget.pipeline_depth + 1  # +1 for the output register

    if N_CLK < Y_PRE_MIN_PIPELINE_DEPTH:
        raise ValueError(
            f"Y_PRE: N_CLK={N_CLK} is below the minimum pipeline depth "
            f"{Y_PRE_MIN_PIPELINE_DEPTH} required by DelayBudget analysis.\n"
            f"{budget.summary()}"
        )

    for i in range(Y_parallelism):
        in_full_name = f"Y_in_complex_{i}"
        out_full_name = f"Y_out_complex_{i}"

        #/ wire [`Qu_Y.DWT`-1:0] `in_full_name`_real = `in_full_name`[`Qu_Y.DWT`-1:0];
        #/ wire [`Qu_Y.DWT`-1:0] `in_full_name`_imag = `in_full_name`[`2*Qu_Y.DWT`-1:`Qu_Y.DWT`];

        for part in ["real", "imag"]:
            suffix = f"{i}_{part}"
            signal_in = f"{in_full_name}_{part}"

            wire_2Y = f"Y_common_2Y_{suffix}"
            #/ wire [`Qu_2Y.DWT`-1:0] `wire_2Y` = {`signal_in`, 1'b0};
            pass

            wire_out_362 = f"Y_res_362_{suffix}"
            if True: # Always generate path 0 -> num_cdm_groups_without_data = 1
                wire_4Y  = f"Y_p0_4Y_{suffix}"
                wire_T   = f"Y_p0_T_{suffix}"
                wire_8T  = f"Y_p0_8T_{suffix}"
                wire_64T = f"Y_p0_64T_{suffix}"
                wire_72T = f"Y_p0_72T_{suffix}"
                wire_362Y = f"Y_p0_362Y_{suffix}"

                #/ wire [`Qu_4Y.DWT`-1:0] `wire_4Y`;
                #/ wire [`Qu_T.DWT`-1:0] `wire_T`;
                #/ wire [`Qu_8T.DWT`-1:0] `wire_8T`;
                #/ wire [`Qu_64T.DWT`-1:0] `wire_64T`;
                #/ wire [`Qu_72T.DWT`-1:0] `wire_72T`;
                #/ wire [`Qu_362Y.DWT`-1:0] `wire_362Y`;
                #/ wire [`Qu_OUT.DWT`-1:0] `wire_out_362`;
                #/ assign `wire_4Y` = {`wire_2Y`, 1'b0};

                ModuleAdd(QU_IN_1=Qu_4Y, QU_IN_2=Qu_Y, QU_OUT=Qu_T, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': wire_4Y, 'i_data_2': signal_in, 'o_data': wire_T})

                #/ assign `wire_8T`  = {`wire_T`, 3'b0};
                #/ assign `wire_64T` = {`wire_8T`, 3'b0};

                ModuleAdd(QU_IN_1=Qu_64T, QU_IN_2=Qu_8T, QU_OUT=Qu_72T, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': wire_64T, 'i_data_2': wire_8T, 'o_data': wire_72T})

                ModuleAdd(QU_IN_1=Qu_72T, QU_IN_2=Qu_2Y, QU_OUT=Qu_362Y, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': wire_72T, 'i_data_2': wire_2Y, 'o_data': wire_362Y})

                ModuleFxMatch(QU_IN=Qu_362Y_temp, QU_OUT=Qu_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS={'i_data': wire_362Y, 'o_data': wire_out_362})

            if MAX_CDM_GROUPS >= 2:
                wire_out_direct = f"Y_res_direct_{suffix}"
                #/ wire [`Qu_OUT.DWT`-1:0] `wire_out_direct`;
                ModuleFxMatch(QU_IN=Qu_Y_half, QU_OUT=Qu_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS={'i_data': signal_in, 'o_data': wire_out_direct})

            if MAX_CDM_GROUPS >= 3:
                wire_out_209 = f"Y_res_209_{suffix}"
                wire_3Y   = f"Y_p2_3Y_{suffix}"
                wire_48Y  = f"Y_p2_48Y_{suffix}"
                wire_256Y = f"Y_p2_256Y_{suffix}"
                wire_208Y = f"Y_p2_208Y_{suffix}"
                wire_209Y = f"Y_p2_209Y_{suffix}"

                #/ wire [`Qu_3Y.DWT`-1:0] `wire_3Y`;
                #/ wire [`Qu_48Y.DWT`-1:0] `wire_48Y`;
                #/ wire [`Qu_256Y.DWT`-1:0] `wire_256Y`;
                #/ wire [`Qu_208Y.DWT`-1:0] `wire_208Y`;
                #/ wire [`Qu_209Y.DWT`-1:0] `wire_209Y`;
                #/ wire [`Qu_OUT.DWT`-1:0] `wire_out_209`;

                ModuleAdd(QU_IN_1=Qu_2Y, QU_IN_2=Qu_Y, QU_OUT=Qu_3Y, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': wire_2Y, 'i_data_2': signal_in, 'o_data': wire_3Y})

                #/ assign `wire_48Y`  = {`wire_3Y`, 4'b0};
                #/ assign `wire_256Y` = {`signal_in`, 8'b0};

                ModuleSub(QU_IN_1=Qu_256Y, QU_IN_2=Qu_48Y, QU_OUT=Qu_208Y, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': wire_256Y, 'i_data_2': wire_48Y, 'o_data': wire_208Y})

                ModuleAdd(QU_IN_1=Qu_208Y, QU_IN_2=Qu_Y, QU_OUT=Qu_209Y, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': wire_208Y, 'i_data_2': signal_in, 'o_data': wire_209Y})

                ModuleFxMatch(QU_IN=Qu_209Y_temp, QU_OUT=Qu_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS={'i_data': wire_209Y, 'o_data': wire_out_209})

            wire_final = f"Y_final_{suffix}"
            reg_final = f"Y_final_{suffix}_reg"

            #/ wire [`Qu_OUT.DWT`-1:0] `reg_final`;

            # It is OK to declear reg and wire to `wire_final`
            if MAX_CDM_GROUPS >= 3:
                #/ reg [`Qu_OUT.DWT`-1:0] `wire_final`;
                #/ always @(*) begin
                #/     case (num_cdm_groups_without_data)
                #/         `sel_bits`'d0: `wire_final` = `wire_out_362`;
                #/         `sel_bits`'d1: `wire_final` = `wire_out_direct`;
                #/         `sel_bits`'d2: `wire_final` = `wire_out_209`;
                #/         default: `wire_final` = {`Qu_OUT.DWT`{1'b0}};
                #/     endcase
                #/ end
                pass
            elif MAX_CDM_GROUPS == 2:
                #/ wire [`Qu_OUT.DWT`-1:0] `wire_final`;
                #/ assign `wire_final` = num_cdm_groups_without_data ? `wire_out_direct` : `wire_out_362`;
                pass
            else:
                #/ wire [`Qu_OUT.DWT`-1:0] `wire_final`;
                #/ assign `wire_final` = `wire_out_362`;
                pass

            ModuleDelay(DWT=Qu_OUT.DWT, N_CLK=N_CLK, IF_RST_N=False, PORTS={'i_data': wire_final, 'o_data': reg_final, 'i_clk': 'clk'})

        reg_final_real_reg = f"Y_final_{i}_real_reg"
        reg_final_imag_reg = f"Y_final_{i}_imag_reg"
        #/ assign `out_full_name` = {`reg_final_imag_reg`, `reg_final_real_reg`};
        pass

    _min_depth = y_pre_pipeline_depth(Qu_Y, Qu_OUT, MAX_CDM_GROUPS)
    #/ // Timing budget: N_CLK=`N_CLK` (auto-min=`_min_depth`, CDM_MUX=`'yes' if MAX_CDM_GROUPS >= 2 else 'no'`)
    #/ endmodule
    pass
