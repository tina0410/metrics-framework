from basic_modules.Delay import ModuleDelay
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))
import math

from basic_modules import ModuleDelay, ModuleSub, QuType, QuMode, OfMode
from helpers.port_helpers import delay_ports, arith_ports

@convert
def ModuleRB_COUNTER(min_RBs:int, max_RBs: int, RB_PARALLELISM: int) -> None:
    """
    RB-level counter for tracking current Resource Block index during channel estimation.
    
    Timing at symbol 0 when num_RBs = 10, RB_PARALLELISM = 4.
    | counter_enable | rb_counter | cond | current_RB_idx | remainder | sym | current_symbol_idx 
    | 1(posedge)     | 0          | 0/0  | X              | X         | X   | X
    | 1              | 4          | 0/0  | 0              | 10        | 0   | 0
    | 1              | 8          | 1/1  | 4              | 6         | 0   | 0
    | 1              | 0          | 0/0  | 8              | 2         | 1   | 0
    | 1              | 4          | 0/0  | 0              | 10        | 0   | 1 
    | 1              | 8          | 1/1  | 4              | 6         | 0   | 1 

    Parameters:
    :param min_RBs: 8
        Minimum number of Resource Blocks (check only).
    :param max_RBs: 52
        Maximum number of Resource Blocks (determines counter bit width only).
        Typical values: 24, 52, 106, 273 for different bandwidths.
    :type max_RBs: int
    :param RB_PARALLELISM: 8
        Number of RBs processed per clock cycle.
        Typical values: 1 (sequential), 2, 4 (for higher throughput designs).
    :type RB_PARALLELISM: int
    """
    
    if min_RBs < RB_PARALLELISM:
        raise ValueError("min_RBs cannot be less than RB_PARALLELISM")
    if min_RBs > max_RBs:
        raise ValueError("max_RBs should be larger or equal to min_RBs")
    if RB_PARALLELISM <= 0 or RB_PARALLELISM > max_RBs:
        raise ValueError("RB_PARALLELISM must be positive and not exceed max_RBs")
    
    # Calculate counter width to accommodate max_RBs (compile-time parameter)
    counter_width = math.ceil(math.log2(max_RBs)) if max_RBs > 1 else 1

    # Width of remainder
    remainder_width = math.ceil(math.log2(RB_PARALLELISM))
    Qu_num_RBs = QuType(DWT=counter_width, FRAC=0, IF_SIGNED=False)
    Qu_remainder = QuType(DWT=remainder_width, FRAC=0, IF_SIGNED=False)
    Qu_RB_parallelism = QuType(DWT=remainder_width+1, FRAC=0, IF_SIGNED=False)

    #/ `timescale 1ns / 1ps
    #/ module RB_COUNTER(
    #/     input                        clk,
    #/     input                        rst_n,
    #/     input                        ctrl_ctr_en,
    #/     input  [`counter_width`-1:0] num_RBs,
    #/     output [`counter_width`-1:0] ctrl_rb_idx_r,
    #/     output [`counter_width`-1:0] ctrl_rb_idx,
    if RB_PARALLELISM > 1:
        #/ output                         ctrl_sym_overflow,
        #/ output [`remainder_width`-1:0] ctrl_rb_remainder,
        pass

    #/ output ctrl_sym_switch
    #/ );
    #/ 
    #/ // Forward declarations
    #/ reg  [`counter_width`-1:0] rb_counter;
    #/ wire [`counter_width`-1:0] rb_limit_reg;
    if RB_PARALLELISM > 1:
        #/ // Multiple-RB PARALLELISM: Indice, overflow detection and Symbol switch conditions are provided.
        #/ // overflow_cond: the clk before the overflow RBs. Start calculation of remainder
        #/ wire overflow_cond = (rb_counter > rb_limit_reg);

        ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=True, PORTS=delay_ports('overflow_cond', 'ctrl_sym_overflow', if_rst_n=True))

        # remainder = num_RBs - rb_counter
        ModuleSub(QU_IN_1=Qu_num_RBs, QU_IN_2=Qu_num_RBs, QU_OUT=Qu_remainder, N_CLK=1, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.ZERO, IF_RST_N=True, PORTS=arith_ports('num_RBs', 'rb_counter', 'ctrl_rb_remainder', if_rst_n=True, n_clk=1))
    elif RB_PARALLELISM == 1:
        #/ // Single-RB PARALLELISM: Only counter & symbol switch are provided.
        pass

    #/ // rb_limit: pre-compute for more timing margin
    #/ // rb_limit_reg forward-declared above

    # might > 8-bit ripple adder, insert a clock
    # Changed 1clk later than num_RBs changed
    ModuleSub(QU_IN_1=Qu_num_RBs, QU_IN_2=Qu_RB_parallelism, QU_OUT=Qu_num_RBs, N_CLK=1, IF_RST_N=True, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.ZERO, PORTS=arith_ports('num_RBs', f"{remainder_width + 1}'d{RB_PARALLELISM}", 'rb_limit_reg', if_rst_n=True, n_clk=1))

    #/ // ctrl_ctr_en_d1: 1-cycle delayed ctrl_ctr_en.
    #/ // Suppresses spurious ctrl_sym_switch on the FIRST cycle of S_RUN
    #/ // when rb_counter=0 and rb_limit_reg=0 (Sub output not yet valid).
    #/ reg ctrl_ctr_en_d1;
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n)
    #/         ctrl_ctr_en_d1 <= 1'b0;
    #/     else
    #/         ctrl_ctr_en_d1 <= ctrl_ctr_en;
    #/ end

    #/ // switch_cond: the clk before next symbol
    #/ // Gate with ctrl_ctr_en AND ctrl_ctr_en_d1 to suppress spurious pulse
    #/ // at both reset AND the first S_RUN cycle (rb_limit_reg needs 1 clk to propagate).
    #/ wire switch_cond = (rb_counter >= rb_limit_reg) & ctrl_ctr_en & ctrl_ctr_en_d1;

    #/ // Guard uses addition-based comparison to avoid unsigned underflow.
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n) begin
    #/         rb_counter <= `counter_width`'d0;
    #/     end
    #/     else if (!ctrl_ctr_en) begin
    #/         rb_counter <= `counter_width`'d0;
    #/     end
    #/     else begin
    #/         if (switch_cond) begin
    #/             rb_counter <= `counter_width`'d0;
    #/         end else begin
    #/             rb_counter <= rb_counter + `counter_width`'d`RB_PARALLELISM`;
    #/         end
    #/     end
    #/ end

    ModuleDelay(DWT=counter_width, N_CLK=1, IF_RST_N=True, PORTS=delay_ports('rb_counter', 'ctrl_rb_idx_r', if_rst_n=True))

    ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=True, PORTS=delay_ports('switch_cond', 'ctrl_sym_switch', if_rst_n=True))

    #/ assign ctrl_rb_idx = rb_counter;
    #/ endmodule
