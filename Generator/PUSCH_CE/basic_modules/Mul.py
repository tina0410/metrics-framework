###################################################################################################
# Module Name: Mul
# Description: This module is used to Multiply two fixed-point numbers.
# Author: Bolin Li
# Author: Yifang Dai
# Date: 2025.3.30
# Version: V0.2.1
# Doc Version: V0.2.1
# Dependency Modules:
#   - Delay (V 0.1.0)
#   - FxMatch (V 0.2.1)
###########################################################################
import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from enum import Enum
from PyTU import QuMode, OfMode, QuType
from Delay import ModuleDelay
from FxMatch import ModuleFxMatch

@convert
def ModuleMul(QU_IN_1:QuType, QU_IN_2:QuType, QU_OUT:QuType, N_CLK:int, QU_MODE:QuMode.TRN | QuMode.RND, OF_MODE:OfMode.WRP | OfMode.SAT, IF_RST_N: bool):

    # Parsing the input arguments
    # the IF_RST_N_LIST should not be passed to the submodules
    if N_CLK > 0:
        # Expand the boolean to a list of the same value
        IF_RST_N_LIST = [IF_RST_N] * N_CLK
    elif N_CLK == 0:
        IF_RST_N_LIST = [False] # No sequential logic. This is only for type alignment
    else: # N_CLK < 0
        raise ValueError("N_CLK must be non-negative.")


    #/ `timescale 1ns / 1ps
    #/ module MUL(
    #/     i_data_1, i_data_2, o_data
    if N_CLK > 0:
        #/ ,i_clk
        if any(IF_RST_N_LIST):
            #/ , i_rst_n
            pass
    #/ );

    #/ input  wire [`QU_IN_1.DWT-1`:0] i_data_1;
    #/ input  wire [`QU_IN_2.DWT-1`:0] i_data_2;
    #/ output wire [`QU_OUT.DWT-1`:0]  o_data;
    if N_CLK > 0:
        #/ input wire i_clk;
        if any(IF_RST_N_LIST):
            #/ input wire i_rst_n;
            pass
        pass


    # Calculate the Multiplier Result Quantization Parameters
    DWT_FIX = QU_IN_1.DWT + QU_IN_2.DWT
    FRAC_FIX = QU_IN_1.FRAC + QU_IN_2.FRAC
    SIGN_FIX = QU_IN_1.IF_SIGNED or QU_IN_2.IF_SIGNED
    QU_IN_FIX = QuType(DWT_FIX, FRAC_FIX, SIGN_FIX)

    if N_CLK >= 2 and SIGN_FIX:
        # --- Pipelined signed multiply: register after unsigned multiply ---
        # Stage 1: abs conversion + unsigned multiply + register
        # Stage 2: sign correction + FxMatch + output register(s)
        #/ wire [`QU_IN_1.DWT-1`:0]   data_1_abs;
        #/ wire [`QU_IN_2.DWT-1`:0]   data_2_abs;
        #/ wire [`QU_IN_FIX.DWT-1`:0] data_mul_ures;
        if QU_IN_1.IF_SIGNED:
            #/ assign data_1_abs = i_data_1[`QU_IN_1.DWT-1`] ? (~i_data_1 + 1'b1) : i_data_1;
            pass
        else:
            #/ assign data_1_abs = i_data_1;
            pass
        if QU_IN_2.IF_SIGNED:
            #/ assign data_2_abs = i_data_2[`QU_IN_2.DWT-1`] ? (~i_data_2 + 1'b1) : i_data_2;
            pass
        else:
            #/ assign data_2_abs = i_data_2;
            pass

        #/ assign data_mul_ures = data_1_abs * data_2_abs;

        # Register the unsigned result and sign bit (pipeline stage 1)
        #/ wire res_sign_comb;
        if QU_IN_1.IF_SIGNED and QU_IN_2.IF_SIGNED:
            #/ assign res_sign_comb = i_data_1[`QU_IN_1.DWT-1`] ^ i_data_2[`QU_IN_2.DWT-1`];
            pass
        elif QU_IN_1.IF_SIGNED:
            #/ assign res_sign_comb = i_data_1[`QU_IN_1.DWT-1`];
            pass
        else:
            #/ assign res_sign_comb = i_data_2[`QU_IN_2.DWT-1`];
            pass

        #/ reg [`QU_IN_FIX.DWT-1`:0] mul_ures_r;
        #/ reg res_sign_r;
        #/ always @(posedge i_clk) begin
        #/     mul_ures_r <= data_mul_ures;
        #/     res_sign_r <= res_sign_comb;
        #/ end

        # Stage 2: sign correction
        QU_IN_FIX.DWT = QU_IN_FIX.DWT + 1
        #/ wire [`QU_IN_FIX.DWT-1`:0] data_mul_res;
        #/ assign data_mul_res = res_sign_r ? (~{1'b0, mul_ures_r} + 1'b1) : {1'b0, mul_ures_r};

        # Output FxMatch (combinational)
        #/ wire [`QU_OUT.DWT-1`:0] result_fixed;
        inst_ports_fxmatch = {
            "i_data": "data_mul_res",
            "o_data": "result_fixed"
        }
        ModuleFxMatch(N_CLK = 0, IF_RST_N = False, QU_IN = QU_IN_FIX, QU_OUT = QU_OUT, QU_MODE = QU_MODE, OF_MODE = OF_MODE, PORTS = inst_ports_fxmatch) # type:ignore

        # Output Delay (N_CLK - 1 stages, since 1 stage used for pipeline register above)
        N_CLK_OUT = N_CLK - 1
        inst_ports = {
             "i_data": "result_fixed",
             "o_data": "o_data"
        }
        if N_CLK_OUT > 0:
            inst_ports["i_clk"] = "i_clk"
            if IF_RST_N:
                inst_ports["i_rst_n"] = "i_rst_n"
        ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_CLK_OUT, IF_RST_N = IF_RST_N, PORTS = inst_ports) # type:ignore

    else:
        # --- Original non-pipelined path (N_CLK < 2 or unsigned) ---
        #/ wire [`QU_IN_1.DWT-1`:0] data_1;
        #/ wire [`QU_IN_2.DWT-1`:0] data_2;
        #/ assign data_1 = i_data_1;
        #/ assign data_2 = i_data_2;

        # Sign-Magnitude Calculation
        #/ wire [`QU_IN_1.DWT-1`:0]   data_1_abs;
        #/ wire [`QU_IN_2.DWT-1`:0]   data_2_abs;
        #/ wire [`QU_IN_FIX.DWT-1`:0] data_mul_ures;
        if QU_IN_1.IF_SIGNED:
            #/ assign data_1_abs = data_1[`QU_IN_1.DWT-1`] ? {~data_1[`QU_IN_1.DWT-1`:0] + 1'b1} : data_1;
            pass
        else:
            #/ assign data_1_abs = data_1;
            pass

        if QU_IN_2.IF_SIGNED:
            #/ assign data_2_abs = data_2[`QU_IN_2.DWT-1`] ? {~data_2[`QU_IN_2.DWT-1`:0] + 1'b1} : data_2;
            pass
        else:
            #/ assign data_2_abs = data_2;
            pass

        #/ assign data_mul_ures = data_1_abs * data_2_abs;
        #/ wire                     res_sign;
        #/ wire [`QU_IN_FIX.DWT`:0] data_mul_res;


        if QU_IN_1.IF_SIGNED and QU_IN_2.IF_SIGNED:
            #/ assign res_sign     = data_1[`QU_IN_1.DWT-1`] ^ data_2[`QU_IN_2.DWT-1`];
            #/ assign data_mul_res = res_sign ? {~{1'b0, data_mul_ures[`QU_IN_FIX.DWT-1`:0]} + 1'b1} : {1'b0, data_mul_ures};
            pass
        elif QU_IN_1.IF_SIGNED:
            #/ assign res_sign     = data_1[`QU_IN_1.DWT-1`];
            #/ assign data_mul_res = res_sign ? {~{1'b0, data_mul_ures[`QU_IN_FIX.DWT-1`:0]} + 1'b1} : {1'b0, data_mul_ures};
            pass
        elif QU_IN_2.IF_SIGNED:
            #/ assign res_sign     = data_2[`QU_IN_2.DWT-1`];
            #/ assign data_mul_res = res_sign ? {~{1'b0, data_mul_ures[`QU_IN_FIX.DWT-1`:0]} + 1'b1} : {1'b0, data_mul_ures};
            pass
        else:
            #/ assign res_sign     = 1'b0;
            #/ assign data_mul_res = {1'b0, data_mul_ures};
            pass

        QU_IN_FIX.DWT = QU_IN_FIX.DWT + 1

        # Output FxMatch
        # N_CLK = 0, hence no reset needed
        #/ wire [`QU_OUT.DWT-1`:0] result_fixed;
        inst_ports_fxmatch = {
            "i_data": "data_mul_res",
            "o_data": "result_fixed"
        }
        ModuleFxMatch(N_CLK = 0, IF_RST_N = False, QU_IN = QU_IN_FIX, QU_OUT = QU_OUT, QU_MODE = QU_MODE, OF_MODE = OF_MODE, PORTS = inst_ports_fxmatch) # type:ignore

        # Delay Module
        inst_ports = {
             "i_data": "result_fixed",
             "o_data": "o_data"
        }
        if N_CLK > 0:
            inst_ports["i_clk"] = "i_clk"
            if any(IF_RST_N_LIST):
                inst_ports["i_rst_n"] = "i_rst_n"

        # Inherit IF_RST_N and N_CLK from the Mul module
        ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_CLK, IF_RST_N = IF_RST_N, PORTS = inst_ports) # type:ignore

    #/ endmodule
