from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from basic_modules import QuType, ModuleDelay
import math


@convert
def ModuleY_RB_ALIGN(Qu_Y: QuType, RB_PARALLELISM: int, RE_PER_RB: int) -> None:
    """
    Per-RB boundary aligner for INPUT_MODE='B'.

    Pipeline position:
      per-RB Y_PATH_REDUCE (valid/ready) -> Y_RB_ALIGN (ready) -> LS pipeline
    
    Timing:
    (X) = data is registered, output 0, backpressure upstream; 
    (R) = use registered data
    
    Critical Path = 8-bit ripple adder.
    
    num_RBs = 53 
    | RB_0 | RB_1 | RB_2 | RB_3 | current_RB_idx | sym_overflow | remainder
    | 48   | 49   | 50   | 51   | 48             | 0            | 0
    | 52   | 0(X) | 1(X) | 2(X) | 52             | 1            | 1
    | 0(R) | 1(R) | 2(R) | 3    | 0              | 0            | 0

    num_RBs = 54
    | RB_0 | RB_1 | RB_2 | RB_3 | current_RB_idx | sym_overflow | remainder
    | 48   | 49   | 50   | 51   | 48             | 0            | 0
    | 52   | 53   | 0(X) | 1(X) | 52             | 1            | 2
    | 0(R) | 1(R) | 2    | 3    | 0              | 0            | 0

    Parameters:
    :param Qu_Y: QuType(10,8,True)

    :param RB_PARALLELISM: 4

    :param RE_PER_RB: 6

    """

    if RB_PARALLELISM < 1:
        raise ValueError(f"RB_PARALLELISM must be >= 1, got {RB_PARALLELISM}")
    if RE_PER_RB < 1:
        raise ValueError(f"RE_PER_RB must be >= 1, got {RE_PER_RB}")

    remainder_width = math.ceil(math.log2(RB_PARALLELISM))
    RB_BITS = RE_PER_RB * 2 * Qu_Y.DWT

    #/ `timescale 1ns / 1ps
    #/ module Y_RB_ALIGN(
    #/     input clk,
    #/     input rst_n,
    if RB_PARALLELISM > 1:
        #/ input [`remainder_width`-1:0] remainder,
        #/ input                         sym_overflow,
        pass
    for rb in range(RB_PARALLELISM):
        #/ input [`RB_BITS`-1:0] `f"Y_rb_{rb}"`,
        pass

    for rb in range(RB_PARALLELISM):
        #/ input `f"Y_valid_rb_{rb}"`,
        pass

    for rb in range(RB_PARALLELISM):
        #/ output `f"Y_ready_rb_{rb}"`,
        pass

    for rb in range(RB_PARALLELISM):
        comma = ',' if rb < RB_PARALLELISM - 1 else ''
        #/ output [`RB_BITS`-1:0] `f"Y_out_rb_{rb}"``comma`
        pass

    #/ );

    if RB_PARALLELISM == 1:
        # Bypass this module.
        # As this module only works when INPUT_MODE is B, corresponding ready signal is needed.
        #/ assign Y_out_rb_0   = Y_valid_rb_0 ? Y_rb_0 : `RB_BITS`'b0;
        #/ assign Y_ready_rb_0 = 1'b1;
        pass
    else:
        # Input Gating
        for rb in range(RB_PARALLELISM):
            #/ wire [`RB_BITS`-1:0] `f"Y_in_rb_{rb}"` = `f"Y_valid_rb_{rb}"` ? `f"Y_rb_{rb}"` : `RB_BITS`'b0;
            pass
        # =====================================================================
        # Per-symbol valid-gated passthrough (RB_PARALLELISM >= 2)
        # =====================================================================
        # Under the authoritative interface contract each symbol's RBs are
        # presented on that symbol's own beats, starting fresh from RB0 on the
        # first beat of the symbol.  A partial final beat (num_RBs % RBP != 0)
        # carries only the low `remainder` tail lanes; the upper padding lanes
        # are marked invalid by the upstream producer (Y_valid = 0).
        #
        # The per-lane `Y_valid` gating in ``Y_in_rb_*`` already drops those
        # padding lanes, so the aligner is a pure pass-through: no boundary
        # buffering, no replay, and no overflow-driven zeroing.  Consuming
        # `sym_overflow`/`remainder` here would zero the NEXT symbol's fresh
        # head lanes, because those control signals are registered one clock
        # behind the Y data by RB_COUNTER (they align with the LS pipeline, not
        # with the combinational Y input).
        #
        # Ready is asserted unconditionally: every valid lane is consumed every
        # beat.  The producer already holds a beat stable until all *active*
        # lanes are ready, so no backpressure is required.
        # =====================================================================

        # -- Output passthrough: out[rb] = Y_valid ? Y_rb : 0 --
        for rb in range(RB_PARALLELISM):
            #/ assign `f"Y_out_rb_{rb}"` = `f"Y_in_rb_{rb}"`;
            pass

        # -- Ready signals: always ready (valid lanes are consumed every beat) --
        for rb in range(RB_PARALLELISM):
            #/ assign `f"Y_ready_rb_{rb}"` = 1'b1;
            pass

    #/ endmodule
