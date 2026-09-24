from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

# Import submodule definitions
from basic_modules import QuType, ModuleDelay, QuMode, OfMode
from v_dmrs_sequence_gen import ModuleDMRS_SEQUENCE_GENERATION, dmrs_re_parallelism
from v_y_pre import ModuleY_PRE
from v_ls_rot import ModuleLS_ROT
from v_occ import ModuleOCC, occ_needs_dmrs_type, occ_needs_l_quote
from v_w_f_calc import ModuleW_F_CALC
from v_averaging import ModuleAVERAGING
from typing import Literal, Any, Dict, List, Optional

# Unified DMRS configuration layer (single source of truth)
from dmrs_config import (
    DmrsArchConfig, PCDMU_Unified,
    CDM_GROUPS_TYPE1, CDM_GROUPS_TYPE2,
    PILOT_RE_TYPE1, PILOT_RE_TYPE2, PILOT_RE_TYPE3,
    compute_required_re_indices,
    get_cdm_group_for_port,
)
from constants import RE_PER_RB


@convert
def ModuleLS(Qu_Y: QuType, QU_H_LS: QuType, QU_MODE_LS: QuMode.TRN | QuMode.RND, OF_MODE_LS: OfMode.WRP | OfMode.SAT, N_CLK_Y_PRE: int, N_CLK_DMRS_SEQ: int, N_CLK_LS_ROT: int, dmrs_Type: int | Literal['Hybrid'], dmrs_Uplink: bool | Literal['Hybrid'], is_ECP: bool | Literal['Hybrid'], is_enhanced: bool | Literal['Hybrid'], is_double_dmrs: bool | Literal['Hybrid'], antenna_ports: List[int], TRUE_INDEX_LIST: List[int], switchable_ports: bool, RB_PARALLELISM: int = 1, fdCDM: Dict[int, Any] = {}, tdCDM: Dict[int, Any] = {}, max_num_RBs: int = 273, HAS_LFSR_ENABLE: bool = False, HAS_LFSR_CTX: bool = False, HAS_AVG_SYM_SWITCH: bool = False, N_LFSR_CTX_SLOTS: int = 2, SRAM_MACRO_CONFIG: Optional[Dict] = None, REPLAY_TOKEN_DWT: int = 0, N_CLK_AVG: int = 1) -> None:
    """
    LS (Least Squares) Channel Estimation Module + De-OCC Averaging
    
    Performs pilot-based channel estimation using DMRS symbols and frequency/time
    averaging (de-OCC part 2). This module combines multiple processing stages:
    1. Y signal pre-scaling (Y_Pre)
    2. DMRS sequence generation (c_init received via FIFO from top-level C_INIT_GENERATION)
    3. OCC application for CDM group orthogonalization
    4. LS rotation for phase compensation
    5. Frequency + Time averaging (AVERAGING, de-OCC part 2)
    
    NOTE: C_INIT_GENERATION has been moved to the top-level module (v_top.py).
    The c_init values arrive at this module through external input ports (from C_INIT_GENERATION).
    
    NOTE: Y_PATH_REDUCE has been moved to the top-level module (v_top.py).
    This module now expects Y signals already reduced to TRUE_INDEX_LIST.
    
    The module supports multiple DMRS types, CDM groups, and antenna ports with configurable parallelism.
    
    :param Qu_Y: QuType(11, 4, True)
    :param QU_H_LS: QuType(12, 4, True)
    :param QU_MODE_LS: QuMode.TRN.TCPL
    :param OF_MODE_LS: OfMode.WRP.TCPL
    :param N_CLK_Y_PRE: 3
    :param N_CLK_DMRS_SEQ: 2
    :param N_CLK_LS_ROT: 3
    :param dmrs_Type: "Hybrid"
    :param dmrs_Uplink: True
    :param is_ECP: False
    :param is_enhanced: True
    :param is_double_dmrs: False
    :param antenna_ports: [0, 1]
    :param TRUE_INDEX_LIST: [0,2,4,6,8,10,1,7]
    :param switchable_ports: True
    :param RB_PARALLELISM: 1
    :param fdCDM: {0: 2}
        Frequency-domain CDM window per active CDM group.  int or "Hybrid".
    :param tdCDM: {0: 1}
        Time-domain CDM window per active CDM group.  int or "Hybrid".
    :param max_num_RBs: 273
    """
    # =========================================================================
    # Step 1: Antenna Port Categorization (via DmrsArchConfig)
    # =========================================================================
    
    arch_config = DmrsArchConfig(
        antenna_ports=antenna_ports,
        dmrs_Type=dmrs_Type,
        TRUE_INDEX_LIST=TRUE_INDEX_LIST,
    )
    
    # Unpack frequently-used attributes for readability
    ENABLED_CDM_GROUPS_TYPE1 = arch_config.ENABLED_CDM_GROUPS_TYPE1
    ENABLED_CDM_GROUPS_TYPE2 = arch_config.ENABLED_CDM_GROUPS_TYPE2
    ENABLED_CDM_GROUPS_TYPE3 = arch_config.ENABLED_CDM_GROUPS_TYPE3
    MAX_CDM_GROUPS = arch_config.MAX_CDM_GROUPS
    pcdmu_instances = arch_config.pcdmu_instances

    # =========================================================================
    # Timing Alignment Assertion
    # =========================================================================
    # Y path delay:    N_CLK_Y_PRE clocks (Y_PRE output register)
    # DMRS path delay: N_CLK_DMRS_SEQ (1-cycle feedback reg + PIPE_CYCLES) + 1 (OCC fixed 1 clk)
    #
    # Both paths must arrive at LS_ROT inputs on the same clock edge.
    N_CLK_DMRS_PATH = N_CLK_DMRS_SEQ + 1  # DMRS_SEQ_GEN total + OCC register
    if N_CLK_Y_PRE != N_CLK_DMRS_PATH:
        raise ValueError(
            f"LS timing misalignment: Y path ({N_CLK_Y_PRE} clk via Y_PRE) != "
            f"DMRS path ({N_CLK_DMRS_PATH} clk = {N_CLK_DMRS_SEQ} DMRS_SEQ + 1 OCC). "
            f"Adjust N_CLK_Y_PRE or N_CLK_DMRS_SEQ so they match."
        )

    # =========================================================================
    # Module Declaration
    # =========================================================================
    
    #/ `timescale 1ns / 1ps
    #/ module LS(
    #/     input clk,
    #/     input rst_n,
    
    # CDM group control signal
    # Used for Y_PRE Path selection
    if MAX_CDM_GROUPS >= 2:
        import math
        sel_bits = math.ceil(math.log2(MAX_CDM_GROUPS))
        #/ input [`sel_bits`-1:0] num_cdm_groups_without_data,
        pass
    
    # Conditional configuration ports
    if dmrs_Type == 'Hybrid':
        #/ input dmrs_type,
        pass
    if is_enhanced == 'Hybrid':
        #/ input is_enhanced,
        pass
    if is_double_dmrs == 'Hybrid':
        #/ input is_double_dmrs,
        pass
    
    # c_init strobe signal from the Controller
    #/ input c_init_strb,

    # c_init input ports (from top-level C_INIT_GENERATION output)
    # Compute enabled_cdm_groups for port declaration
    _enabled_cdm_groups_decl: list[bool] = []
    if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
        if dmrs_Type == "Hybrid":
            _enabled_cdm_groups_decl = [a or b for a, b in zip(ENABLED_CDM_GROUPS_TYPE1 + [False], ENABLED_CDM_GROUPS_TYPE2)]
        elif dmrs_Type == 1:
            _enabled_cdm_groups_decl = ENABLED_CDM_GROUPS_TYPE1
        elif dmrs_Type == 3:
            _enabled_cdm_groups_decl = ENABLED_CDM_GROUPS_TYPE3
        else:
            _enabled_cdm_groups_decl = ENABLED_CDM_GROUPS_TYPE2
        for cdm_idx in range(len(_enabled_cdm_groups_decl)):
            if _enabled_cdm_groups_decl[cdm_idx]:
                #/ input [30:0] `f"c_init_cdm{cdm_idx}"`,
                pass
    else:
        #/ input [30:0] c_init,
        pass

    # Y input data ports (reduced to TRUE_INDEX_LIST)
    Y_PARALLELISM = len(TRUE_INDEX_LIST)
    for i in range(Y_PARALLELISM):
        #/ input [`2*Qu_Y.DWT`-1:0] `f"Y_reduced_complex_{i}"`,
        pass
    
    # l_quote: used by AVERAGING uses it unconditionally as the double DMRS indicator
    # Signal comes from PILOT_SYMBOL_DETECTION module.
    #/ input l_quote,

    # RB index input for k_quote calculation (only needed for Type 1 enhanced DMRS)
    # Determine if any PCDMU needs current_RB_idx_lsb
    needs_rb_idx = False
    if is_enhanced == True or is_enhanced == "Hybrid":
        for pcdmu in pcdmu_instances:
            if pcdmu.has_type1:
                needs_rb_idx = True
                break
    if needs_rb_idx:
        #/ input current_RB_idx_lsb,
        pass
    
    # Port enable signals for switchable port mode (low-power gating)
    if switchable_ports:
        for ant_port in antenna_ports:
            #/ input `f"port_enable_p{ant_port}"`,
            pass
    
    # --- AVERAGING control ports ---
    if HAS_LFSR_ENABLE:
        #/ input enable_ls_pipeline,
        pass

    if HAS_LFSR_CTX:
        _ctx_sel_w = (N_LFSR_CTX_SLOTS - 1).bit_length() if N_LFSR_CTX_SLOTS > 1 else 1
        #/ input lfsr_ctx_save_en,
        #/ input lfsr_ctx_restore_en,
        if N_LFSR_CTX_SLOTS > 1:
            #/ input [`_ctx_sel_w`-1:0] lfsr_ctx_sel,
            pass
    if HAS_AVG_SYM_SWITCH:
        #/ input avg_sym_switch,
        #/ input replay_data_valid,
        pass
    if REPLAY_TOKEN_DWT > 0:
        if not HAS_LFSR_ENABLE:
            raise ValueError("REPLAY_TOKEN_DWT requires HAS_LFSR_ENABLE")
        if N_CLK_AVG < 1:
            raise ValueError("N_CLK_AVG must be >= 1 when replay tokens are enabled")
        #/ input replay_token_valid_in,
        #/ input [`REPLAY_TOKEN_DWT`-1:0] replay_token_in,
        pass
    
    # Active CDM groups for AVERAGING control
    _cdm_active_groups = sorted(set(p.group_idx for p in pcdmu_instances))
    
    for g in _cdm_active_groups:
        if fdCDM.get(g) == 'Hybrid':
            #/ input [1:0] `f"fdCDM_ctrl_cdm{g}"`,
            pass
        if tdCDM.get(g) == 'Hybrid':
            #/ input `f"tdCDM_ctrl_cdm{g}"`,
            pass
    
    # H_avg output data ports — per (antenna_port, RB, pilot_RE) complex
    # Enumerate output ports using PortInterpInfo for each antenna port
    all_avg_output_ports: List[str] = []
    for ant_port in antenna_ports:
        info = arch_config.get_port_interp_info(ant_port)
        for rb in range(RB_PARALLELISM):
            for re_k in info.pilot_re_list:
                port_name = f"H_avg_port{ant_port}_rb{rb}_re{re_k}_complex"
                all_avg_output_ports.append(port_name)
    
    COMPLEX_DWT_LS = 2 * QU_H_LS.DWT
    for idx, port_name in enumerate(all_avg_output_ports):
        comma = "," if idx < len(all_avg_output_ports) - 1 or REPLAY_TOKEN_DWT > 0 else ""
        #/ output [`COMPLEX_DWT_LS`-1:0] `port_name + comma`
        pass
    if REPLAY_TOKEN_DWT > 0:
        #/ output replay_token_valid_out,
        #/ output [`REPLAY_TOKEN_DWT`-1:0] replay_token_out
        pass
    #/ );
    
    
    #/ // ========== Y Signal Data Path ==========
    
    # Y signals arrive already reduced to TRUE_INDEX_LIST by the top-level module
    Qu_Y_Complex = QuType(DWT=2*Qu_Y.DWT, FRAC=Qu_Y.FRAC, IF_SIGNED=Qu_Y.IF_SIGNED)
    
    # Y_PRE (Power Boosting)
    ports_y_pre = {'clk': 'clk'}
    if MAX_CDM_GROUPS >= 2:
        ports_y_pre['num_cdm_groups_without_data'] = 'num_cdm_groups_without_data'
    
    for i in range(Y_PARALLELISM):
        ports_y_pre[f'Y_in_complex_{i}'] = f'Y_reduced_complex_{i}'
        ports_y_pre[f'Y_out_complex_{i}'] = f'Y_pre_complex_{i}'
        #/ wire [`2*QU_H_LS.DWT`-1:0] `f"Y_pre_complex_{i}"`;
    
    ModuleY_PRE(N_CLK=N_CLK_Y_PRE, Y_parallelism=Y_PARALLELISM, Qu_Y=Qu_Y, Qu_OUT=QU_H_LS, QU_MODE=QU_MODE_LS, OF_MODE=OF_MODE_LS, MAX_CDM_GROUPS=MAX_CDM_GROUPS, PORTS=ports_y_pre)
    
    #/ // ========== DMRS Signal Data Path ==========
    
    # C_INIT values arrive from C_INIT_GENERATION (instantiated in v_top.py)
    # The c_init input ports are declared in the module port list above.
    # We only need to compute the enabled_cdm_groups_union for downstream logic.
    enabled_cdm_groups_union: list[bool] = []
    if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
        # Determine which CDM groups need c_init (union of TYPE1 and TYPE2)
        if dmrs_Type == "Hybrid":
            enabled_cdm_groups_union = [a or b for a, b in zip(ENABLED_CDM_GROUPS_TYPE1 + [False], ENABLED_CDM_GROUPS_TYPE2)]
        elif dmrs_Type == 1:
            enabled_cdm_groups_union = ENABLED_CDM_GROUPS_TYPE1
        elif dmrs_Type == 3:
            enabled_cdm_groups_union = ENABLED_CDM_GROUPS_TYPE3
        else:  # dmrs_Type == 2
            enabled_cdm_groups_union = ENABLED_CDM_GROUPS_TYPE2
    
    # DMRS_SEQUENCE_GENERATION
    
    # Determine RE parallelism for DMRS sequence generation from RB_PARALLELISM.
    # Type 1: 6 RE/RB, Type 2: 4 RE/RB, Hybrid uses Type 1 width.
    max_re_count = max(pcdmu.max_re_count for pcdmu in pcdmu_instances) if pcdmu_instances else 0
    DMRS_PARALLELISM = dmrs_re_parallelism(RB_PARALLELISM, dmrs_Type)
    if max_re_count > DMRS_PARALLELISM:
        raise ValueError(
            f"DMRS_PARALLELISM={DMRS_PARALLELISM} (from RB_PARALLELISM={RB_PARALLELISM}, dmrs_Type={dmrs_Type}) "
            f"is smaller than required max_re_count={max_re_count}."
        )

    # DMRS sequence uses fixed 1-cycle feedback register and optional output PIPE_CYCLES.
    _pipe_cycles = max(N_CLK_DMRS_SEQ - 1, 0)
    _strb_signal = 'c_init_strb'
    _avg_strb_signal = 'avg_sym_switch' if HAS_AVG_SYM_SWITCH else _strb_signal
    
    # Generate DMRS sequences for each enabled CDM group
    if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
        for cdm_idx in range(len(enabled_cdm_groups_union)):
            if enabled_cdm_groups_union[cdm_idx]:
                ports_dmrs_seq = {
                    'c_init': f'c_init_cdm{cdm_idx}',
                    'c_init_strb': _strb_signal,
                    'clk': 'clk',
                    'rst_n': 'rst_n'
                }
                
                if dmrs_Type == "Hybrid":
                    ports_dmrs_seq['dmrs_type'] = 'dmrs_type'
                
                if HAS_LFSR_ENABLE:
                    ports_dmrs_seq['enable'] = 'enable_ls_pipeline'

                if HAS_LFSR_CTX:
                    ports_dmrs_seq['ctx_save_en'] = 'lfsr_ctx_save_en'
                    ports_dmrs_seq['ctx_restore_en'] = 'lfsr_ctx_restore_en'
                    if N_LFSR_CTX_SLOTS > 1:
                        ports_dmrs_seq['ctx_sel'] = 'lfsr_ctx_sel'

                for i in range(DMRS_PARALLELISM):
                    #/ wire [1:0] `f"dmrs_base_seq_cdm{cdm_idx}_{i}"`;
                    ports_dmrs_seq[f'dmrs_base_seq_{i}'] = f'dmrs_base_seq_cdm{cdm_idx}_{i}'

                ModuleDMRS_SEQUENCE_GENERATION(RB_PARALLELISM=RB_PARALLELISM, PIPE_CYCLES=_pipe_cycles, IF_RST_N=True, dmrs_Type=dmrs_Type, HAS_ENABLE=HAS_LFSR_ENABLE, HAS_CTX=HAS_LFSR_CTX, N_CTX_SLOTS=N_LFSR_CTX_SLOTS, PORTS=ports_dmrs_seq)
    else:
        # Single c_init for downlink
        ports_dmrs_seq = {
            'c_init': 'c_init',
            'c_init_strb': _strb_signal,
            'clk': 'clk',
            'rst_n': 'rst_n'
        }
        
        if dmrs_Type == "Hybrid":
            ports_dmrs_seq['dmrs_type'] = 'dmrs_type'
        
        if HAS_LFSR_ENABLE:
            ports_dmrs_seq['enable'] = 'enable_ls_pipeline'

        if HAS_LFSR_CTX:
            ports_dmrs_seq['ctx_save_en'] = 'lfsr_ctx_save_en'
            ports_dmrs_seq['ctx_restore_en'] = 'lfsr_ctx_restore_en'
            if N_LFSR_CTX_SLOTS > 1:
                ports_dmrs_seq['ctx_sel'] = 'lfsr_ctx_sel'

        for i in range(DMRS_PARALLELISM):
            #/ wire [1:0] `f"dmrs_base_seq_{i}"`;
            ports_dmrs_seq[f'dmrs_base_seq_{i}'] = f'dmrs_base_seq_{i}'

        ModuleDMRS_SEQUENCE_GENERATION(RB_PARALLELISM=RB_PARALLELISM, PIPE_CYCLES=_pipe_cycles, IF_RST_N=True, dmrs_Type=dmrs_Type, HAS_ENABLE=HAS_LFSR_ENABLE, HAS_CTX=HAS_LFSR_CTX, N_CTX_SLOTS=N_LFSR_CTX_SLOTS, PORTS=ports_dmrs_seq)
    
    # =========================================================================
    # Step 5: Unified PCDMU Processing
    # =========================================================================
    #
    # LS_ROT outputs go to internal H_LS wires (no longer module outputs).
    # These feed into AVERAGING (Step 6) which produces the final output.
    # =========================================================================
    
    # Declare internal H_LS wires driven by LS_ROT
    all_ls_internal_pairs: List[tuple[int, int]] = []
    for pcdmu in pcdmu_instances:
        for ant_port in pcdmu.unified_antenna_ports:
            for re_phy_idx in pcdmu.all_output_re_phy_indices():
                pair = (ant_port, re_phy_idx)
                if pair not in all_ls_internal_pairs:
                    all_ls_internal_pairs.append(pair)
    
    DWT_LS_complex_internal = 2 * QU_H_LS.DWT
    for ant_port, re_phy_idx in all_ls_internal_pairs:
        wire_name = f"H_LS_port{ant_port}_re{re_phy_idx}"
        #/ wire [`DWT_LS_complex_internal`-1:0] `wire_name`;

    # Hybrid mode can map the same physical RE wire from different PCDMU groups
    # (Type1/Type2 views). Collect all candidate sources first, then emit one
    # assign per physical H_LS wire at the end of Step 5.
    hybrid_hls_sources: Dict[tuple[int, int], List[tuple[str, int]]] = {}
    
    #
    # For each unified PCDMU group:
    #   5a. W_F_CALC: instantiate per-type for hybrid, single for mono-type
    #   5b. Per-RE loop:
    #       - DMRS sequence selection (simple 2:1 mux for hybrid)
    #       - Y signal selection (simple 2:1 mux for hybrid)
    #       - W_F mux per port (select Type1 vs Type2 w_f for hybrid)
    #       - OCC instantiation (fixed dmrs_type=1 or 2, NEVER "Hybrid")
    #       - LS_ROT instantiation (type-independent, just needs whid + Y)
    #
    # Key Design Decisions:
    #   1. W_F_CALC MUST be per-type because re_logic_indices differ between Type1/Type2
    #      and k_quote = re_logic_idx % 2 (or %4 for enhanced) gives different values.
    #   2. OCC always gets fixed dmrs_type. For ports 0-3 in CDM groups 0-1,
    #      Type1 and Type2 give identical w_t=0, so either type works.
    #   3. Y and DMRS signals are selected by simple 2:1 assign mux (no case/always).
    #   4. H_LS output: each RE slot writes to ONE output port based on its phy index.
    #      For hybrid, Type1 and Type2 have different phy indices for the same re_idx,
    #      but only one type is active at any given time.
    # =========================================================================
    
    #/ // ========== Unified PCDMU Processing (Architecture v2.0) ==========

    rb_idx_for_wf = 'current_RB_idx_lsb'
    if needs_rb_idx:
        rb_idx_for_wf = 'current_RB_idx_lsb_wf'
        # Align RB index with DMRS sequence output at OCC input.
        # W_F_CALC feeds OCC combinationally; the OCC output register
        # provides the extra clock needed for LS_ROT alignment with Y_PRE.
        #/ wire `rb_idx_for_wf`;
        ModuleDelay(DWT=1, N_CLK=N_CLK_DMRS_SEQ, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'current_RB_idx_lsb', 'o_data': rb_idx_for_wf})

    # Delay l_quote to align with DMRS sequence at OCC input.
    # The OCC uses l_quote combinationally alongside the DMRS_SEQ output,
    # which already has N_CLK_DMRS_SEQ clocks of latency.  Without this
    # delay the last N_CLK_DMRS_SEQ RBs of each DMRS symbol see the NEXT
    # symbol's l_quote, causing a w_t sign flip for Drawer-B ports.
    _need_occ_lquote = (is_double_dmrs == True or is_double_dmrs == "Hybrid")
    if _need_occ_lquote:
        _occ_lquote_d = 'l_quote_occ_d'
        #/ wire `_occ_lquote_d`;
        ModuleDelay(DWT=1, N_CLK=N_CLK_DMRS_SEQ, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'l_quote', 'o_data': _occ_lquote_d})

    for pcdmu in pcdmu_instances:
        #/ // ================================================================
        #/ // Unified PCDMU Group `pcdmu.group_idx`
        #/ // - Type1: `f"ports={pcdmu.type1_antenna_ports}, {len(pcdmu.type1_re_phy_indices)} RE, phy={pcdmu.type1_re_phy_indices}" if pcdmu.has_type1 else "N/A"`
        #/ // - Type2: `f"ports={pcdmu.type2_antenna_ports}, {len(pcdmu.type2_re_phy_indices)} RE, phy={pcdmu.type2_re_phy_indices}" if pcdmu.has_type2 else "N/A"`
        #/ // - Unified: ports=`pcdmu.unified_antenna_ports`, max_re=`pcdmu.max_re_count`
        #/ // ================================================================
        
        # =================================================================
        # 5a. W_F_CALC Instantiation
        # =================================================================
        #
        # W_F_CALC computes w_f from the sequential pilot index k' (k_quote).
        # re_logic_indices for W_F_CALC MUST be the sequential pilot index
        # [0, 1, 2, ...], NOT the TRUE_INDEX_LIST position. For multi-CDM
        # configs the TRUE_INDEX_LIST positions for one group can be all-even,
        # making k'%2 == 0 always and breaking Drawer-B frequency OCC.
        
        if pcdmu.is_hybrid:
            # --- Type1 W_F_CALC ---
            ports_wf_t1 = {}
            if is_enhanced == "Hybrid":
                ports_wf_t1['is_enhanced'] = 'is_enhanced'
            if is_enhanced == True or is_enhanced == "Hybrid":
                ports_wf_t1['current_RB_idx_lsb'] = rb_idx_for_wf
            
            for ant_port in pcdmu.type1_antenna_ports:
                for re_phy_idx in pcdmu.type1_re_phy_indices:
                    sig = f'w_f_t1_grp{pcdmu.group_idx}_p{ant_port}_re{re_phy_idx}'
                    #/ wire [1:0] `sig`;
                    ports_wf_t1[f'w_f_p{ant_port}_re{re_phy_idx}'] = sig
            ports_wf_t1['_unused_dummy'] = '1\'b0'
            
            ModuleW_F_CALC(dmrs_type=1, cdm_group=pcdmu.group_idx, is_enhanced=is_enhanced, antenna_ports=pcdmu.type1_antenna_ports, re_phy_indices=pcdmu.type1_re_phy_indices, re_logic_indices=list(range(len(pcdmu.type1_re_phy_indices))), PORTS=ports_wf_t1)
            
            # --- Type2 W_F_CALC ---
            ports_wf_t2 = {}
            if is_enhanced == "Hybrid":
                ports_wf_t2['is_enhanced'] = 'is_enhanced'
            # Type2 never needs RB index (enhanced k_quote mapping only affects Type1)
            
            for ant_port in pcdmu.type2_antenna_ports:
                for re_phy_idx in pcdmu.type2_re_phy_indices:
                    sig = f'w_f_t2_grp{pcdmu.group_idx}_p{ant_port}_re{re_phy_idx}'
                    #/ wire [1:0] `sig`;
                    ports_wf_t2[f'w_f_p{ant_port}_re{re_phy_idx}'] = sig
            ports_wf_t2['_unused_dummy'] = '1\'b0'
            
            ModuleW_F_CALC(dmrs_type=2, cdm_group=pcdmu.group_idx, is_enhanced=is_enhanced, antenna_ports=pcdmu.type2_antenna_ports, re_phy_indices=pcdmu.type2_re_phy_indices, re_logic_indices=list(range(len(pcdmu.type2_re_phy_indices))), PORTS=ports_wf_t2)
        else:
            # Single-type PCDMU: one W_F_CALC instance
            # Type 3 must be selected explicitly. Falling through to Type 2
            # picks up type2_antenna_ports/type2_re_phy_indices, which are empty
            # for a Type-3 group, so the port loop below never runs and
            # W_F_CALC degenerates to a bare _unused_dummy shell.
            if pcdmu.has_type1:
                active_type = 1
                active_ports = pcdmu.type1_antenna_ports
                active_re_phy = pcdmu.type1_re_phy_indices
            elif pcdmu.has_type3:
                active_type = 3
                active_ports = pcdmu.type3_antenna_ports
                active_re_phy = pcdmu.type3_re_phy_indices
            else:
                active_type = 2
                active_ports = pcdmu.type2_antenna_ports
                active_re_phy = pcdmu.type2_re_phy_indices

            ports_wf = {}
            if is_enhanced == "Hybrid":
                ports_wf['is_enhanced'] = 'is_enhanced'
            if active_type == 1 and (is_enhanced == True or is_enhanced == "Hybrid"):
                ports_wf['current_RB_idx_lsb'] = rb_idx_for_wf

            for ant_port in active_ports:
                for re_phy_idx in active_re_phy:
                    sig = f'w_f_grp{pcdmu.group_idx}_p{ant_port}_re{re_phy_idx}'
                    #/ wire [1:0] `sig`;
                    ports_wf[f'w_f_p{ant_port}_re{re_phy_idx}'] = sig
            ports_wf['_unused_dummy'] = '1\'b0'

            ModuleW_F_CALC(dmrs_type=active_type, cdm_group=pcdmu.group_idx, is_enhanced=is_enhanced, antenna_ports=active_ports, re_phy_indices=active_re_phy, re_logic_indices=list(range(len(active_re_phy))), PORTS=ports_wf)
        
        # =================================================================
        # 5b. Per-RE OCC + LS_ROT Processing Loop
        # =================================================================
        
        for re_idx in range(pcdmu.max_re_count):
            # Determine which types have valid data at this RE slot
            has_t1 = re_idx < len(pcdmu.type1_re_phy_indices) if pcdmu.has_type1 else False
            has_t2 = re_idx < len(pcdmu.type2_re_phy_indices) if pcdmu.has_type2 else False
            has_t3 = re_idx < len(pcdmu.type3_re_phy_indices) if pcdmu.has_type3 else False

            if not (has_t1 or has_t2 or has_t3):
                continue

            # Extract static indices for compile-time use
            t1_logic = pcdmu.type1_re_logic_indices[re_idx] if has_t1 else 0
            t1_phy   = pcdmu.type1_re_phy_indices[re_idx]   if has_t1 else 0
            t2_logic = pcdmu.type2_re_logic_indices[re_idx] if has_t2 else 0
            t2_phy   = pcdmu.type2_re_phy_indices[re_idx]   if has_t2 else 0
            t3_logic = pcdmu.type3_re_logic_indices[re_idx] if has_t3 else 0
            t3_phy   = pcdmu.type3_re_phy_indices[re_idx]   if has_t3 else 0
            
            #/ // --- Group`pcdmu.group_idx` RE base seq `re_idx` (T1:phy=`t1_phy if has_t1 else '-'`,logic=`t1_logic if has_t1 else '-'` | T2:phy=`t2_phy if has_t2 else '-'`,logic=`t2_logic if has_t2 else '-'` | T3:phy=`t3_phy if has_t3 else '-'`,logic=`t3_logic if has_t3 else '-'`) ---
            
            # ---------------------------------------------------------
            # DMRS Sequence Selection
            # ---------------------------------------------------------
            # The DMRS base sequence is indexed by ordinal position within the CDM group
            # (re_idx), NOT by position in TRUE_INDEX_LIST (re_logic_idx).
            #
            # The DMRS_SEQUENCE_GENERATION module generates sequential QPSK symbols
            # from the Gold sequence. For a given CDM group and re_idx:
            #   - Type 1: output[re_idx] is the DMRS value for the re_idx-th RE in the group
            #   - Type 2: output[re_idx] is the DMRS value for the re_idx-th RE in the group
            # The LFSR step size is already adjusted per dmrs_type in Hybrid mode,
            # so both types use the same ordinal index. No runtime mux needed.
            
            if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
                dmrs_seq_signal = f'dmrs_base_seq_cdm{pcdmu.group_idx}_{re_idx}'
            else:
                dmrs_seq_signal = f'dmrs_base_seq_{re_idx}'
            
            # ---------------------------------------------------------
            # Y Signal Selection
            # ---------------------------------------------------------
            # Y_pre_complex is indexed by logic position. Simple 2:1 mux for hybrid.
            
            if pcdmu.is_hybrid and has_t1 and has_t2 and t1_logic != t2_logic:
                y_signal = f"Y_mux_grp{pcdmu.group_idx}_re{re_idx}"
                #/ wire [`2*QU_H_LS.DWT`-1:0] `y_signal`;
                #/ assign `y_signal` = dmrs_type ? Y_pre_complex_`t2_logic` : Y_pre_complex_`t1_logic`;
            else:
                # Type 3 is never part of a Hybrid PCDMU, so it only reaches this
                # single-type branch.
                if has_t1:
                    logic_idx = t1_logic
                elif has_t3:
                    logic_idx = t3_logic
                else:
                    logic_idx = t2_logic
                y_signal = f'Y_pre_complex_{logic_idx}'
            
            # ---------------------------------------------------------
            # W_F Selection (per unified antenna port)
            # ---------------------------------------------------------
            # Build muxed w_f wires to feed into OCC for each antenna port.
            # For hybrid: select between Type1 and Type2 W_F_CALC outputs.
            
            for ant_port in pcdmu.unified_antenna_ports:
                if switchable_ports:
                    w_f_occ_signal = f'w_f_occ_raw_grp{pcdmu.group_idx}_p{ant_port}_re{re_idx}'
                else:
                    w_f_occ_signal = f'w_f_occ_grp{pcdmu.group_idx}_p{ant_port}_re{re_idx}'
                
                if pcdmu.is_hybrid:
                    port_in_t1 = ant_port in pcdmu.type1_antenna_ports and has_t1
                    port_in_t2 = ant_port in pcdmu.type2_antenna_ports and has_t2
                    
                    if port_in_t1 and port_in_t2:
                        # Port exists in both types — mux between Type1 and Type2 w_f
                        t1_wf = f'w_f_t1_grp{pcdmu.group_idx}_p{ant_port}_re{t1_phy}'
                        t2_wf = f'w_f_t2_grp{pcdmu.group_idx}_p{ant_port}_re{t2_phy}'
                        #/ wire [1:0] `w_f_occ_signal`;
                        #/ assign `w_f_occ_signal` = dmrs_type ? `t2_wf` : `t1_wf`;
                    elif port_in_t1:
                        t1_wf = f'w_f_t1_grp{pcdmu.group_idx}_p{ant_port}_re{t1_phy}'
                        #/ wire [1:0] `w_f_occ_signal`;
                        #/ assign `w_f_occ_signal` = `t1_wf`;
                    elif port_in_t2:
                        t2_wf = f'w_f_t2_grp{pcdmu.group_idx}_p{ant_port}_re{t2_phy}'
                        #/ wire [1:0] `w_f_occ_signal`;
                        #/ assign `w_f_occ_signal` = `t2_wf`;
                    else:
                        #/ wire [1:0] `w_f_occ_signal`;
                        #/ assign `w_f_occ_signal` = 2'b00;
                        pass
                else:
                    # Single-type: direct from W_F_CALC output.
                    # The index must match the type the W_F_CALC instance above was
                    # elaborated with (active_type / active_re_phy), otherwise the
                    # generated `w_f_grp*_p*_re*` name has no driver.
                    if pcdmu.has_type1:
                        phy_idx = t1_phy
                    elif pcdmu.has_type3:
                        phy_idx = t3_phy
                    else:
                        phy_idx = t2_phy
                    src_sig = f'w_f_grp{pcdmu.group_idx}_p{ant_port}_re{phy_idx}'
                    #/ wire [1:0] `w_f_occ_signal`;
                    #/ assign `w_f_occ_signal` = `src_sig`;
            
            # ---------------------------------------------------------
            # Port Enable Gating for W_F (low-power)
            # ---------------------------------------------------------
            if switchable_ports:
                for ant_port in pcdmu.unified_antenna_ports:
                    w_f_raw = f'w_f_occ_raw_grp{pcdmu.group_idx}_p{ant_port}_re{re_idx}'
                    w_f_gated = f'w_f_occ_grp{pcdmu.group_idx}_p{ant_port}_re{re_idx}'
                    port_en = f'port_enable_p{ant_port}'
                    #/ wire [1:0] `w_f_gated`;
                    #/ assign `w_f_gated` = `port_en` ? `w_f_raw` : 2'b00;  // Gate W_F for port `ant_port`
            
            # ---------------------------------------------------------
            # OCC Instantiation
            # ---------------------------------------------------------
            # The type-dependent logic in OCC is w_t (time-domain OCC):
            #   Type1: needs_flip = (port >> 2) & 1  →  ports 0-3: 0, ports 4-7: 1
            #   Type2: needs_flip = (port // 6) % 2  →  ports 0-5: 0, ports 6-11: 1
            #
            # For the common case antenna_ports=[0,1] (CDM group 0):
            #   Both Type1 and Type2 give needs_flip=0, w_t=0.
            #   So using either dmrs_Type=1 or 2 produces identical behavior.
            #
            # For higher ports (4-7): Type1 gives needs_flip=1, Type2 gives 0.
            #   These ports typically appear in different CDM groups per type, so
            #   a single-type PCDMU handles them correctly.
            
            if pcdmu.is_hybrid:
                # Select the drawer at runtime. Type-2-only high ports (for
                # example p18) are not representable by a fixed Type-1 rule.
                occ_dmrs_type = "Hybrid"
            else:
                # Type 3 deliberately maps to OCC's dmrs_Type=2. The only
                # type-dependent quantity in OCC is w_t, and for ports 0-23
                # Type 2's `(port // 6) % 2` is identical to Type 3's drawer
                # split `(port % 12) >= 6` (both flip at 6-11 and 18-23).
                # Verified against edu_platform/utils/lut_dmrs_occ.m.
                occ_dmrs_type = 1 if pcdmu.has_type1 else 2
            
            ports_occ = {
                'in': dmrs_seq_signal,
                'clk': 'clk',
                'rst_n': 'rst_n'
            }
            
            for ant_port in pcdmu.unified_antenna_ports:
                ports_occ[f'w_f_p{ant_port}'] = f'w_f_occ_grp{pcdmu.group_idx}_p{ant_port}_re{re_idx}'
            
            # Only connect l_quote when the OCC instance declares it (i.e. some
            # port in this CDM group takes the time-domain flip). Same predicate
            # ModuleOCC uses, imported rather than re-derived.
            if occ_needs_l_quote(pcdmu.unified_antenna_ports, occ_dmrs_type,
                                 is_double_dmrs):
                ports_occ['l_quote'] = _occ_lquote_d
            if occ_needs_dmrs_type(pcdmu.unified_antenna_ports, occ_dmrs_type,
                                    is_double_dmrs):
                ports_occ['dmrs_type'] = 'dmrs_type'
            if is_double_dmrs == "Hybrid":
                ports_occ['is_double_dmrs'] = 'is_double_dmrs'
            
            # NOTE: `whid_signal` carries the effective pilot φ = in × w_f × (-1)^w_t
            # (DMRS {±1±j} encoding). LS_ROT consumes φ and produces Y × conj(φ).
            # The name is retained for historical consistency with OCC/LS_ROT port
            # names (`whid_i`) — see v_occ.py / v_ls_rot.py docstrings.
            for ant_port in pcdmu.unified_antenna_ports:
                whid_signal = f'whid_grp{pcdmu.group_idx}_re{re_idx}_p{ant_port}'
                #/ wire [1:0] `whid_signal`;
                ports_occ[f'out_p{ant_port}'] = whid_signal
            
            ModuleOCC(N_CLK=1, dmrs_Type=occ_dmrs_type, antenna_ports=pcdmu.unified_antenna_ports, is_double_dmrs=is_double_dmrs, PORTS=ports_occ)
            
            # ---------------------------------------------------------
            # LS_ROT Instantiation
            # ---------------------------------------------------------
            # LS_ROT is type-independent: just QPSK rotation based on whid.
            #
            # Output H_LS port naming:
            # For hybrid mode, Type1 and Type2 have different physical RE indices
            # at the same re_idx slot. But since only one type is active per clock,
            # the LS_ROT output wire is DIRECTLY connected to the output port.
            # We connect to Type1's phy index when available (since Type1 is the
            # default OCC type); the actual physical meaning is handled by the
            # downstream consumer which knows the active dmrs_type.
            #
            # NOTE: For a truly clean design, the output should map to ALL possible
            # phy indices with a demux. But since only one type is active at a time,
            # and both Type1 and Type2 have distinct phy indices, we can connect
            # each LS_ROT output to a unique output port based on active type.
            
            ports_ls_rot = {}
            if N_CLK_LS_ROT > 0:
                ports_ls_rot['clk'] = 'clk'
            
            for ant_idx, ant_port in enumerate(pcdmu.unified_antenna_ports):
                whid_signal = f'whid_grp{pcdmu.group_idx}_re{re_idx}_p{ant_port}'
                
                # For module Hybrid mode: always route LS_ROT output to an
                # intermediate wire and defer physical H_LS assignment globally.
                # This avoids multi-driver conflicts across different PCDMU groups.
                if dmrs_Type == "Hybrid":
                    # Output to intermediate wire (unique per re_idx/port)
                    intermediate = f'H_LS_intermediate_grp{pcdmu.group_idx}_re{re_idx}_p{ant_port}'
                    DWT_total_int = 2 * QU_H_LS.DWT
                    #/ wire [`DWT_total_int`-1:0] `intermediate`;
                    h_ls_signal = intermediate

                    # Record all possible physical destinations for this source.
                    if has_t1:
                        hybrid_hls_sources.setdefault((ant_port, t1_phy), []).append((intermediate, 1))
                    if has_t2:
                        hybrid_hls_sources.setdefault((ant_port, t2_phy), []).append((intermediate, 2))
                else:
                    if has_t1:
                        out_phy_idx = t1_phy
                    elif has_t3:
                        out_phy_idx = t3_phy
                    else:
                        out_phy_idx = t2_phy
                    h_ls_signal = f'H_LS_port{ant_port}_re{out_phy_idx}'
                
                ports_ls_rot[f'whid_{ant_idx}'] = whid_signal
                # Low-power gating: zero LS_ROT input when port is disabled
                if switchable_ports:
                    gated_y = f'Y_gated_grp{pcdmu.group_idx}_re{re_idx}_p{ant_port}'
                    port_en = f'port_enable_p{ant_port}'
                    DWT_total = 2 * QU_H_LS.DWT
                    #/ wire [`DWT_total`-1:0] `gated_y`;
                    #/ assign `gated_y` = `port_en` ? `y_signal` : {`DWT_total`{1'b0}};  // Gate Y input for port `ant_port`
                    ports_ls_rot[f'in_complex_{ant_idx}'] = gated_y
                else:
                    ports_ls_rot[f'in_complex_{ant_idx}'] = y_signal
                ports_ls_rot[f'out_complex_{ant_idx}'] = h_ls_signal
            
            ModuleLS_ROT(parallelism=len(pcdmu.unified_antenna_ports), Qu_IN=QU_H_LS, Qu_OUT=QU_H_LS, N_CLK=N_CLK_LS_ROT, PORTS=ports_ls_rot)

    # Emit exactly one assignment per physical H_LS wire in Hybrid mode.
    if dmrs_Type == "Hybrid":
        for (ant_port, phy_idx), sources in hybrid_hls_sources.items():
            wire_name = f'H_LS_port{ant_port}_re{phy_idx}'

            # De-duplicate while preserving order.
            unique_sources: List[tuple[str, int]] = []
            for src in sources:
                if src not in unique_sources:
                    unique_sources.append(src)

            t1_sources = [sig for sig, src_type in unique_sources if src_type == 1]
            t2_sources = [sig for sig, src_type in unique_sources if src_type == 2]

            if t1_sources and t2_sources:
                #/ assign `wire_name` = dmrs_type ? `t2_sources[0]` : `t1_sources[0]`;
                pass
            elif t1_sources:
                #/ assign `wire_name` = `t1_sources[0]`;
                pass
            elif t2_sources:
                #/ assign `wire_name` = `t2_sources[0]`;
                pass
    
    # =========================================================================
    # Step 6: AVERAGING (De-OCC Part 2) 
    # =========================================================================
    #
    # Per (CDM group, antenna_port, component):
    #   - Unpack complex H_LS → real / imag
    #   - Map RE-indexed → pilot-indexed
    #   - Instantiate AVERAGING module
    #   - Map pilot-indexed → RE-indexed complex output
    # =========================================================================
    
    #/ // ========== AVERAGING (de-OCC Part 2, per port per component) ==========
    
    DWT_LS = QU_H_LS.DWT
    
    for pcdmu in pcdmu_instances:
        g = pcdmu.group_idx
        #/ // --- Averaging for CDM group `g` ---

        # Determine pilot count and RE positions for this CDM group
        if pcdmu.has_type1:
            pilot_re_t1 = PILOT_RE_TYPE1[g]
            n_pilots_t1 = len(pilot_re_t1)
        else:
            n_pilots_t1 = 0
        if pcdmu.has_type2:
            pilot_re_t2 = PILOT_RE_TYPE2[g]
            n_pilots_t2 = len(pilot_re_t2)
        else:
            n_pilots_t2 = 0
        if pcdmu.has_type3:
            from dmrs_config import PILOT_RE_TYPE3
            pilot_re_t3 = PILOT_RE_TYPE3[g]
            n_pilots_t3 = len(pilot_re_t3)
        else:
            n_pilots_t3 = 0
        
        n_pilots_avg = max(n_pilots_t1, n_pilots_t2, n_pilots_t3)

        # Determine effective dmrs_Type for this CDM group
        if pcdmu.has_type1 and pcdmu.has_type2:
            avg_dmrs_type = dmrs_Type  # could be "Hybrid" or int
        elif pcdmu.has_type1:
            avg_dmrs_type = 1
        elif pcdmu.has_type3:
            avg_dmrs_type = 3
        else:
            avg_dmrs_type = 2
        
        # ---- LS -> AVERAGING wire assigns ----
        # Unpack complex LS output to real/imag, map RE-indexed to pilot-indexed
        for ant_port in pcdmu.unified_antenna_ports:
            for rb in range(RB_PARALLELISM):
                for k in range(n_pilots_avg):
                    avg_in_r = f"H_LS_avg_in_port{ant_port}_cdm{g}_rb{rb}_pilot{k}_real"
                    avg_in_i = f"H_LS_avg_in_port{ant_port}_cdm{g}_rb{rb}_pilot{k}_imag"
                    
                    if pcdmu.is_hybrid:
                        # Hybrid: mux between Type 1 and Type 2 LS outputs
                        if k < n_pilots_t2:
                            t1_re_phy = rb * RE_PER_RB + pilot_re_t1[k]
                            t2_re_phy = rb * RE_PER_RB + pilot_re_t2[k]
                            t1_sig = f"H_LS_port{ant_port}_re{t1_re_phy}"
                            t2_sig = f"H_LS_port{ant_port}_re{t2_re_phy}"
                            #/ wire [`DWT_LS`-1:0] `avg_in_r`;
                            #/ assign `avg_in_r` = dmrs_type ? `t2_sig`[`DWT_LS`-1:0] : `t1_sig`[`DWT_LS`-1:0];
                            #/ wire [`DWT_LS`-1:0] `avg_in_i`;
                            #/ assign `avg_in_i` = dmrs_type ? `t2_sig`[`2*DWT_LS`-1:`DWT_LS`] : `t1_sig`[`2*DWT_LS`-1:`DWT_LS`];
                        else:
                            t1_re_phy = rb * RE_PER_RB + pilot_re_t1[k]
                            t1_sig = f"H_LS_port{ant_port}_re{t1_re_phy}"
                            #/ wire [`DWT_LS`-1:0] `avg_in_r` = `t1_sig`[`DWT_LS`-1:0];
                            #/ wire [`DWT_LS`-1:0] `avg_in_i` = `t1_sig`[`2*DWT_LS`-1:`DWT_LS`];
                    elif pcdmu.has_type1:
                        re_phy = rb * RE_PER_RB + pilot_re_t1[k]
                        ls_sig = f"H_LS_port{ant_port}_re{re_phy}"
                        #/ wire [`DWT_LS`-1:0] `avg_in_r` = `ls_sig`[`DWT_LS`-1:0];
                        #/ wire [`DWT_LS`-1:0] `avg_in_i` = `ls_sig`[`2*DWT_LS`-1:`DWT_LS`];
                    elif pcdmu.has_type3:
                        re_phy = rb * RE_PER_RB + pilot_re_t3[k]
                        ls_sig = f"H_LS_port{ant_port}_re{re_phy}"
                        #/ wire [`DWT_LS`-1:0] `avg_in_r` = `ls_sig`[`DWT_LS`-1:0];
                        #/ wire [`DWT_LS`-1:0] `avg_in_i` = `ls_sig`[`2*DWT_LS`-1:`DWT_LS`];
                    else:
                        re_phy = rb * RE_PER_RB + pilot_re_t2[k]
                        ls_sig = f"H_LS_port{ant_port}_re{re_phy}"
                        #/ wire [`DWT_LS`-1:0] `avg_in_r` = `ls_sig`[`DWT_LS`-1:0];
                        #/ wire [`DWT_LS`-1:0] `avg_in_i` = `ls_sig`[`2*DWT_LS`-1:`DWT_LS`];
        
        # ---- Per (antenna_port, part) AVERAGING instantiation ----
        need_td_avg = (tdCDM.get(g) == 2 or tdCDM.get(g) == 'Hybrid')

        _fdCDM_g = fdCDM.get(g, 2) # Get the fdCDM configuration for CDM group g

        MAX_FDCDM_G = 4 if _fdCDM_g == 'Hybrid' else (_fdCDM_g if isinstance(_fdCDM_g, int) else 4)

        # Enhanced DMRS Type 1 possibility: The averaging window could span across two RBs
        need_cross_rb_g = (MAX_FDCDM_G == 4) and (avg_dmrs_type == 1 or avg_dmrs_type == 'Hybrid')
        _tdCDM_g = tdCDM.get(g, 1)

        # ---- Delay sym_switch and l_quote to align with AVERAGING data input ----
        # Data arrives at AVERAGING after N_CLK_Y_PRE + N_CLK_LS_ROT clocks,
        # then AVERAGING's Stage 1 register adds 1 more clock before SRAM write.
        # AVERAGING internally delays sym_switch and l_quote by 1 clock each
        # (sym_switch_q, l_quote_q) to align with Stage 1 output.
        #
        # sym_switch: needs total delay = Y_PRE + LS_ROT (ext) + 1 (int) so
        #   sym_switch_q fires at the first l'=1 Stage 1 output clock, resetting
        #   the SRAM address counter for the new symbol.
        # l_quote: needs 1 more external clock than sym_switch because l_quote_q
        #   gates sram_wr_en. If l_quote transitions at the same clock as the
        #   last l'=0 SRAM write, the write would be suppressed.
        _avg_strb_delay = N_CLK_Y_PRE + N_CLK_LS_ROT - 1
        _avg_lquote_delay = N_CLK_Y_PRE + N_CLK_LS_ROT
        _need_avg_strb = need_td_avg or need_cross_rb_g
        if HAS_AVG_SYM_SWITCH:
            _avg_enable_d = f"avg_enable_d_cdm{g}"
            #/ wire `_avg_enable_d`;
            # Y replay is prefetched one cycle before the Gold-sequence
            # advance in single-symbol mode.  Gate AVERAGING with the actual
            # Y-beat descriptor rather than the later LFSR enable.
            ModuleDelay(DWT=1, N_CLK=_avg_lquote_delay, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'replay_data_valid', 'o_data': _avg_enable_d})  # type: ignore
        if _need_avg_strb:
            _avg_strb_d = f"avg_sym_switch_d_cdm{g}"
            #/ wire `_avg_strb_d`;
            ModuleDelay(DWT=1, N_CLK=_avg_strb_delay, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': _avg_strb_signal, 'o_data': _avg_strb_d})  # type: ignore
        if need_td_avg:
            _avg_lquote_d = f"avg_l_quote_d_cdm{g}"
            #/ wire `_avg_lquote_d`;
            ModuleDelay(DWT=1, N_CLK=_avg_lquote_delay, IF_RST_N=False, PORTS={'i_clk': 'clk', 'i_data': 'l_quote', 'o_data': _avg_lquote_d})  # type: ignore
        
        for ant_port in pcdmu.unified_antenna_ports:
            for part in ('real', 'imag'):
                #/ // --- AVERAGING: CDM group `g`, port `ant_port`, `part` ---
                
                ports_avg = {
                    'clk': 'clk',
                }
                ports_avg['rst_n'] = 'rst_n'
                
                # fdCDM/tdCDM control signals
                if _fdCDM_g == 'Hybrid':
                    ports_avg['fdCDM_ctrl'] = f'fdCDM_ctrl_cdm{g}'
                if _tdCDM_g == 'Hybrid':
                    ports_avg['tdCDM_ctrl'] = f'tdCDM_ctrl_cdm{g}'
                if HAS_AVG_SYM_SWITCH:
                    ports_avg['enable'] = _avg_enable_d
                
                if need_td_avg:
                    ports_avg['l_quote'] = _avg_lquote_d
                if need_td_avg or need_cross_rb_g:
                    ports_avg['sym_switch'] = _avg_strb_d
                
                # Connect per-RB, per-pilot inputs and outputs
                for rb in range(RB_PARALLELISM):
                    for k in range(n_pilots_avg):
                        ports_avg[f'h_ls_rb{rb}_pilot{k}'] = f"H_LS_avg_in_port{ant_port}_cdm{g}_rb{rb}_pilot{k}_{part}"
                        
                        out_wire = f"H_avg_port{ant_port}_cdm{g}_rb{rb}_pilot{k}_{part}"
                        #/ wire [`QU_H_LS.DWT`-1:0] `out_wire`;
                        ports_avg[f'h_avg_rb{rb}_pilot{k}'] = out_wire
                
                ModuleAVERAGING(Qu_IN=QU_H_LS, Qu_OUT=QU_H_LS, QU_MODE=QU_MODE_LS, OF_MODE=OF_MODE_LS, IF_RST_N=True, RB_PARALLELISM=RB_PARALLELISM, dmrs_Type=avg_dmrs_type, cdm_group=g, fdCDM=_fdCDM_g, tdCDM=_tdCDM_g, max_num_RBs=max_num_RBs, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG, HAS_ENABLE=HAS_AVG_SYM_SWITCH, PORTS=ports_avg)
    
    # =========================================================================
    # Step 7: AVERAGING → Output Wire Packing
    # =========================================================================
    # Pack pilot-indexed averaged real/imag back to RE-indexed complex outputs.
    # Output port naming: H_avg_port{ant_port}_rb{rb}_re{re_k}_complex
    # =========================================================================
    
    #/ // ========== AVERAGING -> Output wire packing ==========
    
    for ant_port in antenna_ports:
        info = arch_config.get_port_interp_info(ant_port)
        
        for rb in range(RB_PARALLELISM):
            for re_k in info.pilot_re_list:
                avg_complex = f"H_avg_port{ant_port}_rb{rb}_re{re_k}_complex"
                
                if not info.is_dual_type:
                    # Single type: find CDM group and pilot index for this RE
                    if info.type_category == 1:
                        cdm_g = get_cdm_group_for_port(ant_port, 1)
                        pilot_k = PILOT_RE_TYPE1[cdm_g].index(re_k)
                    elif info.type_category == 3:
                        cdm_g = get_cdm_group_for_port(ant_port, 3)
                        pilot_k = PILOT_RE_TYPE3[cdm_g].index(re_k)
                    else:  # type_category == 2
                        cdm_g = get_cdm_group_for_port(ant_port, 2)
                        pilot_k = PILOT_RE_TYPE2[cdm_g].index(re_k)
                    avg_r = f"H_avg_port{ant_port}_cdm{cdm_g}_rb{rb}_pilot{pilot_k}_real"
                    avg_i = f"H_avg_port{ant_port}_cdm{cdm_g}_rb{rb}_pilot{pilot_k}_imag"
                    #/ assign `avg_complex` = {`avg_i`, `avg_r`};
                else:
                    # Dual type: mux between Type 1 and Type 2 pilot data
                    cdm_g1 = get_cdm_group_for_port(ant_port, 1)
                    cdm_g2 = get_cdm_group_for_port(ant_port, 2)
                    in_t1 = re_k in PILOT_RE_TYPE1[cdm_g1]
                    in_t2 = re_k in PILOT_RE_TYPE2[cdm_g2]
                    
                    if in_t1 and in_t2:
                        pk1 = PILOT_RE_TYPE1[cdm_g1].index(re_k)
                        pk2 = PILOT_RE_TYPE2[cdm_g2].index(re_k)
                        r1 = f"H_avg_port{ant_port}_cdm{cdm_g1}_rb{rb}_pilot{pk1}_real"
                        i1 = f"H_avg_port{ant_port}_cdm{cdm_g1}_rb{rb}_pilot{pk1}_imag"
                        r2 = f"H_avg_port{ant_port}_cdm{cdm_g2}_rb{rb}_pilot{pk2}_real"
                        i2 = f"H_avg_port{ant_port}_cdm{cdm_g2}_rb{rb}_pilot{pk2}_imag"
                        #/ assign `avg_complex` = dmrs_type ? {`i2`, `r2`} : {`i1`, `r1`};
                    elif in_t1:
                        pk1 = PILOT_RE_TYPE1[cdm_g1].index(re_k)
                        r1 = f"H_avg_port{ant_port}_cdm{cdm_g1}_rb{rb}_pilot{pk1}_real"
                        i1 = f"H_avg_port{ant_port}_cdm{cdm_g1}_rb{rb}_pilot{pk1}_imag"
                        #/ assign `avg_complex` = {`i1`, `r1`};
                    else:
                        pk2 = PILOT_RE_TYPE2[cdm_g2].index(re_k)
                        r2 = f"H_avg_port{ant_port}_cdm{cdm_g2}_rb{rb}_pilot{pk2}_real"
                        i2 = f"H_avg_port{ant_port}_cdm{cdm_g2}_rb{rb}_pilot{pk2}_imag"
                        #/ assign `avg_complex` = {`i2`, `r2`};
    
    if REPLAY_TOKEN_DWT > 0:
        # The replay token enters beside the Y beat and traverses the same
        # end-to-end latency as Y_PRE -> LS_ROT -> AVERAGING.  Keeping this
        # delay in LS makes publication timing follow the datapath contract
        # instead of a window-controller tap chosen for one protocol mode.
        _replay_token_delay = N_CLK_Y_PRE + N_CLK_LS_ROT + N_CLK_AVG
        ModuleDelay(DWT=1, N_CLK=_replay_token_delay, IF_RST_N=True, PORTS={'i_clk': 'clk', 'i_rst_n': 'rst_n', 'i_data': 'replay_token_valid_in', 'o_data': 'replay_token_valid_out'})
        ModuleDelay(DWT=REPLAY_TOKEN_DWT, N_CLK=_replay_token_delay, IF_RST_N=True, PORTS={'i_clk': 'clk', 'i_rst_n': 'rst_n', 'i_data': 'replay_token_in', 'o_data': 'replay_token_out'})

    #/ endmodule
    
    
    
    
if __name__ == "__main__":
    print('Starting module generation...')
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_debug_mode(False)  # Set True for verbose RTL generation logging
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    ModuleLS(
        Qu_Y=QuType(11, 4, True),
        QU_H_LS=QuType(12, 4, True),
        QU_MODE_LS=QuMode.TRN.TCPL,
        OF_MODE_LS=OfMode.WRP.TCPL,
        N_CLK_Y_PRE=3,
        N_CLK_DMRS_SEQ=2,
        N_CLK_LS_ROT=1,
        dmrs_Type= "Hybrid",
        dmrs_Uplink=True,
        is_ECP=False,
        is_enhanced="Hybrid",
        is_double_dmrs="Hybrid",
        antenna_ports= [0,1],
        TRUE_INDEX_LIST=[0,2,4,6,8,10,1,7],
        switchable_ports=True,
        RB_PARALLELISM=1,
        fdCDM={0: 'Hybrid'},
        tdCDM={0: 'Hybrid'},
        max_num_RBs=273,
    )
    print('SUCCESS: Module generation completed')
