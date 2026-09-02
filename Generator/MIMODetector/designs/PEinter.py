###################################################################################################
# Module Name: PEinter
# Description: This module is used to y = w * x + pass
# Author: Yifang Dai
# Date: 2025.4.25
# Version: V0.1.0
# Dependency Modules: 
#   - Delay (V 0.1.0)
#   - FxMatch (V 0.2.1)
#   - Mul (V 0.2.1)
#   - Add (V 0.2.1)
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
from Mul import ModuleMul
from Add import ModuleAdd

@convert
def ModulePEinter(QU_IN_1:QuType, QU_IN_2:QuType, QU_IN_3:QuType, QU_OUT:QuType, passc, N_PIPELINES=0, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    # Clock, Resets and Enables
    if N_PIPELINES > 0 and type(IF_RST_N) == bool:
        # Expand the boolean to a list of the same value
        IF_RST_N = [IF_RST_N] * N_PIPELINES


    #/ module PEinter(
    #/ i_data_1, i_data_2, i_data_3, o_data
    if passc[0]==0 and passc[1]==0:
        #/    ,i_sel
        pass
    if N_PIPELINES > 0:
        #/    ,i_clk
        if any(IF_RST_N):
            #/    , i_rst_n
            pass
    #/ );

    #/ input wire [`QU_IN_1.DWT-1`:0] i_data_1;
    #/ input wire [`QU_IN_2.DWT-1`:0] i_data_2;
    #/ input wire [`QU_IN_3.DWT-1`:0] i_data_3;
    #/ output wire [`QU_OUT.DWT-1`:0] o_data;
    if passc[0]==0 and passc[1]==0:
        #/ input wire i_sel;
        pass
    if N_PIPELINES > 0:
        #/ input wire i_clk;
        if any(IF_RST_N):
            #/ input wire i_rst_n;
            pass
        pass

    #/ wire [`QU_IN_1.DWT-1`:0] data_1;
    #/ wire [`QU_IN_2.DWT-1`:0] data_2;
    #/ wire [`QU_IN_3.DWT-1`:0] data_3;

    #/ assign data_1 = i_data_1;
    #/ assign data_2 = i_data_2;
    #/ assign data_3 = i_data_3;


    # Calculate the Multiplier Result Quantization Parameters
    DWT_FIX = QU_IN_1.DWT + QU_IN_2.DWT
    FRAC_FIX = QU_IN_1.FRAC + QU_IN_2.FRAC
    SIGN_FIX = QU_IN_1.IF_SIGNED or QU_IN_2.IF_SIGNED
    QU_IN_FIX = QuType(DWT_FIX, FRAC_FIX, SIGN_FIX)
    
    #/ wire [`QU_OUT.DWT-1`:0] mul_result;
    inst_ports_mul = {
        "i_data_1": "data_1",
        "i_data_2": "data_2",
        "o_data": "mul_result"
    }
    ModuleMul(QU_IN_1 = QU_IN_1, QU_IN_2 = QU_IN_2, QU_OUT = QU_OUT, QU_MODE = QU_MODE, OF_MODE = OF_MODE,IF_RST_N=IF_RST_N, PORTS = inst_ports_mul)
    
    #/ wire [`QU_OUT.DWT-1`:0] result_fixed;
    inst_ports_add = {
        "i_data_1": "mul_result",
        "i_data_2": "data_3",
        "o_data": "result_fixed"
    }
    ModuleAdd(QU_IN_1 = QU_OUT, QU_IN_2 = QU_IN_3, QU_OUT = QU_OUT, QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=IF_RST_N, PORTS = inst_ports_add)
    if passc[0]==0 and passc[1]==0:
        #/ assign o_data = (i_sel == 1'b1) ? mul_result : result_fixed;
        pass
    else:
        #/ assign o_data = result_fixed; 
        pass
    #/ endmodule
    
    
    