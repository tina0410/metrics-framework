import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from basic_modules import QuType, ModuleDelay
from v_xor_tree import ModuleXOR_TREE
from typing import Literal
import sys


DMRS_TYPE1_RE_PER_RB = 6
DMRS_TYPE2_RE_PER_RB = 4
DMRS_TYPE3_RE_PER_RB = 2


def dmrs_re_parallelism(RB_PARALLELISM: int, dmrs_Type: int | Literal["Hybrid"] = 1) -> int:
    """Return DMRS RE parallelism from RB parallelism and DMRS type.

    - Type 1: 6 RE/RB
    - Type 2: 4 RE/RB
    - Type 3: 2 RE/RB
    - Hybrid: width sized to Type 1 (6 RE/RB), Type 2 uses leading 4 RE/RB lanes
    """
    if RB_PARALLELISM <= 0:
        raise ValueError("RB_PARALLELISM must be > 0")
    if dmrs_Type == 1 or dmrs_Type == "Hybrid":
        return RB_PARALLELISM * DMRS_TYPE1_RE_PER_RB
    if dmrs_Type == 2:
        return RB_PARALLELISM * DMRS_TYPE2_RE_PER_RB
    if dmrs_Type == 3:
        return RB_PARALLELISM * DMRS_TYPE3_RE_PER_RB
    raise ValueError("dmrs_Type must be 1, 2, 3, or 'Hybrid'")


