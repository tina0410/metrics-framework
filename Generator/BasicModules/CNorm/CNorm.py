###################################################################################################
# Module Name: CNorm
# Description: Complex L1 norm: abs(real) + abs(imag), packed input {imag, real}.
# Version: 1.0.0
# Dependency Modules: Abs, Add (and their FxMatch / Delay dependencies)
###################################################################################################
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
try:
    from .Abs import ModuleAbs
    from .Add import ModuleAdd
    from .PyTU import QuType, QuMode, OfMode
except ImportError:
    from Abs import ModuleAbs
    from Add import ModuleAdd
    from PyTU import QuType, QuMode, OfMode


@convert
def ModuleCNorm(QU_IN: QuType, QU_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool):
    """Return the real L1 norm of a complex input, with N_CLK cycles latency.

    QU_IN describes one component; QU_OUT describes the scalar output.
    Unsigned full-width magnitudes preserve abs(most-negative input).
    The sum is quantized only at the output. This is not a Euclidean norm.
    """
    if min(QU_IN.DWT, QU_OUT.DWT) < 1:
        raise ValueError("All fixed-point widths must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")
    QU_ABS = QuType(QU_IN.DWT, QU_IN.FRAC, False)
    #/ module CNorm(i_data, o_data
    if N_CLK > 0:
        #/ , i_clk
        if IF_RST_N:
            #/ , i_rst_n
            pass
    #/ );
    #/ input wire [`2*QU_IN.DWT`-1:0] i_data;
    #/ output wire [`QU_OUT.DWT`-1:0] o_data;
    if N_CLK > 0:
        #/ input wire i_clk;
        if IF_RST_N:
            #/ input wire i_rst_n;
            pass
    #/ wire [`QU_IN.DWT`-1:0] abs_re;
    #/ wire [`QU_IN.DWT`-1:0] abs_im;
    for lane in range(2):
        ports = {
            "i_data": f"i_data[{(lane+1)*QU_IN.DWT-1}:{lane*QU_IN.DWT}]",
            "o_data": "abs_re" if lane == 0 else "abs_im",
        }
        ModuleAbs(QU_IN=QU_IN, QU_OUT=QU_ABS, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS=ports)  # type: ignore
    ports = {"i_data_1": "abs_re", "i_data_2": "abs_im", "o_data": "o_data"}
    if N_CLK > 0:
        ports["i_clk"] = "i_clk"
        if IF_RST_N:
            ports["i_rst_n"] = "i_rst_n"
    ModuleAdd(QU_IN_1=QU_ABS, QU_IN_2=QU_ABS, QU_OUT=QU_OUT, N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N, PORTS=ports)  # type: ignore
    #/ endmodule
