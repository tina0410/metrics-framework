###################################################################################################
# Module Name: ComplexUnpack
# Description: Unpacks a complex bus into real and imaginary components.
#   Convention: complex_in = {imag, real} (imag in MSBs, real in LSBs).
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
def ModuleComplexUnpack(COMP_DWT: int, N_CLK: int, IF_RST_N: bool) -> None:
    """
    Unpack a complex bus into real and imaginary components.

    Input convention: ``i_data = {imag, real}`` (imag in MSBs, real in LSBs).
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
    #/ module ComplexUnpack (
    #/     input  [`CPLX_DWT`-1:0] i_data,
    #/     output [`COMP_DWT`-1:0] o_real,
    #/     output [`COMP_DWT`-1:0] o_imag
    if N_CLK > 0:
        #/ , input clk
        if IF_RST_N:
            #/ , input rst_n
            pass
    #/ );

    #/ wire [`COMP_DWT`-1:0] real_comb = i_data[`COMP_DWT`-1:0];
    #/ wire [`COMP_DWT`-1:0] imag_comb = i_data[`CPLX_DWT`-1:`COMP_DWT`];

    if N_CLK == 0:
        #/ assign o_real = real_comb;
        #/ assign o_imag = imag_comb;
        pass
    else:
        ports_delay_re = {
            'i_data': 'real_comb',
            'o_data': 'o_real',
            'i_clk': 'clk',
        }
        if IF_RST_N:
            ports_delay_re['i_rst_n'] = 'rst_n'
        ModuleDelay(
            DWT=COMP_DWT,
            N_CLK=N_CLK,
            IF_RST_N=IF_RST_N,
            PORTS=ports_delay_re,  # type: ignore
        )

        ports_delay_im = {
            'i_data': 'imag_comb',
            'o_data': 'o_imag',
            'i_clk': 'clk',
        }
        if IF_RST_N:
            ports_delay_im['i_rst_n'] = 'rst_n'
        ModuleDelay(
            DWT=COMP_DWT,
            N_CLK=N_CLK,
            IF_RST_N=IF_RST_N,
            PORTS=ports_delay_im,  # type: ignore
        )

    #/ endmodule
