import math
from os.path import dirname
import sys
sys.path.append(dirname(__file__))
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from basic_modules.PyTU import QuMode, QuType, OfMode
from typing import Any
from top_api import ArchitectureConfig, ArithmeticConfig, ImplementationConfig, ProtocolSpec, QuantKey, resolve_top_config
from v_ls import ModuleLS
from v_c_init_generation import ModuleC_INIT_GENERATION
from v_freq_interp import ModuleFREQ_INTERP
from v_coeff_sram import ModuleCOEFF_SRAM
from v_port_enable import ModulePORT_ENABLE
from v_cdm_ctrl import ModuleCDM_CTRL
# Averaging is instantiated inside the LS module boundary.
from v_y_path_reduce import ModuleY_PATH_REDUCE
from v_y_rb_align import ModuleY_RB_ALIGN
# Time-domain interpolation modules
from v_time_interp import ModuleTIME_INTERP
from v_cfg_latch import ModuleCFG_LATCH
# Unified DMRS configuration layer
from dmrs_config import (
    DmrsArchConfig, get_pilot_re_for_port_unified, compute_required_re_indices,
)
from analyze_timing import analyze_cinit_timing, analyze_interp_timing, analyze_ls_timing, build_ls_ctrl_graph, build_fi_core_graph, build_ti_ctrl_graph
from typing import Dict, List, Literal, Optional

from v_controller import ModuleCONTROLLER
from v_ls_buf import ModuleLS_BUF
from v_y_buf import ModuleY_BUF
from v_ls_fi_window_ctrl import ModuleLS_FI_WINDOW_CTRL


# =============================================================================
# Pre-computation helper: derive all TOP-level parameters and timing
# =============================================================================

