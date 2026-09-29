###################################################################################################
# Module Name: SxMatch
# Description: FxMatch followed by a bit-preserving fixed-point value shift.
# Author: OpenAI Codex
# Date: 2026.8.4
# Version: V0.1.0
# Dependency Modules:
#   - Delay (V0.1.0)
#   - FxMatch (V0.2.2)
###################################################################################################
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

try:
    from .Delay import ModuleDelay
    from .FxMatch import ModuleFxMatch
    from .PyTU import OfMode, QuMode, QuType
except ImportError:
    from Delay import ModuleDelay
    from FxMatch import ModuleFxMatch
    from PyTU import OfMode, QuMode, QuType


@convert
def ModuleSxMatch(QU_IN: QuType, QU_OUT: QuType, SHIFT: int, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool):
    """Convert through FxMatch, then reinterpret its output with ``SHIFT``.

    The physical output bits are produced by an FxMatch whose output type is
    ``(QU_OUT.DWT, QU_OUT.FRAC + SHIFT, QU_OUT.IF_SIGNED)``. Those same bits
    are exposed as ``QU_OUT``. Positive ``SHIFT`` therefore multiplies the
    matched value by a power of two; negative ``SHIFT`` divides it.

    No losslessness constraint is imposed. Quantization and overflow are
    handled entirely by the internal FxMatch using ``QU_MODE`` and
    ``OF_MODE``.
    """
    if not isinstance(SHIFT, int) or isinstance(SHIFT, bool):
        raise TypeError("SHIFT must be an integer.")
    if QU_IN.DWT < 1:
        raise ValueError("QU_IN.DWT must be positive.")
    if QU_OUT.DWT < 1:
        raise ValueError("QU_OUT.DWT must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")

    QU_MATCH = QuType(
        DWT=QU_OUT.DWT,
        FRAC=QU_OUT.FRAC + SHIFT,
        IF_SIGNED=QU_OUT.IF_SIGNED,
    )

    #/ module SxMatch(
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

    # QU_MATCH configures the generated bits. QU_OUT is only the public
    # interpretation of those same bits, so no shifting hardware is emitted.
    #/ wire [`QU_MATCH.DWT`-1:0] data_matched;
    fxmatch_ports = {
        "i_data": "i_data",
        "o_data": "data_matched",
    }
    ModuleFxMatch(QU_IN=QU_IN, QU_OUT=QU_MATCH, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS=fxmatch_ports)  # type: ignore

    delay_ports = {
        "i_data": "data_matched",
        "o_data": "o_data",
    }
    if N_CLK > 0:
        delay_ports["i_clk"] = "i_clk"
        if IF_RST_N:
            delay_ports["i_rst_n"] = "i_rst_n"

    ModuleDelay(DWT=QU_OUT.DWT, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS=delay_ports)  # type: ignore

    #/ endmodule
