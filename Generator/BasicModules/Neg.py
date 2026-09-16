###################################################################################################
# Module Name: Neg
# Description: This module negates a fixed-point number with one guard bit.
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
def ModuleNeg(QU_IN: QuType, QU_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool):
    """
    Negate ``QU_IN`` in an exact signed format with one guard bit.

    Pass the widened result to FxMatch so the requested output format controls
    quantization, overflow, and the accepted signed or nonnegative encoding.
    """
    if QU_IN.DWT < 1:
        raise ValueError("QU_IN.DWT must be positive.")
    if QU_OUT.DWT < 1:
        raise ValueError("QU_OUT.DWT must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")

    #/ module NEG(
    #/     i_data,
    #/     o_data
    if N_CLK > 0:
        #/     ,i_clk
        if IF_RST_N:
            #/     ,i_rst_n
            pass
    #/ );

    #/ // Input and Output Ports
    #/ input  wire [`QU_IN.DWT`-1:0]  i_data;
    #/ output wire [`QU_OUT.DWT`-1:0] o_data;
    if N_CLK > 0:
        #/ input wire i_clk;
        if IF_RST_N:
            #/ input wire i_rst_n;
            pass

    QU_NEG = QuType(
        DWT=QU_IN.DWT + 1,
        FRAC=QU_IN.FRAC,
        IF_SIGNED=True,
    )

    #/ wire [`QU_NEG.DWT`-1:0] data_neg;
    if QU_IN.IF_SIGNED:
        #/ assign data_neg = ~{i_data[`QU_IN.DWT`-1], i_data} + 1'b1;
        pass
    else:
        #/ assign data_neg = ~{1'b0, i_data} + 1'b1;
        pass

    #/ wire [`QU_OUT.DWT`-1:0] result_fixed;
    inst_ports_fxmatch = {
        "i_data": "data_neg",
        "o_data": "result_fixed",
    }
    ModuleFxMatch(QU_IN=QU_NEG, QU_OUT=QU_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS=inst_ports_fxmatch)  # type: ignore

    inst_ports_delay = {
        "i_data": "result_fixed",
        "o_data": "o_data",
    }
    if N_CLK > 0:
        inst_ports_delay["i_clk"] = "i_clk"
        if IF_RST_N:
            inst_ports_delay["i_rst_n"] = "i_rst_n"

    ModuleDelay(DWT=QU_OUT.DWT, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS=inst_ports_delay)  # type: ignore

    #/ endmodule