def _prepare_top_context(
    pusch_params, puschdmrs_params, Y, RB_PARALLELISM, ANTENNA_PORTS,
    H_interp_f_DWT, freq_interp_method, time_interp_method,
    switchable_ports, INPUT_MODE, QU_H_LS, additional_DMRS_range=None,
    LMMSE_INTERP_PARALLELISM=4,
    TI_LMMSE_COEFF_SOURCE='ROM',
    FI_LMMSE_COEFF_SOURCE='ROM',
    FI_LMMSE_COEFF_DWT=12,
    FI_LMMSE_REAL_COEFF=True,
    FI_RE_PARALLELISM=12,
    TI_RE_PARALLELISM=3,
    RB_PARALLELISM_FOR_TIMING=None,
    production_observation_layouts=None,
):
    """Extract parameter parsing, validation, arch config, and timing analysis
    from ModuleTOP so the @convert body focuses on wiring and instantiation."""

    # ---- Parse PUSCH / PUSCHDMRS protocol params ----
    num_RB_range = pusch_params['num_RB_range']
    min_num_RBs, max_num_RBs = num_RB_range[0], num_RB_range[-1]
    num_symbols_range = pusch_params['num_symbols_range']
    min_pusch_symbols = num_symbols_range[0]
    max_pusch_symbols = num_symbols_range[-1]
    counter_width = math.ceil(math.log2(max_num_RBs)) if max_num_RBs > 1 else 1
    is_ECP = pusch_params['is_ECP']

    dmrs_Type = puschdmrs_params['dmrs_Type']
    is_double_dmrs = puschdmrs_params['is_double_dmrs']
    is_enhanced = puschdmrs_params['is_enhanced']
    dmrs_typeA_pos = puschdmrs_params['dmrs_typeA_pos']
    dmrs_Uplink = puschdmrs_params['dmrs_Uplink']
    if additional_DMRS_range is None:
        additional_DMRS_range = puschdmrs_params['additional_DMRS_range']
    if not additional_DMRS_range:
        raise ValueError("additional_DMRS_range cannot be empty")

    num_front_loaded_dmrs = 2 if (is_double_dmrs is True or is_double_dmrs == 'Hybrid') else 1

    # ---- Y / RE geometry ----
    Y_total_bits = 2 * Y.DWT * 12
    INPUT_INDEX_LIST = list(range(RB_PARALLELISM * 12))
    production_layout_metadata = ()
    production_lane_representatives = {}
    if production_observation_layouts is not None:
        if switchable_ports or dmrs_Type == "Hybrid":
            raise ValueError(
                "descriptor-bound production requires fixed type and generation-time ports"
            )
        if min_num_RBs != max_num_RBs:
            raise ValueError(
                "descriptor-bound production requires one fixed RB allocation"
            )
        from production_observation import (
            local_lane_representatives,
            local_required_re_indices,
            select_production_layouts,
        )

        production_layout_metadata = select_production_layouts(
            production_observation_layouts,
            dmrs_type=dmrs_Type,
            antenna_ports=ANTENNA_PORTS,
            num_rbs=max_num_RBs,
        )
        required_sets = {
            local_required_re_indices(metadata)
            for metadata in production_layout_metadata
        }
        required_re_per_rb = sorted(set().union(*required_sets))
        production_lane_representatives = {
            metadata.antenna_port: local_lane_representatives(metadata)
            for metadata in production_layout_metadata
        }
    else:
        required_re_per_rb = compute_required_re_indices(ANTENNA_PORTS, dmrs_Type)
    TRUE_INDEX_LIST = [
        rb * 12 + re_k
        for rb in range(RB_PARALLELISM)
        for re_k in required_re_per_rb
    ]

    # ---- Validate ----
    if dmrs_Type not in (1, 2, 3, "Hybrid"):
        raise ValueError(f"Invalid dmrs_Type: {dmrs_Type}. Must be 1, 2, 3, or 'Hybrid'.")

    k_positions = set(re % 12 for re in TRUE_INDEX_LIST)
    missing = set(required_re_per_rb) - k_positions
    if missing:
        raise ValueError(
            f"TRUE_INDEX_LIST is missing required pilot RE positions {sorted(missing)} "
            f"(k % 12) for the given antenna_ports={ANTENNA_PORTS} and dmrs_Type={dmrs_Type}.\n"
            f"Required RE positions: {required_re_per_rb} ({len(required_re_per_rb)} RE).\n"
            f"Provided k positions:  {sorted(k_positions)}.\n"
            f"Minimum parallelism per RB/clock: {len(required_re_per_rb)} RE."
        )
    if INPUT_MODE not in ('A', 'B'):
        raise ValueError(f"INPUT_MODE must be 'A', 'B', got {INPUT_MODE!r}")

    # ---- DmrsArchConfig ----
    arch_config = DmrsArchConfig(
        antenna_ports=ANTENNA_PORTS, dmrs_Type=dmrs_Type,
        TRUE_INDEX_LIST=TRUE_INDEX_LIST,
    )
    max_cdm_groups = arch_config.MAX_CDM_GROUPS
    total_cdm_groups = sum(
        (1 if p.has_type1 else 0) + (1 if p.has_type2 else 0)
        for p in arch_config.pcdmu_instances
    )

    # ---- CDM group timing configs ----
    _cdm_active_groups = sorted(set(p.group_idx for p in arch_config.pcdmu_instances))
    _DMRS_PARALLELISM = max(p.max_re_count for p in arch_config.pcdmu_instances) if arch_config.pcdmu_instances else 12

    if production_layout_metadata:
        _fdCDM_timing = {
            metadata.cdm_group: metadata.fd_cdm
            for metadata in production_layout_metadata
        }
        _tdCDM_timing = {
            metadata.cdm_group: metadata.td_cdm
            for metadata in production_layout_metadata
        }
    elif switchable_ports or dmrs_Type == "Hybrid":
        _fdCDM_timing = {g: 'Hybrid' for g in _cdm_active_groups}
        _tdCDM_timing = {g: 'Hybrid' for g in _cdm_active_groups}
    else:
        _fdCDM_timing = {p.group_idx: p.get_fdCDM(dmrs_Type) for p in arch_config.pcdmu_instances}
        _tdCDM_timing = {p.group_idx: p.get_tdCDM(dmrs_Type) for p in arch_config.pcdmu_instances}

    _cdm_group_configs = []
    for _pcdmu in arch_config.pcdmu_instances:
        _g = _pcdmu.group_idx
        if _pcdmu.has_type1 and _pcdmu.has_type2:
            _avg_dt = dmrs_Type
        elif _pcdmu.has_type1:
            _avg_dt = 1
        else:
            _avg_dt = 2
        _cdm_group_configs.append({
            'group_idx': _g, 'avg_dmrs_type': _avg_dt,
            'fdCDM': _fdCDM_timing.get(_g, 2), 'tdCDM': _tdCDM_timing.get(_g, 1),
        })

    # ---- LS pipeline timing ----
    ls_timing = analyze_ls_timing(
        Qu_Y=Y, QU_H_LS=QU_H_LS, MAX_CDM_GROUPS=max_cdm_groups,
        DMRS_PARALLELISM=_DMRS_PARALLELISM, dmrs_Type=dmrs_Type,
        is_double_dmrs=is_double_dmrs, cdm_group_configs=_cdm_group_configs,
        RB_PARALLELISM=RB_PARALLELISM, freq_interp_method=freq_interp_method,
        Qu_H_DWT=H_interp_f_DWT // 2, additional_DMRS_range=additional_DMRS_range,
        LMMSE_P=LMMSE_INTERP_PARALLELISM,
        COEFF_DWT_LMMSE=FI_LMMSE_COEFF_DWT,
        REAL_COEFF_LMMSE=FI_LMMSE_REAL_COEFF,
        FI_RE_PARALLELISM=FI_RE_PARALLELISM,
    )
    LS_DRAIN_CYCLES = ls_timing['total_pipeline_depth']

    # ---- SRAM geometry (shared by ctrl_delay_table and TI) ----
    SRAM_DEPTH = math.ceil(max_num_RBs / RB_PARALLELISM)
    SRAM_ADDR_WIDTH = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1

    # ---- Pre-FI buffer auto-selection ----
    _max_occasions_ctx = 1 + max(additional_DMRS_range)
    HAS_PRE_FI_BUF = ((LMMSE_INTERP_PARALLELISM > 0) and (freq_interp_method == 'lmmse')) or (_max_occasions_ctx == 1 and freq_interp_method in ('nn', 'linear') and time_interp_method in ('nn', 'linear'))

    # ---- Control signal dependency graph (LS phase) ----
    ls_ctrl_graph = build_ls_ctrl_graph(
        ls_timing=ls_timing,
        counter_width=counter_width,
        SRAM_ADDR_WIDTH=SRAM_ADDR_WIDTH,
        RB_PARALLELISM=RB_PARALLELISM,
        freq_interp_method=freq_interp_method,
        max_occasions=_max_occasions_ctx,
        is_double_dmrs=is_double_dmrs,
        has_pre_fi_buf=HAS_PRE_FI_BUF,
    )

    # ---- Interpolation timing ----
    interp_timing = analyze_interp_timing(
        freq_interp_method=freq_interp_method, time_interp_method=time_interp_method,
        Qu_H_DWT=H_interp_f_DWT // 2, additional_DMRS_range=additional_DMRS_range,
        FI_LMMSE_COEFF_DWT=FI_LMMSE_COEFF_DWT,
        FI_LMMSE_P=LMMSE_INTERP_PARALLELISM,
        FI_RB_PARALLELISM=RB_PARALLELISM,
        FI_LMMSE_REAL_COEFF=FI_LMMSE_REAL_COEFF,
        FI_RE_PARALLELISM=FI_RE_PARALLELISM,
        has_pre_fi_buf=HAS_PRE_FI_BUF,
    )
    TI_PIPELINE_DEPTH = interp_timing['time_depth']

    if freq_interp_method == 'lmmse' and HAS_PRE_FI_BUF:
        FI_WINDOW_SIZE = LMMSE_INTERP_PARALLELISM
    elif HAS_PRE_FI_BUF:
        FI_WINDOW_SIZE = RB_PARALLELISM
    else:
        FI_WINDOW_SIZE = 1

    if HAS_PRE_FI_BUF:
        if freq_interp_method == 'lmmse':
            _drain_beats = max(LMMSE_INTERP_PARALLELISM // max(RB_PARALLELISM, 1), 1)
            # Window-controller trigger-to-FI handoff:
            #   accept + load + issue beats + LS drain + save + publish
            #   + consumer bank-detect/wait.
            # Relative to the old ad-hoc sequencer this adds six fixed FSM
            # cycles.  Use beats-per-window (not RB count) for RB_PAR > 1.
            _window_ctrl_handoff = 6
            _replay_setup_single = _drain_beats + ls_timing['pre_fi_pipeline_depth'] + _window_ctrl_handoff
            _replay_setup = _replay_setup_single
            if is_double_dmrs is True or is_double_dmrs == 'Hybrid':
                # A second front-loaded DMRS symbol must traverse the same
                # window before TD-CDM pilots are publishable: LOAD, ISSUE
                # beats, LS drain, and SAVE/transition.
                _replay_setup += _drain_beats + ls_timing['pre_fi_pipeline_depth'] + 2
            # Hold the occasion tag through the final registered drain beat.
            # ``freq_depth`` is trigger-to-first-output latency, while
            # ``_drain_beats`` is the number of valid output beats; therefore
            # the inclusive trigger-to-last-output interval needs the full
            # drain count here.  Subtracting one advances ``fi_occ_sel`` on
            # the edge that writes the final beat into TIME_INTERP.
            FI_CYCLES_PER_OCC_SINGLE = interp_timing['freq_depth'] + _drain_beats + _replay_setup_single
            FI_CYCLES_PER_OCC = interp_timing['freq_depth'] + _drain_beats + _replay_setup
        else:
            # 1 (prefetch next-RB read) + 1 (current-RB SRAM read) + freq_depth (FI pipeline) + 1 (write-before-read guard)
            FI_CYCLES_PER_OCC = interp_timing['freq_depth'] + 3
            FI_CYCLES_PER_OCC_SINGLE = FI_CYCLES_PER_OCC
    else:
        FI_CYCLES_PER_OCC = 0
        FI_CYCLES_PER_OCC_SINGLE = 0

    # ---- TI control path graph ----
    _RE_GROUPS_TI = 12 // TI_RE_PARALLELISM
    _RE_GROUP_WIDTH_TI = max(math.ceil(math.log2(_RE_GROUPS_TI)), 1) if _RE_GROUPS_TI > 1 else 1
    _N_BANKS_PRE_FI = RB_PARALLELISM * _RE_GROUPS_TI
    _BANK_SEL_W_PRE_FI = max(math.ceil(math.log2(_N_BANKS_PRE_FI)), 1) if _N_BANKS_PRE_FI > 1 else 1
    ti_ctrl_graph = build_ti_ctrl_graph(
        ti_pipeline_depth=TI_PIPELINE_DEPTH,
        SRAM_ADDR_WIDTH=SRAM_ADDR_WIDTH,
        RE_GROUP_WIDTH=_RE_GROUP_WIDTH_TI,
        has_pre_fi_buf=HAS_PRE_FI_BUF,
        N_BANKS=_N_BANKS_PRE_FI,
        BANK_SEL_W=_BANK_SEL_W_PRE_FI,
    )

    # ---- C_INIT timing ----
    cinit_timing = analyze_cinit_timing(
        min_num_RBs=min_num_RBs, RB_PARALLELISM=RB_PARALLELISM,
        is_ECP=is_ECP, N_CLK_CINIT=0,
    )

    # ---- Early LS drain ----
    _safe_head = math.ceil(min_num_RBs / RB_PARALLELISM) - 2
    if HAS_PRE_FI_BUF:
        _drain_depth = ls_timing['pre_fi_pipeline_depth']
    else:
        _drain_depth = LS_DRAIN_CYCLES
    EARLY_LS_DRAIN = max(_drain_depth - _safe_head, 1)
    _sym_duration_min = math.ceil(min_num_RBs / RB_PARALLELISM)

    # ---- Safety assertions ----
    assert _safe_head >= 0, (
        f"EARLY_LS_DRAIN unsafe: min_num_RBs={min_num_RBs} too small for RB_PAR={RB_PARALLELISM}")
    assert EARLY_LS_DRAIN <= _sym_duration_min, (
        f"LS drain timing VIOLATED: EARLY_LS_DRAIN ({EARLY_LS_DRAIN}) > sym_duration ({_sym_duration_min})")
    assert cinit_timing['bypass_feasible'], (
        f"C_INIT bypass timing VIOLATED: sym_duration_min={cinit_timing['sym_duration_min']} < "
        f"D_intrinsic={cinit_timing['D_intrinsic']}. Increase min_num_RBs or reduce pipeline depth.")

    # ---- LMMSE freq scaling flag ----
    lmmse_freq_scaling = (freq_interp_method == 'lmmse') and (time_interp_method == 'lmmse')
    HAS_COEFF_SRAM = (
        (freq_interp_method == 'lmmse' and FI_LMMSE_COEFF_SOURCE == 'SRAM') or
        (time_interp_method == 'lmmse' and TI_LMMSE_COEFF_SOURCE == 'SRAM')
    )

    # ---- Enabled CDM groups for C_INIT ----
    ENABLED_CDM_GROUPS_TYPE1 = arch_config.ENABLED_CDM_GROUPS_TYPE1
    ENABLED_CDM_GROUPS_TYPE2 = arch_config.ENABLED_CDM_GROUPS_TYPE2
    ENABLED_CDM_GROUPS_TYPE3 = arch_config.ENABLED_CDM_GROUPS_TYPE3
    enabled_cdm_groups_union: list[bool] = []
    if dmrs_Uplink is True or dmrs_Uplink == "Hybrid":
        if dmrs_Type == "Hybrid":
            enabled_cdm_groups_union = [a or b for a, b in zip(ENABLED_CDM_GROUPS_TYPE1 + [False], ENABLED_CDM_GROUPS_TYPE2)]
        elif dmrs_Type == 1:
            enabled_cdm_groups_union = ENABLED_CDM_GROUPS_TYPE1
        elif dmrs_Type == 3:
            enabled_cdm_groups_union = ENABLED_CDM_GROUPS_TYPE3
        else:
            enabled_cdm_groups_union = ENABLED_CDM_GROUPS_TYPE2
    enabled_indices = [i for i, e in enumerate(enabled_cdm_groups_union) if e] if (dmrs_Uplink is True or dmrs_Uplink == "Hybrid") else []

    return dict(
        # Protocol params
        min_num_RBs=min_num_RBs, max_num_RBs=max_num_RBs,
        num_symbols_range=num_symbols_range,
        min_pusch_symbols=min_pusch_symbols, max_pusch_symbols=max_pusch_symbols,
        counter_width=counter_width, is_ECP=is_ECP,
        dmrs_Type=dmrs_Type, is_double_dmrs=is_double_dmrs,
        is_enhanced=is_enhanced, dmrs_typeA_pos=dmrs_typeA_pos,
        dmrs_Uplink=dmrs_Uplink, additional_DMRS_range=additional_DMRS_range,
        num_front_loaded_dmrs=num_front_loaded_dmrs,
        # Y geometry
        Y_total_bits=Y_total_bits, INPUT_INDEX_LIST=INPUT_INDEX_LIST,
        required_re_per_rb=required_re_per_rb, TRUE_INDEX_LIST=TRUE_INDEX_LIST,
        # Arch config
        arch_config=arch_config, max_cdm_groups=max_cdm_groups,
        _cdm_active_groups=_cdm_active_groups,
        production_layout_metadata=production_layout_metadata,
        production_lane_representatives=production_lane_representatives,
        descriptor_fdCDM=_fdCDM_timing,
        descriptor_tdCDM=_tdCDM_timing,
        # Timing
        ls_timing=ls_timing, LS_DRAIN_CYCLES=LS_DRAIN_CYCLES,
        SRAM_DEPTH=SRAM_DEPTH, SRAM_ADDR_WIDTH=SRAM_ADDR_WIDTH,
        ls_ctrl_graph=ls_ctrl_graph,
        interp_timing=interp_timing,
        TI_PIPELINE_DEPTH=TI_PIPELINE_DEPTH,
        cinit_timing=cinit_timing,
        EARLY_LS_DRAIN=EARLY_LS_DRAIN,
        _safe_head=_safe_head, _sym_duration_min=_sym_duration_min,
        # TI geometry
        RE_GROUPS_TI=_RE_GROUPS_TI, RE_GROUP_WIDTH_TI=_RE_GROUP_WIDTH_TI,
        # Flags
        lmmse_freq_scaling=lmmse_freq_scaling, HAS_COEFF_SRAM=HAS_COEFF_SRAM,
        HAS_PRE_FI_BUF=HAS_PRE_FI_BUF, FI_WINDOW_SIZE=FI_WINDOW_SIZE,
        FI_CYCLES_PER_OCC=FI_CYCLES_PER_OCC,
        FI_CYCLES_PER_OCC_SINGLE=FI_CYCLES_PER_OCC_SINGLE,
        ti_ctrl_graph=ti_ctrl_graph,
        # C_INIT
        ENABLED_CDM_GROUPS_TYPE1=ENABLED_CDM_GROUPS_TYPE1,
        ENABLED_CDM_GROUPS_TYPE2=ENABLED_CDM_GROUPS_TYPE2,
        ENABLED_CDM_GROUPS_TYPE3=ENABLED_CDM_GROUPS_TYPE3,
        enabled_cdm_groups_union=enabled_cdm_groups_union,
        enabled_indices=enabled_indices,
    )


@convert
def ModuleTOP(protocol: ProtocolSpec, architecture: ArchitectureConfig, quants: Dict[QuantKey, QuType], arithmetic: ArithmeticConfig, implementation: ImplementationConfig) -> None:
    """
    * Should be frequently updated according to design changes.
    * A Top module for the CE design.
    * PUSCH Mapping type currently is fixed to Type A since Type B is rarely used in realistic situations.
    * Transform precoding and intra-slot frequency hopping are not considered in this design.
    
    Execute mode parameters:
    :param freq_interp_method: 'lmmse'
    Interpolation method in frequency direction. One of 'linear', 'nn' and 'lmmse'.
    
    :param time_interp_method: 'lmmse'
    Interpolation method in time direction. One of 'linear', 'nn' and 'lmmse'.


    :param switchable_ports: True
    Antenna ports can be switched on/off using port_enable signals when `switchable_ports` is set to True.

    :param INPUT_MODE: 'B'
    Controls how RB-boundary misalignment (num_RBs % RB_PARALLELISM != 0) is handled.
        - 'A': Flat-bus input. One wide Y bus enters TOP, then goes through a single
            Y_PATH_REDUCE instance and directly enters the downstream pipeline. Requires perfect alignment of RB boundary.
        - 'B': Per-RB input with per-RB valid/ready handshake. Each RB first passes
            through RB-local Y_PATH_REDUCE, then RB streams are realigned by a
            barrel-shift-based boundary aligner (zero-pad + per-lane backpressure).
    :type INPUT_MODE: Literal['A', 'B']

    Parallelism parameters:

    :param LMMSE_INTERP_PARALLELISM: 4
    [Used when freq_interp_type is set to 'lmmse'] Number of RBs to perform one LMMSE frequency interpolation.

    :param RB_PARALLELISM: 1
    Input parallelism in resource blocks. Assume input index list is list(range(12*RB_PARALLELISM))
    
    :param TI_RE_PARALLELISM: 3
    Output parallelism in resource elements. Currently must < 1 RB.

    :param ANTENNA_PORTS: [4]
    List of configured antenna ports. When `switchable_ports` is set to True, all ports within `ANTENNA_PORTS` can be switched on/off.

    Data signals:
    :param Y: QuType(11, 4, True)
    :type Y: QuType
    :param QU_H_LS: QuType(12, 4, True)
    :type QU_H_LS: QuType
    :param QU_MODE_LS: QuMode.TRN.TCPL
    :type QU_MODE_LS: QuMode.TRN | QuMode.RND
    :param OF_MODE_LS: OfMode.WRP.TCPL
    :type OF_MODE_LS: OfMode.WRP | OfMode.SAT
    :param Qu_H_interp_f: QuType(12, 4, True)
    Per-component QuType for freq-interpolated H. Complex wire width = 2 * DWT.
    :param Qu_H_interp_t: QuType(12, 4, True)
    Per-component QuType for time-interpolated H output. Complex wire width = 2 * DWT.
    
    :param Qu_symbol_idx: QuType(4, 0, False)
    Should be auto-derived from max_pusch_symbols
    :param Qu_slot_idx: QuType(4, 0, False)
    Slot index quantization type
    
    PUSCH Protocol parameters:
    :param pusch_params: {'num_RB_range': (52, 273), 'num_symbols_range': (4,14), 'is_ECP': 'Hybrid'}
    :type pusch_params: dict[str, Any]
    
    PUSCHDMRS Protocol parameters:
    :param puschdmrs_params: {'dmrs_Uplink': True, 'dmrs_Type': 'Hybrid', 'is_double_dmrs': False, 'is_enhanced': False, 'dmrs_typeA_pos': 'pos2', 'additional_DMRS_range':[0,2]} 

    Time-domain LMMSE interpolation parameters (TI_ prefix):

    :param TI_LMMSE_COEFF_SOURCE: 'ROM'
    Coefficient storage mode. 'ROM' for hardwired coefficients, 'SRAM' for runtime-loaded.
    :param Qu_TI_LMMSE_COEFF: QuType(12, 11, True)
    QuType for time-domain LMMSE coefficients.
    :param TI_LMMSE_REAL_COEFF: True
    Use real-valued Jakes model coefficients.
    :param TI_LMMSE_f_d_norm: 0.01
    Normalized Doppler frequency (f_D * T_sym). Controls Wiener filter shape.
    :param TI_LMMSE_W_coeffs: None
    Pre-computed W matrix coefficients. None triggers auto-generation from Jakes model.
    Frequency-domain LMMSE interpolation parameters (FI_ prefix):
    :param Qu_FI_LMMSE_COEFF: QuType(12, 10, True)
    QuType for frequency-domain LMMSE coefficients.
    :param FI_LMMSE_REAL_COEFF: True
    Use real-valued coefficients for frequency LMMSE.
    :param FI_LMMSE_tau_rms: 3.0
    RMS delay spread (in samples) for the optional sinc covariance model.
    :param FI_LMMSE_snr_linear: 100.0
    Linear SNR for Wiener filter regularization.
    :param FI_LMMSE_COEFF_SOURCE: 'ROM'
    Coefficient storage mode for frequency LMMSE. 'ROM' or 'SRAM'.
    :param FI_LMMSE_channel_model: 'TDL-C'
    TDL channel model for covariance (overrides tau_rms sinc model). Set None to use sinc.
    :param FI_LMMSE_delay_spread: 200e-9
    RMS delay spread in seconds (used with channel_model).
    :param FI_LMMSE_scs: 30e3
    Subcarrier spacing in Hz (used with channel_model).
    """

    # Resolve the semantic public API into private generator-local names.
    _resolved = resolve_top_config(
        protocol, architecture, quants, arithmetic, implementation,
    ).generator_kwargs
    pusch_params = _resolved['pusch_params']
    puschdmrs_params = _resolved['puschdmrs_params']
    LMMSE_INTERP_PARALLELISM = _resolved['LMMSE_INTERP_PARALLELISM']
    Y = _resolved['Y']
    RB_PARALLELISM = _resolved['RB_PARALLELISM']
    ANTENNA_PORTS = _resolved['ANTENNA_PORTS']
    Qu_H_interp_t = _resolved['Qu_H_interp_t']
    Qu_H_interp_f = _resolved['Qu_H_interp_f']
    freq_interp_method = _resolved['freq_interp_method']
    time_interp_method = _resolved['time_interp_method']
    Qu_symbol_idx = _resolved['Qu_symbol_idx']
    Qu_slot_idx = _resolved['Qu_slot_idx']
    QU_H_LS = _resolved['QU_H_LS']
    QU_MODE_LS = _resolved['QU_MODE_LS']
    OF_MODE_LS = _resolved['OF_MODE_LS']
    switchable_ports = _resolved['switchable_ports']
    INPUT_MODE = _resolved['INPUT_MODE']
    TI_RE_PARALLELISM = _resolved['TI_RE_PARALLELISM']
    TI_LMMSE_COEFF_SOURCE = _resolved['TI_LMMSE_COEFF_SOURCE']
    Qu_TI_LMMSE_COEFF = _resolved['Qu_TI_LMMSE_COEFF']
    TI_LMMSE_REAL_COEFF = _resolved['TI_LMMSE_REAL_COEFF']
    TI_LMMSE_f_d_norm = _resolved['TI_LMMSE_f_d_norm']
    TI_LMMSE_W_coeffs = _resolved['TI_LMMSE_W_coeffs']
    Qu_FI_LMMSE_COEFF = _resolved['Qu_FI_LMMSE_COEFF']
    FI_LMMSE_REAL_COEFF = _resolved['FI_LMMSE_REAL_COEFF']
    FI_LMMSE_tau_rms = _resolved['FI_LMMSE_tau_rms']
    FI_LMMSE_snr_linear = _resolved['FI_LMMSE_snr_linear']
    FI_LMMSE_COEFF_SOURCE = _resolved['FI_LMMSE_COEFF_SOURCE']
    FI_LMMSE_channel_model = _resolved['FI_LMMSE_channel_model']
    FI_LMMSE_delay_spread = _resolved['FI_LMMSE_delay_spread']
    FI_LMMSE_scs = _resolved['FI_LMMSE_scs']
    FI_RE_PARALLELISM = _resolved['FI_RE_PARALLELISM']
    SRAM_MACRO_CONFIG = _resolved['SRAM_MACRO_CONFIG']
    production_observation_layouts = _resolved['production_observation_layouts']

    # ---- Derive raw widths from QuType ----
    H_interp_f_DWT = 2 * Qu_H_interp_f.DWT
    H_interp_t_DWT = 2 * Qu_H_interp_t.DWT
    FI_LMMSE_COEFF_DWT = Qu_FI_LMMSE_COEFF.DWT
    FI_LMMSE_COEFF_FRAC = Qu_FI_LMMSE_COEFF.FRAC
    TI_LMMSE_COEFF_DWT = Qu_TI_LMMSE_COEFF.DWT

    # ---- Input validation ----
    if 12 % TI_RE_PARALLELISM != 0:
        raise ValueError(
            f"TI_RE_PARALLELISM must divide 12 (valid: 1,2,3,4,6,12), "
            f"got {TI_RE_PARALLELISM}"
        )

    # ---- Pre-compute all derived parameters, timing, and validation ----
    # =====================================================================
    # ModuleTOP Region Map (for navigation):
    #   0. Context unpacking + derived constants
    #   1. Port declarations (module TOP(...);)
    #   2. Wire declarations (grouped by subsystem)
    #   3. Combinational assigns
    #   4. Module instantiations (dataflow order)
    #   5. Latency summary + endmodule
    # =====================================================================
    ctx = _prepare_top_context(
        pusch_params=pusch_params, puschdmrs_params=puschdmrs_params,
        Y=Y, RB_PARALLELISM=RB_PARALLELISM, ANTENNA_PORTS=ANTENNA_PORTS,
        H_interp_f_DWT=H_interp_f_DWT, freq_interp_method=freq_interp_method,
        time_interp_method=time_interp_method, switchable_ports=switchable_ports,
        INPUT_MODE=INPUT_MODE, QU_H_LS=QU_H_LS,
        LMMSE_INTERP_PARALLELISM=LMMSE_INTERP_PARALLELISM,
        TI_LMMSE_COEFF_SOURCE=TI_LMMSE_COEFF_SOURCE,
        FI_LMMSE_COEFF_DWT=FI_LMMSE_COEFF_DWT,
        FI_LMMSE_REAL_COEFF=FI_LMMSE_REAL_COEFF,
        FI_LMMSE_COEFF_SOURCE=FI_LMMSE_COEFF_SOURCE,
        FI_RE_PARALLELISM=FI_RE_PARALLELISM,
        TI_RE_PARALLELISM=TI_RE_PARALLELISM,
        production_observation_layouts=production_observation_layouts,
    )

    # Unpack context into local namespace
    min_num_RBs = ctx['min_num_RBs']
    max_num_RBs = ctx['max_num_RBs']
    num_symbols_range = ctx['num_symbols_range']
    min_pusch_symbols = ctx['min_pusch_symbols']
    max_pusch_symbols = ctx['max_pusch_symbols']
    counter_width = ctx['counter_width']
    is_ECP = ctx['is_ECP']
    dmrs_Type = ctx['dmrs_Type']
    is_double_dmrs = ctx['is_double_dmrs']
    is_enhanced = ctx['is_enhanced']
    dmrs_typeA_pos = ctx['dmrs_typeA_pos']
    dmrs_Uplink = ctx['dmrs_Uplink']
    additional_DMRS_range = ctx['additional_DMRS_range']
    Y_total_bits = ctx['Y_total_bits']
    INPUT_INDEX_LIST = ctx['INPUT_INDEX_LIST']
    required_re_per_rb = ctx['required_re_per_rb']
    TRUE_INDEX_LIST = ctx['TRUE_INDEX_LIST']
    arch_config = ctx['arch_config']
    max_cdm_groups = ctx['max_cdm_groups']
    _cdm_active_groups = ctx['_cdm_active_groups']
    ls_timing = ctx['ls_timing']
    LS_DRAIN_CYCLES = ctx['LS_DRAIN_CYCLES']
    SRAM_DEPTH = ctx['SRAM_DEPTH']
    SRAM_ADDR_WIDTH = ctx['SRAM_ADDR_WIDTH']
    ls_ctrl_graph = ctx['ls_ctrl_graph']
    interp_timing = ctx['interp_timing']
    TI_PIPELINE_DEPTH = ctx['TI_PIPELINE_DEPTH']
    cinit_timing = ctx['cinit_timing']
    EARLY_LS_DRAIN = ctx['EARLY_LS_DRAIN']
    _safe_head = ctx['_safe_head']
    _sym_duration_min = ctx['_sym_duration_min']
    HAS_COEFF_SRAM = ctx['HAS_COEFF_SRAM']
    HAS_PRE_FI_BUF = ctx['HAS_PRE_FI_BUF']
    FI_WINDOW_SIZE = ctx['FI_WINDOW_SIZE']
    FI_CYCLES_PER_OCC = ctx['FI_CYCLES_PER_OCC']
    FI_CYCLES_PER_OCC_SINGLE = ctx['FI_CYCLES_PER_OCC_SINGLE']
    ti_ctrl_graph = ctx['ti_ctrl_graph']
    RE_GROUPS_TI = ctx['RE_GROUPS_TI']
    RE_GROUP_WIDTH_TI = ctx['RE_GROUP_WIDTH_TI']
    ENABLED_CDM_GROUPS_TYPE1 = ctx['ENABLED_CDM_GROUPS_TYPE1']
    ENABLED_CDM_GROUPS_TYPE2 = ctx['ENABLED_CDM_GROUPS_TYPE2']
    ENABLED_CDM_GROUPS_TYPE3 = ctx['ENABLED_CDM_GROUPS_TYPE3']
    enabled_cdm_groups_union = ctx['enabled_cdm_groups_union']
    enabled_indices = ctx['enabled_indices']
    production_layout_metadata = ctx['production_layout_metadata']
    production_lane_representatives = ctx['production_lane_representatives']
    descriptor_fdCDM = ctx['descriptor_fdCDM']
    descriptor_tdCDM = ctx['descriptor_tdCDM']

    # ---- Derived constants for wire widths ----
    N_CLK_CINIT = 0
    N_CLK_Y_PRE = ls_timing['N_CLK_Y_PRE']
    N_CLK_DMRS_SEQ = ls_timing['N_CLK_DMRS_SEQ']
    N_CLK_LS_ROT = ls_timing['N_CLK_LS_ROT']
    _replay_pipe_delay = ls_timing['pre_fi_pipeline_depth']
    _pb_addr_w = max((LMMSE_INTERP_PARALLELISM - 1).bit_length(), 1)
    _lmmse_p_w = max(LMMSE_INTERP_PARALLELISM.bit_length(), 1)
    _lmmse_delay = LMMSE_INTERP_PARALLELISM + _replay_pipe_delay

    max_occasions = 1 + max(additional_DMRS_range)
    _symbols_per_occasion = 2 if is_double_dmrs else 1
    _ybuf_total_planes = max_occasions * _symbols_per_occasion
    _ybuf_plane_sel_w = max(math.ceil(math.log2(_ybuf_total_planes)), 1) if _ybuf_total_planes > 1 else 1
    _max_windows_rm = math.ceil(max_num_RBs / LMMSE_INTERP_PARALLELISM) if LMMSE_INTERP_PARALLELISM > 0 else 1
    _win_cnt_w = max(math.ceil(math.log2(_max_windows_rm)), 1) if _max_windows_rm > 1 else 1
    _occ_cnt_w = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
    _beats_per_window_precomp = max(FI_WINDOW_SIZE // RB_PARALLELISM, 1) if HAS_PRE_FI_BUF else 1
    _local_rb_width_precomp = max(math.ceil(math.log2(_beats_per_window_precomp)), 1) if _beats_per_window_precomp > 1 else 1
    _replay_token_dwt = _ybuf_plane_sel_w + _local_rb_width_precomp
    OCC_SEL_WIDTH = (
        max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
    )
    Y_PARALLELISM = len(TRUE_INDEX_LIST)
    RE_PER_RB = len(required_re_per_rb)
    RB_BITS = RE_PER_RB * 2 * Y.DWT
    Qu_Y_Complex = QuType(DWT=2 * Y.DWT, FRAC=Y.FRAC, IF_SIGNED=Y.IF_SIGNED)
    COMPLEX_DWT_LS = 2 * QU_H_LS.DWT
    SRAM_DATA_WIDTH = RB_PARALLELISM * 12 * H_interp_f_DWT
    N_PORTS = len(ANTENNA_PORTS)
    _cdm_sel_bits = (
        math.ceil(math.log2(max_cdm_groups)) if max_cdm_groups >= 2 else 0
    )
    _n_add_max_latch = (
        max(additional_DMRS_range) if len(additional_DMRS_range) > 1 else 0
    )
    _n_add_width_latch = (
        (math.ceil(math.log2(_n_add_max_latch + 1)) if _n_add_max_latch > 0
         else 1) if len(additional_DMRS_range) > 1 else 0
    )
    _num_ports_latch = len(ANTENNA_PORTS) if switchable_ports else 0
    _has_any_type1 = any(p.has_type1 for p in arch_config.pcdmu_instances)

    # =================================================================
    # REGION 1: Module port list
    # =================================================================
    #/ `timescale 1ns / 1ps
    #/ module TOP (
    #/     input clk,
    #/     input rst_n,
    #/     input start,
    #/
    #/     // Configuration signals
    #/     input [15:0]                  N_ID,
    #/     input                         n_scid,
    #/     input [`Qu_slot_idx.DWT`-1:0] current_slot_idx,
    #/     input [3:0]                   pusch_symbol_length,
    #/
    #/     // Protocol change stimulation
    #/     input protocol_switch,
    if INPUT_MODE == 'A':
        #/ input [`RB_PARALLELISM*Y_total_bits`-1:0] Y,
        pass
    else:
        for rb in range(RB_PARALLELISM):
            y_name = f"Y_rb{rb}"
            y_valid = f"Y_valid_rb{rb}"
            y_ready = f"Y_ready_rb{rb}"
            #/ input [`Y_total_bits`-1:0] `y_name`,
            #/ input  `y_valid`,
            #/ output `y_ready`,
            pass

    #/ // PUSCHDMRS protocol configuration signals
    if dmrs_Type == "Hybrid":
        #/ input dmrs_type,
        pass
    if is_double_dmrs == "Hybrid":
        #/ input is_double_dmrs,
        pass
    if is_enhanced == "Hybrid":
        #/ input is_enhanced,
        pass
    if dmrs_typeA_pos == "Hybrid":
        #/ input dmrs_typeA_pos_sel,
        pass
    if max_cdm_groups >= 2:
        sel_bits = math.ceil(math.log2(max_cdm_groups))
        #/ input [`sel_bits`-1:0] num_cdm_groups_without_data,
        pass
    if is_ECP == "Hybrid":
        #/ input is_ECP,
        pass
    if len(additional_DMRS_range) > 1:
        n_add_max = max(additional_DMRS_range)
        n_add_width = (
            math.ceil(math.log2(n_add_max + 1)) if n_add_max > 0 else 1
        )
        #/ input [`n_add_width`-1:0] n_additional_dmrs,
        pass
    if switchable_ports:
        for port in ANTENNA_PORTS:
            #/ input `f"port_enable_p{port}"`,
            pass
    if time_interp_method == 'lmmse' and TI_LMMSE_COEFF_SOURCE == 'SRAM':
        _ti_coeff_n_occ = 1 + max(additional_DMRS_range)
        _ti_coeff_total = max_pusch_symbols * _ti_coeff_n_occ
        _ti_coeff_addr_w = (
            max(math.ceil(math.log2(_ti_coeff_total)), 1)
            if _ti_coeff_total > 1 else 1
        )
        #/ // TI LMMSE coefficient write ports
        #/ input                            ti_coeff_wr_en,
        #/ input [`_ti_coeff_addr_w`-1:0]   ti_coeff_wr_addr,
        #/ input [`TI_LMMSE_COEFF_DWT`-1:0] ti_coeff_wr_data,
        pass

    if freq_interp_method == 'lmmse' and FI_LMMSE_COEFF_SOURCE == 'SRAM':
        _fi_coeff_n_pilots_per_rb = max(
            len(
                production_lane_representatives.get(
                    p, arch_config.get_port_interp_info(p).pilot_re_compact
                    or arch_config.get_port_interp_info(p).pilot_re_list
                )
            )
            for p in ANTENNA_PORTS
        )
        _fi_coeff_total_entries = (
            (FI_RE_PARALLELISM * LMMSE_INTERP_PARALLELISM) *
            (_fi_coeff_n_pilots_per_rb * LMMSE_INTERP_PARALLELISM)
        )
        _fi_coeff_addr_w = max(math.ceil(math.log2(_fi_coeff_total_entries)), 1)
        #/ // Shared FI COEFF_SRAM coefficient write ports
        #/ input                              fi_coeff_wr_en,
        #/ input [`_fi_coeff_addr_w`-1:0]      fi_coeff_wr_addr,
        #/ input [`Qu_FI_LMMSE_COEFF.DWT`-1:0] fi_coeff_wr_data,
        pass

    if HAS_COEFF_SRAM:
        #/ // Coefficient-loading handshake (shared by FI and TI)
        #/ input  coeff_load_done,
        #/ input  coeff_reload_req,
        pass

    #/ input [`counter_width`-1:0] num_RBs,
    #/
    #/ // Time interpolation outputs
    #/ output ti_data_valid,
    #/ output slot_ce_done,
    all_ti_out_ports = []
    for ant_port in ANTENNA_PORTS:
        for re_lane in range(TI_RE_PARALLELISM):
            for sym in range(max_pusch_symbols):
                all_ti_out_ports.append(
                    f"h_ti_port{ant_port}_re{re_lane}_sym{sym}"
                )
    for idx, port_name in enumerate(all_ti_out_ports):
        comma = "," if idx < len(all_ti_out_ports) - 1 else ""
        #/ output [`H_interp_t_DWT`-1:0] `port_name + comma`
        pass
    #/ );

    # =================================================================
    # REGION 2: Wire declarations (all wires before any instantiation)
    # =================================================================

    # Precompute shared FI coefficient-SRAM geometry before emitting any RTL.
    # The resulting declarations must remain in Region 2 even though the SRAM
    # instances are emitted later in Region 4.
    _share_cdm_srams: dict = {}
    _all_coeff_groups: dict[tuple, list[int]] = {}
    _port_coeff_key: dict[int, tuple] = {}
    _shared_coeff_specs: list[dict[str, Any]] = []
    if freq_interp_method == 'lmmse' and FI_LMMSE_COEFF_SOURCE == 'SRAM':
        for _p in ANTENNA_PORTS:
            _re_key = tuple(
                production_lane_representatives.get(
                    _p, arch_config.get_port_interp_info(_p).pilot_re_list
                )
            )
            _all_coeff_groups.setdefault(_re_key, []).append(_p)
            _port_coeff_key[_p] = _re_key
        for _gidx, (_re_key, _plist) in enumerate(sorted(_all_coeff_groups.items())):
            _sN_PILOTS_PER_RB = len(_re_key)
            _sOUTPUT_GROUPS = 12 // FI_RE_PARALLELISM
            _sFILL_BEATS_ORIG = max(LMMSE_INTERP_PARALLELISM // max(RB_PARALLELISM, 1), 1)
            _sFILL_BEATS = _sFILL_BEATS_ORIG * _sOUTPUT_GROUPS
            _sN_OUTPUT = FI_RE_PARALLELISM * LMMSE_INTERP_PARALLELISM
            _sN_PILOTS = _sN_PILOTS_PER_RB * LMMSE_INTERP_PARALLELISM
            _sN_PILOTS_PER_BEAT = _sN_PILOTS_PER_RB * RB_PARALLELISM
            _sBEAT_IDX_W = max(math.ceil(math.log2(_sFILL_BEATS)), 1)
            _sCOEFF_PER_BEAT = _sN_OUTPUT * _sN_PILOTS_PER_BEAT
            if FI_LMMSE_REAL_COEFF:
                _sCOEFF_BEAT_DWT = _sCOEFF_PER_BEAT * Qu_FI_LMMSE_COEFF.DWT
            else:
                _sCOEFF_BEAT_DWT = _sCOEFF_PER_BEAT * 2 * Qu_FI_LMMSE_COEFF.DWT
            _rd_data_w = f"shared_coeff_rd_data_g{_gidx}"
            _rd_idx_w = f"shared_coeff_rd_idx_g{_gidx}"
            _shared_coeff_specs.append({
                're_key': _re_key, 'ports': _plist,
                'n_output': _sN_OUTPUT, 'n_pilots': _sN_PILOTS,
                'n_pilots_per_beat': _sN_PILOTS_PER_BEAT,
                'fill_beats': _sFILL_BEATS, 'beat_idx_w': _sBEAT_IDX_W,
                'coeff_beat_dwt': _sCOEFF_BEAT_DWT,
                'rd_data_w': _rd_data_w, 'rd_idx_w': _rd_idx_w,
            })
            _share_cdm_srams[_re_key] = (_rd_data_w, _rd_idx_w, _sBEAT_IDX_W)

    # -- 2.1 FSM & core control --
    #/ // ========== FSM & Core Control Wires ==========
    #/ wire cfg_latch_en;
    #/ wire ctrl_ctr_en;
    #/ wire ctrl_ls_en;
    #/ wire ctrl_ti_en;
    #/ wire ctrl_ti_done;
    if HAS_COEFF_SRAM:
        #/ wire coeff_loading;
        pass
    if HAS_PRE_FI_BUF:
        #/ //   Pre-FI LS_BUF: per-occasion mixed mode -- last occasion dual_port
        pass
    #/ //   Early TI start: LS_DRAIN reduced from `LS_DRAIN_CYCLES` to `EARLY_LS_DRAIN` clk
    #/ //     -- min_num_RBs = `min_num_RBs`, RB_PAR=`RB_PARALLELISM` -> `_safe_head` safe head clks

    # -- 2.2 Counter outputs (from CONTROLLER) --
    #/ // ========== Counter Wires ==========
    #/ wire [`counter_width`-1:0] ctrl_rb_idx;
    #/ wire [`counter_width`-1:0] ctrl_rb_idx_r;
    #/ wire [`Qu_symbol_idx.DWT`-1:0] ctrl_sym_idx;
    #/ wire [`Qu_symbol_idx.DWT`-1:0] ctrl_sym_idx_next;
    if INPUT_MODE == 'B' and RB_PARALLELISM > 1:
        bit_remainder = math.ceil(math.log2(RB_PARALLELISM))
        #/ wire [`bit_remainder`-1:0] ctrl_rb_remainder;
        #/ wire                       ctrl_sym_overflow;
        pass

    # -- 2.3 Pilot detection outputs (from CONTROLLER) --
    #/ // ========== Pilot Detection Wires ==========
    #/ wire ctrl_is_pilot;
    #/ wire ctrl_l_prime;
    #/ wire ctrl_is_last_dmrs;
    #/ wire ctrl_c_init_strb;

    # -- 2.4 Delay-aligned LS control (from CONTROLLER) --
    #/ // ========== Delay-Aligned LS Control Wires ==========
    #/ wire                           ctrl_pilot_wr_en_raw;
    #/ wire [`SRAM_ADDR_WIDTH`-1:0]   ctrl_pilot_wr_addr;
    # RB-boundary flags exist only for the FI cores that consume them (NN,
    # Linear). LMMSE resolves slot edges through its coefficient set, so under
    # LMMSE CONTROLLER does not declare these outputs at all. Must match the
    # predicate in v_controller.py / v_ti_ctrl.py.
    _needs_rb_boundary = freq_interp_method in ('nn', 'linear')
    if _needs_rb_boundary and not HAS_PRE_FI_BUF:
        #/ wire                           ctrl_first_rb_d;
        #/ wire                           ctrl_last_rb_d;
        if RB_PARALLELISM > 1:
            #/ wire [`RB_PARALLELISM`-1:0] ctrl_lane_last_d;
            pass
        pass
    if max_occasions > 1:
        #/ wire [`OCC_SEL_WIDTH`-1:0] ctrl_occ_idx;
        pass
    if HAS_PRE_FI_BUF and max_occasions > 1:
        #/ wire [`OCC_SEL_WIDTH`-1:0] ctrl_ybuf_occ_tag;
        pass
    if freq_interp_method == 'lmmse' and not HAS_PRE_FI_BUF:
        #/ wire ctrl_freq_interp_en;
        pass

    # -- 2.4b Pre-FI buffer control wires --
    if HAS_PRE_FI_BUF:
        #/ // ========== Pre-FI Buffer Control Wires ==========
        #/ wire fi_trigger;
        if max_occasions > 1:
            _fi_occ_sel_w = max(math.ceil(math.log2(max_occasions)), 1)
            #/ wire [`_fi_occ_sel_w`-1:0] fi_occ_sel;
            pass
        #/ wire [`SRAM_ADDR_WIDTH`-1:0] fi_window_base;
        if _needs_rb_boundary:
            #/ wire fi_first_rb;
            #/ wire fi_last_rb;
            if RB_PARALLELISM > 1:
                #/ wire [`RB_PARALLELISM`-1:0] fi_lane_last;
                pass
            pass
        pass

    # -- 2.5 TI control outputs (from CONTROLLER) --
    #/ // ========== TI Control Wires ==========
    #/ wire                           ctrl_ti_sram_rd_en;
    #/ wire [`SRAM_ADDR_WIDTH`-1:0]   ctrl_ti_rb_addr;
    #/ wire [`RE_GROUP_WIDTH_TI`-1:0] ctrl_ti_re_group;
    if RB_PARALLELISM > 1:
        _rb_within_width = max(math.ceil(math.log2(RB_PARALLELISM)), 1)
        #/ wire [`_rb_within_width`-1:0] ti_rb_within_beat;
        pass

    # -- 2.6 CFG_LATCH outputs --
    #/ // ========== Config Latch Output Wires ==========
    #/ wire [15:0]                  cfg_N_ID;
    #/ wire [`Qu_slot_idx.DWT`-1:0] cfg_current_slot_idx;
    #/ wire [3:0]                   cfg_pusch_symbol_length;
    #/ wire [`counter_width`-1:0]   cfg_num_RBs;
    #/ wire                         cfg_n_scid;
    if len(additional_DMRS_range) > 1:
        #/ wire [`_n_add_width_latch`-1:0] cfg_n_additional_dmrs;
        pass
    if is_double_dmrs == "Hybrid":
        #/ wire cfg_is_double_dmrs;
        pass
    if is_enhanced == "Hybrid":
        #/ wire cfg_is_enhanced;
        pass
    if dmrs_Type == "Hybrid":
        #/ wire cfg_dmrs_type;
        pass
    if dmrs_typeA_pos == "Hybrid":
        #/ wire cfg_dmrs_typeA_pos_sel;
        pass
    if is_ECP == "Hybrid":
        #/ wire cfg_is_ECP;
        pass
    if max_cdm_groups >= 2:
        import math as _math
        _cdm_sel_bits_w = _math.ceil(_math.log2(max_cdm_groups))
        #/ wire [`_cdm_sel_bits_w`-1:0] cfg_num_cdm_groups_without_data;
        pass
    if switchable_ports:
        for _port in ANTENNA_PORTS:
            #/ wire `f"cfg_port_enable_p{_port}"`;
            pass

    # -- 2.7 Port enable & CDM control --
    if switchable_ports:
        #/ // ========== Port Enable & CDM Control Wires ==========
        #/ wire [`N_PORTS`-1:0] ports_enable_combined;
        pass
    if switchable_ports or dmrs_Type == 'Hybrid':
        for g in _cdm_active_groups:
            #/ wire [1:0] `f"fdCDM_cdm{g}"`;
            #/ wire       `f"tdCDM_cdm{g}"`;
            pass

    # -- 2.8 C_INIT output wires --
    #/ // ========== C_INIT Generation Wires ==========
    if dmrs_Uplink is True or dmrs_Uplink == "Hybrid":
        for cdm_idx in range(len(enabled_cdm_groups_union)):
            if enabled_cdm_groups_union[cdm_idx]:
                #/ wire [30:0] `f"cinit_gen_cdm{cdm_idx}"`;
                pass
    else:
        #/ wire [30:0] cinit_gen;
        pass
    # cinit_symbol_idx is structural and its width derives from the explicit
    # symbol-index format.  Only its assignment belongs in Region 3.
    #/ wire [`Qu_symbol_idx.DWT`-1:0] cinit_symbol_idx;

    # -- 2.9 Y data path wires --
    #/ // ========== Y Data Path Wires ==========
    if INPUT_MODE == 'A':
        #/ // Mode A: flat bus + global PATH_REDUCE
        for i in INPUT_INDEX_LIST:
            #/ wire [`2*Y.DWT`-1:0] `f"Y_in_complex_{i}"`;
            pass
        for i in range(Y_PARALLELISM):
            #/ wire [`2*Y.DWT`-1:0] `f"Y_reduced_complex_{i}"`;
            pass
    elif INPUT_MODE == 'B':
        #/ // Mode B: per-RB handshake + barrel align
        for rb in range(RB_PARALLELISM):
            #/ wire `f"Y_align_ready_rb{rb}"`;
            #/ wire `f"Y_align_valid_rb{rb}"`;
            for k in range(12):
                #/ wire [`2*Y.DWT`-1:0] `f"Y_in_rb{rb}_complex_{k}"`;
                pass
            for r in range(RE_PER_RB):
                #/ wire [`2*Y.DWT`-1:0] `f"Y_reduced_rb{rb}_complex_{r}"`;
                pass
            #/ wire [`RB_BITS`-1:0] `f"Y_rb_in_{rb}"`;
            #/ wire [`RB_BITS`-1:0] `f"Y_rb_out_{rb}"`;
            pass
    # Y_buffered: common downstream wires (mode-independent count)
    for i in range(Y_PARALLELISM):
        #/ wire [`2*Y.DWT`-1:0] `f"Y_buffered_complex_{i}"`;
        pass

    # -- 2.10 LS output wires --
    #/ // ========== LS Channel Estimation Output Wires ==========
    all_avg_output_wires: list[tuple[int, int, int]] = []
    for ant_port in ANTENNA_PORTS:
        info = arch_config.get_port_interp_info(ant_port)
        for rb in range(RB_PARALLELISM):
            for re_k in info.pilot_re_list:
                wire_name = f"H_avg_port{ant_port}_rb{rb}_re{re_k}_complex"
                #/ wire [`COMPLEX_DWT_LS`-1:0] `wire_name`;
                all_avg_output_wires.append((ant_port, rb, re_k))
    if (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'):
        # Replay descriptor returned by LS after the same pre-FI latency as
        # the associated H_LS data: {plane, local_rb} plus an explicit valid.
        #/ wire wctrl_replay_token_valid_in;
        #/ wire [`_replay_token_dwt`-1:0] wctrl_replay_token_in;
        #/ wire wctrl_replay_token_valid_out;
        #/ wire [`_replay_token_dwt`-1:0] wctrl_replay_token_out;
        pass
    if (is_enhanced == "Hybrid" or is_enhanced is True) and _has_any_type1:
        #/ wire current_RB_idx_lsb;
        pass

    # Hybrid compact LS-buffer mux declarations.  Their conditional values
    # are emitted as continuous assignments in Region 3.
    if HAS_PRE_FI_BUF:
        for ant_port in ANTENNA_PORTS:
            _info = arch_config.get_port_interp_info(ant_port)
            if _info.is_dual_type:
                _compact_re = sorted(_info.pilot_re_compact)
                _cplx_dw = COMPLEX_DWT_LS
                for rb in range(RB_PARALLELISM):
                    for compact_re_val in _compact_re:
                        _cw = f"ls_compact_p{ant_port}_rb{rb}_re{compact_re_val}"
                        #/ wire [`_cplx_dw`-1:0] `_cw`;
                        pass

    # -- 2.11 Frequency interpolation output wires --
    #/ // ========== Frequency Interpolation Output Wires ==========
    for ant_port in ANTENNA_PORTS:
        for rb in range(RB_PARALLELISM):
            for re_k in range(12):
                #/ wire [`H_interp_f_DWT`-1:0] `f"H_interp_f_port{ant_port}_rb{rb}_re{re_k}_complex"`;
                pass
        if freq_interp_method == 'lmmse' or HAS_PRE_FI_BUF:
            #/ wire `f"drain_valid_port{ant_port}"`;
            pass

    if not HAS_PRE_FI_BUF:
        # -- 2.12 Pilot SRAM wires (post-FI only) --
        #/ // ========== Pilot SRAM Wires ==========
        for ant_port in ANTENNA_PORTS:
            #/ wire [`SRAM_DATA_WIDTH`-1:0] `f"pilot_wr_data_port{ant_port}"`;
            pass
        #/ wire ctrl_pilot_wr_en;
    else:
        # -- 2.12b LS_BUF + FI→TI wires (pre-FI mode) --
        #/ // ========== Pre-FI LS_BUF and FI→TI Wires ==========
        _fill_beats_orig = max(FI_WINDOW_SIZE // max(RB_PARALLELISM, 1), 1)
        _ls_buf_beat_w = max(math.ceil(math.log2(_fill_beats_orig)), 1)
        for ant_port in ANTENNA_PORTS:
            _info = arch_config.get_port_interp_info(ant_port)
            _descriptor_re = production_lane_representatives.get(ant_port)
            _n_pilots = (
                len(_descriptor_re)
                if _descriptor_re is not None
                else _info.num_pilots_compact
            )
            _ls_buf_dw = _n_pilots * RB_PARALLELISM * COMPLEX_DWT_LS
            #/ wire [`_ls_buf_dw`-1:0] `f"ls_buf_wr_data_port{ant_port}"`;
            #/ wire [`_ls_buf_dw`-1:0] `f"ls_buf_rd_data_port{ant_port}"`;
            #/ wire `f"ls_buf_rd_en_port{ant_port}"`;
            #/ wire [`_ls_buf_beat_w`-1:0] `f"ls_buf_rd_beat_port{ant_port}"`;
            #/ wire `f"fi_out_valid_port{ant_port}"`;
            #/ wire [`SRAM_DATA_WIDTH`-1:0] `f"fi_out_data_port{ant_port}"`;
            if freq_interp_method != 'lmmse':
                #/ wire [`SRAM_ADDR_WIDTH`-1:0] `f"ls_buf_rd_addr_port{ant_port}"`;
                pass
            pass

        # Local TI address slice is required for every pre-FI configuration.
        #/ wire [`_local_rb_width_precomp`-1:0] ti_rb_addr_local;

    # -- 2.13 Shared FI coefficient SRAM wires --
    if _shared_coeff_specs:
        #/ // ========== Shared FI Coefficient SRAM Wires ==========
        #/ wire shared_coeff_sram_rst_n;
        for _spec in _shared_coeff_specs:
            _rd_idx_w = _spec['rd_idx_w']
            _rd_data_w = _spec['rd_data_w']
            _sBEAT_IDX_W = _spec['beat_idx_w']
            _sCOEFF_BEAT_DWT = _spec['coeff_beat_dwt']
            #/ wire [`_sBEAT_IDX_W`-1:0] `_rd_idx_w`;
            #/ wire [`_sCOEFF_BEAT_DWT`-1:0] `_rd_data_w`;
        for _re_key, _plist in sorted(_all_coeff_groups.items()):
            _rd_data_w, _rd_idx_w, _sbeat_w = _share_cdm_srams[_re_key]
            for _p in _plist[1:]:
                _idx_nc = f"{_rd_idx_w}_port{_p}_nc"
                #/ wire [`_sbeat_w`-1:0] `_idx_nc`;

    # -- 2.14 Rate-matched pre-FI replay wires and storage --
    if HAS_PRE_FI_BUF and freq_interp_method == 'lmmse':
        _pilot_bank_depth = LMMSE_INTERP_PARALLELISM // RB_PARALLELISM
        _pilot_bank_addr_w = max(math.ceil(math.log2(_pilot_bank_depth)), 1)
        _ybuf_data_w = Y_PARALLELISM * 2 * Y.DWT
        _ybuf_re_w = 2 * Y.DWT
        #/ // ========== Rate-Matched LS-FI Replay Wires ==========
        #/ wire ls_en_muxed;
        #/ wire c_init_strb_muxed;
        #/ wire [`SRAM_ADDR_WIDTH`-1:0] ybuf_wr_addr;
        #/ wire [`_ybuf_data_w`-1:0] ybuf_wr_data;
        #/ wire [`_ybuf_data_w`-1:0] ybuf_rd_data;
        if _ybuf_total_planes > 1:
            #/ wire [`_ybuf_plane_sel_w`-1:0] ybuf_wr_plane_sel;
            pass
        #/ wire wctrl_ybuf_rd_en;
        if _ybuf_total_planes > 1:
            #/ wire [`_ybuf_plane_sel_w`-1:0] wctrl_ybuf_rd_plane_sel;
            pass
        #/ wire [`SRAM_ADDR_WIDTH`-1:0] wctrl_ybuf_rd_addr;
        #/ wire wctrl_ls_enable;
        if _symbols_per_occasion > 1:
            #/ wire wctrl_replay_data_valid;
            pass
        #/ wire wctrl_ls_sym_switch;
        #/ wire wctrl_lfsr_ctx_save;
        #/ wire wctrl_lfsr_ctx_restore;
        if _symbols_per_occasion > 1:
            #/ wire wctrl_lfsr_ctx_sel;
            pass
        #/ wire wctrl_avg_sym_switch;
        #/ wire wctrl_pilot_bank_wr_done;
        #/ wire wctrl_pilot_bank_sel;
        #/ wire wctrl_c_init_strb;
        #/ wire wctrl_fi_enable;
        #/ wire wctrl_pilot_wr_en;
        #/ wire [`_pilot_bank_addr_w`-1:0] wctrl_pilot_wr_addr;
        if _ybuf_total_planes > 1:
            #/ wire [`_ybuf_plane_sel_w`-1:0] wctrl_pilot_wr_plane;
            pass
        #/ wire wctrl_done;
        #/ wire wctrl_done_dup;
        if max_occasions > 1:
            #/ wire [`_occ_cnt_w`-1:0] wctrl_cur_occasion;
            pass
        #/ wire [`_win_cnt_w`-1:0] wctrl_cur_window;
        if dmrs_Uplink is True or dmrs_Uplink == "Hybrid":
            for cdm_idx in enabled_indices:
                if _ybuf_total_planes > 1:
                    #/ reg [30:0] `f"cinit_stored_cdm{cdm_idx}_plane"` [0:`_ybuf_total_planes - 1`];
                    #/ wire [30:0] `f"cinit_stored_cdm{cdm_idx}"`;
                    pass
                else:
                    #/ reg [30:0] `f"cinit_stored_cdm{cdm_idx}"`;
                    pass

    # =================================================================
    # REGION 3: Combinational assigns
    # =================================================================
    #/
    #/ // ========== Combinational Logic ==========

    # cinit_symbol_idx: look-ahead for C_INIT (current + 1)
    #/ assign cinit_symbol_idx = ctrl_sym_idx + `Qu_symbol_idx.DWT`'d1;

    # Y input unpacking
    if INPUT_MODE == 'A':
        #/ // Mode A: slice flat Y bus into per-RE complex wires
        for i in INPUT_INDEX_LIST:
            #/ assign `f"Y_in_complex_{i}"` = Y[`(i+1)*2*Y.DWT`-1:`i*2*Y.DWT`];
            pass
        for i in range(Y_PARALLELISM):
            if not (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'):
                #/ assign `f"Y_buffered_complex_{i}"` = `f"Y_reduced_complex_{i}"`;
                pass
    elif INPUT_MODE == 'B':
        #/ // Mode B: per-RB slice, reduce, pack, align, then unpack
        for rb in range(RB_PARALLELISM):
            for k in range(12):
                #/ assign `f"Y_in_rb{rb}_complex_{k}"` = `f"Y_rb{rb}"`[`(k+1)*2*Y.DWT`-1:`k*2*Y.DWT`];
                pass
            # Concatenate reduced REs into packed RB wire
            #/ assign `f"Y_rb_in_{rb}"` = {
            for r in range(RE_PER_RB - 1, -1, -1):
                if r > 0:
                    #/ `f"Y_reduced_rb{rb}_complex_{r}"`,
                    pass
                else:
                    #/ `f"Y_reduced_rb{rb}_complex_{r}"`
                    pass
            #/ };
            pass
        # Unpack aligned per-RB outputs to per-RE downstream wires
        for rb in range(RB_PARALLELISM):
            re_start = rb * RE_PER_RB
            for r in range(RE_PER_RB):
                idx = re_start + r
                if not (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'):
                    #/ assign `f"Y_buffered_complex_{idx}"` = `f"Y_rb_out_{rb}"`[`(r+1)*2*Y.DWT`-1:`r*2*Y.DWT`];
                    pass

    # current_RB_idx_lsb for enhanced Type 1 DMRS
    if (is_enhanced == "Hybrid" or is_enhanced is True) and _has_any_type1:
        if HAS_PRE_FI_BUF and freq_interp_method == 'lmmse':
            # During rate-matched replay the main controller no longer owns the
            # Y sample entering LS.  Derive the base logical-RB parity from the
            # replay beat address so enhanced Type-1 w_f stays aligned with Y.
            if RB_PARALLELISM % 2:
                #/ assign current_RB_idx_lsb = wctrl_ybuf_rd_addr[0];
                pass
            else:
                # Every beat begins on an even logical RB when RBP is even.
                #/ assign current_RB_idx_lsb = 1'b0;
                pass
        else:
            #/ assign current_RB_idx_lsb = ctrl_rb_idx[0];
            pass
        pass

    if not HAS_PRE_FI_BUF:
        # Pilot SRAM write data concatenation (per antenna port)
        #/ // Pilot SRAM write data: {RB_{P-1}_RE11, ..., RB0_RE0}
        for ant_port in ANTENNA_PORTS:
            concat_parts = []
            for rb in range(RB_PARALLELISM - 1, -1, -1):
                for re_k in range(11, -1, -1):
                    concat_parts.append(
                        f"H_interp_f_port{ant_port}_rb{rb}_re{re_k}_complex"
                    )
            concat_expr = "{" + ", ".join(concat_parts) + "}"
            #/ assign `f"pilot_wr_data_port{ant_port}"` = `concat_expr`;
            pass

        # Pilot SRAM write enable gating
        if freq_interp_method == 'lmmse':
            first_port = ANTENNA_PORTS[0]
            #/ assign ctrl_pilot_wr_en = ctrl_pilot_wr_en_raw & `f"drain_valid_port{first_port}"`;
            pass
        else:
            #/ assign ctrl_pilot_wr_en = ctrl_pilot_wr_en_raw;
            pass
    else:
        # LS_BUF write data concatenation (per antenna port, pilot REs only)
        #/ // LS_BUF write data: {RB_{P-1}_pilot_last, ..., RB0_pilot0}
        for ant_port in ANTENNA_PORTS:
            _info = arch_config.get_port_interp_info(ant_port)
            _descriptor_re = production_lane_representatives.get(ant_port)
            if _descriptor_re is not None:
                concat_parts = []
                for rb in range(RB_PARALLELISM - 1, -1, -1):
                    for re_k in reversed(_descriptor_re):
                        concat_parts.append(
                            f"H_avg_port{ant_port}_rb{rb}_re{re_k}_complex"
                        )
                concat_expr = "{" + ", ".join(concat_parts) + "}"
                #/ assign `f"ls_buf_wr_data_port{ant_port}"` = `concat_expr`;
                pass
            elif _info.is_dual_type:
                # Hybrid dual-type: compact 8→6 at write time using cfg_dmrs_type MUX
                _compact_re = sorted(_info.pilot_re_compact)
                _t1_sorted = sorted(_info.re_list_type1)
                _t2_sorted = sorted(_info.re_list_type2)
                _cplx_dw = COMPLEX_DWT_LS
                #/ // Hybrid compact MUX for LS_BUF write (port `ant_port`)
                for rb in range(RB_PARALLELISM):
                    for slot_idx, compact_re_val in enumerate(_compact_re):
                        _cw = f"ls_compact_p{ant_port}_rb{rb}_re{compact_re_val}"
                        t1_re = _t1_sorted[slot_idx]
                        t1_src = f"H_avg_port{ant_port}_rb{rb}_re{t1_re}_complex"
                        if slot_idx in _info.compact_zero_slots:
                            #/ assign `_cw` = cfg_dmrs_type ? `_cplx_dw`'d0 : `t1_src`;
                            pass
                        elif slot_idx in _info.compact_t2_slots:
                            t2_idx = _info.compact_t2_slots.index(slot_idx)
                            t2_re = _t2_sorted[t2_idx]
                            t2_src = f"H_avg_port{ant_port}_rb{rb}_re{t2_re}_complex"
                            if t1_re == t2_re:
                                #/ assign `_cw` = `t1_src`;
                                pass
                            else:
                                #/ assign `_cw` = cfg_dmrs_type ? `t2_src` : `t1_src`;
                                pass
                        else:
                            #/ assign `_cw` = `t1_src`;
                            pass
                concat_parts = []
                for rb in range(RB_PARALLELISM - 1, -1, -1):
                    for compact_re_val in reversed(_compact_re):
                        concat_parts.append(
                            f"ls_compact_p{ant_port}_rb{rb}_re{compact_re_val}"
                        )
                concat_expr = "{" + ", ".join(concat_parts) + "}"
                #/ assign `f"ls_buf_wr_data_port{ant_port}"` = `concat_expr`;
                pass
            else:
                concat_parts = []
                for rb in range(RB_PARALLELISM - 1, -1, -1):
                    for re_k in reversed(_info.pilot_re_list):
                        concat_parts.append(
                            f"H_avg_port{ant_port}_rb{rb}_re{re_k}_complex"
                        )
                concat_expr = "{" + ", ".join(concat_parts) + "}"
                #/ assign `f"ls_buf_wr_data_port{ant_port}"` = `concat_expr`;
                pass

        # FI→TI data concatenation (pack all FI output REs into fi_out_data)
        #/ // FI output → TI occasion register: {RB_{P-1}_RE11, ..., RB0_RE0}
        for ant_port in ANTENNA_PORTS:
            concat_parts = []
            for rb in range(RB_PARALLELISM - 1, -1, -1):
                for re_k in range(11, -1, -1):
                    concat_parts.append(
                        f"H_interp_f_port{ant_port}_rb{rb}_re{re_k}_complex"
                    )
            concat_expr = "{" + ", ".join(concat_parts) + "}"
            #/ assign `f"fi_out_data_port{ant_port}"` = `concat_expr`;
            #/ assign `f"fi_out_valid_port{ant_port}"` = `f"drain_valid_port{ant_port}"`;
            pass

    if HAS_PRE_FI_BUF:
        #/ assign ti_rb_addr_local = ctrl_ti_rb_addr[`_local_rb_width_precomp`-1:0];
        if freq_interp_method != 'lmmse':
            for ant_port in ANTENNA_PORTS:
                #/ assign `f"ls_buf_rd_addr_port{ant_port}"` = fi_window_base + {{(`SRAM_ADDR_WIDTH` - `_ls_buf_beat_w`){1'b0}}, `f"ls_buf_rd_beat_port{ant_port}"`};
                pass

    if _shared_coeff_specs:
        #/ assign shared_coeff_sram_rst_n = 1'b1;
        pass

    if HAS_PRE_FI_BUF and freq_interp_method == 'lmmse':
        #/ // Rate-matched replay combinational wiring
        #/ assign ls_en_muxed = wctrl_ls_enable;
        #/ assign c_init_strb_muxed = wctrl_c_init_strb;
        for i in range(Y_PARALLELISM):
            _hi = (i + 1) * _ybuf_re_w - 1
            _lo = i * _ybuf_re_w
            _dw = _ybuf_re_w
            #/ assign `f"Y_buffered_complex_{i}"` = wctrl_ybuf_rd_en ? ybuf_rd_data[`_hi`:`_lo`] : `_dw`'d0;
            pass

        if RB_PARALLELISM == 1:
            #/ assign ybuf_wr_addr = ctrl_rb_idx[`SRAM_ADDR_WIDTH`-1:0];
            pass
        else:
            _ybuf_addr_shift = math.ceil(math.log2(RB_PARALLELISM))
            #/ assign ybuf_wr_addr = ctrl_rb_idx[`SRAM_ADDR_WIDTH + _ybuf_addr_shift - 1`:`_ybuf_addr_shift`];
            pass

        _ybuf_wr_parts = []
        for i in range(Y_PARALLELISM - 1, -1, -1):
            if INPUT_MODE == 'A':
                _ybuf_wr_parts.append(f"Y_reduced_complex_{i}")
            else:
                _ybuf_rb = i // RE_PER_RB
                _ybuf_re = i % RE_PER_RB
                _ybuf_hi = (_ybuf_re + 1) * 2 * Y.DWT - 1
                _ybuf_lo = _ybuf_re * 2 * Y.DWT
                _ybuf_wr_parts.append(
                    f"Y_rb_out_{_ybuf_rb}[{_ybuf_hi}:{_ybuf_lo}]"
                )
        _ybuf_wr_concat = "{" + ", ".join(_ybuf_wr_parts) + "}"
        #/ assign ybuf_wr_data = `_ybuf_wr_concat`;
        if _ybuf_total_planes > 1:
            if _symbols_per_occasion > 1 and max_occasions > 1:
                #/ assign ybuf_wr_plane_sel = {ctrl_ybuf_occ_tag, ctrl_l_prime};
                pass
            elif _symbols_per_occasion > 1:
                #/ assign ybuf_wr_plane_sel = ctrl_l_prime;
                pass
            else:
                #/ assign ybuf_wr_plane_sel = ctrl_ybuf_occ_tag[`_ybuf_plane_sel_w`-1:0];
                pass

        # c_init replay storage declarations are in Region 2.  Keep the same
        # capture behavior while placing all procedural logic before instances.
        if dmrs_Uplink is True or dmrs_Uplink == "Hybrid":
            if _ybuf_total_planes > 1:
                for cdm_idx in enabled_indices:
                    #/ assign `f"cinit_stored_cdm{cdm_idx}"` = `f"cinit_stored_cdm{cdm_idx}_plane"`[wctrl_ybuf_rd_plane_sel];
                    pass
                if _symbols_per_occasion > 1 and max_occasions > 1:
                    _cinit_capture_sel = "{ctrl_ybuf_occ_tag, ctrl_l_prime}"
                elif _symbols_per_occasion > 1:
                    _cinit_capture_sel = "ctrl_l_prime"
                else:
                    _cinit_capture_sel = f"ctrl_ybuf_occ_tag[{_ybuf_plane_sel_w - 1}:0]"
                #/ always @(posedge clk) begin
                #/     if (ctrl_c_init_strb) begin
                for cdm_idx in enabled_indices:
                    #/         `f"cinit_stored_cdm{cdm_idx}_plane"`[`_cinit_capture_sel`] <= `f"cinit_gen_cdm{cdm_idx}"`;
                    pass
                #/     end
                #/ end
            else:
                #/ always @(posedge clk) begin
                #/     if (ctrl_c_init_strb) begin
                for cdm_idx in enabled_indices:
                    #/         `f"cinit_stored_cdm{cdm_idx}"` <= `f"cinit_gen_cdm{cdm_idx}"`;
                    pass
                #/     end
                #/ end

    # =================================================================
    # REGION 4: Module instantiations (dataflow order)
    # =================================================================

    # -- 4.1 CONTROLLER (FSM + counters + pilot detection + delay chains) --
    #/ // ========== CONTROLLER ==========
    ports_controller = {
        'clk': 'clk',
        'rst_n': 'rst_n',
        'ctrl_start': 'start',
        'cfg_pusch_symbol_length': 'cfg_pusch_symbol_length',
        'cfg_num_RBs': 'cfg_num_RBs',
        # Core FSM outputs
        'ctrl_ctr_en': 'ctrl_ctr_en',
        'ctrl_ls_en': 'ctrl_ls_en',
        'ctrl_ti_en': 'ctrl_ti_en',
        'slot_ce_done': 'slot_ce_done',
        'cfg_latch_en': 'cfg_latch_en',
        # Counter outputs
        'ctrl_rb_idx': 'ctrl_rb_idx',
        'ctrl_rb_idx_r': 'ctrl_rb_idx_r',
        'ctrl_sym_idx': 'ctrl_sym_idx',
        'ctrl_sym_idx_next': 'ctrl_sym_idx_next',
        # Pilot detection outputs
        'ctrl_is_pilot': 'ctrl_is_pilot',
        'ctrl_l_prime': 'ctrl_l_prime',
        'ctrl_is_last_dmrs': 'ctrl_is_last_dmrs',
        # Symbol boundaries
        'ctrl_c_init_strb': 'ctrl_c_init_strb',
        # Delay-aligned LS signals
        'ctrl_pilot_wr_en_raw': 'ctrl_pilot_wr_en_raw',
        'ctrl_pilot_wr_addr': 'ctrl_pilot_wr_addr',
        # TI control outputs
        'ctrl_ti_sram_rd_en': 'ctrl_ti_sram_rd_en',
        'ctrl_ti_rb_addr': 'ctrl_ti_rb_addr',
        'ctrl_ti_re_group': 'ctrl_ti_re_group',
        'ctrl_ti_valid': 'ti_data_valid',
        'ctrl_ti_done': 'ctrl_ti_done',
    }
    if _needs_rb_boundary and not HAS_PRE_FI_BUF:
        ports_controller['ctrl_first_rb_d'] = 'ctrl_first_rb_d'
        ports_controller['ctrl_last_rb_d'] = 'ctrl_last_rb_d'
        if RB_PARALLELISM > 1:
            ports_controller['ctrl_lane_last_d'] = 'ctrl_lane_last_d'
    if len(additional_DMRS_range) > 1:
        ports_controller['cfg_n_additional_dmrs'] = 'cfg_n_additional_dmrs'
    if dmrs_typeA_pos == "Hybrid":
        ports_controller['cfg_dmrs_typeA_pos_sel'] = 'cfg_dmrs_typeA_pos_sel'
    if is_double_dmrs == "Hybrid":
        ports_controller['cfg_is_double_dmrs'] = 'cfg_is_double_dmrs'
    if HAS_COEFF_SRAM:
        ports_controller['coeff_load_done'] = 'coeff_load_done'
        ports_controller['coeff_loading'] = 'coeff_loading'
        ports_controller['coeff_reload_req'] = 'coeff_reload_req'
    if max_occasions > 1:
        ports_controller['ctrl_occ_idx'] = 'ctrl_occ_idx'
    if HAS_PRE_FI_BUF and max_occasions > 1:
        ports_controller['ctrl_ybuf_occ_tag'] = 'ctrl_ybuf_occ_tag'
    if freq_interp_method == 'lmmse' and not HAS_PRE_FI_BUF:
        ports_controller['ctrl_freq_interp_en'] = 'ctrl_freq_interp_en'
    if HAS_PRE_FI_BUF:
        ports_controller['fi_trigger'] = 'fi_trigger'
        if max_occasions > 1:
            ports_controller['fi_occ_sel'] = 'fi_occ_sel'
        ports_controller['fi_window_base'] = 'fi_window_base'
        if _needs_rb_boundary:
            ports_controller['fi_first_rb'] = 'fi_first_rb'
            ports_controller['fi_last_rb'] = 'fi_last_rb'
            if RB_PARALLELISM > 1:
                ports_controller['fi_lane_last'] = 'fi_lane_last'
    if RB_PARALLELISM > 1 and INPUT_MODE == 'B':
        ports_controller['ctrl_rb_remainder'] = 'ctrl_rb_remainder'
        ports_controller['ctrl_sym_overflow'] = 'ctrl_sym_overflow'
    if RB_PARALLELISM > 1:
        ports_controller['ti_rb_within_beat'] = 'ti_rb_within_beat'

    _fi_fill_beats_orig = max(LMMSE_INTERP_PARALLELISM // max(RB_PARALLELISM, 1), 1) if freq_interp_method == 'lmmse' else 1
    _output_groups = (12 // FI_RE_PARALLELISM) if HAS_PRE_FI_BUF else 1
    _fi_fill_beats = _fi_fill_beats_orig * _output_groups

    ModuleCONTROLLER(min_num_RBs=min_num_RBs, max_num_RBs=max_num_RBs, RB_PARALLELISM=RB_PARALLELISM, max_pusch_symbols=max_pusch_symbols, is_double_dmrs=is_double_dmrs, additional_DMRS_range=additional_DMRS_range, dmrs_typeA_pos=dmrs_typeA_pos, num_symbols_range=num_symbols_range, LS_DRAIN_CYCLES=EARLY_LS_DRAIN, TI_PIPELINE_DEPTH=TI_PIPELINE_DEPTH, TI_RE_PARALLELISM=TI_RE_PARALLELISM, HAS_COEFF_SRAM=HAS_COEFF_SRAM, ls_ctrl_graph=ls_ctrl_graph, freq_interp_method=freq_interp_method, max_occasions=max_occasions, counter_width=counter_width, SRAM_ADDR_WIDTH=SRAM_ADDR_WIDTH, Qu_symbol_idx=Qu_symbol_idx, INPUT_MODE=INPUT_MODE, is_enhanced=is_enhanced, dmrs_Type=dmrs_Type, is_ECP=is_ECP, switchable_ports=switchable_ports, ANTENNA_PORTS=ANTENNA_PORTS, has_pre_fi_buf=HAS_PRE_FI_BUF, FI_WINDOW_SIZE=FI_WINDOW_SIZE, FI_CYCLES_PER_OCC=FI_CYCLES_PER_OCC, FI_CYCLES_PER_OCC_SINGLE=FI_CYCLES_PER_OCC_SINGLE, FI_FILL_BEATS=_fi_fill_beats, HAS_TI_GATE=False, PORTS=ports_controller)

    # -- 4.2 CFG_LATCH (per-slot configuration freeze) --
    #/ // ========== Config Latching ==========
    ports_cfg_latch: dict = {
        'clk': 'clk',
        'rst_n': 'rst_n',
        'latch_en': 'cfg_latch_en',
        'N_ID': 'N_ID',
        'cfg_N_ID': 'cfg_N_ID',
        'n_scid': 'n_scid',
        'cfg_n_scid': 'cfg_n_scid',
        'current_slot_idx': 'current_slot_idx',
        'cfg_current_slot_idx': 'cfg_current_slot_idx',
        'pusch_symbol_length': 'pusch_symbol_length',
        'cfg_pusch_symbol_length': 'cfg_pusch_symbol_length',
        'num_RBs': 'num_RBs',
        'cfg_num_RBs': 'cfg_num_RBs',
    }
    if is_double_dmrs == "Hybrid":
        ports_cfg_latch['is_double_dmrs'] = 'is_double_dmrs'
        ports_cfg_latch['cfg_is_double_dmrs'] = 'cfg_is_double_dmrs'
    if is_enhanced == "Hybrid":
        ports_cfg_latch['is_enhanced'] = 'is_enhanced'
        ports_cfg_latch['cfg_is_enhanced'] = 'cfg_is_enhanced'
    if dmrs_Type == "Hybrid":
        ports_cfg_latch['dmrs_type'] = 'dmrs_type'
        ports_cfg_latch['cfg_dmrs_type'] = 'cfg_dmrs_type'
    if dmrs_typeA_pos == "Hybrid":
        ports_cfg_latch['dmrs_typeA_pos_sel'] = 'dmrs_typeA_pos_sel'
        ports_cfg_latch['cfg_dmrs_typeA_pos_sel'] = 'cfg_dmrs_typeA_pos_sel'
    if max_cdm_groups >= 2:
        ports_cfg_latch['num_cdm_groups_without_data'] = 'num_cdm_groups_without_data'
        ports_cfg_latch['cfg_num_cdm_groups_without_data'] = 'cfg_num_cdm_groups_without_data'
    if is_ECP == "Hybrid":
        ports_cfg_latch['is_ECP'] = 'is_ECP'
        ports_cfg_latch['cfg_is_ECP'] = 'cfg_is_ECP'
    if len(additional_DMRS_range) > 1:
        ports_cfg_latch['n_additional_dmrs'] = 'n_additional_dmrs'
        ports_cfg_latch['cfg_n_additional_dmrs'] = 'cfg_n_additional_dmrs'
    if switchable_ports:
        for _i, _port in enumerate(ANTENNA_PORTS):
            ports_cfg_latch[f'port_enable_{_i}'] = f'port_enable_p{_port}'
            ports_cfg_latch[f'cfg_port_enable_{_i}'] = f'cfg_port_enable_p{_port}'

    ModuleCFG_LATCH(Qu_slot_idx=Qu_slot_idx, counter_width=counter_width, N_CLK=1, IF_RST_N=True, has_is_double_dmrs=is_double_dmrs == 'Hybrid', has_is_enhanced=is_enhanced == 'Hybrid', has_dmrs_type=dmrs_Type == 'Hybrid', has_typeA_pos=dmrs_typeA_pos == 'Hybrid', cdm_sel_bits=_cdm_sel_bits, has_is_ECP=is_ECP == 'Hybrid', n_add_width=_n_add_width_latch, num_ports=_num_ports_latch, PORTS=ports_cfg_latch)

    # -- 4.3 PORT_ENABLE (runtime port gating) --
    if switchable_ports:
        #/ // ========== Port Enable ==========
        ports_port_enable = {}
        if is_enhanced == "Hybrid":
            ports_port_enable['is_enhanced'] = 'cfg_is_enhanced'
        if is_double_dmrs == "Hybrid":
            ports_port_enable['is_double_dmrs'] = 'cfg_is_double_dmrs'
        if dmrs_Type == "Hybrid":
            ports_port_enable['dmrs_type'] = 'cfg_dmrs_type'
        for i, port in enumerate(ANTENNA_PORTS):
            ports_port_enable[f'port_enable_ext_{i}'] = f'cfg_port_enable_p{port}'
        ports_port_enable['ports_enable'] = 'ports_enable_combined'

        ModulePORT_ENABLE(antenna_ports=ANTENNA_PORTS, dmrs_Type=dmrs_Type, is_enhanced=is_enhanced, is_double_dmrs=is_double_dmrs, has_ext_enable=True, PORTS=ports_port_enable)

    # -- 4.4 CDM_CTRL (runtime fdCDM/tdCDM calculation) --
    if switchable_ports:
        #/ // ========== Runtime fdCDM/tdCDM Calculation ==========
        ports_cdm_ctrl = {}
        ports_cdm_ctrl['ports_enable'] = 'ports_enable_combined'
        if dmrs_Type == "Hybrid":
            ports_cdm_ctrl['dmrs_type'] = 'cfg_dmrs_type'
        for g in _cdm_active_groups:
            ports_cdm_ctrl[f'fdCDM_cdm{g}'] = f'fdCDM_cdm{g}'
            ports_cdm_ctrl[f'tdCDM_cdm{g}'] = f'tdCDM_cdm{g}'

        ModuleCDM_CTRL(antenna_ports=ANTENNA_PORTS, dmrs_Type=dmrs_Type, PORTS=ports_cdm_ctrl)
        fdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
        tdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
    elif not switchable_ports and dmrs_Type == 'Hybrid':
        #/ // ========== FD/TD Averaging Window Configuration ==========
        ports_cdm_ctrl = {}
        ports_cdm_ctrl['dmrs_type'] = 'cfg_dmrs_type'
        for g in _cdm_active_groups:
            ports_cdm_ctrl[f'fdCDM_cdm{g}'] = f'fdCDM_cdm{g}'
            ports_cdm_ctrl[f'tdCDM_cdm{g}'] = f'tdCDM_cdm{g}'

        ModuleCDM_CTRL(antenna_ports=ANTENNA_PORTS, dmrs_Type=dmrs_Type, has_ports_enable=False, PORTS=ports_cdm_ctrl)
        fdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
        tdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
    else:
        assert isinstance(dmrs_Type, int)
        if production_layout_metadata:
            fdCDM = dict(descriptor_fdCDM)
            tdCDM = dict(descriptor_tdCDM)
        else:
            fdCDM = {
                pcdmu.group_idx: pcdmu.get_fdCDM(dmrs_Type)
                for pcdmu in arch_config.pcdmu_instances
            }
            tdCDM = {
                pcdmu.group_idx: pcdmu.get_tdCDM(dmrs_Type)
                for pcdmu in arch_config.pcdmu_instances
            }

    # -- 4.5 C_INIT_GENERATION --
    #/ // ========== C_INIT Generation ==========
    ports_c_init = {
        'clk': 'clk',
        'rst_n': 'rst_n',
        'N_ID': 'cfg_N_ID',
        'n_scid': 'cfg_n_scid',
        'current_symbol_idx': 'cinit_symbol_idx',
        'current_slot_idx': 'cfg_current_slot_idx',
    }
    if is_ECP == "Hybrid":
        ports_c_init['is_ECP'] = 'cfg_is_ECP'
    if dmrs_Uplink == "Hybrid":
        ports_c_init['dmrs_uplink'] = 'dmrs_uplink'
    if dmrs_Uplink is True or dmrs_Uplink == "Hybrid":
        for cdm_idx in range(len(enabled_cdm_groups_union)):
            if enabled_cdm_groups_union[cdm_idx]:
                ports_c_init[f'c_init_cdm{cdm_idx}'] = f'cinit_gen_cdm{cdm_idx}'
    else:
        ports_c_init['c_init'] = 'cinit_gen'

    ModuleC_INIT_GENERATION(Qu_symbol_idx=Qu_symbol_idx, Qu_slot_idx=Qu_slot_idx, N_CLK=N_CLK_CINIT, dmrs_Type=dmrs_Type, dmrs_Uplink=dmrs_Uplink, is_ECP=is_ECP, ENABLED_CDM_GROUPS_TYPE1=ENABLED_CDM_GROUPS_TYPE1, ENABLED_CDM_GROUPS_TYPE2=ENABLED_CDM_GROUPS_TYPE2, ENABLED_CDM_GROUPS_TYPE3=ENABLED_CDM_GROUPS_TYPE3, PORTS=ports_c_init)

    # -- 4.6 Y_PATH_REDUCE (+ Y_RB_ALIGN for Mode B) --
    if INPUT_MODE == 'A':
        #/ // ========== INPUT_MODE A: Global PATH_REDUCE ==========
        ports_y_path_reduce = {}
        for i in range(len(INPUT_INDEX_LIST)):
            ports_y_path_reduce[f'data_in_{i}'] = f'Y_in_complex_{i}'
        for i in range(Y_PARALLELISM):
            ports_y_path_reduce[f'data_out_{i}'] = f'Y_reduced_complex_{i}'

        ModuleY_PATH_REDUCE(Qu_Data=Qu_Y_Complex, INPUT_INDEX_LIST=INPUT_INDEX_LIST, OUTPUT_INDEX_LIST=TRUE_INDEX_LIST, HAS_VALID_READY=False, PORTS=ports_y_path_reduce)

    elif INPUT_MODE == 'B':
        #/ // ========== INPUT_MODE B: Per-RB PATH_REDUCE + Barrel Align ==========
        for rb in range(RB_PARALLELISM):
            ports_y_path_reduce_rb = {}
            for k in range(12):
                ports_y_path_reduce_rb[f'data_in_{k}'] = f'Y_in_rb{rb}_complex_{k}'
            for r in range(RE_PER_RB):
                ports_y_path_reduce_rb[f'data_out_{r}'] = f'Y_reduced_rb{rb}_complex_{r}'
            ports_y_path_reduce_rb['valid_in'] = f'Y_valid_rb{rb}'
            ports_y_path_reduce_rb['valid_out'] = f'Y_align_valid_rb{rb}'
            ports_y_path_reduce_rb['ready_in'] = f'Y_ready_rb{rb}'
            ports_y_path_reduce_rb['ready_out'] = f'Y_align_ready_rb{rb}'

            ModuleY_PATH_REDUCE(Qu_Data=Qu_Y_Complex, INPUT_INDEX_LIST=list(range(12)), OUTPUT_INDEX_LIST=required_re_per_rb, HAS_VALID_READY=True, PORTS=ports_y_path_reduce_rb)

        # -- Y_RB_ALIGN (barrel shifter for Mode B boundary alignment) --
        if RB_PARALLELISM > 1:
            ports_y_rb_align = {
                'clk': 'clk',
                'rst_n': 'rst_n',
                'remainder': 'ctrl_rb_remainder',
                'sym_overflow': 'ctrl_sym_overflow',
            }
        else:
            ports_y_rb_align = {
                'clk': 'clk',
                'rst_n': 'rst_n',
            }
        for rb in range(RB_PARALLELISM):
            ports_y_rb_align[f'Y_rb_{rb}'] = f'Y_rb_in_{rb}'
            ports_y_rb_align[f'Y_valid_rb_{rb}'] = f'Y_align_valid_rb{rb}'
            ports_y_rb_align[f'Y_ready_rb_{rb}'] = f'Y_align_ready_rb{rb}'
            ports_y_rb_align[f'Y_out_rb_{rb}'] = f'Y_rb_out_{rb}'

        ModuleY_RB_ALIGN(Qu_Y=Y, RB_PARALLELISM=RB_PARALLELISM, RE_PER_RB=RE_PER_RB, PORTS=ports_y_rb_align)

    # -- 4.7 LS Channel Estimation --
    #/ // ========== LS Channel Estimation ==========
    ports_ls = {
        'clk': 'clk',
        'rst_n': 'rst_n',
    }
    if max_cdm_groups >= 2:
        ports_ls['num_cdm_groups_without_data'] = 'cfg_num_cdm_groups_without_data'
    if dmrs_Type == "Hybrid":
        ports_ls['dmrs_type'] = 'cfg_dmrs_type'
    if is_enhanced == "Hybrid":
        ports_ls['is_enhanced'] = 'cfg_is_enhanced'
    if is_double_dmrs == "Hybrid":
        ports_ls['is_double_dmrs'] = 'cfg_is_double_dmrs'
    if dmrs_Uplink is True or dmrs_Uplink == "Hybrid":
        for cdm_idx in enabled_indices:
            if (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'):
                ports_ls[f'c_init_cdm{cdm_idx}'] = f'cinit_stored_cdm{cdm_idx}'
            else:
                ports_ls[f'c_init_cdm{cdm_idx}'] = f'cinit_gen_cdm{cdm_idx}'
    else:
        ports_ls['c_init'] = 'cinit_gen'
    if (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse' and _symbols_per_occasion > 1):
        # Replay occurs after the main controller has left the DMRS symbols, so
        # its l' value is stale.  Drive the LS/OCC/averaging path from the
        # window controller's active replay plane instead.
        ports_ls['l_quote'] = 'wctrl_lfsr_ctx_sel'
    else:
        ports_ls['l_quote'] = 'ctrl_l_prime'
    if (is_enhanced == "Hybrid" or is_enhanced is True) and _has_any_type1:
        ports_ls['current_RB_idx_lsb'] = 'current_RB_idx_lsb'
    for i in range(Y_PARALLELISM):
        ports_ls[f'Y_reduced_complex_{i}'] = f'Y_buffered_complex_{i}'
    if switchable_ports:
        for i, port in enumerate(ANTENNA_PORTS):
            ports_ls[f'port_enable_p{port}'] = f'ports_enable_combined[{i}]'
    if (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'):
        ports_ls['enable_ls_pipeline'] = 'ls_en_muxed'
        ports_ls['c_init_strb'] = 'c_init_strb_muxed'
        ports_ls['lfsr_ctx_save_en'] = 'wctrl_lfsr_ctx_save'
        ports_ls['lfsr_ctx_restore_en'] = 'wctrl_lfsr_ctx_restore'
        if _symbols_per_occasion > 1:
            ports_ls['avg_sym_switch'] = 'wctrl_avg_sym_switch'
            ports_ls['replay_data_valid'] = 'wctrl_replay_data_valid'
        if _ybuf_total_planes > 1:
            # LFSR progress is independent for every replay plane.  A plane
            # is (occasion * symbols_per_occasion + l'), matching Y_BUF and
            # c_init storage exactly; selecting only l' or occasion[0]
            # aliases contexts as soon as more than two planes are present.
            ports_ls['lfsr_ctx_sel'] = 'wctrl_ybuf_rd_plane_sel'
        ports_ls['replay_token_valid_in'] = 'wctrl_replay_token_valid_in'
        ports_ls['replay_token_in'] = 'wctrl_replay_token_in'
        ports_ls['replay_token_valid_out'] = 'wctrl_replay_token_valid_out'
        ports_ls['replay_token_out'] = 'wctrl_replay_token_out'
    else:
        ports_ls['enable_ls_pipeline'] = 'ctrl_ls_en'
        ports_ls['c_init_strb'] = 'ctrl_c_init_strb'
    for g in _cdm_active_groups:
        if fdCDM[g] == 'Hybrid':
            ports_ls[f'fdCDM_ctrl_cdm{g}'] = f'fdCDM_cdm{g}'
        if tdCDM[g] == 'Hybrid':
            ports_ls[f'tdCDM_ctrl_cdm{g}'] = f'tdCDM_cdm{g}'
    for ant_port in ANTENNA_PORTS:
        info = arch_config.get_port_interp_info(ant_port)
        for rb in range(RB_PARALLELISM):
            for re_k in info.pilot_re_list:
                wire_name = f"H_avg_port{ant_port}_rb{rb}_re{re_k}_complex"
                ports_ls[
                    f'H_avg_port{ant_port}_rb{rb}_re{re_k}_complex'
                ] = wire_name

    ModuleLS(Qu_Y=Y, QU_H_LS=QU_H_LS, QU_MODE_LS=QU_MODE_LS, OF_MODE_LS=OF_MODE_LS, N_CLK_Y_PRE=N_CLK_Y_PRE, N_CLK_DMRS_SEQ=N_CLK_DMRS_SEQ, N_CLK_LS_ROT=N_CLK_LS_ROT, dmrs_Type=dmrs_Type, dmrs_Uplink=dmrs_Uplink, is_ECP=is_ECP, is_enhanced=is_enhanced, is_double_dmrs=is_double_dmrs, antenna_ports=ANTENNA_PORTS, TRUE_INDEX_LIST=TRUE_INDEX_LIST, switchable_ports=switchable_ports, RB_PARALLELISM=RB_PARALLELISM, fdCDM=fdCDM, tdCDM=tdCDM, max_num_RBs=max_num_RBs, HAS_LFSR_ENABLE=True, HAS_LFSR_CTX=HAS_PRE_FI_BUF and freq_interp_method == 'lmmse', HAS_AVG_SYM_SWITCH=HAS_PRE_FI_BUF and freq_interp_method == 'lmmse' and (_symbols_per_occasion > 1), N_LFSR_CTX_SLOTS=_ybuf_total_planes, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG, REPLAY_TOKEN_DWT=_replay_token_dwt if HAS_PRE_FI_BUF and freq_interp_method == 'lmmse' else 0, N_CLK_AVG=ls_timing['N_CLK_AVG'], PORTS=ports_ls)

    # -- 4.8 Frequency Interpolation --
    #/ // ========== Frequency Interpolation ==========

    # When COEFF_SOURCE='SRAM':
    # share one COEFF_SRAM per CDM group.  All ports in a CDM group
    # share identical LMMSE coefficient matrices (same pilot RE positions).
    if _shared_coeff_specs:
        for _spec in _shared_coeff_specs:
            _rd_data_w = _spec['rd_data_w']
            _rd_idx_w = _spec['rd_idx_w']
            _ssram_ports = {
                'clk': 'clk',
                'rst_n': 'shared_coeff_sram_rst_n',
                'wr_en': 'fi_coeff_wr_en',
                'wr_addr': 'fi_coeff_wr_addr',
                'wr_data': 'fi_coeff_wr_data',
                'rd_beat_idx': _rd_idx_w,
                'rd_data': _rd_data_w,
            }

            ModuleCOEFF_SRAM(N_OUTPUT=_spec['n_output'], N_PILOTS=_spec['n_pilots'], Qu_COEFF=Qu_FI_LMMSE_COEFF, COEFF_STORAGE='SRAM', is_hybrid=False, rom_data_bank0=None, rom_data_bank1=None, BEAT_MODE=True, N_PILOTS_PER_BEAT=_spec['n_pilots_per_beat'], FILL_BEATS=_spec['fill_beats'], PORTS=_ssram_ports)

    _production_layout_by_port = {
        metadata.antenna_port: metadata.canonical_dict()
        for metadata in production_layout_metadata
    }
    for ant_port in ANTENNA_PORTS:
        info = arch_config.get_port_interp_info(ant_port)
        _production_layout = _production_layout_by_port.get(ant_port)
        #/ // --- Frequency interpolation for antenna port `ant_port` ---
        # first_RB/last_RB only exist on the NN and Linear FI wrappers; the LMMSE
        # wrapper does not declare them (nothing inside consumes them).
        ports_interp = {'clk': 'clk'}
        if freq_interp_method in ('nn', 'linear'):
            if HAS_PRE_FI_BUF:
                ports_interp['first_RB'] = 'fi_first_rb'
                ports_interp['last_RB'] = 'fi_last_rb'
                if RB_PARALLELISM > 1:
                    ports_interp['lane_last'] = 'fi_lane_last'
            else:
                ports_interp['first_RB'] = 'ctrl_first_rb_d'
                ports_interp['last_RB'] = 'ctrl_last_rb_d'
                if RB_PARALLELISM > 1:
                    ports_interp['lane_last'] = 'ctrl_lane_last_d'
        if info.is_dual_type:
            ports_interp['dmrs_type'] = 'cfg_dmrs_type'
        if not HAS_PRE_FI_BUF:
            for rb in range(RB_PARALLELISM):
                for re_k in info.pilot_re_list:
                    interp_in_name = info.interp_input_name(rb, re_k)
                    avg_complex = f"H_avg_port{ant_port}_rb{rb}_re{re_k}_complex"
                    ports_interp[interp_in_name] = avg_complex
        for rb in range(RB_PARALLELISM):
            for re_k in range(12):
                out_name = info.interp_output_name(
                    freq_interp_method, rb, re_k
                )
                ports_interp[out_name] = (
                    f"H_interp_f_port{ant_port}_rb{rb}"
                    f"_re{re_k}_complex"
                )

        if freq_interp_method in ('nn', 'linear'):
            if HAS_PRE_FI_BUF:
                ports_interp['enable'] = 'fi_trigger'
                ports_interp['drain_valid'] = f"drain_valid_port{ant_port}"
                ports_interp['ls_buf_rd_data'] = f"ls_buf_rd_data_port{ant_port}"
                ports_interp['ls_buf_rd_en'] = f"ls_buf_rd_en_port{ant_port}"
                ports_interp['ls_buf_rd_beat'] = f"ls_buf_rd_beat_port{ant_port}"
            ModuleFREQ_INTERP(IF_RST_N=False, RB_parallelism=RB_PARALLELISM, Qu_H_LS=QU_H_LS, Qu_H=Qu_H_interp_f, antenna_port=ant_port, RE_INDEX_LIST=info.pilot_re_list, method=freq_interp_method, dmrs_Type=dmrs_Type, pilot_re_compact=info.pilot_re_compact if info.is_dual_type else None, compact_t2_slots=info.compact_t2_slots if info.is_dual_type else None, compact_zero_slots=info.compact_zero_slots if info.is_dual_type else None, pilot_re_t1=info.re_list_type1 if info.is_dual_type else None, pilot_re_t2=info.re_list_type2 if info.is_dual_type else None, has_pre_fi_buf=HAS_PRE_FI_BUF, production_observation_layout=_production_layout, PORTS=ports_interp)
        elif freq_interp_method == 'lmmse':
            if not HAS_PRE_FI_BUF:
                ports_interp['enable'] = 'ctrl_freq_interp_en'
            else:
                ports_interp['enable'] = 'wctrl_fi_enable'
            ports_interp['drain_valid'] = f"drain_valid_port{ant_port}"

            if HAS_PRE_FI_BUF:
                ports_interp['ls_buf_rd_data'] = f"ls_buf_rd_data_port{ant_port}"
                ports_interp['ls_buf_rd_en'] = f"ls_buf_rd_en_port{ant_port}"
                ports_interp['ls_buf_rd_beat'] = f"ls_buf_rd_beat_port{ant_port}"

            _coeff_shared = bool(_share_cdm_srams)
            if _coeff_shared:
                _re_key = _port_coeff_key[ant_port]
                _srd_data, _srd_idx, _sbeat_w = _share_cdm_srams[_re_key]
                ports_interp['coeff_rd_data'] = _srd_data
                _is_first = (_all_coeff_groups[_re_key][0] == ant_port)
                if _is_first:
                    ports_interp['coeff_rd_idx'] = _srd_idx
                else:
                    _idx_nc = f"{_srd_idx}_port{ant_port}_nc"
                    ports_interp['coeff_rd_idx'] = _idx_nc

            ModuleFREQ_INTERP(IF_RST_N=False, RB_parallelism=RB_PARALLELISM, Qu_H_LS=QU_H_LS, Qu_H=Qu_H_interp_f, antenna_port=ant_port, RE_INDEX_LIST=info.pilot_re_list, method='lmmse', dmrs_Type=dmrs_Type, LMMSE_P=LMMSE_INTERP_PARALLELISM, Qu_COEFF=Qu_FI_LMMSE_COEFF, REAL_COEFF=FI_LMMSE_REAL_COEFF, tau_rms=FI_LMMSE_tau_rms, snr_linear=FI_LMMSE_snr_linear, COEFF_SOURCE=FI_LMMSE_COEFF_SOURCE, COEFF_SRAM_SHARED=_coeff_shared, channel_model=FI_LMMSE_channel_model, delay_spread=FI_LMMSE_delay_spread, scs=FI_LMMSE_scs, pilot_re_compact=info.pilot_re_compact if info.is_dual_type else None, compact_t2_slots=info.compact_t2_slots if info.is_dual_type else None, compact_zero_slots=info.compact_zero_slots if info.is_dual_type else None, pilot_re_t1=info.re_list_type1 if info.is_dual_type else None, pilot_re_t2=info.re_list_type2 if info.is_dual_type else None, FI_RE_PARALLELISM=FI_RE_PARALLELISM, has_pre_fi_buf=HAS_PRE_FI_BUF, fi_core_graph=build_fi_core_graph(N_PILOTS_PER_RB=len(production_lane_representatives.get(ant_port, info.pilot_re_compact or info.pilot_re_list)), LMMSE_P=LMMSE_INTERP_PARALLELISM, RB_PARALLELISM=RB_PARALLELISM, H_DWT=H_interp_f_DWT // 2, COEFF_DWT=FI_LMMSE_COEFF_DWT, REAL_COEFF=FI_LMMSE_REAL_COEFF, FI_RE_PARALLELISM=FI_RE_PARALLELISM, has_pre_fi_buf=HAS_PRE_FI_BUF)[0], production_observation_layout=_production_layout, PORTS=ports_interp)

    # -- 4.8b LS_BUF instantiation (pre-FI mode only) --
    if HAS_PRE_FI_BUF:
        #/ // ========== LS_BUF (Pre-FI Pilot Buffer) ==========
        if freq_interp_method == 'lmmse':
            _pilot_bank_depth = LMMSE_INTERP_PARALLELISM // RB_PARALLELISM
            _pilot_bank_addr_w = max(math.ceil(math.log2(_pilot_bank_depth)), 1)
        for ant_port in ANTENNA_PORTS:
            _info = arch_config.get_port_interp_info(ant_port)
            _descriptor_re = production_lane_representatives.get(ant_port)
            _n_pilots = (
                len(_descriptor_re)
                if _descriptor_re is not None
                else _info.num_pilots_compact
            )
            _ls_buf_dw = _n_pilots * RB_PARALLELISM * COMPLEX_DWT_LS

            if freq_interp_method == 'lmmse':
                _rd_addr_w = f"ls_buf_rd_beat_port{ant_port}"
            else:
                #/ // --- LS_BUF read address = fi_window_base + ls_buf_rd_beat ---
                _rd_addr_w = f"ls_buf_rd_addr_port{ant_port}"

            if freq_interp_method == 'lmmse':
                ports_lsbuf = {
                    'clk': 'clk',
                    'rst_n': 'rst_n',
                    'wr_en': 'wctrl_pilot_wr_en',
                    'wr_addr': 'wctrl_pilot_wr_addr',
                    'wr_data': f'ls_buf_wr_data_port{ant_port}',
                    'rd_en': f'ls_buf_rd_en_port{ant_port}',
                    'rd_addr': _rd_addr_w,
                    'rd_data': f'ls_buf_rd_data_port{ant_port}',
                }
            else:
                ports_lsbuf = {
                    'clk': 'clk',
                    'rst_n': 'rst_n',
                    'wr_en': 'ctrl_pilot_wr_en_raw',
                    'wr_addr': 'ctrl_pilot_wr_addr',
                    'wr_data': f'ls_buf_wr_data_port{ant_port}',
                    'rd_en': f'ls_buf_rd_en_port{ant_port}',
                    'rd_addr': _rd_addr_w,
                    'rd_data': f'ls_buf_rd_data_port{ant_port}',
                }
                if max_occasions > 1:
                    ports_lsbuf['wr_occasion_sel'] = 'ctrl_occ_idx'
                    ports_lsbuf['rd_occasion_sel'] = 'fi_occ_sel'

            #/ // --- LS_BUF for antenna port `ant_port` ---
            _lsbuf_depth = _pilot_bank_depth if freq_interp_method == 'lmmse' else SRAM_DEPTH
            _lsbuf_occ = 1 if freq_interp_method == 'lmmse' else max_occasions
            ModuleLS_BUF(max_occasions=_lsbuf_occ, SRAM_DEPTH=_lsbuf_depth, DATA_WIDTH=_ls_buf_dw, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG, PORTS=ports_lsbuf)

    # -- 4.8c Rate-Matched LS-FI: Y_BUF + Window Controller --
    if (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'):
        #/ // ========== Y_BUF (Shared Pre-LS Buffer) ==========
        ports_ybuf = {
            'clk': 'clk',
            'rst_n': 'rst_n',
            'wr_en': 'ctrl_ls_en',
            'wr_addr': 'ybuf_wr_addr',
            'wr_data': 'ybuf_wr_data',
            'rd_en': 'wctrl_ybuf_rd_en',
            'rd_addr': 'wctrl_ybuf_rd_addr',
            'rd_data': 'ybuf_rd_data',
        }
        if _ybuf_total_planes > 1:
            ports_ybuf['wr_plane_sel'] = 'ybuf_wr_plane_sel'
            ports_ybuf['rd_plane_sel'] = 'wctrl_ybuf_rd_plane_sel'

        ModuleY_BUF(max_occasions=max_occasions, symbols_per_occasion=_symbols_per_occasion, SRAM_DEPTH=SRAM_DEPTH, DATA_WIDTH=_ybuf_data_w, PORTS=ports_ybuf)
        #/ // ========== LS-FI Window Controller ==========
        ports_wctrl = {
            'clk': 'clk',
            'rst_n': 'rst_n',
            'ctrl_start': 'fi_trigger',
            'num_RBs': 'num_RBs',
            'ybuf_rd_en': 'wctrl_ybuf_rd_en',
            'ybuf_rd_addr': 'wctrl_ybuf_rd_addr',
            'ls_enable': 'wctrl_ls_enable',
            'replay_token_valid_in': 'wctrl_replay_token_valid_in',
            'replay_token_in': 'wctrl_replay_token_in',
            'replay_token_valid_out': 'wctrl_replay_token_valid_out',
            'replay_token_out': 'wctrl_replay_token_out',
            'ls_sym_switch': 'wctrl_ls_sym_switch',
            'lfsr_ctx_save_en': 'wctrl_lfsr_ctx_save',
            'lfsr_ctx_restore_en': 'wctrl_lfsr_ctx_restore',
            'avg_sym_switch': 'wctrl_avg_sym_switch',
            'pilot_bank_wr_done': 'wctrl_pilot_bank_wr_done',
            'pilot_bank_sel': 'wctrl_pilot_bank_sel',
            'replay_c_init_strb': 'wctrl_c_init_strb',
            'fi_enable': 'wctrl_fi_enable',
            'pilot_wr_en': 'wctrl_pilot_wr_en',
            'pilot_wr_addr': 'wctrl_pilot_wr_addr',
            'fi_mac_done': '1\'b0',
            'cur_window': 'wctrl_cur_window',
            'all_done': 'wctrl_done',
            'ctrl_done': 'wctrl_done_dup',
        }
        if is_double_dmrs == "Hybrid":
            ports_wctrl['cfg_is_double_dmrs'] = 'cfg_is_double_dmrs'
        if len(additional_DMRS_range) > 1:
            ports_wctrl['cfg_n_additional_dmrs'] = 'cfg_n_additional_dmrs'
        if _ybuf_total_planes > 1:
            ports_wctrl['ybuf_rd_plane_sel'] = 'wctrl_ybuf_rd_plane_sel'
            ports_wctrl['pilot_wr_plane'] = 'wctrl_pilot_wr_plane'
        if _symbols_per_occasion > 1:
            ports_wctrl['replay_data_valid'] = 'wctrl_replay_data_valid'
            ports_wctrl['lfsr_ctx_sel'] = 'wctrl_lfsr_ctx_sel'
        if max_occasions > 1:
            ports_wctrl['cur_occasion'] = 'wctrl_cur_occasion'

        ModuleLS_FI_WINDOW_CTRL(max_num_RBs=max_num_RBs, RB_PARALLELISM=RB_PARALLELISM, LMMSE_P=LMMSE_INTERP_PARALLELISM, FI_RE_PARALLELISM=FI_RE_PARALLELISM, max_occasions=max_occasions, symbols_per_occasion=_symbols_per_occasion, LS_DRAIN_CYCLES=_replay_pipe_delay, is_double_dmrs=is_double_dmrs, runtime_n_additional=len(additional_DMRS_range) > 1, PORTS=ports_wctrl)

    # -- 4.9 Time-Domain Interpolation (per antenna port) --
    #/ // ========== Time-Domain Interpolation ==========
    needs_runtime_l0 = (dmrs_typeA_pos == 'Hybrid')
    needs_runtime_dbl = (is_double_dmrs == "Hybrid")
    needs_runtime_nadd = (len(additional_DMRS_range) > 1)
    needs_runtime_nsym = (
        len(list(range(min_pusch_symbols, max_pusch_symbols + 1))) > 1
    )

    # In pre-FI mode TIME_INTERP indexes the per-window occasion register,
    # which is only LOCAL_RB_WIDTH bits wide -- slice the low bits of the
    # full-width ctrl_ti_rb_addr to avoid a bit-width mismatch.
    if HAS_PRE_FI_BUF:
        _beats_per_window = max(FI_WINDOW_SIZE // RB_PARALLELISM, 1)
        _local_rb_width = _local_rb_width_precomp

    for ant_port in ANTENNA_PORTS:
        #/ // --- Time-domain interpolation for antenna port `ant_port` ---
        ports_ti = {
            'clk': 'clk',
            'rst_n': 'rst_n',
            'ti_sram_rd_en': 'ctrl_ti_sram_rd_en',
            'ti_rb_addr': 'ti_rb_addr_local' if HAS_PRE_FI_BUF else 'ctrl_ti_rb_addr',
            'ti_re_group': 'ctrl_ti_re_group',
        }
        if not HAS_PRE_FI_BUF:
            ports_ti['wr_en'] = 'ctrl_pilot_wr_en'
            ports_ti['wr_addr'] = 'ctrl_pilot_wr_addr'
            ports_ti['wr_data'] = f'pilot_wr_data_port{ant_port}'
            if max_occasions > 1:
                ports_ti['wr_occasion_sel'] = 'ctrl_occ_idx'
        else:
            ports_ti['fi_out_valid'] = f'fi_out_valid_port{ant_port}'
            ports_ti['fi_out_data'] = f'fi_out_data_port{ant_port}'
            if max_occasions > 1:
                ports_ti['fi_occ_sel'] = 'fi_occ_sel'
        if RB_PARALLELISM > 1:
            ports_ti['ti_rb_within_beat'] = 'ti_rb_within_beat'

        if needs_runtime_l0:
            ports_ti['dmrs_typeA_pos_sel'] = 'cfg_dmrs_typeA_pos_sel'
        if needs_runtime_dbl:
            ports_ti['is_double_dmrs'] = 'cfg_is_double_dmrs'
        if needs_runtime_nadd:
            ports_ti['n_additional_dmrs'] = 'cfg_n_additional_dmrs'
        if needs_runtime_nsym:
            ports_ti['pusch_symbol_length'] = 'cfg_pusch_symbol_length'
        if time_interp_method == 'lmmse':
            if TI_LMMSE_COEFF_SOURCE == 'SRAM':
                ports_ti['ti_coeff_wr_en'] = 'ti_coeff_wr_en'
                ports_ti['ti_coeff_wr_addr'] = 'ti_coeff_wr_addr'
                ports_ti['ti_coeff_wr_data'] = 'ti_coeff_wr_data'

        for re_lane in range(TI_RE_PARALLELISM):
            for sym in range(max_pusch_symbols):
                out_wire = f"h_ti_port{ant_port}_re{re_lane}_sym{sym}"
                ports_ti[f'h_time_re{re_lane}_sym{sym}'] = out_wire

        ModuleTIME_INTERP(antenna_port=ant_port, max_occasions=max_occasions, max_num_RBs=max_num_RBs, RB_PARALLELISM=RB_PARALLELISM, TI_RE_PARALLELISM=TI_RE_PARALLELISM, Qu_H_interp_f=Qu_H_interp_f, Qu_H_interp_t=Qu_H_interp_t, time_interp_method=time_interp_method, dmrs_typeA_pos=dmrs_typeA_pos, is_double_dmrs=is_double_dmrs, additional_DMRS_range=additional_DMRS_range, num_symbols_range=list(range(min_pusch_symbols, max_pusch_symbols + 1)), LMMSE_REAL_COEFF=TI_LMMSE_REAL_COEFF, Qu_TI_LMMSE_COEFF=Qu_TI_LMMSE_COEFF, n_additional_dmrs_fixed=max(additional_DMRS_range), f_d_norm=TI_LMMSE_f_d_norm, W_coeffs=TI_LMMSE_W_coeffs, COEFF_SOURCE=TI_LMMSE_COEFF_SOURCE, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG, has_pre_fi_buf=HAS_PRE_FI_BUF, FI_RE_PARALLELISM=FI_RE_PARALLELISM, FI_WINDOW_SIZE=FI_WINDOW_SIZE, ti_ctrl_graph=ti_ctrl_graph, PORTS=ports_ti)

    # =================================================================
    # REGION 5: Latency summary + endmodule
    # =================================================================
    _aln = ls_timing['alignment']
    #/ // ----------------- Latency Arrangement Summary -------------------
    #/ // LS pipeline timing budget (auto-computed by analyze_ls_timing):
    #/ //   Y_PRE path:     `N_CLK_Y_PRE` clk  (min=`_aln['y_pre_min']`, `'padded' if _aln['y_pre_padded'] else 'exact'`)
    #/ //   DMRS_SEQ+OCC:   `N_CLK_DMRS_SEQ`+`ls_timing['N_CLK_OCC']` = `N_CLK_DMRS_SEQ + ls_timing['N_CLK_OCC']` clk  (min=`_aln['dmrs_path_min']`, `'padded' if _aln['dmrs_seq_padded'] else 'exact'`)
    #/ //   LS_ROT:         `N_CLK_LS_ROT` clk
    #/ //   AVERAGING:      `ls_timing['N_CLK_AVG']` clk  (`', '.join(f"cdm{d['group_idx']}={d['depth']}" for d in ls_timing['avg_details'])`)
    #/ //   FREQ_INTERP:    `ls_timing['N_CLK_FREQ']` clk  (`freq_interp_method`)
    #/ //   LS_DRAIN_TOTAL: `LS_DRAIN_CYCLES` clk  (= Y_PRE + LS_ROT + AVG + FREQ)
    #/ //
    #/ // C_INIT timing (bypass mode):
    #/ //   Pipeline depth D = `cinit_timing['D_intrinsic']` clk
    #/ //
    #/ // TI pipeline timing budget:
    #/ //   Core depth:     `TI_PIPELINE_DEPTH` clk  (`time_interp_method`)
    #/ //
    #/ // FSM drain cycle summary:
    #/ //
    #/ // ========== TIMING VERIFICATION REPORT ==========
    #/ // C_INIT bypass:       sym_duration_min=`cinit_timing['sym_duration_min']` >= D_intrinsic=`cinit_timing['D_intrinsic']` ✓
    #/ // LS drain:            EARLY_LS_DRAIN=`EARLY_LS_DRAIN` <= sym_duration=`_sym_duration_min` ✓
    #/ // EARLY_LS safe_head:  `_safe_head` >= 0 ✓
    #/ endmodule
