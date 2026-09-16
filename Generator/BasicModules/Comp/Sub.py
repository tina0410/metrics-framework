###################################################################################################
# Module Name: Sub
# Description: This module subtracts two fixed-point numbers.
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Dependency Modules:
#   - Delay (1.0.0)
#   - FxMatch (1.0.0)
###################################################################################################
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

try:
    from .Delay import ModuleDelay
except ImportError:
    from Delay import ModuleDelay
try:
    from .FxMatch import ModuleFxMatch
except ImportError:
    from FxMatch import ModuleFxMatch
try:
    from .PyTU import OfMode, QuMode, QuType
except ImportError:
    from PyTU import OfMode, QuMode, QuType


@convert
def ModuleSub(QU_IN_1: QuType, QU_IN_2: QuType, QU_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool):
    """Subtract ``QU_IN_2`` from ``QU_IN_1`` and convert once to ``QU_OUT``."""
    if QU_IN_1.DWT < 1 or QU_IN_2.DWT < 1 or QU_OUT.DWT < 1:
        raise ValueError("All fixed-point widths must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")

    #/ `timescale 1ns / 1ps
    #/ module SUB(
    #/     i_data_1,
    #/     i_data_2,
    #/     o_data
    if N_CLK > 0:
        if IF_RST_N:
            #/     ,i_rst_n
            pass
        #/     ,i_clk
        pass
    #/ );

    #/ // Input and Output Ports
    #/ input  wire [`QU_IN_1.DWT`-1:0] i_data_1;
    #/ input  wire [`QU_IN_2.DWT`-1:0] i_data_2;
    #/ output wire [`QU_OUT.DWT`-1:0]  o_data;
    if N_CLK > 0:
        #/ input wire i_clk;
        if IF_RST_N:
            #/ input wire i_rst_n;
            pass

    #/ wire [`QU_IN_1.DWT`-1:0] data_1;
    #/ wire [`QU_IN_2.DWT`-1:0] data_2;
    #/ assign data_1 = i_data_1;
    #/ assign data_2 = i_data_2;

    # Form the exact signed two's-complement negative of operand 2 in one
    # additional bit before aligning the operands.
    #/ wire [`QU_IN_2.DWT`:0] data_2_minus;
    if QU_IN_2.IF_SIGNED:
        #/ assign data_2_minus = ~{data_2[`QU_IN_2.DWT`-1], data_2} + 1'b1;
        pass
    else:
        #/ assign data_2_minus = ~{1'b0, data_2} + 1'b1;
        pass

    LSB_FIX = -max(QU_IN_1.FRAC, QU_IN_2.FRAC)
    MSB_FIX = max(
        QU_IN_1.DWT - QU_IN_1.FRAC,
        QU_IN_2.DWT - QU_IN_2.FRAC + 1,
    )
    QU_IN_FIX = QuType(
        DWT=MSB_FIX - LSB_FIX + 1,
        FRAC=-LSB_FIX,
        IF_SIGNED=True,
    )
    QU_IN_2_MINUS = QuType(
        DWT=QU_IN_2.DWT + 1,
        FRAC=QU_IN_2.FRAC,
        IF_SIGNED=True,
    )

    #/ wire [`QU_IN_FIX.DWT`-1:0] data_1_fixed;
    #/ wire [`QU_IN_FIX.DWT`-1:0] data_2_fixed;
    input1_match_ports = {
        "i_data": "data_1",
        "o_data": "data_1_fixed",
    }
    ModuleFxMatch(QU_IN=QU_IN_1, QU_OUT=QU_IN_FIX, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, N_CLK=0, IF_RST_N=False, PORTS=input1_match_ports)  # type: ignore
    input2_match_ports = {
        "i_data": "data_2_minus",
        "o_data": "data_2_fixed",
    }
    ModuleFxMatch(QU_IN=QU_IN_2_MINUS, QU_OUT=QU_IN_FIX, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, N_CLK=0, IF_RST_N=False, PORTS=input2_match_ports)  # type: ignore

    # Perform the subtraction in the common exact type, then apply the public
    # quantization and overflow policy exactly once.
    #/ wire [`QU_IN_FIX.DWT`-1:0] result_unfixed;
    #/ wire [`QU_OUT.DWT`-1:0] result_fixed;
    #/ assign result_unfixed = data_1_fixed + data_2_fixed;
    output_match_ports = {
        "i_data": "result_unfixed",
        "o_data": "result_fixed",
    }
    ModuleFxMatch(QU_IN=QU_IN_FIX, QU_OUT=QU_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS=output_match_ports)  # type: ignore

    delay_ports = {
        "i_data": "result_fixed",
        "o_data": "o_data",
    }
    if N_CLK > 0:
        delay_ports["i_clk"] = "i_clk"
        if IF_RST_N:
            delay_ports["i_rst_n"] = "i_rst_n"
    ModuleDelay(DWT=QU_OUT.DWT, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS=delay_ports)  # type: ignore

    #/ endmodule
