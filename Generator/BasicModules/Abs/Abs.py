###################################################################################################
# Module Name: Abs
# Description: This module calculates the absolute value of a fixed-point number.
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
def ModuleAbs(QU_IN: QuType, QU_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool):
    """
    Calculate an absolute value and convert it to ``QU_OUT``.

    Treat a signed input's magnitude bits as an unsigned fixed-point value
    before passing them to FxMatch. This preserves the magnitude of the most
    negative input while leaving output quantization and overflow to FxMatch.
    """
    if QU_IN.DWT < 1:
        raise ValueError("QU_IN.DWT must be positive.")
    if QU_OUT.DWT < 1:
        raise ValueError("QU_OUT.DWT must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")

    #/ module ABS(
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

    #/ wire [`QU_OUT.DWT`-1:0] result_fixed;

    if QU_IN.IF_SIGNED:
        # Interpret the absolute-value bits as a non-negative magnitude. FxMatch
        # adds its own leading zero when it converts this format internally.
        QU_ABS = QuType(
            DWT=QU_IN.DWT,
            FRAC=QU_IN.FRAC,
            IF_SIGNED=False,
        )
        #/ wire [`QU_IN.DWT`-1:0] data_abs;
        #/ assign data_abs = i_data[`QU_IN.DWT`-1] ? (~i_data + 1'b1) : i_data;
        fxmatch_input = "data_abs"
    else:
        # An input that is already non-negative needs only format conversion.
        QU_ABS = QU_IN
        fxmatch_input = "i_data"

    inst_ports_fxmatch = {
        "i_data": fxmatch_input,
        "o_data": "result_fixed",
    }
    ModuleFxMatch(QU_IN=QU_ABS, QU_OUT=QU_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS=inst_ports_fxmatch)  # type: ignore

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
