###################################################################################################
# Module Name: Add
# Description: This module is used to add two fixed-point numbers.
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Dependency Modules:
#   - Delay (1.0.0)
#   - FxMatch (1.0.0)
# Note: Modified to support type hints for better clarity.
###########################################################################
import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader


from enum import Enum
try:
    from .PyTU import QuMode, OfMode, QuType
except ImportError:
    from PyTU import QuMode, OfMode, QuType
try:
    from .Delay import ModuleDelay
except ImportError:
    from Delay import ModuleDelay
try:
    from .FxMatch import ModuleFxMatch
except ImportError:
    from FxMatch import ModuleFxMatch

@convert
def ModuleAdd(QU_IN_1:QuType, QU_IN_2:QuType, QU_OUT:QuType, N_CLK:int, QU_MODE:QuMode.TRN | QuMode.RND, OF_MODE:OfMode.WRP | OfMode.SAT, IF_RST_N:bool):

    # Parsing the input arguments
    # the IF_RST_N_LIST should not be passed to the submodules
    if N_CLK > 0:
        # Expand the boolean to a list of the same value
        IF_RST_N_LIST = [IF_RST_N] * N_CLK
    elif N_CLK == 0:
        IF_RST_N_LIST = [False] # No sequential logic. This is only for type alignment
    else: # N_CLK < 0
        raise ValueError("N_CLK must be non-negative.")



    #/ module ADD(
    #/     i_data_1,
    #/     i_data_2,
    #/     o_data
    if N_CLK > 0:

        if any(IF_RST_N_LIST) == True:
            #/ , i_rst_n
            pass
        #/ , i_clk
        pass
    #/ );

    #/ // Input and Output Ports
    #/ input  wire [`QU_IN_1.DWT`-1:0] i_data_1;
    #/ input  wire [`QU_IN_2.DWT`-1:0] i_data_2;
    #/ output wire [`QU_OUT.DWT`-1:0]  o_data;
    if N_CLK > 0:
        #/ input wire i_clk;
        if any(IF_RST_N_LIST) == True:
            #/ input wire i_rst_n;
            pass
    #/ wire [`QU_IN_1.DWT`-1:0] data_1;
    #/ wire [`QU_IN_2.DWT`-1:0] data_2;

    #/ assign data_1 = i_data_1;
    #/ assign data_2 = i_data_2;

    LSB_FIX = -max(QU_IN_1.FRAC, QU_IN_2.FRAC)
    MSB_FIX = max(QU_IN_1.DWT - QU_IN_1.FRAC, QU_IN_2.DWT - QU_IN_2.FRAC)
    QU_IN_FIX = QuType(DWT=MSB_FIX - LSB_FIX + 1, FRAC=-LSB_FIX, IF_SIGNED=QU_IN_1.IF_SIGNED or QU_IN_2.IF_SIGNED)

    #/ wire [`QU_IN_FIX.DWT`-1:0] data_1_fixed;
    #/ wire [`QU_IN_FIX.DWT`-1:0] data_2_fixed;

    # FxMatch
    inst_ports_fxmatch_1 = {
        "i_data": "data_1",
        "o_data": "data_1_fixed"
    }
    ModuleFxMatch(N_CLK = 0, IF_RST_N= False, QU_IN = QU_IN_1, QU_OUT = QU_IN_FIX, QU_MODE= QuMode.TRN.TCPL, OF_MODE= OfMode.WRP.TCPL, PORTS = inst_ports_fxmatch_1) #type:ignore

    inst_ports_fxmatch_2 = {
        "i_data": "data_2",
        "o_data": "data_2_fixed"
    }
    ModuleFxMatch(N_CLK = 0, IF_RST_N= False, QU_IN=QU_IN_2, QU_OUT=QU_IN_FIX,QU_MODE= QuMode.TRN.TCPL, OF_MODE= OfMode.WRP.TCPL, PORTS = inst_ports_fxmatch_2) #type:ignore

    # Adder
    # Consider binary carry
    #/ wire [`QU_IN_FIX.DWT`-1:0] result_unfixed;
    #/ wire [`QU_OUT.DWT`-1:0]    result_fixed;
    #/ assign result_unfixed = data_1_fixed + data_2_fixed;
    # Output Fix
    inst_ports_fxmatch_3 = {
        "i_data": "result_unfixed",
        "o_data": "result_fixed"
    }
    ModuleFxMatch(N_CLK = 0, IF_RST_N= False, QU_IN = QU_IN_FIX, QU_OUT = QU_OUT, QU_MODE = QU_MODE, OF_MODE = OF_MODE, PORTS = inst_ports_fxmatch_3) # type:ignore

    # Delay Module
    inst_ports = {
         "i_data": "result_fixed",
         "o_data": "o_data"
    }
    if N_CLK > 0:
        inst_ports["i_clk"] = "i_clk"
        if any(IF_RST_N_LIST):
            inst_ports["i_rst_n"] = "i_rst_n"

    ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_CLK, IF_RST_N = IF_RST_N, PORTS = inst_ports) # type:ignore
    #/ endmodule
