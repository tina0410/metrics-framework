###################################################################################################
# Module Name: Delay
# Description: This module is used to delay the input data by N_CLK clock cycles.
# Author: Changhan Li
# Date: 2024.10.12
# Version: V0.1.0
# Doc Version: V0.1.0
# Dependency Modules: None
# Additional Notes: Modified to support type hints for better clarity.
###################################################################################################
import pytv
from pytv.Converter import convert


@convert
def ModuleDelay(DWT: int, N_CLK: int, IF_RST_N: bool):
    """
    Docstring for ModuleDelay
    
    :param DWT: 8
    :type DWT: int
    :param N_CLK: 1
    :type N_CLK: int
    :param IF_RST_N: True
    :type IF_RST_N: bool
    """
    # Parsing the input arguments
    # the IF_RST_N_LIST should not be passed to the submodules
    if N_CLK > 0:
        # Expand the boolean to a list of the same value
        IF_RST_N_LIST = [IF_RST_N] * N_CLK
    elif N_CLK == 0:
        IF_RST_N_LIST = [False] # No sequential logic. This is only for type alignment
    else: # N_CLK < 0
        raise ValueError("N_CLK must be non-negative.")
    
    
    #/ `timescale 1ns / 1ps
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
    

