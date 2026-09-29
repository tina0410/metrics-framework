###################################################################################################
# Module Name: CMul
# Description: Complex multiplication, full precision until output conversion.
# Version: 1.0.0
# Dependency Modules: Mul, Add, FxMatch, Delay
###################################################################################################
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
try:
    from .Mul import ModuleMul
    from .Add import ModuleAdd
    from .FxMatch import ModuleFxMatch
    from .PyTU import QuType, QuMode, OfMode
except ImportError:
    from Mul import ModuleMul
    from Add import ModuleAdd
    from FxMatch import ModuleFxMatch
    from PyTU import QuType, QuMode, OfMode


@convert
def ModuleCMul(QU_IN_1: QuType, QU_IN_2: QuType, QU_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool, METHOD: str = '4mul'):
    """Compute (ar*br-ai*bi, ar*bi+ai*br), packed as {imag, real}.

    METHOD selects four real multipliers or Gauss's three multipliers. Both
    preserve exact intermediate values and quantize each output once. The
    output pipeline has N_CLK cycles. QuTypes describe component formats.
    Legacy ComplexMul remains available with its original stage quantization.
    """
    if min(QU_IN_1.DWT, QU_IN_2.DWT, QU_OUT.DWT) < 1:
        raise ValueError("All component widths must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")
    if METHOD not in ('4mul', '3mul'):
        raise ValueError("METHOD must be '4mul' or '3mul'.")
    # Signed workspace also accommodates unsigned inputs and Gauss pre-adds.
    W1 = QU_IN_1.DWT + int(not QU_IN_1.IF_SIGNED)
    W2 = QU_IN_2.DWT + int(not QU_IN_2.IF_SIGNED)
    QU_WORK = QuType(W1 + W2 + 3, QU_IN_1.FRAC + QU_IN_2.FRAC, True)
    #/ module CMul(i_data_1, i_data_2, o_data
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
    #/ wire [`QU_IN_1.DWT`-1:0] ar = i_data_1[`QU_IN_1.DWT`-1:0];
    #/ wire [`QU_IN_1.DWT`-1:0] ai = i_data_1[`2*QU_IN_1.DWT`-1:`QU_IN_1.DWT`];
    #/ wire [`QU_IN_2.DWT`-1:0] br = i_data_2[`QU_IN_2.DWT`-1:0];
    #/ wire [`QU_IN_2.DWT`-1:0] bi = i_data_2[`2*QU_IN_2.DWT`-1:`QU_IN_2.DWT`];
    #/ wire signed [`QU_WORK.DWT`-1:0] p0, p1, p2, re_exact, im_exact;
    ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_WORK, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'ar', 'i_data_2': 'br', 'o_data': 'p0'})  # type: ignore
    ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_WORK, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'ai', 'i_data_2': 'bi', 'o_data': 'p1'})  # type: ignore
    #/ assign re_exact = p0 - p1;
    if METHOD == '4mul':
        #/ wire signed [`QU_WORK.DWT`-1:0] p3;
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_WORK, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'ar', 'i_data_2': 'bi', 'o_data': 'p2'})  # type: ignore
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_WORK, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'ai', 'i_data_2': 'br', 'o_data': 'p3'})  # type: ignore
        #/ assign im_exact = p2 + p3;
        pass
    else:
        QU_PRE_1 = QuType(W1 + 1, QU_IN_1.FRAC, True)
        QU_PRE_2 = QuType(W2 + 1, QU_IN_2.FRAC, True)
        #/ wire [`QU_PRE_1.DWT`-1:0] a_sum;
        #/ wire [`QU_PRE_2.DWT`-1:0] b_sum;
        ModuleAdd(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_1, QU_OUT=QU_PRE_1, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'ar', 'i_data_2': 'ai', 'o_data': 'a_sum'})  # type: ignore
        ModuleAdd(QU_IN_1=QU_IN_2, QU_IN_2=QU_IN_2, QU_OUT=QU_PRE_2, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'br', 'i_data_2': 'bi', 'o_data': 'b_sum'})  # type: ignore
        ModuleMul(QU_IN_1=QU_PRE_1, QU_IN_2=QU_PRE_2, QU_OUT=QU_WORK, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'a_sum', 'i_data_2': 'b_sum', 'o_data': 'p2'})  # type: ignore
        #/ assign im_exact = p2 - p0 - p1;
        pass
    for lane in range(2):
        ports = {
            'i_data': 're_exact' if lane == 0 else 'im_exact',
            'o_data': f'o_data[{(lane+1)*QU_OUT.DWT-1}:{lane*QU_OUT.DWT}]',
        }
        if N_CLK > 0:
            ports['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports['i_rst_n'] = 'i_rst_n'
        ModuleFxMatch(QU_IN=QU_WORK, QU_OUT=QU_OUT, N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N, PORTS=ports)  # type: ignore
    #/ endmodule
