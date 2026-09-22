###################################################################################################
# Module Name: ICG
# Description: Latch-based Integrated Clock Gating cell.
#   Latches enable on the falling edge of clk to prevent glitches.
#   Output: gated_clk = clk & en_latched.
#   DC will map the latch to a standard cell latch from the target library.
#
# Author: Auto-generated
# Date: 2026.5.21
# Version: V1.0.0
###################################################################################################
from pytv.Converter import convert


@convert
def ModuleICG():
    """
    Latch-based Integrated Clock Gating (ICG) cell.

    Ports:
      clk    : input  - source clock
      en     : input  - clock enable (active high)
      clk_o  : output - gated clock (clk & en_latched)

    The enable signal is latched on the falling edge of clk to ensure
    glitch-free gated clock output.
    """
    #/ `timescale 1ns / 1ps
    #/ module ICG (
    #/     input  clk,
    #/     input  en,
    #/     output clk_o
    #/ );
    #/ reg en_latched;
    #/ always @(clk or en)
    #/     if (!clk) en_latched <= en;
    #/ assign clk_o = clk & en_latched;
    #/ endmodule
