###################################################################################################
# Module Name: CSub
# Description: Fixed-point complex subtraction, packed as {imag, real}.
# Version: 1.0.0
# Dependency Modules: Sub (and its FxMatch / Delay dependencies)
###################################################################################################
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
try:
    from .Sub import ModuleSub
    from .PyTU import QuType, QuMode, OfMode
except ImportError:
    from Sub import ModuleSub
    from PyTU import QuType, QuMode, OfMode


@convert
def ModuleCSub(QU_IN_1: QuType, QU_IN_2: QuType, QU_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool):
    """Componentwise complex subtraction with N_CLK cycles of latency.

    Each QuType describes one component. Quantization and overflow apply
    independently to the real and imaginary results, exactly once each.
    """
    if min(QU_IN_1.DWT, QU_IN_2.DWT, QU_OUT.DWT) < 1:
        raise ValueError("All component widths must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")
    #/ module CSub(i_data_1, i_data_2, o_data
    if N_CLK > 0:
        #/ , i_clk
        if IF_RST_N:
            #/ , i_rst_n
            pass
    #/ );
    #/ input wire [`2*QU_IN_1.DWT`-1:0] i_data_1;
    #/ input wire [`2*QU_IN_2.DWT`-1:0] i_data_2;
    #/ output wire [`2*QU_OUT.DWT`-1:0] o_data;
    if N_CLK > 0:
        #/ input wire i_clk;
        if IF_RST_N:
            #/ input wire i_rst_n;
            pass
    for lane in range(2):
        ports = {
            "i_data_1": f"i_data_1[{(lane+1)*QU_IN_1.DWT-1}:{lane*QU_IN_1.DWT}]",
            "i_data_2": f"i_data_2[{(lane+1)*QU_IN_2.DWT-1}:{lane*QU_IN_2.DWT}]",
            "o_data": f"o_data[{(lane+1)*QU_OUT.DWT-1}:{lane*QU_OUT.DWT}]",
        }
        if N_CLK > 0:
            ports["i_clk"] = "i_clk"
            if IF_RST_N:
                ports["i_rst_n"] = "i_rst_n"
        ModuleSub(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT, N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N, PORTS=ports)  # type: ignore
    #/ endmodule