@convert
def ModuleDMRS_SEQUENCE_GENERATION(RB_PARALLELISM:int, PIPE_CYCLES: int, IF_RST_N: bool, dmrs_Type: int | Literal["Hybrid"] = 1, HAS_ENABLE: bool = False, HAS_CTX: bool = False, N_CTX_SLOTS: int = 2) -> None:
    """
    This module generates the 2-bit DMRS base sequence for a fixed number of r(n) in frequency direction from c_init value.
   
    This module resets the LFSR to State N = 1600 upon c_init_strb or rst_n assertion. c_init_strb will be delayed internally to match the latency of the XOR tree.
    
    :param RB_PARALLELISM: 1
    Number of RBs processed in parallel for DMRS sequence generation.
    Effective RE parallelism is derived by DMRS type:
    - Type 1: RB_PARALLELISM * 6 RE/RB
    - Type 2: RB_PARALLELISM * 4 RE/RB
    - Hybrid: output width follows Type 1 (6 RE/RB), Type 2 uses leading 4 RE/RB lanes.
    Maybe it could be a type like List[int], and we can directly parse TRUE_INDEX_LIST to this function.
    :type RB_PARALLELISM: int
    :param PIPE_CYCLES: 0
    Number of pipeline stages to insert after the output assignments. Note that the first value is available after PIPE_CYCLES + 1 clock cycles.
    :type PIPE_CYCLES: int
    :param IF_RST_N: True
    Whether the module has rst_n port. Currently must be set to True.
    :type IF_RST_N: bool
    :param dmrs_Type: "Hybrid"
    Configures the LFSR step size for different DMRS types. 
    - If 1: Step = (RB_PARALLELISM * 6) * 2 bits.
    - If 2: Step = (RB_PARALLELISM * 4) * 2 bits.
    - If "Hybrid": Generates hardware for both step sizes and muxes based on input port dmrs_Type. The module will have an additional 1-bit input port dmrs_type (0 for Type 1, 1 for Type 2).
    :type dmrs_Type: int | Literal["Hybrid"]
    """
    # This module must have a clk
    if PIPE_CYCLES < 0:
        raise ValueError("ModuleDMRS_SEQUENCE_GENERATION requires PIPE_CYCLES >= 0")
    if IF_RST_N != True:
        raise ValueError("ModuleDMRS_SEQUENCE_GENERATION requires IF_RST_N = True")
    if dmrs_Type not in [1, 2, 3, "Hybrid"]:
        raise ValueError("ModuleDMRS_SEQUENCE_GENERATION requires dmrs_Type to be 1, 2, 3, or 'Hybrid'")

    # Calculate step sizes from RB-level parallelism
    # Type 1: 6 RE/RB, Type 2: 4 RE/RB, Type 3: 2 RE/RB. Each RE contributes 2 bits.
    re_parallelism_type1 = dmrs_re_parallelism(RB_PARALLELISM, 1)
    re_parallelism_type2 = dmrs_re_parallelism(RB_PARALLELISM, 2)
    re_parallelism_type3 = dmrs_re_parallelism(RB_PARALLELISM, 3)
    re_parallelism = dmrs_re_parallelism(RB_PARALLELISM, dmrs_Type)

    bits_step_type1 = re_parallelism_type1 * 2
    bits_step_type2 = re_parallelism_type2 * 2
    bits_step_type3 = re_parallelism_type3 * 2
    
    # Determine which step size(s) to use
    # In Hybrid mode, output width follows Type 1 (6 RE/RB)
    # so downstream can always index by the superset lanes.
    bit_parallelism = bits_step_type1
    # X1
    rows_x1 = [0] * 31
    for i in range(30):
        rows_x1[i] = (1 << (i + 1)) # The next state bit
    rows_x1[30] = (1 << 3) | (1 << 0) # Feedback: taps at 3 and 0
    
    
    # X2
    rows_x2 = [0] * 31
    for i in range(30):
        rows_x2[i] = (1 << (i + 1))
    rows_x2[30] = (1 << 3) | (1 << 2) | (1 << 1) | (1 << 0) # Feedback: taps at 3,2,1,0
    
    pipe_delays_for_1600taps = 0
    #/ `timescale 1ns / 1ps
    #/ module DMRS_SEQUENCE_GENERATION(
    #/     input [30:0] c_init, // X2 initial state
    #/     input        c_init_strb,
    #/     input        clk,
    #/     input        rst_n,
    if HAS_ENABLE:
        #/ input enable,
        pass
    if HAS_CTX:
        CTX_SEL_W = max(math.ceil(math.log2(N_CTX_SLOTS)), 1) if N_CTX_SLOTS > 1 else 1
        #/ input ctx_save_en,
        #/ input ctx_restore_en,
        if N_CTX_SLOTS > 1:
            #/ input [`CTX_SEL_W`-1:0] ctx_sel,
            pass
    if dmrs_Type == "Hybrid":
        #/ input dmrs_type, // 0 for Type 1, 1 for Type 2
        pass
    for i in range(re_parallelism):
        base_seq_port = f"dmrs_base_seq_{i}," if i < re_parallelism - 1 else f"dmrs_base_seq_{i}"
        #/ output [1:0] `base_seq_port`
        pass
    #/ );
    x1_value = 1581799488 # This is a 31-bit value



    # Truncate LSB operation should be performed in output stage
    x1_init = f"31'b{x1_value:031b}"
    #/ // should be fixed value
    #/ wire [30:0] x1_1600d = `x1_init`;
    #/ // depends on c_init
    #/ wire [30:0] x2_1600d;
    
    # The XOR-1600 tree requires no delay since the depth of XOR tree is less than 5.
    # Module instantiation from: v_xor_tree.py
    # Conditional ports:
    #   i_clk: if (N_CLK > 0)
    #   i_rst_n: if (N_CLK > 0) and (IF_RST_N)
    ModuleXOR_TREE(LFSR=rows_x2, N_taps=1600, N_bits=31, N_CLK=0, IF_RST_N=True, PORTS={'i_data': 'c_init', 'o_data': 'x2_1600d'})
    #/ wire [30:0] x1_next;
    #/ wire [30:0] x2_next;
    #/ wire [30:0] x1_current_d;
    #/ wire [30:0] x2_current_d;

    if HAS_CTX:
        # Context state banks: per-slot storage for LFSR state
        for s in range(N_CTX_SLOTS):
            #/ reg [30:0] `f"ctx_x1_{s}"`;
            #/ reg [30:0] `f"ctx_x2_{s}"`;
            pass
        #/ reg [`N_CTX_SLOTS`-1:0] ctx_valid;

        # Restore mux
        if N_CTX_SLOTS == 1:
            #/ wire [30:0] ctx_x1_restore = ctx_x1_0;
            #/ wire [30:0] ctx_x2_restore = ctx_x2_0;
            pass
        else:
            restore_cases_x1 = []
            restore_cases_x2 = []
            for s in range(N_CTX_SLOTS):
                restore_cases_x1.append(f"(ctx_sel == {CTX_SEL_W}'d{s}) ? ctx_x1_{s}")
                restore_cases_x2.append(f"(ctx_sel == {CTX_SEL_W}'d{s}) ? ctx_x2_{s}")
            x1_mux = " : ".join(restore_cases_x1) + f" : ctx_x1_0"
            x2_mux = " : ".join(restore_cases_x2) + f" : ctx_x2_0"
            #/ wire [30:0] ctx_x1_restore = `x1_mux`;
            #/ wire [30:0] ctx_x2_restore = `x2_mux`;

        # Priority: c_init_strb > ctx_restore_en > (enable ? advance : hold)
        if HAS_ENABLE:
            #/ wire [30:0] x1_current = c_init_strb ? x1_1600d : (ctx_restore_en ? ctx_x1_restore : (enable ? x1_next : x1_current_d));
            #/ wire [30:0] x2_current = c_init_strb ? x2_1600d : (ctx_restore_en ? ctx_x2_restore : (enable ? x2_next : x2_current_d));
            pass
        else:
            #/ wire [30:0] x1_current = c_init_strb ? x1_1600d : (ctx_restore_en ? ctx_x1_restore : x1_next);
            #/ wire [30:0] x2_current = c_init_strb ? x2_1600d : (ctx_restore_en ? ctx_x2_restore : x2_next);
            pass

        # Context save logic
        #/ always @(posedge clk) begin
        #/     if (ctx_save_en) begin
        if N_CTX_SLOTS == 1:
            #/         ctx_x1_0 <= x1_current_d;
            #/         ctx_x2_0 <= x2_current_d;
            #/         ctx_valid[0] <= 1'b1;
            pass
        else:
            for s in range(N_CTX_SLOTS):
                cond = "if" if s == 0 else "end else if"
                #/ `cond` (ctx_sel == `CTX_SEL_W`'d`s`) begin
                #/             `f"ctx_x1_{s}"` <= x1_current_d;
                #/             `f"ctx_x2_{s}"` <= x2_current_d;
                #/             ctx_valid[`s`] <= 1'b1;
                pass
            #/         end
        #/     end
        if IF_RST_N:
            #/     if (!rst_n) ctx_valid <= `N_CTX_SLOTS`'b0;
            pass
        #/     if (c_init_strb) ctx_valid <= `N_CTX_SLOTS`'b0;
        #/ end
    elif HAS_ENABLE:
        #/ wire [30:0] x1_current = c_init_strb ? x1_1600d : (enable ? x1_next : x1_current_d);
        #/ wire [30:0] x2_current = c_init_strb ? x2_1600d : (enable ? x2_next : x2_current_d);
        pass
    else:
        #/ wire [30:0] x1_current = c_init_strb ? x1_1600d : x1_next;
        #/ wire [30:0] x2_current = c_init_strb ? x2_1600d : x2_next;
        pass
    #/ 
    #/ // Fixed 1-cycle state register for LFSR feedback
    
    ModuleDelay(DWT=31, N_CLK=1, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'x1_current', 'o_data': 'x1_current_d'})
    
    ModuleDelay(DWT=31, N_CLK=1, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'x2_current', 'o_data': 'x2_current_d'})
    
    # =========================================================================
    # NEXT STATE LOGIC - Generate next state based on DMRS Type
    # =========================================================================
    
    if dmrs_Type == 1:
        # Fixed Type 1: Only generate Type 1 step
        ModuleXOR_TREE(LFSR=rows_x1, N_taps=bits_step_type1, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x1_current_d', 'o_data': 'x1_next'})
        ModuleXOR_TREE(LFSR=rows_x2, N_taps=bits_step_type1, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x2_current_d', 'o_data': 'x2_next'})
    
    elif dmrs_Type == 2:
        # Fixed Type 2: Only generate Type 2 step
        ModuleXOR_TREE(LFSR=rows_x1, N_taps=bits_step_type2, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x1_current_d', 'o_data': 'x1_next'})
        ModuleXOR_TREE(LFSR=rows_x2, N_taps=bits_step_type2, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x2_current_d', 'o_data': 'x2_next'})

    elif dmrs_Type == 3:
        # Fixed Type 3: Only generate Type 3 step (2 RE/RB)
        ModuleXOR_TREE(LFSR=rows_x1, N_taps=bits_step_type3, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x1_current_d', 'o_data': 'x1_next'})
        ModuleXOR_TREE(LFSR=rows_x2, N_taps=bits_step_type3, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x2_current_d', 'o_data': 'x2_next'})

    else:  # Hybrid mode
        # Generate both Type 1 and Type 2 steps, then mux based on dmrs_type input
        #/ wire [30:0] x1_next_type1;
        #/ wire [30:0] x2_next_type1;
        ModuleXOR_TREE(LFSR=rows_x1, N_taps=bits_step_type1, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x1_current_d', 'o_data': 'x1_next_type1'})
        ModuleXOR_TREE(LFSR=rows_x2, N_taps=bits_step_type1, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x2_current_d', 'o_data': 'x2_next_type1'})
        
        #/ wire [30:0] x1_next_type2;
        #/ wire [30:0] x2_next_type2;
        ModuleXOR_TREE(LFSR=rows_x1, N_taps=bits_step_type2, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x1_current_d', 'o_data': 'x1_next_type2'})
        ModuleXOR_TREE(LFSR=rows_x2, N_taps=bits_step_type2, N_bits=31, N_CLK=0, IF_RST_N=False, PORTS={'i_data': 'x2_current_d', 'o_data': 'x2_next_type2'})
        
        # Mux the next state based on dmrs_type input (1 for Type 2, 0 for Type 1)
        #/ assign x1_next = dmrs_type ? x1_next_type2 : x1_next_type1;
         
        #/ assign x2_next = dmrs_type ? x2_next_type2 : x2_next_type1;
         
    
    
    #/ // Output assignments - {imag, real}
    #/ // Note: In Type 2 mode, only the first (RB_PARALLELISM * 4) outputs contain valid DMRS sequence for this cycle.
    #/ // The remaining outputs contain valid Gold sequence bits but should not be used in Type 2 mapping.
    #/ // Downstream connection logic will handle this by indexing based on DMRS density.

    # When 2*re_parallelism > 31, direct bit-select on the 31-bit LFSR state
    # goes out of bounds.  Expand via XOR_TREE (N_taps=0) to produce the
    # required number of consecutive output bits.
    need_expand = (2 * re_parallelism > 31)

    if need_expand:
        n_out_bits = 2 * re_parallelism
        #/ wire [`n_out_bits`-1:0] x1_bits;
        #/ wire [`n_out_bits`-1:0] x2_bits;
        if PIPE_CYCLES == 0:
            x1_src, x2_src = 'x1_current', 'x2_current'
        else:
            x1_src, x2_src = 'x1_current_d', 'x2_current_d'
        ModuleXOR_TREE(LFSR=rows_x1, N_taps=0, N_bits=n_out_bits, N_CLK=0, IF_RST_N=False, PORTS={'i_data': x1_src, 'o_data': 'x1_bits'})
        ModuleXOR_TREE(LFSR=rows_x2, N_taps=0, N_bits=n_out_bits, N_CLK=0, IF_RST_N=False, PORTS={'i_data': x2_src, 'o_data': 'x2_bits'})
        x1_sig = 'x1_bits'
        x2_sig = 'x2_bits'
    else:
        if PIPE_CYCLES == 0:
            x1_sig, x2_sig = 'x1_current', 'x2_current'
        else:
            x1_sig, x2_sig = 'x1_current_d', 'x2_current_d'

    # Order: {imag, real}
    if PIPE_CYCLES  == 0:
        for i in range(re_parallelism):
            base_seq_port = f"dmrs_base_seq_{i}"
            #/ assign `base_seq_port` = {`x1_sig`[`2*i + 1`] ^ `x2_sig`[`2*i + 1`], `x1_sig`[`2*i`] ^ `x2_sig`[`2*i`]};
            pass
    elif PIPE_CYCLES > 0:
        # First, assemble the outputs
        for i in range(re_parallelism):
            base_seq_port = f"dmrs_base_seq_{i}_comb"
            #/ wire [1:0] `base_seq_port` = {`x1_sig`[`2*i + 1`] ^ `x2_sig`[`2*i + 1`], `x1_sig`[`2*i`] ^ `x2_sig`[`2*i`]};
            pass
        # Then, add pipeline delay
        for i in range(re_parallelism):
            base_seq_port_out = f"dmrs_base_seq_{i}"
            base_seq_port_in = f"dmrs_base_seq_{i}_comb"
            
            ports_delay = {
                'i_clk': 'clk',
                'i_data': base_seq_port_in,
                'o_data': base_seq_port_out
            }
            if IF_RST_N:
                ports_delay['i_rst_n'] = 'rst_n'
            
            ModuleDelay(DWT=2, N_CLK=PIPE_CYCLES, IF_RST_N=IF_RST_N, PORTS=ports_delay)
    else:
        raise ValueError("PIPE_CYCLES must be non-negative.")
    #/ // Timing budget: fixed feedback register=1 clk, output PIPE_CYCLES=`PIPE_CYCLES`, dmrs_Type=`dmrs_Type`
    #/ endmodule
    
