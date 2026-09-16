###################################################################################################
# Module Name: Delay
# Description: This module is used to delay the input data by N_CLK clock cycles.
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Dependency Modules: None
# Additional Notes: Modified to support type hints for better clarity.
###################################################################################################
import pytv
from pytv.Converter import convert


@convert
def ModuleDelay(DWT: int, N_CLK: int, IF_RST_N: bool | list[bool]):
    """
    Docstring for ModuleDelay

    :param DWT: 8
    :type DWT: int
    :param N_CLK: 1
    :type N_CLK: int
    :param IF_RST_N: True
    :type IF_RST_N: bool
    """
    if DWT < 1:
        raise ValueError("DWT must be positive.")
    if N_CLK < 0:
        raise ValueError("N_CLK must be non-negative.")

    # A scalar applies one reset policy to every stage. A list preserves the
    # per-stage reset contract used by the migrated jigger composite modules.
    if isinstance(IF_RST_N, bool):
        IF_RST_N_LIST = [IF_RST_N] * N_CLK
    elif isinstance(IF_RST_N, list):
        if len(IF_RST_N) != N_CLK:
            raise ValueError("IF_RST_N must contain exactly N_CLK entries.")
        if not all(isinstance(value, bool) for value in IF_RST_N):
            raise TypeError("Every IF_RST_N entry must be bool.")
        IF_RST_N_LIST = IF_RST_N
    else:
        raise TypeError("IF_RST_N must be bool or list[bool].")


    #/ module Delay(
    #/     i_data, o_data
    if N_CLK > 0:
        #/ , i_clk
        if any(IF_RST_N_LIST):
            #/ , i_rst_n
            pass
    #/ );
    #/ // Input and output ports
    #/ input  [`DWT`-1:0] i_data;
    #/ output [`DWT`-1:0] o_data;
    if N_CLK > 0:
        #/ input i_clk;
        if any(IF_RST_N_LIST):
            #/ input i_rst_n;
            pass

    if N_CLK == 0:
        #/ assign o_data = i_data;
        pass
    else: # N_CLK > 0
        #/ reg [`DWT`-1:0] data_d [0:`N_CLK`-1];
        if IF_RST_N_LIST[0]:
            #/ always @(posedge i_clk, negedge i_rst_n) begin
            #/     if (~i_rst_n) begin
            #/         data_d[0] <= `DWT`'b0;
            #/     end
            #/     else begin
            #/         data_d[0] <= i_data;
            #/     end
            #/ end
            pass
        else:
            #/ always @(posedge i_clk) begin
            #/     data_d[0] <= i_data;
            #/ end
            pass
        # Delaying the data (if N_CLK > 1)
        for i in range(1, N_CLK):
            if IF_RST_N_LIST[i]:
                #/ always @(posedge i_clk, negedge i_rst_n) begin
                #/     if (~i_rst_n) begin
                #/         data_d[`i`] <= `DWT`'b0;
                #/     end
                #/     else begin
                #/         data_d[`i`] <= data_d[`i-1`];
                #/     end
                #/ end
                pass
            else:
                #/ always @(posedge i_clk) begin
                #/     data_d[`i`] <= data_d[`i-1`];
                #/ end
                pass
        pass
        #/ assign o_data = data_d[`N_CLK`-1];

    #/ endmodule
