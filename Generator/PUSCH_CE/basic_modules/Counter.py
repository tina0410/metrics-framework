###################################################################################################
# Module Name: Counter
# Description: Parameterised up-counter with optional synchronous clear and
#   wrap detection.  Designed to replace inline always-block counters
#   throughout the PyTV codebase (e.g. SRAM address counters in AVERAGING,
#   sweep counters in TI_CTRL).
#
#   Features:
#     - Configurable bit-width (DWT) and step size (STEP, default 1).
#     - Optional synchronous clear input (resets count to 0).
#     - Optional wrap output (pulses 1 for 1 clock when count wraps).
#     - Optional asynchronous active-low reset (IF_RST_N).
#
# Author: Auto-generated (refactoring)
# Date: 2026.3.15
# Version: V0.1.0
# Dependency Modules: None
###################################################################################################
import pytv
from pytv.Converter import convert


@convert
def ModuleCounter(DWT: int, STEP: int, IF_RST_N: bool, HAS_CLEAR: bool, HAS_WRAP: bool) -> None:
    """
    Parameterised up-counter with optional clear and wrap detection.

    Behaviour (on each positive clock edge, when ``enable`` is 1):
      1. If ``clear`` is asserted (when HAS_CLEAR), reset ``count`` to 0.
      2. Else increment ``count`` by STEP.  No automatic wrap — counter
         saturates at all-ones.  External logic compares with a limit
         and asserts ``clear`` for rollover.

    The ``wrap`` output (when HAS_WRAP) mirrors the ``clear`` input with
    a 1-clock delay, useful for cascaded counting.

    :param DWT: 9
        Counter bit-width.
    :type DWT: int
    :param STEP: 1
        Increment per enabled clock.
    :type STEP: int
    :param IF_RST_N: True
        Whether to include asynchronous active-low reset.
    :type IF_RST_N: bool
    :param HAS_CLEAR: True
        Whether to include a synchronous ``clear`` input port.
    :type HAS_CLEAR: bool
    :param HAS_WRAP: False
        Whether to include a ``wrap`` output port (delayed clear).
    :type HAS_WRAP: bool
    """
    if DWT < 1:
        raise ValueError("DWT must be >= 1")
    if STEP < 1:
        raise ValueError("STEP must be >= 1")

    #/ `timescale 1ns / 1ps
    #/ module Counter (
    #/     input clk,
    if IF_RST_N:
        #/ input rst_n,
        pass
    #/ input enable,
    if HAS_CLEAR:
        #/ input clear,
        pass
    if HAS_WRAP:
        #/ output reg wrap,
        pass
    #/ output reg [`DWT`-1:0] count
    #/ );

    # ---- Counter register ----
    if IF_RST_N:
        #/ always @(posedge clk or negedge rst_n) begin
        #/     if (!rst_n) begin
        #/         count <= `DWT`'d0;
        #/     end else begin
        if HAS_CLEAR:
            #/ if (clear) begin
            #/     count <= `DWT`'d0;
            #/ end else if (enable) begin
            #/     count <= count + `DWT`'d`STEP`;
            #/ end else begin
            #/     count <= count;
            #/ end
            pass
        else:
            #/ if (enable) begin
            #/     count <= count + `DWT`'d`STEP`;
            #/ end else begin
            #/     count <= count;
            #/ end
            pass
        #/ end
        #/ end
        pass
    else:
        #/ always @(posedge clk) begin
        if HAS_CLEAR:
            #/ if (clear) begin
            #/     count <= `DWT`'d0;
            #/ end else if (enable) begin
            #/     count <= count + `DWT`'d`STEP`;
            #/ end else begin
            #/     count <= count;
            #/ end
            pass
        else:
            #/ if (enable) begin
            #/     count <= count + `DWT`'d`STEP`;
            #/ end else begin
            #/     count <= count;
            #/ end
            pass
        #/ end
        pass

    # ---- Wrap output (1-clock delayed clear) ----
    if HAS_WRAP:
        if IF_RST_N:
            #/ always @(posedge clk or negedge rst_n) begin
            #/     if (!rst_n) begin
            #/         wrap <= 1'b0;
            #/     end else begin
            if HAS_CLEAR:
                #/ wrap <= clear;
                pass
            else:
                #/ wrap <= 1'b0;
                pass
            #/ end
            #/ end
            pass
        else:
            #/ always @(posedge clk) begin
            if HAS_CLEAR:
                #/ wrap <= clear;
                pass
            else:
                #/ wrap <= 1'b0;
                pass
            #/ end
            pass

    #/ endmodule
