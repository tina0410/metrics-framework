from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

# Import submodule definitions
from basic_modules import QuType, ModuleDelay, ModuleFxMatch, QuMode, OfMode, ModuleAdd, ModuleSub
from delay_budget import DelayBudget, cost_adder, DEFAULT_BUDGET


def ls_rot_pipeline_depth(Qu_IN: QuType) -> int:
    """Minimum pipeline depth for LS_ROT (callable without instantiation).

    Combinational cost: one Add/Sub with width = Qu_IN.DWT + 2.
    """
    Qu_SUM_DWT = Qu_IN.DWT + 2
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    budget.add_comb(cost_adder(Qu_SUM_DWT), tag="ls_rot_add_sub")
    return budget.pipeline_depth + 1  # +1 for output register


@convert
def ModuleLS_ROT(parallelism: int, Qu_IN: QuType, Qu_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND | None = None, OF_MODE: OfMode.WRP | OfMode.SAT | None = None) -> None:
    """
    Least Squares (LS) rotator — the conjugate-multiply stage of LS channel
    estimation.

    Consumes the effective pilot φ = in × w_f × (-1)^w_t (2-bit DMRS-encoded
    output of OCC) on the `whid_i` input, and the pre-scaled received symbol
    Y_PRE = Y/(√2·β_DMRS) on `in_complex_i`.  Produces:

        h_ls = Y_PRE × conj(φ)  where  φ ∈ {±1±j},  |φ|² = 2

    Since Y_PRE already includes ÷(√2·β_DMRS) = ÷√(2·N_CDM), the output
    h_ls = Y × conj(φ) / (√2·β_DMRS) = Y × conj(φ_unit) / β_DMRS, which
    matches the 3GPP LS estimate Y / ref (with ref = φ_unit × β_DMRS).

    Mathematical Operation:
        Z_out = Z_in × conj(a + j·b) = Z_in × (a − j·b)
    where:
        a = (-1)^whid[0]    (real sign of φ)
        b = (-1)^whid[1]    (imag sign of φ — negated internally for conj)

    Signal Encoding (whid carries φ on DMRS constellation):
    ```
    whid    φ            conj(φ)       Operation on Z_in = x + jy
    ────────────────────────────────────────────────────────────────
    00     1 + j        1 - j          Z_out = (x+y) + j(y-x)
    01    -1 + j       -1 - j          Z_out = (-x+y) + j(-y-x)
    10     1 - j        1 + j          Z_out = (x-y) + j(y+x)
    11    -1 - j       -1 + j          Z_out = (-x-y) + j(-y+x)
    ```

    Implementation Strategy:
    Z × (a − j·b) = (a·x + b·y) + j·(a·y − b·x)
        Real: a·x + b·y
        Imag: a·y − b·x
    Realized by driving `sign_b = ~whid[1]` into the same adder/sub tree used
    for forward multiply; the single inverter converts forward→conjugate
    complex multiply at zero gate cost beyond the existing adder/sub.

    Parameters:
    --------------
    :param parallelism : 3
        Number of parallel paths to process simultaneously.
    :param Qu_IN : QuType(11, 4, True)
        Quantization type of input data.
    :param Qu_OUT : QuType(12, 4, True)
        Quantization type of output data.
    :param N_CLK : 3 
        Number of clock cycles for output delay (pipeline registers).
    """
   
    if Qu_IN.IF_SIGNED == False or Qu_OUT.IF_SIGNED == False:
        raise ValueError("LS-estimated datas must be signed types.")

    # Standalone leaf generation may omit modes; the integrated LS path passes
    # the semantic arithmetic policy explicitly at its own quantization sites.
    if QU_MODE is None:
        QU_MODE = QuMode.TRN.TCPL
    if OF_MODE is None:
        OF_MODE = OfMode.WRP.TCPL

    # =========================================================================
    # DelayBudget analysis — compute minimum pipeline depth for LS_ROT
    # =========================================================================
    # Per path:
    #   XOR sign inversion: cost 0 (bit-wise)
    #   Sub(a*x - b*y): width Qu_SUM.DWT = Qu_IN.DWT + 2
    #   Add(b*x + a*y): width Qu_SUM.DWT = Qu_IN.DWT + 2
    #   FxMatch (bit-select): cost 0
    Qu_SUM_budget = QuType(DWT=Qu_IN.DWT + 2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    budget.add_comb(cost_adder(Qu_SUM_budget.DWT), tag="ls_rot_add_sub")

    LS_ROT_MIN_PIPELINE_DEPTH = budget.pipeline_depth + 1  # +1 for output register

    if N_CLK < LS_ROT_MIN_PIPELINE_DEPTH:
        raise ValueError(
            f"LS_ROT: N_CLK={N_CLK} is below the minimum pipeline depth "
            f"{LS_ROT_MIN_PIPELINE_DEPTH} required by DelayBudget analysis.\n"
            f"{budget.summary()}"
        )

    #/ `timescale 1ns / 1ps
    #/ module LS_ROT(
    if N_CLK > 0:
        #/ input clk,
        pass

    for i in range(parallelism):
        p_whid         = f"whid_{i}"
        p_in_complex  = f"in_complex_{i}"
        p_out_complex = f"out_complex_{i}"
        comma = "," if i < parallelism - 1 else ""
        #/ input  [1:0]                `p_whid`,
        #/ input  [`2*Qu_IN.DWT`-1:0]  `p_in_complex`,
        #/ output [`2*Qu_OUT.DWT`-1:0] `p_out_complex``comma`
        pass
    #/ );

    Qu_EXT = QuType(DWT=Qu_IN.DWT + 1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
    Qu_SUM = QuType(DWT=Qu_IN.DWT + 2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)

    for i in range(parallelism):
        name_whid = f"whid_{i}"
        name_in  = f"in_complex_{i}"
        name_out = f"out_complex_{i}"

        in_real = f"in_real_{i}"
        in_imag = f"in_imag_{i}"

        sign_a = f"sign_a_{i}"
        sign_b = f"sign_b_{i}"

        x_ext  = f"x_ext_{i}"
        y_ext  = f"y_ext_{i}"


        real_calc = f"real_calc_{i}"
        imag_calc = f"imag_calc_{i}"

        real_out  = f"real_out_{i}"
        imag_out  = f"imag_out_{i}"

        out_inst  = f"out_inst_{i}"

        #/ // ======================= Path `i` =======================

        #/ wire [`Qu_IN.DWT`-1:0] `in_real` = `name_in`[`Qu_IN.DWT`-1:0];
        #/ wire [`Qu_IN.DWT`-1:0] `in_imag` = `name_in`[`2*Qu_IN.DWT`-1:`Qu_IN.DWT`];

        # whid encodes the effective pilot φ in DMRS {±1±j} form:
        #   whid[0] = real_sign(φ),  whid[1] = imag_sign(φ).
        # LS_ROT computes Z × conj(φ), i.e. forward multiply with imag sign
        # inverted. So sign_b inverts whid[1] before driving the signed-y path.
        #/ wire `sign_a` = `name_whid`[0];
        #/ wire `sign_b` = ~`name_whid`[1];

        # Sign extension
        #/ wire [`Qu_EXT.DWT`-1:0] `x_ext` = {`in_real`[`Qu_IN.DWT`-1], `in_real`};
        #/ wire [`Qu_EXT.DWT`-1:0] `y_ext` = {`in_imag`[`Qu_IN.DWT`-1], `in_imag`};

        # Signed versions for real part: a*x, b*y
        x_s_real    = f"x_s_real_{i}"
        y_s_real    = f"y_s_real_{i}"
        #/ wire [`Qu_EXT.DWT`-1:0] `x_s_real` = (`x_ext` ^ {`Qu_EXT.DWT`{`sign_a`}}) + `sign_a`;
        #/ wire [`Qu_EXT.DWT`-1:0] `y_s_real` = (`y_ext` ^ {`Qu_EXT.DWT`{`sign_b`}}) + `sign_b`;

        # Signed versions for imag part: b*x, a*y (swapped signs)
        x_s_imag = f"x_s_imag_{i}"
        y_s_imag = f"y_s_imag_{i}"
        #/ wire [`Qu_EXT.DWT`-1:0] `x_s_imag` = (`x_ext` ^ {`Qu_EXT.DWT`{`sign_b`}}) + `sign_b`;
        #/ wire [`Qu_EXT.DWT`-1:0] `y_s_imag` = (`y_ext` ^ {`Qu_EXT.DWT`{`sign_a`}}) + `sign_a`;

        # Intermediate wire declarations for proper bit widths
        #/ wire [`Qu_SUM.DWT`-1:0] `real_calc`;
        #/ wire [`Qu_SUM.DWT`-1:0] `imag_calc`;
        #/ wire [`Qu_OUT.DWT`-1:0] `real_out`;
        #/ wire [`Qu_OUT.DWT`-1:0] `imag_out`;

        # real = a*x - b*y
        ModuleSub(QU_IN_1=Qu_EXT, QU_IN_2=Qu_EXT, QU_OUT=Qu_SUM, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': x_s_real, 'i_data_2': y_s_real, 'o_data': real_calc})  # Sub is full-precision  # type: ignore

        # imag = b*x + a*y (using swapped sign versions)
        ModuleAdd(QU_IN_1=Qu_EXT, QU_IN_2=Qu_EXT, QU_OUT=Qu_SUM, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': x_s_imag, 'i_data_2': y_s_imag, 'o_data': imag_calc})  # Add is full-precision  # type: ignore

        ModuleFxMatch(QU_IN=Qu_SUM, QU_OUT=Qu_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS={'i_data': real_calc, 'o_data': real_out})  # type: ignore

        ModuleFxMatch(QU_IN=Qu_SUM, QU_OUT=Qu_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS={'i_data': imag_calc, 'o_data': imag_out})  # type: ignore

        #/ wire [`2*Qu_OUT.DWT`-1:0] `out_inst` = {`imag_out`, `real_out`};

        ports_delay = {'i_data': out_inst, 'o_data': name_out}  # type: ignore
        if N_CLK > 0:
            ports_delay['i_clk'] = 'clk'

        ModuleDelay(DWT=2 * Qu_OUT.DWT, N_CLK=N_CLK, IF_RST_N=False, PORTS=ports_delay)  # type: ignore

    _min_depth = ls_rot_pipeline_depth(Qu_IN)
    #/ // Timing budget: N_CLK=`N_CLK` (auto-min=`_min_depth`)
    #/ endmodule
