###################################################################################################
# Module Name: ComplexPack
# Description: Packs real and imaginary components into a single complex bus.
#   Convention: complex_out = {imag, real} (imag in MSBs, real in LSBs).
#   Supports optional pipeline register (N_CLK >= 1).
#
# Author: Auto-generated (refactoring)
# Date: 2026.3.15
# Version: V0.1.0
# Dependency Modules:
#   - Delay (V0.1.0) — when N_CLK > 0
###################################################################################################
import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))
from Delay import ModuleDelay


@convert
def ModuleComplexPack(COMP_DWT: int, N_CLK: int, IF_RST_N: bool) -> None:
    """
    Pack real and imaginary components into a complex bus: ``{imag, real}``.

    Pure combinational when ``N_CLK == 0``; pipelined when ``N_CLK > 0``.

    :param COMP_DWT: 12
        Per-component bit-width (real or imag).
    :type COMP_DWT: int
    :param N_CLK: 0
        Pipeline stages.  0 = combinational.
    :type N_CLK: int
    :param IF_RST_N: False
        Whether pipeline registers use asynchronous active-low reset.
    :type IF_RST_N: bool
    """
    CPLX_DWT = 2 * COMP_DWT

    #/ `timescale 1ns / 1ps
    #/ module ComplexPack (
    #/     input  [`COMP_DWT`-1:0] i_real,
    #/     input  [`COMP_DWT`-1:0] i_imag,
    #/     output [`CPLX_DWT`-1:0] o_data
    if N_CLK > 0:
        #/ , input clk
        if IF_RST_N:
            #/ , input rst_n
            pass
    #/ );

    #/ wire [`CPLX_DWT`-1:0] packed = {i_imag, i_real};

    if N_CLK == 0:
        #/ assign o_data = packed;
        pass
    else:
        ports_delay = {
            'i_data': 'packed',
            'o_data': 'o_data',
            'i_clk': 'clk',
        }
        if IF_RST_N:
            ports_delay['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=CPLX_DWT, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS=ports_delay)

    #/ endmodule
