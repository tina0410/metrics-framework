###################################################################################################
# Module Name: ComplexMul
# Description: Complex multiplication of two fixed-point complex numbers.
#   Supports two architectures selectable via METHOD parameter:
#     '4mul': Classic  (a+bi)(c+di) = (ac-bd) + (ad+bc)i
#             4 real multipliers + 1 adder + 1 subtractor
#     '3mul': Gauss    k1=c(a+b), k2=a(d-c), k3=b(d+c)
#             3 real multipliers + 5 adders/subtractors (saves 25% DSP)
#
#   Complex packing convention: {imag[DWT-1:0], real[DWT-1:0]}
#   Total complex width = 2 × QU_IN.DWT
#
# Author: Auto-generated
# Date: 2026.3.7
# Version: V0.1.0
# Dependency Modules:
#   - Mul  (V 0.2.1)
#   - Add  (V 0.2.1)
#   - Sub  (V 0.2.1)
###################################################################################################
import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from PyTU import QuMode, OfMode, QuType
from Mul import ModuleMul
from Add import ModuleAdd
from Sub import ModuleSub
from typing import Literal


    


@convert
def ModuleComplexMul(QU_IN_1: QuType, QU_IN_2: QuType, QU_OUT: QuType, N_CLK: int, QU_MODE: QuMode.TRN | QuMode.RND, OF_MODE: OfMode.WRP | OfMode.SAT, IF_RST_N: bool, METHOD: Literal['4mul', '3mul']):
    """
    Complex fixed-point multiplier.

    Computes  z = a × b  where a and b are complex numbers packed as
    ``{imag, real}`` in 2×DWT-bit vectors.

    Two methods:
      - '4mul': 4 real multiplies + 2 add/sub.  Minimal adder usage.
      - '3mul': 3 real multiplies + 5 add/sub.  Saves 25% DSP.

    Pipeline: N_CLK clock cycles total.
      - N_CLK is applied to each internal ModuleMul instance.
      - The post-multiply add/sub is combinational (N_CLK=0).

    Port widths:
      - i_data_1: 2 × QU_IN_1.DWT  (complex input A)
      - i_data_2: 2 × QU_IN_2.DWT  (complex input B)
      - o_data:   2 × QU_OUT.DWT   (complex output Z)

    :param QU_IN_1: QuType(12, 4, True)
    :param QU_IN_2: QuType(12, 4, True)
    :param QU_OUT: QuType(12, 4, True)
    :param N_CLK: 1
    :param QU_MODE: QuMode.TRN.TCPL
    :param OF_MODE: OfMode.SAT.TCPL
    :param IF_RST_N: True
    :param METHOD: '4mul'
    """
    COMP_DWT_1 = QU_IN_1.DWT
    COMP_DWT_2 = QU_IN_2.DWT
    COMP_DWT_O = QU_OUT.DWT
    CPLX_DWT_1 = 2 * COMP_DWT_1
    CPLX_DWT_2 = 2 * COMP_DWT_2
    CPLX_DWT_O = 2 * COMP_DWT_O

    # Product QuType: full precision before truncation
    PROD_DWT = QU_IN_1.DWT + QU_IN_2.DWT
    PROD_FRAC = QU_IN_1.FRAC + QU_IN_2.FRAC
    PROD_SIGNED = QU_IN_1.IF_SIGNED or QU_IN_2.IF_SIGNED
    QU_PROD = QuType(PROD_DWT, PROD_FRAC, PROD_SIGNED)

    # Sum QuType: add/sub result before output truncation
    SUM_DWT = PROD_DWT + 1
    SUM_FRAC = PROD_FRAC
    QU_SUM = QuType(SUM_DWT, SUM_FRAC, True)

    if N_CLK > 0:
        IF_RST_N_LIST = [IF_RST_N] * N_CLK
    else:
        IF_RST_N_LIST = [False]

    #/ `timescale 1ns / 1ps
    #/ module COMPLEXMUL(
    #/     i_data_1, i_data_2, o_data
    if N_CLK > 0:
        #/ , i_clk
        if any(IF_RST_N_LIST):
            #/ , i_rst_n
            pass
    #/ );

    #/ input  wire [`CPLX_DWT_1`-1:0] i_data_1;
    #/ input  wire [`CPLX_DWT_2`-1:0] i_data_2;
    #/ output wire [`CPLX_DWT_O`-1:0] o_data;
    if N_CLK > 0:
        #/ input wire i_clk;
        if any(IF_RST_N_LIST):
            #/ input wire i_rst_n;
            pass

    # ---- Extract real/imag components ----
    #/ wire [`COMP_DWT_1`-1:0] a_re = i_data_1[`COMP_DWT_1`-1:0];
    #/ wire [`COMP_DWT_1`-1:0] a_im = i_data_1[`CPLX_DWT_1`-1:`COMP_DWT_1`];
    #/ wire [`COMP_DWT_2`-1:0] b_re = i_data_2[`COMP_DWT_2`-1:0];
    #/ wire [`COMP_DWT_2`-1:0] b_im = i_data_2[`CPLX_DWT_2`-1:`COMP_DWT_2`];

    

    if METHOD == '4mul':
        
        # ============================================================
        # 4-Multiplier Classic Architecture
        # z_re = a_re*b_re - a_im*b_im
        # z_im = a_re*b_im + a_im*b_re
        # ============================================================

        #/ wire [`COMP_DWT_O`-1:0] prod_ar_br;
        #/ wire [`COMP_DWT_O`-1:0] prod_ai_bi;
        #/ wire [`COMP_DWT_O`-1:0] prod_ar_bi;
        #/ wire [`COMP_DWT_O`-1:0] prod_ai_br;

        # Mul 1: a_re * b_re
        ports_mul_ar_br = {
            'i_data_1': 'a_re',
            'i_data_2': 'b_re',
            'o_data': 'prod_ar_br',
        }
        if N_CLK > 0:
            ports_mul_ar_br['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports_mul_ar_br['i_rst_n'] = 'i_rst_n'
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT,
                  N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N,
                  PORTS=ports_mul_ar_br)  # type: ignore

        # Mul 2: a_im * b_im
        ports_mul_ai_bi = {
            'i_data_1': 'a_im',
            'i_data_2': 'b_im',
            'o_data': 'prod_ai_bi',
        }
        if N_CLK > 0:
            ports_mul_ai_bi['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports_mul_ai_bi['i_rst_n'] = 'i_rst_n'
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT,
                  N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N,
                  PORTS=ports_mul_ai_bi)  # type: ignore

        # Mul 3: a_re * b_im
        ports_mul_ar_bi = {
            'i_data_1': 'a_re',
            'i_data_2': 'b_im',
            'o_data': 'prod_ar_bi',
        }
        if N_CLK > 0:
            ports_mul_ar_bi['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports_mul_ar_bi['i_rst_n'] = 'i_rst_n'
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT,
                  N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N,
                  PORTS=ports_mul_ar_bi)  # type: ignore

        # Mul 4: a_im * b_re
        ports_mul_ai_br = {
            'i_data_1': 'a_im',
            'i_data_2': 'b_re',
            'o_data': 'prod_ai_br',
        }
        if N_CLK > 0:
            ports_mul_ai_br['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports_mul_ai_br['i_rst_n'] = 'i_rst_n'
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT,
                  N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N,
                  PORTS=ports_mul_ai_br)  # type: ignore

        # Sub: z_re = prod_ar_br - prod_ai_bi (combinational)
        #/ wire [`COMP_DWT_O`-1:0] z_re;
        ModuleSub(QU_IN_1=QU_OUT, QU_IN_2=QU_OUT, QU_OUT=QU_OUT,
                  N_CLK=0, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=False,
                  PORTS={'i_data_1': 'prod_ar_br', 'i_data_2': 'prod_ai_bi', 'o_data': 'z_re'})  # type: ignore

        # Add: z_im = prod_ar_bi + prod_ai_br (combinational)
        #/ wire [`COMP_DWT_O`-1:0] z_im;
        ModuleAdd(QU_IN_1=QU_OUT, QU_IN_2=QU_OUT, QU_OUT=QU_OUT,
                  N_CLK=0, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=False,
                  PORTS={'i_data_1': 'prod_ar_bi', 'i_data_2': 'prod_ai_br', 'o_data': 'z_im'})  # type: ignore

    elif METHOD == '3mul':
        # ============================================================
        # 3-Multiplier Gauss Architecture
        # s1 = a_re + a_im;   s2 = b_re + b_im;   d = b_im - b_re
        # k1 = a_re * b_re;   k2 = a_im * b_im;   k3 = s1 * s2
        # z_re = k1 - k2;     z_im = k3 - k1 - k2
        # ============================================================

        # Pre-add QuType: 1 extra bit for addition before multiplication
        PRE_DWT_1 = QU_IN_1.DWT + 1
        PRE_DWT_2 = QU_IN_2.DWT + 1
        QU_PRE_1 = QuType(PRE_DWT_1, QU_IN_1.FRAC, True)
        QU_PRE_2 = QuType(PRE_DWT_2, QU_IN_2.FRAC, True)

        # s1 = a_re + a_im (combinational)
        #/ wire [`PRE_DWT_1`-1:0] s1;
        ModuleAdd(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_1, QU_OUT=QU_PRE_1,
                  N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False,
                  PORTS={'i_data_1': 'a_re', 'i_data_2': 'a_im', 'o_data': 's1'})  # type: ignore

        # s2 = b_re + b_im (combinational)
        #/ wire [`PRE_DWT_2`-1:0] s2;
        ModuleAdd(QU_IN_1=QU_IN_2, QU_IN_2=QU_IN_2, QU_OUT=QU_PRE_2,
                  N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False,
                  PORTS={'i_data_1': 'b_re', 'i_data_2': 'b_im', 'o_data': 's2'})  # type: ignore

        # k1 = a_re * b_re
        #/ wire [`COMP_DWT_O`-1:0] k1;
        ports_mul_k1 = {
            'i_data_1': 'a_re',
            'i_data_2': 'b_re',
            'o_data': 'k1',
        }
        if N_CLK > 0:
            ports_mul_k1['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports_mul_k1['i_rst_n'] = 'i_rst_n'
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT,
                  N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N,
                  PORTS=ports_mul_k1)  # type: ignore

        # k2 = a_im * b_im
        #/ wire [`COMP_DWT_O`-1:0] k2;
        ports_mul_k2 = {
            'i_data_1': 'a_im',
            'i_data_2': 'b_im',
            'o_data': 'k2',
        }
        if N_CLK > 0:
            ports_mul_k2['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports_mul_k2['i_rst_n'] = 'i_rst_n'
        ModuleMul(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_OUT,
                  N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N,
                  PORTS=ports_mul_k2)  # type: ignore

        # k3 = s1 * s2
        #/ wire [`COMP_DWT_O`-1:0] k3;
        ports_mul_k3 = {
            'i_data_1': 's1',
            'i_data_2': 's2',
            'o_data': 'k3',
        }
        if N_CLK > 0:
            ports_mul_k3['i_clk'] = 'i_clk'
            if IF_RST_N:
                ports_mul_k3['i_rst_n'] = 'i_rst_n'
        ModuleMul(QU_IN_1=QU_PRE_1, QU_IN_2=QU_PRE_2, QU_OUT=QU_OUT,
                  N_CLK=N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N,
                  PORTS=ports_mul_k3)  # type: ignore

        # z_re = k1 - k2 (combinational)
        #/ wire [`COMP_DWT_O`-1:0] z_re;
        ModuleSub(QU_IN_1=QU_OUT, QU_IN_2=QU_OUT, QU_OUT=QU_OUT,
                  N_CLK=0, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=False,
                  PORTS={'i_data_1': 'k1', 'i_data_2': 'k2', 'o_data': 'z_re'})  # type: ignore

        # z_im = k3 - k1 - k2 = k3 - (k1 + k2)
        #/ wire [`COMP_DWT_O`-1:0] k1_plus_k2;
        ModuleAdd(QU_IN_1=QU_OUT, QU_IN_2=QU_OUT, QU_OUT=QU_OUT,
                  N_CLK=0, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=False,
                  PORTS={'i_data_1': 'k1', 'i_data_2': 'k2', 'o_data': 'k1_plus_k2'})  # type: ignore

        #/ wire [`COMP_DWT_O`-1:0] z_im;
        ModuleSub(QU_IN_1=QU_OUT, QU_IN_2=QU_OUT, QU_OUT=QU_OUT,
                  N_CLK=0, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=False,
                  PORTS={'i_data_1': 'k3', 'i_data_2': 'k1_plus_k2', 'o_data': 'z_im'})  # type: ignore

    else:
        raise ValueError(f"Invalid METHOD: {METHOD!r}. Must be '4mul' or '3mul'.")

    # ---- Pack output ----
    #/ assign o_data = {z_im, z_re};

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Test 4-mul method
    ModuleComplexMul(
        QU_IN_1=QuType(12, 4, True),
        QU_IN_2=QuType(12, 4, True),
        QU_OUT=QuType(12, 4, True),
        N_CLK=1,
        QU_MODE=QuMode.TRN.TCPL,
        OF_MODE=OfMode.SAT.TCPL,
        IF_RST_N=True,
        METHOD='4mul',
    )
