from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from typing import Literal, List
import sys
from os.path import dirname
import warnings
# Now the preview generator can see PyTU module.
sys.path.append(dirname(__file__))
from basic_modules import QuType, QuMode, OfMode
from basic_modules import ModuleAdd
from basic_modules import ModuleDelay
from basic_modules import ModuleMul
from delay_budget import DelayBudget, COST_ADDER_8B, COST_MUL_8B, DEFAULT_BUDGET
@convert
def ModuleC_INIT_GENERATION(Qu_symbol_idx: QuType, Qu_slot_idx: QuType, N_CLK:int, dmrs_Type: int | Literal["Hybrid"], dmrs_Uplink:bool | Literal["Hybrid"], is_ECP:bool | Literal["Hybrid"], ENABLED_CDM_GROUPS_TYPE1: List[bool], ENABLED_CDM_GROUPS_TYPE2: List[bool], ENABLED_CDM_GROUPS_TYPE3: List[bool] | None = None) -> None:
    """
    ModuleC_INIT_GENERATION
    Generates c_init values for DMRS sequence generation. This module supports pruning of unused CDM groups
    based on the enabled_cdm_groups parameter to reduce hardware resource usage.
    
    When dmrs_Uplink is True or "Hybrid", the module generates separate c_init values for each enabled CDM group.
    The enabled CDM groups are determined by the union of ENABLED_CDM_GROUPS_TYPE1 and ENABLED_CDM_GROUPS_TYPE2
    when dmrs_Type is "Hybrid", or by the corresponding type-specific list otherwise.
    
    :param Qu_symbol_idx: QuType(4, 0, False)
        QuType of current OFDM symbol index. Its DWT is determined by the maximum number of OFDM symbols within a PUSCH transmission.
    :type Qu_symbol_idx: QuType
    :param Qu_slot_idx: QuType(7, 0, False)
        QuType of current slot index. Its DWT is determined by SCS. slot_idx_max = 10*2^(SCS_idx)
    :type Qu_slot_idx: QuType
    :param N_CLK: 1
        Number of pipeline stages. If > 0, output is registered.
    :type N_CLK: int
    :param dmrs_Type: 2
        DMRS Type: 1, 2, or "Hybrid"
    :type dmrs_Type: int | Literal["Hybrid"]
    :param dmrs_Uplink: "Hybrid"
        Whether uplink DMRS (with CDM-group-specific c_init). Can be True, False, or "Hybrid".
    :type dmrs_Uplink: bool | Literal["Hybrid"]
    :param is_ECP: "Hybrid"
        Extended CP mode: True (12 symbols/slot), False (14 symbols/slot), or "Hybrid".
    :type is_ECP: bool | Literal["Hybrid"]
    :param ENABLED_CDM_GROUPS_TYPE1: [True, False]
        List of 2 booleans indicating which CDM groups are enabled for DMRS Type 1 (Group 0, Group 1).
    :type ENABLED_CDM_GROUPS_TYPE1: List[bool]
    :param ENABLED_CDM_GROUPS_TYPE2: [False, True, True]
        List of 3 booleans indicating which CDM groups are enabled for DMRS Type 2 (Group 0, Group 1, Group 2).
    :type ENABLED_CDM_GROUPS_TYPE2: List[bool]
    """
    
    # Calculate enabled_cdm_groups: union of enabled groups across DMRS types
    # This determines which c_init_cdmx outputs to generate
    if dmrs_Type == "Hybrid":
        # Pad TYPE1 to length 3 for comparison with TYPE2
        enabled_cdm_groups = [a or b for a, b in zip(ENABLED_CDM_GROUPS_TYPE1 + [False], ENABLED_CDM_GROUPS_TYPE2)]
    elif dmrs_Type == 1:
        enabled_cdm_groups = ENABLED_CDM_GROUPS_TYPE1
    elif dmrs_Type == 2:
        enabled_cdm_groups = ENABLED_CDM_GROUPS_TYPE2
    elif dmrs_Type == 3:
        enabled_cdm_groups = ENABLED_CDM_GROUPS_TYPE3 if ENABLED_CDM_GROUPS_TYPE3 else [False] * 6
    else:
        raise ValueError("Invalid DMRS Type.")


    # =========================================================================
    # Delay Budget: automatic pipeline register management
    # Max combinational cost per stage = 1 × 8-bit multiplier = 3 × 8-bit adders
    # =========================================================================
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)

    #/ `timescale 1ns / 1ps
    #/ module C_INIT_GENERATION (
    #/     

    #/ input        clk,
    #/ input        rst_n,
    #/ input [15:0] N_ID,
    #/ input        n_scid,
    if dmrs_Uplink == "Hybrid":
        #/ input dmrs_uplink,
        pass 
    #/ input [`Qu_symbol_idx.DWT`-1:0] current_symbol_idx,
    #/ input [`Qu_slot_idx.DWT`-1:0]   current_slot_idx,
    if is_ECP == "Hybrid":
        #/ input is_ECP,
        pass
        
    # C_INIT is fixed to 31 bits
    if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
        # Output only enabled CDM groups
        enabled_indices = [i for i, enabled in enumerate(enabled_cdm_groups) if enabled]
        for idx, cdm_idx in enumerate(enabled_indices):
            output_name = f"c_init_cdm{cdm_idx}"
            # Add comma if not the last enabled output
            comma = "," if idx < len(enabled_indices) - 1 else ""
            #/ output [30:0] `output_name + comma`
            pass
    else: # No separation between cdm groups
        #/ output [30:0] c_init
        pass
        pass
    #/ );
        
    # Stage 1: n_{s,f} * N_symb^slot
    # Public Types & Signals
    #/ // Stage 1: Multiply a constant N_symb^slot
    Qu_stage1_idx = QuType(DWT = Qu_slot_idx.DWT + 4, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    Qu_slot_idx_ext3 = QuType(DWT = Qu_slot_idx.DWT + 3, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    Qu_slot_idx_ext2 = QuType(DWT = Qu_slot_idx.DWT + 2, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    Qu_slot_idx_ext1 = QuType(DWT = Qu_slot_idx.DWT + 1, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    #/ wire [`Qu_slot_idx_ext3.DWT`-1:0 ] current_slot_idx_ext3 = {current_slot_idx, 3'b0};
    #/ wire [`Qu_slot_idx_ext2.DWT`-1:0 ] current_slot_idx_ext2 = {current_slot_idx, 2'b0};
    #/ wire [`Qu_stage1_idx.DWT`-1:0    ] c_init_high_stage1;
    if is_ECP == True:
        # n_symb_slot = 12 -> (A << 3) + (A << 2)
        # Need 1 adder
        budget.add_comb(COST_ADDER_8B, tag="stage1_add_ecp")
        ModuleAdd(QU_IN_1=Qu_slot_idx_ext3, QU_IN_2=Qu_slot_idx_ext2, QU_OUT=Qu_stage1_idx, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'current_slot_idx_ext3', 'i_data_2': 'current_slot_idx_ext2', 'o_data': 'c_init_high_stage1'})
        pass
    elif is_ECP == False:
        # n_symb_slot = 14 -> (A << 3) + (A << 2) + (A << 1)
        # Need 2 adders
        budget.add_comb(2 * COST_ADDER_8B, tag="stage1_add_ncp")
        #/ wire [`Qu_slot_idx_ext1.DWT`-1:0 ] current_slot_idx_ext1 = {current_slot_idx, 1'b0};
        
        #/ wire [`Qu_stage1_idx.DWT`-1:0    ] c_init_high_stage1_temp;
        ModuleAdd(QU_IN_1=Qu_slot_idx_ext3, QU_IN_2=Qu_slot_idx_ext2, QU_OUT=Qu_stage1_idx, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'current_slot_idx_ext3', 'i_data_2': 'current_slot_idx_ext2', 'o_data': 'c_init_high_stage1_temp'})
        
        ModuleAdd(QU_IN_1=Qu_stage1_idx, QU_IN_2=Qu_slot_idx_ext1, QU_OUT=Qu_stage1_idx, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'c_init_high_stage1_temp', 'i_data_2': 'current_slot_idx_ext1', 'o_data': 'c_init_high_stage1'})
    elif is_ECP == "Hybrid":
        # Need a selector: 2 adders + mux, then explicit register
        budget.add_comb(2 * COST_ADDER_8B, tag="stage1_add_hybrid")
        #/ wire [`Qu_slot_idx_ext1.DWT`-1:0 ] current_slot_idx_ext1 = {current_slot_idx, 1'b0};
        #/ wire [`Qu_stage1_idx.DWT`-1:0    ] c_init_high_stage1_ECP;
        #/ wire [`Qu_stage1_idx.DWT`-1:0]     c_init_high_stage1_NCP; // normal CP
        #/ wire [`Qu_stage1_idx.DWT`-1:0    ] c_init_high_stage1_temp;
        ModuleAdd(QU_IN_1=Qu_slot_idx_ext3, QU_IN_2=Qu_slot_idx_ext2, QU_OUT=Qu_stage1_idx, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'current_slot_idx_ext3', 'i_data_2': 'current_slot_idx_ext2', 'o_data': 'c_init_high_stage1_ECP'})
        
        ModuleAdd(QU_IN_1=Qu_stage1_idx, QU_IN_2=Qu_slot_idx_ext1, QU_OUT=Qu_stage1_idx, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': 'c_init_high_stage1_ECP', 'i_data_2': 'current_slot_idx_ext1', 'o_data': 'c_init_high_stage1_NCP'})
        
        # Make a selector
        #/ assign c_init_high_stage1_temp = is_ECP ? c_init_high_stage1_ECP : c_init_high_stage1_NCP;

        ModuleDelay(DWT=Qu_stage1_idx.DWT, N_CLK=1, IF_RST_N=False, PORTS={'i_data': 'c_init_high_stage1_temp', 'o_data': 'c_init_high_stage1', 'i_clk': 'clk'})
        budget.add_register(1, tag="stage1_hybrid_mux_reg")
    else:
        raise ValueError("is_ECP must be either True, False, or 'Hybrid'.")
    
    #/ // Stage 2: Add OFDM symbol Index
    Qu_stage2_idx = Qu_stage1_idx
    #/ wire [`Qu_stage2_idx.DWT`-1:0 ] c_init_high_stage2;
    
    Qu_symbol_idx_add_1 = QuType(DWT=Qu_symbol_idx.DWT + 1, FRAC=Qu_symbol_idx.FRAC, IF_SIGNED=Qu_symbol_idx.IF_SIGNED)
    #/ // +1 to current_symbol_idx, and then align to c_init_high_stage1
    #/ wire [`Qu_symbol_idx_add_1.DWT`-1:0] current_symbol_idx_add_1 = current_symbol_idx + 1'b1;
    #/ wire [`Qu_symbol_idx_add_1.DWT`-1:0] current_symbol_idx_add_1_d;
    
    _stage2_delay_ports: dict = {
        'i_data': 'current_symbol_idx_add_1',
        'o_data': 'current_symbol_idx_add_1_d'
    }
    if budget.pipeline_depth > 0:
        _stage2_delay_ports['i_clk'] = 'clk'
    
    ModuleDelay(DWT=Qu_symbol_idx_add_1.DWT, N_CLK=budget.pipeline_depth, IF_RST_N=False, PORTS=_stage2_delay_ports)
    # Stage 2 adder: 1 adder cost, then explicit pipeline register
    budget.add_comb(COST_ADDER_8B, tag="stage2_add")
    budget.flush(tag="stage2_pipe")  # force register after adder
    ModuleAdd(QU_IN_1=Qu_stage1_idx, QU_IN_2=Qu_symbol_idx_add_1, QU_OUT=Qu_stage2_idx, N_CLK=1, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data_1': 'c_init_high_stage1', 'i_data_2': 'current_symbol_idx_add_1_d', 'o_data': 'c_init_high_stage2'})
    #/ // Stage 3: Compute (N_ID << 1) + 1 and multiply it with previous result
    #/ wire [15:0] N_ID_stage3;
    #/ wire [16:0] N_ID_x2_1 = {N_ID_stage3, 1'b1};
    ModuleDelay(DWT=16, N_CLK=budget.pipeline_depth, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'N_ID', 'o_data': 'N_ID_stage3'})
    
    
    # number of higher bits is fixed to 14 bits, since the lower 17 bits is occupied by c_init_low. But we need LSBs rather than MSBs, so quantization method is NOT truncation.
    Qu_stage3_idx = QuType(DWT = 14, FRAC = Qu_stage2_idx.FRAC, IF_SIGNED = Qu_stage2_idx.IF_SIGNED)
    Qu_mul_idx = QuType(DWT = Qu_stage2_idx.DWT + 17, FRAC = Qu_stage2_idx.FRAC, IF_SIGNED = Qu_stage2_idx.IF_SIGNED)
    #/ wire [`Qu_mul_idx.DWT`-1:0    ] c_init_mul_result;
    #/ // Take lower bits
    #/ wire [`Qu_stage3_idx.DWT`-1:0 ] c_init_high_stage3 = c_init_mul_result[`Qu_stage3_idx.DWT`-1:0 ];
    # Module instantiation from: Mul.py
    # Multiplier: cost = COST_MUL_8B, pipelined with N_CLK=2
    budget.add_comb(COST_MUL_8B, tag="stage3_mul")
    budget.add_register(2, tag="stage3_mul_pipe")
    ModuleMul(QU_IN_1=Qu_stage2_idx, QU_IN_2=QuType(DWT=17, FRAC=0, IF_SIGNED=False), QU_OUT=Qu_mul_idx, N_CLK=2, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data_1': 'c_init_high_stage2', 'i_data_2': 'N_ID_x2_1', 'o_data': 'c_init_mul_result'})
    
    #/ wire [15:0] N_ID_stage4;
    ModuleDelay(DWT=16, N_CLK=2, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'N_ID_stage3', 'o_data': 'N_ID_stage4'})
    
    #/ wire n_scid_stage4;
    ModuleDelay(DWT=1, N_CLK=budget.pipeline_depth, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'n_scid', 'o_data': 'n_scid_stage4'})

    if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
        # Create new QuType object to avoid aliasing Qu_stage3_idx
        # DWT=14: matches c_init_high_stage3 width (only [13:0] used in final concat)
        Qu_stage4_idx = QuType(DWT=14, FRAC=Qu_stage3_idx.FRAC, IF_SIGNED=Qu_stage3_idx.IF_SIGNED)
        #/ // Stage 4 (Final): for dmrs_Uplink = True, separate cdm groups
        #/ // Concat higher bits and lower bits of c_init
        # XOR truth table: 00 -> 0 01 -> 1 10 -> 1 11 -> 0
        _dmrs_uplink_delayed = False
        for cdm_idx, is_enabled in enumerate(enabled_cdm_groups):

            if not is_enabled:
                continue

            # lower part generation: even groups use n_scid, odd groups use ~n_scid
            if cdm_idx % 2 == 0:
                #/ wire [16:0] `f"c_init_low_{cdm_idx}"` = {N_ID_stage4, n_scid_stage4};
                pass
            else:
                #/ wire [16:0] `f"c_init_low_{cdm_idx}"` = {N_ID_stage4, ~n_scid_stage4};
                pass

            # higher part generation
            high_name = f"c_init_cdm{cdm_idx}_high_stage4"
            output_name = f"c_init_cdm{cdm_idx}"

            if cdm_idx <= 1:
                #/ wire [`Qu_stage4_idx.DWT`-1:0] `high_name` = c_init_high_stage3;
                pass
            elif cdm_idx >= 2 and dmrs_Uplink == "Hybrid":
                if not _dmrs_uplink_delayed:
                    #/ wire dmrs_uplink_d;
                    ModuleDelay(DWT=1, N_CLK=budget.pipeline_depth, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'dmrs_uplink', 'o_data': 'dmrs_uplink_d'})
                    _dmrs_uplink_delayed = True
                _offset = cdm_idx // 2
                #/ wire [`Qu_stage4_idx.DWT`-1:0 ] `high_name` = dmrs_uplink_d ? (c_init_high_stage3 + `_offset`) : c_init_high_stage3;
                pass
            else:
                _offset = cdm_idx // 2
                #/ wire [`Qu_stage4_idx.DWT`-1:0 ] `high_name` = c_init_high_stage3 + `_offset`;
                pass

            # Delay or assign output
            #/ wire [30:0] `output_name`_temp = {`high_name`[13:0], `f"c_init_low_{cdm_idx}"`};
            if N_CLK > 0:
                ModuleDelay(DWT=31, N_CLK=N_CLK, IF_RST_N=True, PORTS={'i_data': f'{output_name}_temp', 'o_data': output_name, 'i_clk': 'clk', 'i_rst_n': 'rst_n'})
            else:
                #/ assign `output_name` = `output_name`_temp;
                pass
    else: # dmrs_Uplink == False
        #/ // Stage 4: dmrs_Uplink = False, no difference between cdm_groups
        #/ // Concat higher bits and lower bits of c_init
        #/ wire [16:0] c_init_low = {N_ID_stage4, n_scid_stage4};
        #/ wire [30:0] c_init_temp = {c_init_high_stage3, c_init_low};
        
        if N_CLK > 0:
            # Register output if clock is used
            ModuleDelay(DWT=31, N_CLK=N_CLK, IF_RST_N=True, PORTS={'i_data': 'c_init_temp', 'o_data': 'c_init', 'i_clk': 'clk', 'i_rst_n': 'rst_n'})
        else:
            # Direct assignment if no clock
            #/ assign c_init = c_init_temp;
            pass
    
    budget.add_register(N_CLK, tag="stage4_output_reg")
    #/ // ---- Total Intrinsic Delay: `budget.pipeline_depth` Clocks (auto-budgeted) ----
    #/ endmodule
