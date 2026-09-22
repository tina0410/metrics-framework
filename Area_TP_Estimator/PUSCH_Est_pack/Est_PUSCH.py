import sys
import os
import pandas as pd
import numpy as np
import time
import joblib
import warnings
import traceback
import ast
import re
from collections import defaultdict
import math
from typing import Dict, Literal, List, Tuple, Any, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from analyze_timing import ControlSignalGraph
from delay_budget import DelayBudget, COST_ADDER_8B, COST_MUL_8B, DEFAULT_BUDGET, cost_mul
from dmrs_config import (
    DmrsArchConfig, PCDMU_Unified,
    CDM_GROUPS_TYPE1, CDM_GROUPS_TYPE2,
    PILOT_RE_TYPE1, PILOT_RE_TYPE2, PILOT_RE_TYPE3,
    compute_required_re_indices,
    get_cdm_group_for_port,
)
from dmrs_config import InterpTopology
warnings.filterwarnings("ignore")

from top_api import ArchitectureConfig, ArithmeticConfig, ImplementationConfig, ProtocolSpec, QuantKey, resolve_top_config
from analyze_timing import analyze_cinit_timing, analyze_interp_timing, analyze_ls_timing, build_ls_ctrl_graph, build_fi_core_graph, build_ti_ctrl_graph
from EstModule import Est_SUB, Est_ADD, Est_MUL, Est_AT
from PyTU import OfMode, QuMode, QuType
from helpers.config_space import expand_config_space
from v_pilot_symbol_detection import DMRS_POSITION_MAP
from v_csd_helpers import (
    FRAC_BITS,
    _build_all_lin_tables,
    _build_csd_emission_plan,
)

RE_PER_RB = 12              # Resource Elements per Resource Block
LFSR_WIDTH = 31             # Gold sequence LFSR register width (3GPP TS 38.211 §5.2.1)
C_INIT_WIDTH = LFSR_WIDTH   # c_init seed width (same as LFSR width)

# ---------------------------------------------------------------------------
# Architecture Constants
# ---------------------------------------------------------------------------
MAX_FDCDM = 4               # Maximum fdCDM averaging window size
Q_ROUNDING_BITS = 8         # Fractional bits for ×51/256 rounding in linear interpolation

DMRS_TYPE1_RE_PER_RB = 6
DMRS_TYPE2_RE_PER_RB = 4
DMRS_TYPE3_RE_PER_RB = 2

FI_LMMSE_MULTIPLIER_LATENCY = 1

def fi_lmmse_multiplier_latency() -> int:
    """Return the intrinsic latency of the concrete FI multiplier datapath."""

    return FI_LMMSE_MULTIPLIER_LATENCY

def _lin_pilot_wire(re_k, rb_idx, port_remap):
    """Build the pilot input wire name, applying port_remap if provided."""
    mapped = port_remap[re_k] if (port_remap and re_k in port_remap) else re_k
    return f"pilot_rb{rb_idx}_re{mapped}"

def _nn_assignment_map_positions(
    pilot_re: List[int], sample_positions: List[float]
) -> List[Tuple[int, int]]:
    """Map REs to descriptor centroids, including adjacent-RB samples."""

    if len(pilot_re) != len(sample_positions) or not pilot_re:
        raise ValueError("descriptor NN samples must match pilot input labels")
    ordered = sorted(zip(sample_positions, pilot_re))
    candidates = (
        [(ordered[-1][0] - RE_PER_RB, -1)]
        + [(position, label) for position, label in ordered]
        + [(ordered[0][0] + RE_PER_RB, -2)]
    )
    return [
        (
            output_re,
            min(candidates, key=lambda item: (abs(item[0] - output_re), item[0]))[1],
        )
        for output_re in range(RE_PER_RB)
    ]

def _nn_assignment_map(pilot_re: List[int]) -> List[Tuple[int, int]]:
    """
    Compute nearest-neighbor assignment for all 12 REs within one RB.

    For each RE k in [0..11], find the nearest pilot RE.
    For interior REs equidistant from two pilots, select the *lower* pilot
    (convention: left-biased NN, matching 3GPP channel estimation practice).

    Returns a list of 12 tuples (k, nearest_pilot_k).

    Additionally identifies boundary REs that require cross-RB data:
      - REs below the lowest pilot → need highest pilot from previous RB
      - REs above the highest pilot → need lowest pilot from next RB
    These are marked with nearest_pilot = -1 (left boundary) or -2 (right boundary).
    """
    assignment: List[Tuple[int, int]] = []
    pilots_sorted = sorted(pilot_re)
    lowest = pilots_sorted[0]
    highest = pilots_sorted[-1]

    for k in range(RE_PER_RB):
        if k in pilots_sorted:
            assignment.append((k, k))
            continue

        # Find nearest pilot
        left_pilots = [p for p in pilots_sorted if p < k]
        right_pilots = [p for p in pilots_sorted if p > k]

        if left_pilots and right_pilots:
            # Interior: pick closer; tie → lower pilot
            d_left = k - left_pilots[-1]
            d_right = right_pilots[0] - k
            if d_left <= d_right:
                assignment.append((k, left_pilots[-1]))
            else:
                assignment.append((k, right_pilots[0]))
        elif not left_pilots:
            # Below lowest pilot → left boundary (need previous RB)
            assignment.append((k, -1))
        else:
            # Above highest pilot → right boundary (need next RB)
            assignment.append((k, -2))

    return assignment

def _build_nearest_occ_table(
    *,
    dmrs_typeA_pos: int,         # resolved l0 (2 or 3)
    is_double_dmrs: bool,
    n_additional_dmrs: int,
    pusch_symbol_length: int,
) -> list[int]:
    """
    For each target OFDM symbol index (0 .. pusch_symbol_length-1), determine
    which DMRS *occasion* index (0-based) has the nearest pilot symbol.

    For double-DMRS, each occasion spans 2 consecutive symbols; we use the
    midpoint ``(pos + pos+1) / 2 = pos + 0.5`` as the effective pilot position.

    Returns a list of length ``pusch_symbol_length`` with values in
    ``[0, num_occasions-1]``.
    """
    symbol_type = 'double' if is_double_dmrs else 'single'
    key = ('A', symbol_type, n_additional_dmrs)
    entries = DMRS_POSITION_MAP.get(key, [])

    # Find position list for this duration
    pos_raw = [0]  # fallback
    for dur_range, pos_list in entries:
        if pusch_symbol_length in dur_range:
            pos_raw = pos_list
            break

    # Resolve positions: 0 → l0
    l0 = dmrs_typeA_pos
    positions = [l0 if p == 0 else p for p in pos_raw]
    num_occasions = len(positions)

    # Effective pilot symbol position per occasion
    if is_double_dmrs:
        # Midpoint of the 2-symbol pair
        eff_pos = [p + 0.5 for p in positions]
    else:
        eff_pos = [float(p) for p in positions]

    # For each target symbol, find nearest occasion
    nearest = []
    for sym in range(pusch_symbol_length):
        best_occ = 0
        best_dist = abs(sym - eff_pos[0])
        for occ_idx in range(1, num_occasions):
            d = abs(sym - eff_pos[occ_idx])
            if d < best_dist:
                best_dist = d
                best_occ = occ_idx
        nearest.append(best_occ)

    return nearest

def _build_all_nn_tables(
    *,
    dmrs_typeA_pos_options: list[int],    # e.g. [2] or [2, 3]
    is_double_dmrs_options: list[bool],   # e.g. [False] or [False, True]
    additional_DMRS_range: list[int],     # e.g. [0, 2]
    num_symbols_range: list[int],         # e.g. [4, 14] or range(4, 15)
    n_out_syms: int,
) -> dict:
    """
    Build nearest-occ tables for all valid (l0, double, n_add, n_sym) combos.
    Returns dict keyed by (l0, double, n_add, n_sym) → list[int] of length n_sym.
    """
    tables = {}
    for l0 in dmrs_typeA_pos_options:
        for dbl in is_double_dmrs_options:
            for n_add in additional_DMRS_range:
                for n_sym in num_symbols_range:
                    tbl = _build_nearest_occ_table(
                        dmrs_typeA_pos=l0,
                        is_double_dmrs=dbl,
                        n_additional_dmrs=n_add,
                        pusch_symbol_length=n_sym,
                    )
                    # Pad to n_out_syms with last valid value
                    while len(tbl) < n_out_syms:
                        tbl.append(tbl[-1] if tbl else 0)
                    tables[(l0, dbl, n_add, n_sym)] = tbl
    return tables

def _classify_nn_output(pilot_re: List[int]) -> dict:
    """
    Classify all 12 REs into categories for NN interpolation.

    Returns dict with keys:
      'immediate': list of (re_k, source_pilot_k) — outputtable this clock
      'left_boundary': list of re_k — need prev RB's highest pilot
      'right_boundary': list of re_k — need next RB's lowest pilot
    """
    assignment = _nn_assignment_map(pilot_re)
    result = {
        'immediate': [],
        'left_boundary': [],
        'right_boundary': [],
    }
    for k, src in assignment:
        if src == -1:
            result['left_boundary'].append(k)
        elif src == -2:
            result['right_boundary'].append(k)
        else:
            result['immediate'].append((k, src))
    return result

def _classify_assignment(assignment: List[Tuple[int, int]]) -> dict:
    result = {"immediate": [], "left_boundary": [], "right_boundary": []}
    for output_re, source in assignment:
        if source == -1:
            result["left_boundary"].append(output_re)
        elif source == -2:
            result["right_boundary"].append(output_re)
        else:
            result["immediate"].append((output_re, source))
    return result

TI_LMMSE_MULTIPLIER_LATENCY = 1

def _resolve_positions(positions_raw: list[int], l0: int, is_double: bool) -> tuple[int, int, int]:
    """
    Given a raw position list (with 0 = l0 placeholder) and the actual l0 value,
    compute three 14-bit bitmasks:
      - pilot_mask:      bit[i] = 1 if symbol i is a DMRS pilot
      - l_quote_mask:    bit[i] = 1 if symbol i is the *second* symbol of a
                         double-DMRS pair (l' = 1)
      - last_dmrs_mask:  bit[i] = 1 if symbol i belongs to the *last* DMRS
                         occasion in this slot

    For single-symbol DMRS, each position occupies 1 symbol.
    For double-symbol DMRS, each position occupies 2 consecutive symbols
    (pos, pos+1).  The second symbol of each pair has l'=1.
    """
    pilot_mask = 0
    l_quote_mask = 0
    last_dmrs_mask = 0
    max_actual = -1
    for p in positions_raw:
        actual = l0 if p == 0 else p
        if actual < 14:
            pilot_mask |= (1 << actual)
            if actual > max_actual:
                max_actual = actual
        if is_double:
            second = actual + 1
            if second < 14:
                pilot_mask |= (1 << second)
                l_quote_mask |= (1 << second)
    # Mark last DMRS occasion symbols
    # For double DMRS, only mark the l'=1 (second) symbol of the last pair.
    # Marking l'=0 would trigger FSM drain before the second symbol is processed.
    if max_actual >= 0:
        if is_double and max_actual + 1 < 14:
            last_dmrs_mask |= (1 << (max_actual + 1))
        else:
            last_dmrs_mask |= (1 << max_actual)
    return pilot_mask, l_quote_mask, last_dmrs_mask

def build_bitmask_table(
    l0: int,
    is_double: bool,
    additional_DMRS_range: list[int],
    num_symbols_range: list[int],
) -> dict[tuple[int, int], tuple[int, int, int]]:
    """
    Build a dict mapping (n_additional, duration) -> (pilot_mask_14b, l_quote_mask_14b, last_dmrs_mask_14b).
    Only entries for supported durations and additional DMRS counts are generated.
    """
    symbol_type = 'double' if is_double else 'single'
    table: dict[tuple[int, int], tuple[int, int, int]] = {}

    for n_add in additional_DMRS_range:
        key = ('A', symbol_type, n_add)
        entries = DMRS_POSITION_MAP.get(key, [])
        for dur in num_symbols_range:
            # Find matching range
            for dur_range, pos_list in entries:
                if dur in dur_range:
                    pm, lm, ldm = _resolve_positions(pos_list, l0, is_double)
                    table[(n_add, dur)] = (pm, lm, ldm)
                    break
            else:
                # No matching entry -> only front-loaded DMRS
                pm, lm, ldm = _resolve_positions([0], l0, is_double)
                table[(n_add, dur)] = (pm, lm, ldm)
    return table

def ti_lmmse_multiplier_latency() -> int:
    """Return the intrinsic latency of the concrete TI multiplier datapath."""

    return TI_LMMSE_MULTIPLIER_LATENCY

def _analyze_nn_table_structure(max_occasions, dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range, N_OUT_SYMS):
    from v_pilot_symbol_detection import DMRS_POSITION_MAP

    l0_options = [2, 3] if dmrs_typeA_pos == "Hybrid" else (
        [2] if dmrs_typeA_pos == 'pos2' else [3])
    dbl_options = [False, True] if is_double_dmrs == "Hybrid" else [bool(is_double_dmrs)]

    all_tables = []
    for l0 in l0_options:
        for dbl in dbl_options:
            for n_add in additional_DMRS_range:
                for n_sym in num_symbols_range:
                    tbl = _build_nearest_occ_table(
                        dmrs_typeA_pos=l0, is_double_dmrs=dbl,
                        n_additional_dmrs=n_add, pusch_symbol_length=n_sym)
                    while len(tbl) < N_OUT_SYMS:
                        tbl.append(tbl[-1] if tbl else 0)
                    all_tables.append(tuple(tbl))

    unique_tables = list(set(all_tables))
    if len(unique_tables) == 1:
        return True, 0

    # 统计每个符号位上，不同表选的 occasion 是否一致
    n_mux_syms = 0
    for sym in range(N_OUT_SYMS):
        occ_per_table = {tbl[sym] for tbl in unique_tables}
        if len(occ_per_table) > 1:
            n_mux_syms += 1

    return False, n_mux_syms

def time_lmmse_pipeline_depth(max_occasions: int) -> int:
    """Compute total pipeline latency of the time-domain LMMSE core.

    Full-parallel:
        depth = intrinsic multiplier latency + TREE_DEPTH + 1
    """
    tree_depth = math.ceil(math.log2(max(max_occasions, 1))) if max_occasions > 1 else 0
    return ti_lmmse_multiplier_latency() + tree_depth + 1

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

def Est_Delay(DWT, CLK, IS_RST_N):
    if CLK == 0:
        return 1.12 * DWT
    if isinstance(IS_RST_N, bool):
        multiplier = 6.72 if IS_RST_N else 5.88
        return multiplier * DWT * CLK
    else:
        y_pred = 0
        for rst_flag in IS_RST_N:
            multiplier = 6.72 if rst_flag else 5.88
            y_pred += multiplier * DWT
        return y_pred

def Est_FSM(max_pusch_symbols, is_double_dmrs, LS_DRAIN_CYCLES, HAS_COEFF_SRAM):
    ls_drain_cnt_w = max(math.ceil(math.log2(LS_DRAIN_CYCLES + 1)), 1)
    area = 0
    area += 3 * 7.0 + 14.28 + (6.72 + 5.32)*ls_drain_cnt_w + ((6.72 + 15.12)if HAS_COEFF_SRAM else 0)
    return area

def Est_RB_COUNTER(Model_ADD, Sub_db, min_RBs, max_RBs, RB_PARALLELISM):
    area = 0
    counter_width = math.ceil(math.log2(max_RBs)) if max_RBs > 1 else 1
    remainder_width = math.ceil(math.log2(RB_PARALLELISM))
    Qu_num_RBs = QuType(DWT=counter_width, FRAC=0, IF_SIGNED=False)
    Qu_remainder = QuType(DWT=remainder_width, FRAC=0, IF_SIGNED=False)
    Qu_RB_parallelism = QuType(DWT=remainder_width+1, FRAC=0, IF_SIGNED=False)
    if RB_PARALLELISM > 1:
        area += Est_Delay(1, 1, True)
        area += Est_SUB(Model_ADD, Sub_db, Qu_num_RBs.DWT, Qu_num_RBs.FRAC, Qu_num_RBs.IF_SIGNED, Qu_num_RBs.DWT, Qu_num_RBs.FRAC, Qu_num_RBs.IF_SIGNED, Qu_remainder.DWT, Qu_remainder.FRAC, 1)
    area += Est_SUB(Model_ADD, Sub_db, Qu_num_RBs.DWT, Qu_num_RBs.FRAC, Qu_num_RBs.IF_SIGNED, Qu_RB_parallelism.DWT, Qu_RB_parallelism.FRAC, Qu_RB_parallelism.IF_SIGNED, Qu_num_RBs.DWT, Qu_num_RBs.FRAC, 1)
    area += Est_Delay(counter_width, 1, True)
    area += Est_Delay(1, 1, True)
    return area

def Est_SYMBOL_COUNTER(max_pusch_symbols):
    area = 0
    symbol_width  = math.ceil(math.log2(max_pusch_symbols)) if max_pusch_symbols > 1 else 1
    area += 12 + 17.86 * symbol_width
    return area

def Est_PILOT_SYMBOL_DETECT(max_pusch_symbols, dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range):
    area = 0
    W = max(math.ceil(math.log2(max_pusch_symbols)), 1)
    l0_options = [2, 3] if dmrs_typeA_pos == "Hybrid" else \
                 ([2] if dmrs_typeA_pos == 'pos2' else [3])
    dbl_options = [False, True] if is_double_dmrs == "Hybrid" else [bool(is_double_dmrs)]
    all_pilot, all_lq, all_ldm = set(), set(), set()
    for l0 in l0_options:
        for dbl in dbl_options:
            tbl = build_bitmask_table(l0, dbl, additional_DMRS_range, num_symbols_range)
            for (pm, lm, ldm) in tbl.values():
                all_pilot.add(pm); all_lq.add(lm); all_ldm.add(ldm)
    and_all = 0x3FFF
    for m in all_pilot | all_lq | all_ldm:
        and_all &= m
    Z_low = 0
    for i in range(W):
        if (and_all >> i) & 1 == 0:
            Z_low += 1
        else:
            break
    W_eff = W - Z_low

    def A_out(mask_set, is_variable):
        nonzero = [m for m in mask_set if m != 0]
        if not nonzero:
            return 0.0
        n_max = max(bin(m).count('1') for m in nonzero)
        base = 3.5 if n_max == 1 else (4.0 if n_max == 2 else 5.0 + (n_max-2)*1.0)
        return base + (2.0 if is_variable else 0.0)

    is_var_pilot = len(all_pilot) > 1
    is_var_lq    = len(all_lq) > 1
    is_var_ldm   = len(all_ldm) > 1
    A_pilot = A_out(all_pilot, is_var_pilot)
    A_lq    = A_out(all_lq,    is_var_lq)
    A_ldm   = A_out(all_ldm,   is_var_ldm)

    T = 2 if dmrs_typeA_pos == "Hybrid" else 1
    L = 2 if is_double_dmrs == "Hybrid" else 1

    B_eff = 1
    for l0 in l0_options:
        for dbl in dbl_options:
            tbl = build_bitmask_table(l0, dbl, additional_DMRS_range, num_symbols_range)
            # 统计不同 n_add 值对应的掩码集合数
            nadd_masks = {}
            for (na, dur), masks in tbl.items():
                nadd_masks.setdefault(na, set()).add(masks)
            B_eff = max(B_eff, len(nadd_masks))

    area += 3.0
    area += 2.80 * W_eff
    area += A_pilot + A_lq + A_ldm
    area += 3.0 * (T - 1) + 3.0 * (L - 1)
    area += 1.5 * (B_eff - 1)
    return area

def Est_TI_CTRL(max_num_RBs, RB_PARALLELISM, TI_RE_PARALLELISM, TI_PIPELINE_DEPTH, has_pre_fi_buf, max_occasions, FI_WINDOW_SIZE, FI_CYCLES_PER_OCC, FI_CYCLES_PER_OCC_SINGLE, FI_FILL_BEATS, needs_rb_boundary, runtime_n_additional, runtime_double_dmrs):
    area = 0
    def bw(n):
        """位宽 = max(ceil(log2(n)), 1)"""
        return max(math.ceil(math.log2(n)), 1) if n > 1 else 1

    # ---------- 共享派生量 ----------
    W_counter = bw(max_num_RBs)
    DRAIN_CYCLES = max(TI_PIPELINE_DEPTH + 1, 2)
    W_drain = bw(DRAIN_CYCLES + 1)
    W_valid = 1 + TI_PIPELINE_DEPTH
    W_rbw   = bw(RB_PARALLELISM) if RB_PARALLELISM > 1 else 0

    if not has_pre_fi_buf:
        # ==================== POST-FI 模式 ====================
        MAX_RB_BEATS = math.ceil(max_num_RBs / RB_PARALLELISM)
        W_rb = bw(MAX_RB_BEATS)

        N_DRN  = 2 + W_rb + W_rbw + W_drain       # ti_state, rb_beat, rb_within, drain
        N_DRNQ = W_valid                          # valid_shift
        Sigma_W = W_rb + W_rbw + W_drain + W_counter
        C0 = 24.0

    else:
        # ==================== PRE-FI 模式 ====================
        BEATS_PER_WINDOW = FI_WINDOW_SIZE // RB_PARALLELISM
        MAX_WINDOWS = math.ceil(max_num_RBs / FI_WINDOW_SIZE)

        W_win      = bw(MAX_WINDOWS)
        W_occ      = bw(max_occasions)
        W_fiwait   = bw(FI_CYCLES_PER_OCC)
        W_local_rb = bw(BEATS_PER_WINDOW) if BEATS_PER_WINDOW > 1 else 0

        N_DRN  = 2 + W_win + W_occ + W_fiwait + W_local_rb + W_rbw + W_drain
        N_DRNQ = W_valid + 1                      # valid_shift + fi_trigger_r

        if FI_FILL_BEATS > 1:
            N_DRN += bw(FI_FILL_BEATS)            # fi_fill_cnt

        Sigma_W = W_win + W_occ + W_fiwait + W_local_rb + W_rbw + W_drain + W_counter
        C0 = 48.0

    area = C0
    area += 7.00 * N_DRN
    area += 6.72 * N_DRNQ
    area += 4.50 * Sigma_W

    if has_pre_fi_buf:
        if needs_rb_boundary:
            area += 1.5
        if runtime_n_additional:
            area += 2.0
        if runtime_double_dmrs:
            area += 2.0
    return area

def Est_CONTROLLER(Model_ADD, Sub_db, min_num_RBs, max_num_RBs, RB_PARALLELISM, max_pusch_symbols, is_double_dmrs, additional_DMRS_range, dmrs_typeA_pos, num_symbols_range, LS_DRAIN_CYCLES, TI_PIPELINE_DEPTH, TI_RE_PARALLELISM, HAS_COEFF_SRAM, ls_ctrl_graph, freq_interp_method, max_occasions, counter_width, SRAM_ADDR_WIDTH, Qu_symbol_idx, INPUT_MODE, is_enhanced, dmrs_Type, is_ECP, switchable_ports, ANTENNA_PORTS, has_pre_fi_buf, FI_WINDOW_SIZE, FI_CYCLES_PER_OCC, FI_CYCLES_PER_OCC_SINGLE, FI_FILL_BEATS, HAS_TI_GATE=False):
    area = 0
    area_fsm = 0
    area_RB = 0
    area_SYMBOL = 0
    area_PILOT = 0
    area_TI = 0
    _needs_rb_boundary = freq_interp_method in ('nn', 'linear')
    area_fsm = Est_FSM(max_pusch_symbols, is_double_dmrs, LS_DRAIN_CYCLES, HAS_COEFF_SRAM)
    area += area_fsm
    area_RB = Est_RB_COUNTER(Model_ADD, Sub_db, min_num_RBs, max_num_RBs, RB_PARALLELISM)
    area += area_RB
    area_SYMBOL = Est_SYMBOL_COUNTER(max_pusch_symbols)
    area += area_SYMBOL
    area_PILOT = Est_PILOT_SYMBOL_DETECT(max_pusch_symbols, dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range)
    area += area_PILOT
    area_TI = Est_TI_CTRL(max_num_RBs, RB_PARALLELISM, TI_RE_PARALLELISM, TI_PIPELINE_DEPTH, has_pre_fi_buf, max_occasions, FI_WINDOW_SIZE, FI_CYCLES_PER_OCC, FI_CYCLES_PER_OCC_SINGLE, FI_FILL_BEATS, _needs_rb_boundary, (len(additional_DMRS_range) > 1), (is_double_dmrs == "Hybrid"))
    area += area_TI
    for _sig_name, _sig_info in ls_ctrl_graph.build_delay_table().items():
        _n_clk = _sig_info['delay']
        _dwt = _sig_info['width']
        area += Est_Delay(_dwt, _n_clk, False)
    # print(area[0])
    return area

def Est_CFG_LATCH(Qu_slot_idx, counter_width, has_is_double_dmrs, has_is_enhanced, has_dmrs_type, has_typeA_pos, cdm_sel_bits, has_is_ECP, n_add_width, num_ports, N_CLK=1, IF_RST_N=True):
    area = 0
    SI_DWT = Qu_slot_idx.DWT
    fields: list[tuple[str, str, int]] = []
    fields.append(('N_ID',                'cfg_N_ID',                16))
    fields.append(('n_scid',              'cfg_n_scid',              1))
    fields.append(('current_slot_idx',    'cfg_current_slot_idx',    SI_DWT))
    fields.append(('pusch_symbol_length', 'cfg_pusch_symbol_length', 4))
    fields.append(('num_RBs',             'cfg_num_RBs',             counter_width))
    if has_is_double_dmrs:
        fields.append(('is_double_dmrs',            'cfg_is_double_dmrs',             1))
    if has_is_enhanced:
        fields.append(('is_enhanced',               'cfg_is_enhanced',                1))
    if has_dmrs_type:
        fields.append(('dmrs_type',                 'cfg_dmrs_type',                  1))
    if has_typeA_pos:
        fields.append(('dmrs_typeA_pos_sel',        'cfg_dmrs_typeA_pos_sel',         1))
    if cdm_sel_bits > 0:
        fields.append(('num_cdm_groups_without_data', 'cfg_num_cdm_groups_without_data', cdm_sel_bits))
    if has_is_ECP:
        fields.append(('is_ECP',                    'cfg_is_ECP',                     1))
    if n_add_width > 0:
        fields.append(('n_additional_dmrs',         'cfg_n_additional_dmrs',          n_add_width))
    for i in range(num_ports):
        fields.append((f'port_enable_{i}', f'cfg_port_enable_{i}', 1))

    TOTAL_W = sum(w for _, _, w in fields)
    area += Est_Delay(TOTAL_W, N_CLK, IF_RST_N)
    return area

def Est_PORT_ENABLE(antenna_ports, dmrs_Type, is_enhanced, is_double_dmrs, has_ext_enable=True):
    """One-hot ``ports_enable`` generator -- pure buffering of per-port enables.

    Calibrated bit-exact against the 23 synthesized PORT_ENABLE reports:
    the netlist always reduces to one ``LVT_CLKBUFHDV1`` per configured port.
    """
    area = 0
    area += Est_Delay(len(antenna_ports), 0, False)
    return area

def Est_CDM_CTRL(antenna_ports, dmrs_Type, has_ports_enable=False):
    """Drawer popcount / fdCDM-tdCDM decoder -- small combinational block.

    Not bit-exact: measured 2.5..26.9 um^2 over 34 reports.  Model approximates
    it as 2.52 um^2 per configured port (worst absolute error ~12 um^2, i.e.
    below 2e-5 of any TOP area).
    """
    area = 0
    area += 2.52 * max(1, len(antenna_ports))
    return area

_CINIT_MUL_SCALE_BY_WIDTH = {5: 0.896, 7: 0.876, 8: 0.872, 9: 0.520, 10: 0.487, 11: 0.454, 12: 0.431}

def _cinit_mul_scale(dwt_in_1):
    """Calibration of ``Est_MUL`` for the C_INIT stage-3 multiplier.

    The stage-3 multiplier is a narrow unsigned operand times the 17-bit
    ``2*N_ID+1`` value.  The frozen leaf model over-estimates these specific
    multipliers by up to 2.3x and the ratio depends only on the width of the
    first operand: 0.90 at 5 bits, 0.87 at 8 bits, 0.52 at 9 bits and 0.43 at
    12 bits.  The table below is measured against the C_INIT_GENERATION
    reports (real Mul area / Est_MUL); other widths use the nearest entry.
    """
    widths = sorted(_CINIT_MUL_SCALE_BY_WIDTH)
    w = int(dwt_in_1)
    nearest = min(widths, key=lambda x: abs(x - w))
    return _CINIT_MUL_SCALE_BY_WIDTH[nearest]

def Est_C_INIT_GENERATION(Model_MUL, Model_SU_out, SU_in_db, model, Sub_db, Qu_symbol_idx, Qu_slot_idx, N_CLK, dmrs_Type, dmrs_Uplink, is_ECP, ENABLED_CDM_GROUPS_TYPE1, ENABLED_CDM_GROUPS_TYPE2, ENABLED_CDM_GROUPS_TYPE3):
    area = 0
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
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    Qu_stage1_idx = QuType(DWT = Qu_slot_idx.DWT + 4, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    Qu_slot_idx_ext3 = QuType(DWT = Qu_slot_idx.DWT + 3, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    Qu_slot_idx_ext2 = QuType(DWT = Qu_slot_idx.DWT + 2, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    Qu_slot_idx_ext1 = QuType(DWT = Qu_slot_idx.DWT + 1, FRAC = Qu_slot_idx.FRAC, IF_SIGNED = Qu_slot_idx.IF_SIGNED)
    if is_ECP == True:
        budget.add_comb(COST_ADDER_8B, tag="stage1_add_ecp")
        area += Est_ADD(model, Qu_slot_idx_ext3.DWT, Qu_slot_idx_ext3.FRAC, Qu_slot_idx_ext3.IF_SIGNED, Qu_slot_idx_ext2.DWT, Qu_slot_idx_ext2.FRAC, Qu_slot_idx_ext2.IF_SIGNED, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, 0)
    elif is_ECP == False:
        budget.add_comb(2 * COST_ADDER_8B, tag="stage1_add_ncp")
        area += Est_ADD(model, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, Qu_stage1_idx.IF_SIGNED, Qu_slot_idx_ext1.DWT, Qu_slot_idx_ext1.FRAC, Qu_slot_idx_ext1.IF_SIGNED, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, 0)
        area += Est_ADD(model, Qu_slot_idx_ext3.DWT, Qu_slot_idx_ext3.FRAC, Qu_slot_idx_ext3.IF_SIGNED, Qu_slot_idx_ext2.DWT, Qu_slot_idx_ext2.FRAC, Qu_slot_idx_ext2.IF_SIGNED, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, 0)
    elif is_ECP == "Hybrid":
        budget.add_comb(2 * COST_ADDER_8B, tag="stage1_add_hybrid")
        area += Est_ADD(model, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, Qu_stage1_idx.IF_SIGNED, Qu_slot_idx_ext1.DWT, Qu_slot_idx_ext1.FRAC, Qu_slot_idx_ext1.IF_SIGNED, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, 0)
        area += Est_ADD(model, Qu_slot_idx_ext3.DWT, Qu_slot_idx_ext3.FRAC, Qu_slot_idx_ext3.IF_SIGNED, Qu_slot_idx_ext2.DWT, Qu_slot_idx_ext2.FRAC, Qu_slot_idx_ext2.IF_SIGNED, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, 0)
        area += Est_Delay(Qu_stage1_idx.DWT, 1, False)
        budget.add_register(1, tag="stage1_hybrid_mux_reg")
    else:
        raise ValueError("is_ECP must be either True, False, or 'Hybrid'.")
    Qu_symbol_idx_add_1 = QuType(DWT=Qu_symbol_idx.DWT + 1, FRAC=Qu_symbol_idx.FRAC, IF_SIGNED=Qu_symbol_idx.IF_SIGNED)
    Qu_stage2_idx = Qu_stage1_idx
    budget.add_comb(COST_ADDER_8B, tag="stage2_add")
    budget.flush(tag="stage2_pipe")
    area += Est_Delay(Qu_symbol_idx_add_1.DWT, budget.pipeline_depth, False)
    area += Est_ADD(model, Qu_stage1_idx.DWT, Qu_stage1_idx.FRAC, Qu_stage1_idx.IF_SIGNED, Qu_symbol_idx_add_1.DWT, Qu_symbol_idx_add_1.FRAC, Qu_symbol_idx_add_1.IF_SIGNED, Qu_stage2_idx.DWT, Qu_stage2_idx.FRAC, 1)
    area += Est_Delay(16, budget.pipeline_depth, False)
    Qu_stage3_idx = QuType(DWT = 14, FRAC = Qu_stage2_idx.FRAC, IF_SIGNED = Qu_stage2_idx.IF_SIGNED)
    Qu_mul_idx = QuType(DWT = Qu_stage2_idx.DWT + 17, FRAC = Qu_stage2_idx.FRAC, IF_SIGNED = Qu_stage2_idx.IF_SIGNED)
    budget.add_comb(COST_MUL_8B, tag="stage3_mul")
    budget.add_register(2, tag="stage3_mul_pipe")
    area += Est_MUL(Model_MUL, Model_SU_out, SU_in_db, Qu_stage2_idx.DWT, Qu_stage2_idx.FRAC, Qu_stage2_idx.IF_SIGNED, 17, 0, False, Qu_mul_idx.DWT, Qu_mul_idx.FRAC, 2) * _cinit_mul_scale(Qu_stage2_idx.DWT)
    area += Est_Delay(16, 2, False)
    area += Est_Delay(1, budget.pipeline_depth, False)
    if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
        _dmrs_uplink_delayed = False
        for cdm_idx, is_enabled in enumerate(enabled_cdm_groups):
            if cdm_idx >= 2 and dmrs_Uplink == "Hybrid":
                if not _dmrs_uplink_delayed:
                    area += Est_Delay(1, budget.pipeline_depth, False)
                    _dmrs_uplink_delayed = True
            if N_CLK > 0:
                area += Est_Delay(31, N_CLK, True)
    else:
        if N_CLK > 0:
            area += Est_Delay(31, N_CLK, True)
    budget.add_register(N_CLK, tag="stage4_output_reg")
    return area

def Est_Y_PATH_REDUCE(Qu_Data, INPUT_INDEX_LIST, OUTPUT_INDEX_LIST, HAS_VALID_READY=False):
    """Static-routing wire crossbar (Banyan) -- pure buffering, no logic.

    Bit-exact model fitted on the 44 synthesized Y_PATH_REDUCE reports
    (max relative error 0.000%): one ``LVT_CLKBUFHDV1`` (1.12 um^2, i.e.
    ``Est_Delay(DWT, 0, False)``) per output bit, plus two buffers for the
    valid/ready handshake.
    """
    area = 0
    area += Est_Delay(Qu_Data.DWT, 0, False) * len(OUTPUT_INDEX_LIST)
    if HAS_VALID_READY:
        area += 2 * Est_Delay(1, 0, False)
    return area

def Est_Y_RB_ALIGN(Qu_Y, RB_PARALLELISM, RE_PER_RB):
    """Per-RB boundary aligner -- valid-gated passthrough.

    Bit-exact model fitted on the 22 synthesized Y_RB_ALIGN reports
    (max relative error 0.000%): one AND2 per payload bit (``valid ? Y : 0``)
    plus one inverter per RB lane.  (The RB_PARALLELISM == 1 bypass variant is
    not covered by the reports and uses the same expression.)
    """
    A_AND2 = 1.4     # LVT_AND2HDV2
    A_INV = 0.84     # LVT_INHDV1
    RB_BITS = RE_PER_RB * 2 * Qu_Y.DWT
    area = 0
    area += A_AND2 * RB_PARALLELISM * RB_BITS
    area += A_INV * RB_PARALLELISM
    return area

def Est_Y_PRE(model, Sub_db, N_CLK, Y_parallelism, Qu_Y: QuType, Qu_OUT, MAX_CDM_GROUPS):
    area = 0
    Qu_2Y = QuType(Qu_Y.DWT + 1, Qu_Y.FRAC, True)
    Qu_4Y = QuType(Qu_Y.DWT + 2, Qu_Y.FRAC, True)

    Qu_Y_half = QuType(Qu_Y.DWT, Qu_Y.FRAC + 1, True)  # ÷2 via FxMatch FRAC shift

    Qu_T    = QuType(Qu_Y.DWT + 3, Qu_Y.FRAC, True)
    Qu_8T   = QuType(Qu_Y.DWT + 6, Qu_Y.FRAC, True)
    Qu_64T  = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)
    Qu_72T  = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)
    Qu_362Y = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC, True)

    Qu_3Y   = QuType(Qu_Y.DWT + 2, Qu_Y.FRAC, True)
    Qu_48Y  = QuType(Qu_Y.DWT + 6, Qu_Y.FRAC, True)
    Qu_256Y = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC, True)
    Qu_208Y = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC, True)
    Qu_209Y = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC, True)

    Qu_362Y_temp = QuType(Qu_Y.DWT + 9, Qu_Y.FRAC + 9, True)
    Qu_209Y_temp = QuType(Qu_Y.DWT + 8, Qu_Y.FRAC + 9, True)
    for i in range(Y_parallelism):
        for part in ["real", "imag"]:
            area += Est_ADD(model, Qu_4Y.DWT, Qu_4Y.FRAC, Qu_4Y.IF_SIGNED, Qu_Y.DWT, Qu_Y.FRAC, Qu_Y.IF_SIGNED, Qu_T.DWT, Qu_T.FRAC, 0)
            area += Est_ADD(model, Qu_64T.DWT, Qu_64T.FRAC, Qu_64T.IF_SIGNED, Qu_8T.DWT, Qu_8T.FRAC, Qu_8T.IF_SIGNED, Qu_72T.DWT, Qu_72T.FRAC, 0)
            area += Est_ADD(model, Qu_72T.DWT, Qu_72T.FRAC, Qu_72T.IF_SIGNED, Qu_2Y.DWT, Qu_2Y.FRAC, Qu_2Y.IF_SIGNED, Qu_362Y.DWT, Qu_362Y.FRAC, 0)
            area += Est_Delay(Qu_OUT.DWT, 0, False)
            if MAX_CDM_GROUPS >= 2:
                area += Est_Delay(Qu_OUT.DWT, 0, False)
            if MAX_CDM_GROUPS >= 3:
                area += Est_ADD(model, Qu_2Y.DWT, Qu_2Y.FRAC, Qu_2Y.IF_SIGNED, Qu_Y.DWT, Qu_Y.FRAC, Qu_Y.IF_SIGNED, Qu_3Y.DWT, Qu_3Y.FRAC, 0)
                area += Est_SUB(model, Sub_db, Qu_256Y.DWT, Qu_256Y.FRAC, Qu_256Y.IF_SIGNED, Qu_48Y.DWT, Qu_48Y.FRAC, Qu_48Y.IF_SIGNED, Qu_208Y.DWT, Qu_48Y.FRAC, 0)
                area += Est_ADD(model, Qu_208Y.DWT, Qu_208Y.FRAC, Qu_208Y.IF_SIGNED, Qu_Y.DWT, Qu_Y.FRAC, Qu_Y.IF_SIGNED, Qu_209Y.DWT, Qu_209Y.FRAC, 0)
                area += Est_Delay(Qu_OUT.DWT, 0, False)
            area += Est_Delay(Qu_OUT.DWT, N_CLK, False)
    return area

def Est_XOR_TREE(LFSR, N_taps, N_bits, N_CLK, IF_RST_N):
    area = 0
    if N_CLK > 0:
        area += Est_Delay(N_bits, N_CLK, IF_RST_N)
    return area

def Est_DRMS_SEQ_GEN(RB_PARALLELISM, PIPE_CYCLES, IF_RST_N, dmrs_Type, HAS_ENABLE, HAS_CTX, N_CTX_SLOTS):
    area = 0
    rows_x1 = [0] * 31
    for i in range(30):
        rows_x1[i] = (1 << (i + 1)) # The next state bit
    rows_x1[30] = (1 << 3) | (1 << 0) # Feedback: taps at 3 and 0
    rows_x2 = [0] * 31
    re_parallelism_type1 = dmrs_re_parallelism(RB_PARALLELISM, 1)
    re_parallelism_type2 = dmrs_re_parallelism(RB_PARALLELISM, 2)
    re_parallelism_type3 = dmrs_re_parallelism(RB_PARALLELISM, 3)
    re_parallelism = dmrs_re_parallelism(RB_PARALLELISM, dmrs_Type)
    bits_step_type1 = re_parallelism_type1 * 2
    bits_step_type2 = re_parallelism_type2 * 2
    bits_step_type3 = re_parallelism_type3 * 2
    for i in range(30):
        rows_x2[i] = (1 << (i + 1))
    rows_x2[30] = (1 << 3) | (1 << 2) | (1 << 1) | (1 << 0)
    area += Est_XOR_TREE(rows_x2, 1600, 31, 0, True)
    area += Est_Delay(31, 1, False) * 2
    if dmrs_Type == 1:
        area += Est_XOR_TREE(rows_x1, bits_step_type1, 31, 0, False)
        area += Est_XOR_TREE(rows_x2, bits_step_type1, 31, 0, False)
    elif dmrs_Type == 2:
        area += Est_XOR_TREE(rows_x1, bits_step_type2, 31, 0, False)
        area += Est_XOR_TREE(rows_x2, bits_step_type2, 31, 0, False)
    elif dmrs_Type == 3:
        area += Est_XOR_TREE(rows_x1, bits_step_type3, 31, 0, False)
        area += Est_XOR_TREE(rows_x2, bits_step_type3, 31, 0, False)
    else:
        area += Est_XOR_TREE(rows_x1, bits_step_type1, 31, 0, False)
        area += Est_XOR_TREE(rows_x2, bits_step_type1, 31, 0, False)
        area += Est_XOR_TREE(rows_x1, bits_step_type2, 31, 0, False)
        area += Est_XOR_TREE(rows_x2, bits_step_type2, 31, 0, False)
    need_expand = (2 * re_parallelism > 31)
    if need_expand:
        n_out_bits = 2 * re_parallelism
        area += Est_XOR_TREE(rows_x1, 0, n_out_bits, 0, False)
        area += Est_XOR_TREE(rows_x2, 0, n_out_bits, 0, False)
    if PIPE_CYCLES > 0:
        for i in range(re_parallelism):
            area += Est_Delay(2, PIPE_CYCLES, IF_RST_N)
    return area

def Est_W_F_CALC(dmrs_type, cdm_group, is_enhanced, antenna_ports, re_phy_indices, re_logic_indices):
    area = 0
    return area

def Est_OCC(N_CLK, dmrs_Type, antenna_ports, is_double_dmrs):
    area = 0
    if N_CLK > 0:
        area += Est_Delay(2, N_CLK, True)
    return area

def Est_LS_ROT(model, Sub_db, parallelism, Qu_IN, Qu_OUT, N_CLK):
    area = 0
    Qu_EXT = QuType(DWT=Qu_IN.DWT + 1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
    Qu_SUM = QuType(DWT=Qu_IN.DWT + 2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
    for i in range(parallelism):
        area += Est_SUB(model, Sub_db, Qu_EXT.DWT, Qu_EXT.FRAC, Qu_EXT.IF_SIGNED, Qu_EXT.DWT, Qu_EXT.FRAC, Qu_EXT.IF_SIGNED, Qu_SUM.DWT, Qu_SUM.FRAC, 0)
        area += Est_ADD(model, Qu_EXT.DWT, Qu_EXT.FRAC, Qu_EXT.IF_SIGNED, Qu_EXT.DWT, Qu_EXT.FRAC, Qu_EXT.IF_SIGNED, Qu_SUM.DWT, Qu_SUM.FRAC, 0)
        area += Est_Delay(Qu_OUT.DWT, 0, False) * 2
        area += Est_Delay(2 * Qu_OUT.DWT, N_CLK, False)
    return area

def Est_Counter(DWT, STEP, IF_RST_N, HAS_CLEAR, HAS_WRAP):
    """Small up-counter (DRN flops + carry chain + enable gating).

    The synthesized area depends only on the counter width; the three
    calibrated points below come from the Counter reports (widths 3/4/5),
    other widths are linearly interpolated / extrapolated.
    """
    _AREA_BY_WIDTH = {3: 35.56, 4: 47.60, 5: 64.96}
    w = max(int(DWT), 1)
    if w in _AREA_BY_WIDTH:
        return _AREA_BY_WIDTH[w]
    xs = sorted(_AREA_BY_WIDTH)
    x0, x1 = (xs[0], xs[1]) if w < xs[0] else (xs[-2], xs[-1])
    slope = (_AREA_BY_WIDTH[x1] - _AREA_BY_WIDTH[x0]) / (x1 - x0)
    return _AREA_BY_WIDTH[x0] + slope * (w - x0)

def Est_SRAM(DWT, DEPTH, MODE, IF_RST_N):
    """Behavioural register-file SRAM (SP/DP) as used inside AVERAGING.

    Cost model = A_bit * DWT * DEPTH, with A_bit least-squares fitted on the
    AVERAGING blocks of the 24 TOP designs (mean residual +2.4%).
    """
    A_bit = 10.65
    if MODE == 'DP':
        A_bit *= 1.3
    area = A_bit * DWT * DEPTH
    return area

def Est_AVERAGING(model, Qu_IN, Qu_OUT, IF_RST_N, RB_PARALLELISM, dmrs_Type, cdm_group, fdCDM, tdCDM, max_num_RBs, SRAM_MACRO_CONFIG, HAS_ENABLE):
    area = 0
    if dmrs_Type == 1 or dmrs_Type == "Hybrid":
        pilot_re_t1 = PILOT_RE_TYPE1[cdm_group]
        n_pilots_t1 = len(pilot_re_t1)  # 6
    if dmrs_Type == 2 or dmrs_Type == "Hybrid":
        pilot_re_t2 = PILOT_RE_TYPE2[cdm_group]
        n_pilots_t2 = len(pilot_re_t2)  # 4
    if dmrs_Type == 3:
        from dmrs_config import PILOT_RE_TYPE3
        pilot_re_t3 = PILOT_RE_TYPE3[cdm_group]
        n_pilots_t3 = len(pilot_re_t3)  # 2
    if dmrs_Type == 1:
        N_PILOTS = n_pilots_t1  # 6
    elif dmrs_Type == 2:
        N_PILOTS = n_pilots_t2  # 4
    elif dmrs_Type == 3:
        N_PILOTS = n_pilots_t3  # 2
    else:  # Hybrid
        N_PILOTS = max(n_pilots_t1, n_pilots_t2)  # 6
    n_l1 = N_PILOTS // 2
    DWT_L1 = Qu_IN.DWT + 1
    DWT_L2 = Qu_IN.DWT + 2
    DWT_TD = Qu_IN.DWT + 1
    USE_MACRO = SRAM_MACRO_CONFIG is not None
    base_sram_depth = math.ceil(max_num_RBs / RB_PARALLELISM)
    SRAM_DEPTH = base_sram_depth
    SRAM_ADDR_WIDTH = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1
    if fdCDM == "Hybrid":
        MAX_FDCDM = 4
    else:
        MAX_FDCDM = fdCDM
    need_cross_rb_t1 = (MAX_FDCDM == 4 and dmrs_Type in (1, "Hybrid")
                        and RB_PARALLELISM % 2 != 0)
    need_td_avg = (tdCDM == 2 or tdCDM == "Hybrid")
    for rb in range(RB_PARALLELISM):
        for j in range(n_l1):
            Qu_L1 = QuType(DWT=Qu_IN.DWT, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L1_O = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            area += Est_ADD(model, Qu_L1.DWT, Qu_L1.FRAC, Qu_L1.IF_SIGNED, Qu_L1.DWT, Qu_L1.FRAC, Qu_L1.IF_SIGNED, Qu_L1_O.DWT, Qu_L1_O.FRAC, 0)
        if MAX_FDCDM >= 4 and n_l1 >= 2:
            Qu_L2 = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L2_O = QuType(DWT=DWT_L2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            area += Est_ADD(model, Qu_L2.DWT, Qu_L2.FRAC, Qu_L2.IF_SIGNED, Qu_L2.DWT, Qu_L2.FRAC, Qu_L2.IF_SIGNED, Qu_L2_O.DWT, Qu_L2_O.FRAC, 0)
        if MAX_FDCDM >= 4 and n_l1 == 3:
            Qu_L2_1 = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L2_1_O = QuType(DWT=DWT_L2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            area += Est_ADD(model, Qu_L2_1.DWT, Qu_L2_1.FRAC, Qu_L2_1.IF_SIGNED, Qu_L2_1.DWT, Qu_L2_1.FRAC, Qu_L2_1.IF_SIGNED, Qu_L2_1_O.DWT, Qu_L2_1_O.FRAC, 0)
        if need_cross_rb_t1:
            if HAS_ENABLE:
                pass
            else:
                area += Est_Delay(DWT_L1, 1, IF_RST_N)
            Qu_L2 = QuType(DWT=DWT_L1, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            Qu_L2_O = QuType(DWT=DWT_L2, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
            area += Est_ADD(model, Qu_L2.DWT, Qu_L2.FRAC, Qu_L2.IF_SIGNED, Qu_L2.DWT, Qu_L2.FRAC, Qu_L2.IF_SIGNED, Qu_L2_O.DWT, Qu_L2_O.FRAC, 0)
        for k in range(N_PILOTS):
            if HAS_ENABLE:
                pass
            else:
                area += Est_Delay(Qu_IN.DWT, 1, IF_RST_N)
    if need_td_avg:
        area += Est_Delay(1, 1, IF_RST_N) * 3
        if HAS_ENABLE:
            area += Est_Delay(1, 1, IF_RST_N)
        area += Est_Counter(SRAM_ADDR_WIDTH, 1, IF_RST_N, True, False)
        for rb in range(RB_PARALLELISM):
            for k in range(N_PILOTS):
                if not USE_MACRO:
                    area += Est_SRAM(Qu_IN.DWT, SRAM_DEPTH, 'SP', False)
                Qu_TD = QuType(DWT=Qu_IN.DWT, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
                Qu_TD_O = QuType(DWT=DWT_TD, FRAC=Qu_IN.FRAC, IF_SIGNED=True)
                area += Est_Delay(Qu_IN.DWT, 1, IF_RST_N)
                area += Est_ADD(model, Qu_TD.DWT, Qu_TD.FRAC, Qu_TD.IF_SIGNED, Qu_TD.DWT, Qu_TD.FRAC, Qu_TD.IF_SIGNED, Qu_TD_O.DWT, Qu_TD_O.FRAC, 0)
    for rb in range(RB_PARALLELISM):
        area += Est_Delay(Qu_OUT.DWT, 0, False)
    return area

def Est_LS(model, Sub_db, Qu_Y, QU_H_LS, QU_MODE_LS, OF_MODE_LS, N_CLK_Y_PRE, N_CLK_DMRS_SEQ, N_CLK_LS_ROT, dmrs_Type, dmrs_Uplink, is_ECP, is_enhanced, is_double_dmrs, antenna_ports, TRUE_INDEX_LIST, switchable_ports, RB_PARALLELISM, fdCDM, tdCDM, max_num_RBs, HAS_LFSR_CTX, HAS_AVG_SYM_SWITCH, N_LFSR_CTX_SLOTS, SRAM_MACRO_CONFIG, REPLAY_TOKEN_DWT, N_CLK_AVG, HAS_LFSR_ENABLE=True):
    area = 0
    arch_config = DmrsArchConfig(antenna_ports=antenna_ports, dmrs_Type=dmrs_Type, TRUE_INDEX_LIST=TRUE_INDEX_LIST,)
    MAX_CDM_GROUPS = arch_config.MAX_CDM_GROUPS
    pcdmu_instances = arch_config.pcdmu_instances
    ENABLED_CDM_GROUPS_TYPE1 = arch_config.ENABLED_CDM_GROUPS_TYPE1
    ENABLED_CDM_GROUPS_TYPE2 = arch_config.ENABLED_CDM_GROUPS_TYPE2
    ENABLED_CDM_GROUPS_TYPE3 = arch_config.ENABLED_CDM_GROUPS_TYPE3
    Y_PARALLELISM = len(TRUE_INDEX_LIST)
    enabled_cdm_groups_union: list[bool] = []
    _pipe_cycles = max(N_CLK_DMRS_SEQ - 1, 0)
    _strb_signal = 'c_init_strb'
    _avg_strb_signal = 'avg_sym_switch' if HAS_AVG_SYM_SWITCH else _strb_signal
    needs_rb_idx = False
    if is_enhanced == True or is_enhanced == "Hybrid":
        for pcdmu in pcdmu_instances:
            if pcdmu.has_type1:
                needs_rb_idx = True
                break
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
    area += Est_Y_PRE(
        model, Sub_db, N_CLK_Y_PRE, Y_PARALLELISM, Qu_Y, QU_H_LS,
        MAX_CDM_GROUPS,
    )
    if dmrs_Uplink == True or dmrs_Uplink == "Hybrid":
        for cdm_idx in range(len(enabled_cdm_groups_union)):
            if enabled_cdm_groups_union[cdm_idx]:
                area += Est_DRMS_SEQ_GEN(RB_PARALLELISM, _pipe_cycles, True, dmrs_Type, HAS_LFSR_ENABLE, HAS_LFSR_CTX, N_LFSR_CTX_SLOTS)
    else:
        area += Est_DRMS_SEQ_GEN(RB_PARALLELISM, _pipe_cycles, True, dmrs_Type, HAS_LFSR_ENABLE, HAS_LFSR_CTX, N_LFSR_CTX_SLOTS)
    if needs_rb_idx:
        area += Est_Delay(1, N_CLK_DMRS_SEQ, False)
    _need_occ_lquote = (is_double_dmrs == True or is_double_dmrs == "Hybrid")
    if _need_occ_lquote:
        area += Est_Delay(1, N_CLK_DMRS_SEQ, False)
    for pcdmu in pcdmu_instances:
        if pcdmu.is_hybrid:
            area += Est_W_F_CALC(1, pcdmu.group_idx, is_enhanced, pcdmu.type1_antenna_ports, pcdmu.type1_re_phy_indices, list(range(len(pcdmu.type1_re_phy_indices))))
            area += Est_W_F_CALC(2, pcdmu.group_idx, is_enhanced, pcdmu.type2_antenna_ports, pcdmu.type2_re_phy_indices, list(range(len(pcdmu.type2_re_phy_indices))))
        else:
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
            area += Est_W_F_CALC(active_type, pcdmu.group_idx, is_enhanced, active_ports, active_re_phy, list(range(len(active_re_phy))))
        for re_idx in range(pcdmu.max_re_count):
            if pcdmu.is_hybrid:
                occ_dmrs_type = "Hybrid"
            else:
                occ_dmrs_type = 1 if pcdmu.has_type1 else 2
            area += Est_OCC(1, occ_dmrs_type, pcdmu.unified_antenna_ports, is_double_dmrs)
            area += Est_LS_ROT(model, Sub_db, len(pcdmu.unified_antenna_ports), QU_H_LS, QU_H_LS, N_CLK_LS_ROT)
    for pcdmu in pcdmu_instances:
        g = pcdmu.group_idx
        if pcdmu.has_type1 and pcdmu.has_type2:
            avg_dmrs_type = dmrs_Type  # could be "Hybrid" or int
        elif pcdmu.has_type1:
            avg_dmrs_type = 1
        elif pcdmu.has_type3:
            avg_dmrs_type = 3
        else:
                    avg_dmrs_type = 2
        need_td_avg = (tdCDM.get(g) == 2 or tdCDM.get(g) == 'Hybrid')
        _fdCDM_g = fdCDM.get(g, 2) # Get the fdCDM configuration for CDM group g
        _tdCDM_g = tdCDM.get(g, 1)
        MAX_FDCDM_G = 4 if _fdCDM_g == 'Hybrid' else (_fdCDM_g if isinstance(_fdCDM_g, int) else 4)
        need_cross_rb_g = (MAX_FDCDM_G == 4) and (avg_dmrs_type == 1 or avg_dmrs_type == 'Hybrid')
        _avg_strb_delay = N_CLK_Y_PRE + N_CLK_LS_ROT - 1
        _avg_lquote_delay = N_CLK_Y_PRE + N_CLK_LS_ROT
        _need_avg_strb = need_td_avg or need_cross_rb_g
        if HAS_AVG_SYM_SWITCH:
            area += Est_Delay(1, _avg_lquote_delay, False)
        if _need_avg_strb:
            area += Est_Delay(1, _avg_strb_delay, False)
        if need_td_avg:
            area += Est_Delay(1, _avg_lquote_delay, False)
        for ant_port in pcdmu.unified_antenna_ports:
            for part in ('real', 'imag'):
                area += Est_AVERAGING(model, QU_H_LS, QU_H_LS, True, RB_PARALLELISM, avg_dmrs_type, g, _fdCDM_g, _tdCDM_g, max_num_RBs, SRAM_MACRO_CONFIG, HAS_AVG_SYM_SWITCH)
    if REPLAY_TOKEN_DWT > 0:
        _replay_token_delay = N_CLK_Y_PRE + N_CLK_LS_ROT + N_CLK_AVG
        area += Est_Delay(1, _replay_token_delay, True)
        area += Est_Delay(REPLAY_TOKEN_DWT, _replay_token_delay, True)
    return area

def Est_COEFF_SRAM(N_OUTPUT, N_PILOTS, Qu_COEFF, COEFF_STORAGE, is_hybrid, rom_data_bank0, rom_data_bank1, BEAT_MODE, N_PILOTS_PER_BEAT, FILL_BEATS):
    area = 0
    return area

def Est_CORE_NN_INTERP(IF_RST_N, RB_PARALLELISM, Qu_H, pilot_re, dmrs_Type, pilot_re_t1, pilot_re_t2, compact_t2_slots, sample_positions, has_next_rb_lowest, has_prev_rb_highest):
    area = 0
    is_hybrid = (dmrs_Type == "Hybrid" and pilot_re_t1 is not None and pilot_re_t2 is not None)
    COMPLEX_DWT = 2 * Qu_H.DWT
    _use_compact = is_hybrid and compact_t2_slots is not None
    pilot_re_sorted = sorted(pilot_re)
    lowest_pilot_t1 = pilot_re_sorted[0]
    highest_pilot_t1 = pilot_re_sorted[-1]
    lowest_pilot_t2 = pilot_re_sorted[0]
    highest_pilot_t2 = pilot_re_sorted[-1]
    if is_hybrid:
        assert pilot_re_t1 is not None and pilot_re_t2 is not None
        _re_t1 = sorted(pilot_re_t1)
        _re_t2 = sorted(pilot_re_t2)
    _t2_port_map = {}
    if is_hybrid and _use_compact:
        assert compact_t2_slots is not None
        for t2_idx, slot in enumerate(compact_t2_slots):
            _t2_port_map[_re_t2[t2_idx]] = pilot_re_sorted[slot]
    if is_hybrid:
        pilot_re_t1 = _re_t1
        pilot_re_t2 = _re_t2

        lowest_pilot_t1 = pilot_re_t1[0]
        highest_pilot_t1 = pilot_re_t1[-1]
        lowest_pilot_t2 = pilot_re_t2[0]
        highest_pilot_t2 = pilot_re_t2[-1]

        # Union extremes (used for shared registrations)
        lowest_pilot = pilot_re_sorted[0]
        highest_pilot = pilot_re_sorted[-1]
    else:
        lowest_pilot = pilot_re_sorted[0]
        highest_pilot = pilot_re_sorted[-1]
    area += Est_Delay(1, 1, IF_RST_N) * 2
    if RB_PARALLELISM > 1:
        area += Est_Delay(RB_PARALLELISM, 1, IF_RST_N)
    def _gen_nn_datapath(tag, sub_pilot_re, sub_lowest, sub_highest, rb, output_prefix, port_remap=None, assignment_override=None):
        sarea = 0
        sub_nn = (
            _classify_assignment(assignment_override)
            if assignment_override is not None
            else _classify_nn_output(sub_pilot_re)
        )
        sub_imm = sub_nn['immediate']
        sub_left = sub_nn['left_boundary']
        sub_right = sub_nn['right_boundary']
        pfx = f"{tag}_rb{rb}" if tag else f"rb{rb}"
        prev_h = f"prev_highest_{pfx}"
        if has_prev_rb_highest and (RB_PARALLELISM == 1 or rb == 0):
            pass
        elif RB_PARALLELISM > 1 and rb > 0:
            sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
        else:
            sarea += Est_Delay(COMPLEX_DWT, 2, IF_RST_N)
        sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
        for re_k, src_k in sub_imm:
            sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
        if sub_left:
            sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
        if sub_right:
            if RB_PARALLELISM > 1 and rb < RB_PARALLELISM - 1:
                sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
        return sarea
    for rb in range(RB_PARALLELISM):
        if is_hybrid:
            area += _gen_nn_datapath('t1', pilot_re_t1, lowest_pilot_t1, highest_pilot_t1, rb, f"nn_t1_rb{rb}")
            area += _gen_nn_datapath('t2', pilot_re_t2, lowest_pilot_t2, highest_pilot_t2, rb, f"nn_t2_rb{rb}", port_remap=_t2_port_map if _use_compact else None)
        else:
            area += _gen_nn_datapath('', pilot_re_sorted, lowest_pilot, highest_pilot, rb, f"nn_single_rb{rb}", assignment_override=(_nn_assignment_map_positions(pilot_re_sorted, sample_positions) if sample_positions is not None else None),)
    return area

def Est_CORE_LIN_INTERP(Model_ADD, Sub_db, IF_RST_N, RB_PARALLELISM, Qu_H : QuType, pilot_re, dmrs_Type, pilot_re_t1, pilot_re_t2, compact_t2_slots, sample_positions, has_next_rb_lowest, has_prev_rb_highest):
    area = 0
    DWT = Qu_H.DWT
    FRAC = Qu_H.FRAC
    COMPLEX_DWT = 2 * DWT
    SUM_W = DWT + 1
    Qu_diff = QuType(DWT + 1, FRAC, True)
    Qu_d_s4 = QuType(DWT + 5, FRAC, True)
    Qu_x17  = QuType(DWT + 6, FRAC, True)
    Qu_x17s1 = QuType(DWT + 7, FRAC, True)
    Qu_x51  = QuType(DWT + 8, FRAC, True)
    Qu_step = QuType(DWT + 8, FRAC + 8, True)
    # ``pfx`` is branch/RB-specific and is assigned inside the loop below.
    # The signal name is only descriptive for this area estimator, so use a
    # neutral initial name until each branch establishes its local prefix.
    prev_h = "prev_h"
    is_hybrid = (dmrs_Type == "Hybrid" and pilot_re_t1 is not None and pilot_re_t2 is not None)
    _re_t1 = sorted(pilot_re_t1) if is_hybrid else []
    _re_t2 = sorted(pilot_re_t2) if is_hybrid else []
    area += Est_Delay(1, 2, IF_RST_N) * 2
    pilot_re_sorted = sorted(pilot_re)
    if RB_PARALLELISM > 1:
        area += Est_Delay(RB_PARALLELISM, 2, IF_RST_N) * 2
    def _gen_scaled_add(d):
        sarea = 0
        if d == 1:
            sarea += Est_ADD(Model_ADD, Qu_H.DWT, Qu_H.FRAC, Qu_H.IF_SIGNED, Qu_step.DWT, Qu_step.FRAC, Qu_step.IF_SIGNED, Qu_H.DWT, Qu_H.FRAC, 0)
        elif d == 2:
            Qu_step_d2 = QuType(Qu_step.DWT + 1, Qu_step.FRAC, True)
            sarea += Est_ADD(Model_ADD, Qu_H.DWT, Qu_H.FRAC, Qu_H.IF_SIGNED, Qu_step_d2.DWT, Qu_step_d2.FRAC, Qu_step_d2.IF_SIGNED, Qu_H.DWT, Qu_H.FRAC, 0)
        elif d == 3:
            Qu_x51s1_d3 = QuType(Qu_x51.DWT + 1, Qu_x51.FRAC, True)
            Qu_x51x3 = QuType(Qu_x51.DWT + 2, Qu_x51.FRAC, True)
            Qu_step_d3 = QuType(Qu_x51x3.DWT, Qu_x51x3.FRAC + 8, True)
            sarea += Est_ADD(Model_ADD, Qu_x51.DWT, Qu_x51.FRAC, Qu_x51.IF_SIGNED, Qu_x51s1_d3.DWT, Qu_x51s1_d3.FRAC, Qu_x51s1_d3.IF_SIGNED, Qu_x51x3.DWT, Qu_x51x3.FRAC, 0)
            sarea += Est_ADD(Model_ADD, Qu_H.DWT, Qu_H.FRAC, Qu_H.IF_SIGNED, Qu_step_d3.DWT, Qu_step_d3.FRAC, Qu_step_d3.IF_SIGNED, Qu_H.DWT, Qu_H.FRAC, 0)
        elif d == 4:
            Qu_step_d4 = QuType(Qu_step.DWT + 2, Qu_step.FRAC, True)
            sarea += Est_ADD(Model_ADD, Qu_H.DWT, Qu_H.FRAC, Qu_H.IF_SIGNED, Qu_step_d4.DWT, Qu_step_d4.FRAC, Qu_step_d4.IF_SIGNED, Qu_H.DWT, Qu_H.FRAC, 0)
        return sarea
    def _gen_x51_chain(chain_tag, h_l_r, h_l_i, h_r_r, h_r_i):
        sarea = 0
        for pt, h_l, h_r in [('r', h_l_r, h_r_r), ('i', h_l_i, h_r_i)]:
            sarea += Est_SUB(Model_ADD, Sub_db, Qu_H.DWT, Qu_H.FRAC, Qu_H.IF_SIGNED, Qu_H.DWT, Qu_H.FRAC, Qu_H.IF_SIGNED, Qu_diff.DWT, Qu_diff.FRAC, 0)
            sarea += Est_ADD(Model_ADD, Qu_diff.DWT, Qu_diff.FRAC, Qu_diff.IF_SIGNED, Qu_d_s4.DWT, Qu_d_s4.FRAC, Qu_d_s4.IF_SIGNED, Qu_x17.DWT, Qu_x17.FRAC, 1)
            sarea += Est_ADD(Model_ADD, Qu_x17.DWT, Qu_x17.FRAC, Qu_x17.IF_SIGNED, Qu_x17s1.DWT, Qu_x17s1.FRAC, Qu_x17s1.IF_SIGNED, Qu_x51.DWT, Qu_x51.FRAC, 0)
        return sarea
    def _gen_lin_datapath(tag, sub_pilot_re, rb, out_pfx, port_remap=None):
        sp = sorted(sub_pilot_re)
        lo = sp[0]
        hi = sp[-1]
        sub_topo = InterpTopology(sp)
        sub_nn = _classify_nn_output(sp)
        sub_left = sub_nn['left_boundary']
        sub_right = sub_nn['right_boundary']
        sub_cross_gap = (RE_PER_RB + lo) - hi
        sub_pairs: dict = defaultdict(list)
        for (re_k, lp, rp) in sub_topo.interior_re:
            sub_pairs[(lp, rp)].append(re_k)

        pfx = f"{tag}_rb{rb}" if tag else f"rb{rb}"
        reg_h = f"reg_h_{pfx}"
        sarea = 0
        if has_prev_rb_highest and (RB_PARALLELISM == 1 or rb == 0):
            pass
        elif RB_PARALLELISM > 1 and rb > 0:
            pass
        else:
            sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
        sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N) * 3
        for k in sp:
            sarea += Est_Delay(COMPLEX_DWT, 2, IF_RST_N)
        for (lp, rp), re_list in sub_pairs.items():
            gap = rp - lp
            h_l_base_r = f"{pfx}_pil{lp}_r"
            h_l_base_i = f"{pfx}_pil{lp}_i"
            h_r_base_r = f"{pfx}_pil{rp}_r"
            h_r_base_i = f"{pfx}_pil{rp}_i"
            pair_tag = f"{pfx}_p{lp}_{rp}"
            if gap == 2:
                for re_k in re_list:
                    sarea += Est_Delay(COMPLEX_DWT, 2, IF_RST_N)
            elif gap == 5:
                sarea += _gen_x51_chain(pair_tag, h_l_base_r, h_l_base_i, h_r_base_r, h_r_base_i)
                h_l_q_r = f"h_l_q_{pair_tag}_r"
                h_l_q_i = f"h_l_q_{pair_tag}_i"
                sarea += Est_Delay(DWT, 1, IF_RST_N) * 2
                for re_k in re_list:
                    d = re_k - lp
                    for pt, h_l in [('r', h_l_q_r), ('i', h_l_q_i)]:
                        sarea += _gen_scaled_add(d)
                    sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
            else:
                for re_k in re_list:
                    sarea += Est_Delay(COMPLEX_DWT, 2, IF_RST_N)
        if sub_left:
            sarea += Est_Delay(COMPLEX_DWT, 2, IF_RST_N)
            if sub_cross_gap == 5:
                lbnd_tag = f"lbnd_{pfx}"
                sarea += _gen_x51_chain(lbnd_tag, prev_h + '_r', prev_h + '_i', f"{pfx}_pil{lo}_r", f"{pfx}_pil{lo}_i")
                for re_k in sub_left:
                    d = re_k + RE_PER_RB - hi
                    for pt in ['r', 'i']:
                        sarea += _gen_scaled_add(d)
                    sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
            elif sub_cross_gap == 2:
                _lb2_reg_depth = 2
                for re_k in sub_left:
                    sarea += Est_Delay(COMPLEX_DWT, _lb2_reg_depth, IF_RST_N)
            else:
                pass
        if sub_right:
            if RB_PARALLELISM > 1 and rb < RB_PARALLELISM - 1:
                sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
            next_lo_r = f"next_lo_{pfx}_r"
            next_lo_i = f"next_lo_{pfx}_i"
            if sub_cross_gap == 5:
                rbnd_tag = f"rbnd_{pfx}"
                sarea += _gen_x51_chain(rbnd_tag, reg_h + '_r', reg_h + '_i', next_lo_r, next_lo_i)
                for re_k in sub_right:
                    d = re_k - hi
                    for pt in ['r', 'i']:
                        sarea += _gen_scaled_add(d)
            elif sub_cross_gap == 2:
                for re_k in sub_right:
                    sarea += Est_Delay(COMPLEX_DWT, 1, IF_RST_N)
            else:
                _extra_delay = 1 if (RB_PARALLELISM > 1 and rb < RB_PARALLELISM - 1) else 2
                for re_k in sub_right:
                    d_high = re_k - hi
                    d_next = (RE_PER_RB + lo) - re_k
                    if d_high <= d_next:
                        pass
                    else:
                        sarea += Est_Delay(COMPLEX_DWT, _extra_delay, IF_RST_N)
        return sarea
    for rb in range(RB_PARALLELISM):
        _use_compact = is_hybrid and compact_t2_slots is not None
        _t2_port_map = {}
        if is_hybrid and _use_compact:
            assert compact_t2_slots is not None
            for t2_idx, slot in enumerate(compact_t2_slots):
                _t2_port_map[_re_t2[t2_idx]] = pilot_re_sorted[slot]
        if is_hybrid:
            area += _gen_lin_datapath('t1', _re_t1, rb, f"lin_t1_rb{rb}")
            area += _gen_lin_datapath('t2', _re_t2, rb, f"lin_t2_rb{rb}", port_remap=_t2_port_map if _use_compact else None)
        else:
            area += _gen_lin_datapath('', pilot_re_sorted, rb, f"lin_single_rb{rb}")
    return area

def Est_CORE_LMMSE_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, IF_RST_N, LMMSE_P, RB_PARALLELISM, Qu_H_LS, Qu_H, pilot_re, output_re, dmrs_Type, Qu_COEFF, REAL_COEFF, W_matrix_override, tau_rms, snr_linear, COEFF_SOURCE, channel_model, delay_spread, scs, pilot_re_t1, pilot_re_t2, compact_t2_slots, compact_zero_slots, FI_RE_PARALLELISM, has_pre_fi_buf, fi_core_graph):
    area = 0
    N_PILOTS_PER_RB = len(pilot_re)
    N_OUTPUT_PER_RB = len(output_re)
    N_PILOTS = N_PILOTS_PER_RB * LMMSE_P
    N_OUTPUT = N_OUTPUT_PER_RB * LMMSE_P
    N_PILOTS_PER_BEAT = N_PILOTS_PER_RB * RB_PARALLELISM
    COEFF_DWT = Qu_COEFF.DWT
    COEFF_FRAC = Qu_COEFF.FRAC
    COMP_DWT_IN = Qu_H_LS.DWT
    COMP_DWT_OUT = Qu_H.DWT
    CPLX_DWT_IN = 2 * COMP_DWT_IN
    CPLX_DWT_OUT = 2 * COMP_DWT_OUT
    PROD_DWT = COMP_DWT_IN + COEFF_DWT
    PROD_FRAC = Qu_H_LS.FRAC + COEFF_FRAC
    OUTPUT_GROUPS = 12 // FI_RE_PARALLELISM
    N_OUTPUT_ACTIVE = FI_RE_PARALLELISM * LMMSE_P
    QU_COEFF = Qu_COEFF
    QU_PROD = QuType(PROD_DWT, PROD_FRAC, True)
    QU_TREE_IN = QU_PROD
    MUL_LATENCY = fi_lmmse_multiplier_latency()
    _budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    TREE_DEPTH = math.ceil(math.log2(max(N_PILOTS_PER_BEAT, 1))) if N_PILOTS_PER_BEAT > 1 else 0
    REG_POST_CMUL = not REAL_COEFF and MUL_LATENCY > 0 and TREE_DEPTH > 0
    ACC_GUARD_TREE = math.ceil(math.log2(max(N_PILOTS_PER_BEAT, 1))) if N_PILOTS_PER_BEAT > 1 else 0
    TREE_OUT_DWT = QU_TREE_IN.DWT + ACC_GUARD_TREE
    QU_TREE_OUT = QuType(TREE_OUT_DWT, QU_TREE_IN.FRAC, True)
    FILL_BEATS_ORIG = LMMSE_P // RB_PARALLELISM
    FILL_BEATS = FILL_BEATS_ORIG * OUTPUT_GROUPS
    PIPE_DELAY = _budget.pipeline_depth
    pilot_signals = []
    if has_pre_fi_buf:
        for q in range(N_PILOTS_PER_BEAT):
            pilot_signals.append(f"ls_pilot_{q}")
    else:
        for rb in range(RB_PARALLELISM):
            for re_k in pilot_re:
                pilot_signals.append(f"h_ls_rb{rb}_re{re_k}")
    REG_COEFF = _budget.need_register_before(cost_mul(COMP_DWT_IN, COEFF_DWT))
    if has_pre_fi_buf:
        REG_COEFF = True
    if REG_COEFF and not has_pre_fi_buf:
        for q in range(N_PILOTS_PER_BEAT):
            orig = pilot_signals[q]
            delayed = f"{orig}_d"
            area += Est_Delay(CPLX_DWT_IN, 1, IF_RST_N)
            pilot_signals[q] = delayed
    if REG_COEFF:
        _en_delay = fi_core_graph.build_delay_table()['enable_gated']['delay']
        area += Est_Delay(1, _en_delay, IF_RST_N)
    for q in range(N_PILOTS_PER_BEAT):
        orig = pilot_signals[q]
        gated = f"{orig}_g"
        pilot_signals[q] = gated
    for k in range(N_OUTPUT_ACTIVE):
        for q in range(N_PILOTS_PER_BEAT):
            pilot_sig = pilot_signals[q]
            if REAL_COEFF:
                area += Est_MUL(Model_MUL, Model_SU_out, SU_in_db, Qu_H_LS.DWT, Qu_H_LS.FRAC, Qu_H_LS.IF_SIGNED, QU_COEFF.DWT, QU_COEFF.FRAC, QU_COEFF.IF_SIGNED, QU_PROD.DWT, QU_PROD.FRAC, MUL_LATENCY) * 2
            else:
                QU_CPLX_COEFF = Qu_COEFF
                area += Est_MUL(Model_MUL, Model_SU_out, SU_in_db, Qu_H_LS.DWT, Qu_H_LS.FRAC, Qu_H_LS.IF_SIGNED, QU_CPLX_COEFF.DWT, QU_CPLX_COEFF.FRAC, QU_CPLX_COEFF.IF_SIGNED, QU_PROD.DWT, QU_PROD.FRAC, MUL_LATENCY) * 4
                area += Est_ADD(Model_ADD, QU_PROD.DWT, QU_PROD.FRAC, QU_PROD.IF_SIGNED, QU_PROD.DWT, QU_PROD.FRAC, QU_PROD.IF_SIGNED, QU_PROD.DWT, QU_PROD.FRAC, 0)
                area += Est_SUB(Model_ADD, Sub_db, QU_PROD.DWT, QU_PROD.FRAC, QU_PROD.IF_SIGNED, QU_PROD.DWT, QU_PROD.FRAC, QU_PROD.IF_SIGNED, QU_PROD.DWT, QU_PROD.FRAC, 0)
    if REG_POST_CMUL:
        for k in range(N_OUTPUT_ACTIVE):
            for q in range(N_PILOTS_PER_BEAT):
                area += Est_Delay(2*QU_PROD.DWT, 1, IF_RST_N)
    for k in range(N_OUTPUT_ACTIVE):
        if REAL_COEFF:
            if N_PILOTS_PER_BEAT == 1:
                pass
            else:
                area += Est_AT(Model_ADD, N_PILOTS_PER_BEAT, QU_TREE_IN, QU_TREE_OUT, TREE_DEPTH) * 2
        else:
            _tree_pipes = TREE_DEPTH - 1 if REG_POST_CMUL else TREE_DEPTH
            if N_PILOTS_PER_BEAT == 1:
                pass
            else:
                for comp_tag in ['re', 'im']:
                    area += Est_AT(Model_ADD, N_PILOTS_PER_BEAT, QU_TREE_IN, QU_TREE_OUT, _tree_pipes)
    if FILL_BEATS > 1:
        _fi_delay_table = fi_core_graph.build_delay_table()
        for _dst in ('fill_cnt_d', 'fill_cnt_dd'):
            _sig_info = _fi_delay_table[_dst]
            _n_clk = _sig_info['delay']
            _dwt = _sig_info['width']
            area += Est_Delay(_dwt, _n_clk, IF_RST_N)
        for k in range(N_OUTPUT_ACTIVE):
            area += Est_Delay(Qu_H.DWT, 0, False) * 2
    else:
        for k in range(N_OUTPUT):
            area += Est_Delay(Qu_H.DWT, 0, False) * 2
            area += Est_Delay(CPLX_DWT_OUT, 1, IF_RST_N)
        _direct_valid_delay = PIPE_DELAY + 2
        area += Est_Delay(1, _direct_valid_delay, IF_RST_N)
    return area

def _fxmatch_unit_area(QU_IN, QU_OUT):
    """Area of one FxMatch (fixed-point shift / round / saturate) instance.

    FxMatch is a mode-dependent quantiser: the generator keeps
    ``EQ_QU_IN.DWT`` bits, shifts to the output precision and then saturates.
    A parametric fit on the 27 synthesized FREQ_INTERP reports (which embed
    384 FxMatch instances each) gives ~30% residual, i.e. far better than not
    modelling the block at all (it is 6k-29k um^2 per FI lane).
    """
    EQ_IN = QU_IN.DWT + (0 if QU_IN.IF_SIGNED else 1)
    EQ_OUT = QU_OUT.DWT + (0 if QU_OUT.IF_SIGNED else 1)
    eq_in_msb = EQ_IN - QU_IN.FRAC - 1
    eq_in_lsb = -QU_IN.FRAC
    eq_out_msb = EQ_OUT - QU_OUT.FRAC - 1
    eq_out_lsb = -QU_OUT.FRAC
    if eq_out_lsb > eq_in_lsb:
        # precision truncation/rounding: keep [EQ_IN.MSB : EQ_OUT.LSB]
        quan = eq_in_msb - eq_out_lsb + 1
    else:
        # precision expansion: keep [EQ_OUT.MSB : EQ_IN.LSB]
        quan = eq_out_msb - eq_in_lsb + 1
    area = -57.925 + 7.283 * EQ_IN + 4.454 * QU_OUT.FRAC - 3.03 * quan
    return max(area, 5.0)

def Est_FxMatch(QU_IN, QU_OUT, N_INST):
    """Total FxMatch area for ``N_INST`` parallel conversion lanes."""
    return N_INST * _fxmatch_unit_area(QU_IN, QU_OUT)

def Est_FREQ_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, IF_RST_N: bool, RB_parallelism: int, Qu_H_LS: QuType, Qu_H: QuType, antenna_port: int, RE_INDEX_LIST: List[int], method: Literal["nn"] | Literal["linear"] | Literal["lmmse"], dmrs_Type: int | Literal["Hybrid"], LMMSE_P: int = 4, Qu_COEFF: QuType = QuType(12, 10, True), REAL_COEFF: bool = True, tau_rms: float = 3.0, snr_linear: float = 100.0, COEFF_SOURCE: Literal['ROM', 'SRAM'] = 'ROM', channel_model: Optional[str] = 'TDL-C', delay_spread: float = 200e-9, scs: float = 30e3, COEFF_SRAM_SHARED: bool = False, pilot_re_compact: Optional[List[int]] = None, compact_t2_slots: Optional[List[int]] = None, compact_zero_slots: Optional[List[int]] = None, pilot_re_t1: Optional[List[int]] = None, pilot_re_t2: Optional[List[int]] = None, FI_RE_PARALLELISM: int = 12, has_pre_fi_buf: bool = False, fi_core_graph: Optional['ControlSignalGraph'] = None, production_observation_layout:Optional[Dict]=None):
    area = 0
    COEFF_DWT = Qu_COEFF.DWT
    re_index_list_sorted = sorted(RE_INDEX_LIST)
    num_pilots = len(re_index_list_sorted)
    is_dual_type = (dmrs_Type == "Hybrid" and num_pilots == 8)
    _use_compact = is_dual_type and pilot_re_compact is not None
    need_fxmatch = (Qu_H_LS.DWT != Qu_H.DWT or Qu_H_LS.FRAC != Qu_H.FRAC)
    if production_observation_layout is not None:
        from production_observation import (
            frequency_window_observations,
            local_centroid_positions,
            local_lane_centroids,
            local_lane_representatives,
            metadata_from_canonical_dict,
        )
        descriptor_payload = {
            key: value
            for key, value in production_observation_layout.items()
            if key != "case_id"
        }
        descriptor_metadata = metadata_from_canonical_dict(descriptor_payload)
        descriptor_pilot_re = list(local_lane_representatives(descriptor_metadata))
    else:
        descriptor_metadata = None
        descriptor_pilot_re = None
        descriptor_centroids = None
    if descriptor_pilot_re is not None:
        compact_re_sorted = sorted(descriptor_pilot_re)
    elif _use_compact:
        compact_re_sorted = sorted(pilot_re_compact)
    else:
        compact_re_sorted = re_index_list_sorted
    if method == "nn":
        area += Est_CORE_NN_INTERP(IF_RST_N, RB_parallelism, Qu_H_LS, compact_re_sorted, dmrs_Type, pilot_re_t1, pilot_re_t2, compact_t2_slots, descriptor_centroids, has_pre_fi_buf, has_pre_fi_buf)
        # Output FxMatch bank: one instance per (RB lane, RE, I/Q component).
        # Present in every synthesized FI (384 lanes at RB_PARALLELISM = 16),
        # even when Qu_H_LS == Qu_H, because the core emits a wider internal
        # result.  Previously this block was not modelled at all.
        area += Est_FxMatch(Qu_H_LS, Qu_H, RB_parallelism * 12 * 2)
    elif method == "linear":
        area += Est_CORE_LIN_INTERP(Model_ADD, Sub_db, IF_RST_N, RB_parallelism, Qu_H_LS, compact_re_sorted, dmrs_Type, pilot_re_t1, pilot_re_t2, compact_t2_slots, descriptor_centroids, has_pre_fi_buf, has_pre_fi_buf)
        area += Est_FxMatch(Qu_H_LS, Qu_H, RB_parallelism * 12 * 2)
    elif method == "lmmse":
        _N_PILOTS_PER_RB = len(compact_re_sorted)
        _OUTPUT_GROUPS = 12 // FI_RE_PARALLELISM
        _FILL_BEATS_ORIG = max(LMMSE_P // max(RB_parallelism, 1), 1)
        _FILL_BEATS = _FILL_BEATS_ORIG * _OUTPUT_GROUPS
        _N_PILOTS_PER_BEAT = _N_PILOTS_PER_RB * RB_parallelism
        _N_OUTPUT = FI_RE_PARALLELISM * LMMSE_P
        _N_PILOTS = _N_PILOTS_PER_RB * LMMSE_P
        _COEFF_PER_BEAT = _N_OUTPUT * _N_PILOTS_PER_BEAT
        _COEFF_BEAT_DWT = _COEFF_PER_BEAT * COEFF_DWT if REAL_COEFF else _COEFF_PER_BEAT * 2 * COEFF_DWT
        if COEFF_SOURCE == 'SRAM' and not COEFF_SRAM_SHARED:
            area += Est_COEFF_SRAM(N_OUTPUT=_N_OUTPUT, N_PILOTS=_N_PILOTS, Qu_COEFF=Qu_COEFF, COEFF_STORAGE='SRAM', is_hybrid=False, rom_data_bank0=None, rom_data_bank1=None, BEAT_MODE=True, N_PILOTS_PER_BEAT=_N_PILOTS_PER_BEAT, FILL_BEATS=_FILL_BEATS)
        descriptor_W = None
        if descriptor_metadata is not None and COEFF_SOURCE == 'ROM':
            from lmmse_matrix_gen import (
                compute_freq_covariance,
                compute_freq_lmmse_W_from_observations,
            )
            window_start = (
                min(descriptor_metadata.required_physical_subcarriers) // 12
            ) * 12
            observations = frequency_window_observations(
                descriptor_metadata,
                start_subcarrier=window_start,
                num_subcarriers=12 * LMMSE_P,
            )
            descriptor_W = compute_freq_lmmse_W_from_observations(
                observations,
                list(range(12 * LMMSE_P)),
                12 * LMMSE_P,
                tau_rms=tau_rms,
                snr_linear=snr_linear,
                R_freq=(
                    None
                    if channel_model is None
                    else compute_freq_covariance(
                        12 * LMMSE_P,
                        model=channel_model,
                        scs=scs,
                        delay_spread=delay_spread,
                    )
                ),
                grid_start_subcarrier=window_start,
                inter_stage_gain_policy="none",
            )
        area += Est_CORE_LMMSE_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, IF_RST_N=IF_RST_N, LMMSE_P=LMMSE_P, RB_PARALLELISM=RB_parallelism, Qu_H_LS=Qu_H_LS, Qu_H=Qu_H, pilot_re=compact_re_sorted, output_re=list(range(12)), dmrs_Type=dmrs_Type, Qu_COEFF=Qu_COEFF, REAL_COEFF=REAL_COEFF, W_matrix_override=descriptor_W, tau_rms=tau_rms, snr_linear=snr_linear, COEFF_SOURCE=COEFF_SOURCE, channel_model=channel_model, delay_spread=delay_spread, scs=scs, pilot_re_t1=pilot_re_t1, pilot_re_t2=pilot_re_t2, compact_t2_slots=compact_t2_slots, compact_zero_slots=compact_zero_slots, FI_RE_PARALLELISM=FI_RE_PARALLELISM, has_pre_fi_buf=has_pre_fi_buf, fi_core_graph=fi_core_graph)
    return area

def Est_LS_BUF(max_occasions, SRAM_DEPTH, DATA_WIDTH, SRAM_MACRO_CONFIG):
    """Pre-FI pilot buffer: ``max_occasions`` arrays of SRAM_DEPTH x DATA_WIDTH
    plus one read register bank.

    Structure verified in LS_BUF0000000001.v of designs 5/13/30/46
    (``reg [DATA_WIDTH-1:0] sram_occ0 [0:SRAM_DEPTH-1]`` + ``sram_rd_occ0``),
    hence bits = max_occasions * (SRAM_DEPTH + 1) * DATA_WIDTH.
    Decode/read-mux overhead G is fitted on the 18 LS_BUF reports:
    G = 0.06 per bit for single-word arrays, 0.108 * SRAM_DEPTH otherwise.
    """
    bits = max_occasions * (SRAM_DEPTH + 1) * DATA_WIDTH
    area = 0
    if SRAM_MACRO_CONFIG is None:
        A_FF = 7.84
        G = 0.06 if SRAM_DEPTH <= 1 else 0.108 * SRAM_DEPTH
        area += (A_FF + G) * bits
    else:
        cfg = SRAM_MACRO_CONFIG
        MACRO_DEPTH = cfg.get('macro_depth', SRAM_DEPTH)
        if MACRO_DEPTH < SRAM_DEPTH:
            raise ValueError("MACRO_DEPTH < SRAM_DEPTH")
        A_bit_macro = cfg.get('area_per_bit', 0.40)
        area += bits * A_bit_macro
    return area

def Est_Y_BUF(max_occasions, symbols_per_occasion, SRAM_DEPTH, DATA_WIDTH):
    area = 0
    return area

def Est_LS_FI_WINDOW_CTRL(max_num_RBs, RB_PARALLELISM, LMMSE_P, FI_RE_PARALLELISM, max_occasions, symbols_per_occasion, LS_DRAIN_CYCLES, is_double_dmrs, runtime_n_additional):
    area = 0
    return area

def Est_PILOT_SRAM_BANK(max_occasions, SRAM_DEPTH, Qu_H_interp_f, TI_RE_PARALLELISM, RB_PARALLELISM, SRAM_MACRO_CONFIG):
    area = 0
    if max_occasions < 1:
        raise ValueError("max_occasions must be >= 1")
    if SRAM_DEPTH < 1:
        raise ValueError("SRAM_DEPTH must be >= 1")
    if 12 % TI_RE_PARALLELISM != 0:
        raise ValueError("TI_RE_PARALLELISM must divide 12")

    H_DWT = 2 * Qu_H_interp_f.DWT
    W_FULL = RB_PARALLELISM * 12 * H_DWT
    W_BANK = TI_RE_PARALLELISM * H_DWT
    TotalBits = max_occasions * SRAM_DEPTH * W_FULL

    if SRAM_MACRO_CONFIG is None:
        # ---- 行为模式（实测标定）----
        A_FF    = 7.84    # µm²/bit（EDQ 带使能触发器）
        A_glue  = 1.14    # µm²/bit（写译码 + buffer 树）
        A_mux   = 3.86    # µm²/bit（读 bank MUX 树，每 FULL 位）
        TotalBits_eff = TotalBits + max_occasions * W_BANK  # 含读输出 FF
        area += (A_FF * TotalBits_eff + A_glue * TotalBits + A_mux * max_occasions * W_FULL)
    else:
        # ---- 宏模式 ----
        cfg = SRAM_MACRO_CONFIG
        MACRO_DEPTH = cfg.get('macro_depth', SRAM_DEPTH)
        if MACRO_DEPTH < SRAM_DEPTH:
            raise ValueError("MACRO_DEPTH < SRAM_DEPTH")
        N_BANKS = RB_PARALLELISM * (12 // TI_RE_PARALLELISM)
        TotalBits_macro = max_occasions * N_BANKS * MACRO_DEPTH * W_BANK
        A_bit_macro = cfg.get('area_per_bit', 0.40)
        A_glue = 1.14 * TotalBits + 3.86 * max_occasions * W_FULL
        area += TotalBits_macro * A_bit_macro + A_glue
    return area

def Est_CORE_TIME_NN_INTERP(max_occasions, Qu_H, dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range):
    area = 0
    if max_occasions < 1:
        raise ValueError("max_occasions must be >= 1")
    if dmrs_typeA_pos not in ('pos2', 'pos3', 'Hybrid'):
        raise ValueError(f"Invalid dmrs_typeA_pos: {dmrs_typeA_pos}")

    # ---------- 派生量 ----------
    H_DWT = 2 * Qu_H.DWT
    N_OUT_SYMS = max(num_symbols_range)        # 输出符号数

    # ---------- 判断单表 / 多表结构 ----------
    # 复用 v_pilot_symbol_detection 的最近邻表构建逻辑
    is_single_table, n_mux_syms = _analyze_nn_table_structure(
        max_occasions, dmrs_typeA_pos, is_double_dmrs,
        additional_DMRS_range, num_symbols_range, N_OUT_SYMS)

    # ---------- 面积计算 ----------
    A_FF = 5.88      # 每 bit 寄存器面积（含延迟子模块内部逻辑）
    A_mux = 0.57     # 每 bit MUX 面积

    area = N_OUT_SYMS * H_DWT * A_FF

    if is_single_table:
        # 单表：无 MUX，仅有极小的输出直连
        area += 5.0
    else:
        # 多表：需要 MUX 的符号才计入 MUX 面积
        area += n_mux_syms * H_DWT * A_mux
        # 表选择逻辑（case 译码 + 运行时条件比较）
        n_runtime_conds = (
            (1 if dmrs_typeA_pos == "Hybrid" else 0) +
            (1 if is_double_dmrs == "Hybrid" else 0) +
            (1 if len(additional_DMRS_range) > 1 else 0) +
            (1 if len(num_symbols_range) > 1 else 0)
        )
        area += 20.0 + 3.0 * n_runtime_conds
    return area

def Est_CORE_TIME_LIN_INTERP(Model_ADD, Sub_db, max_occasions, Qu_H, dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range):
    area = 0
    cs = expand_config_space(dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range)
    l0_options = cs.l0_options
    dbl_options = cs.dbl_options
    sym_list = cs.sym_list
    N_OUT_SYMS = cs.N_OUT_SYMS
    H_DWT = 2 * Qu_H.DWT
    COMP_DWT = H_DWT // 2
    FRAC     = Qu_H.FRAC
    Qu_comp  = QuType(COMP_DWT,     FRAC, True)
    Qu_diff  = QuType(COMP_DWT + 1, FRAC, True)
    unique_tables = []
    table_to_idx  = {}
    all_tables = _build_all_lin_tables(
        dmrs_typeA_pos_options=l0_options,
        is_double_dmrs_options=dbl_options,
        additional_DMRS_range=additional_DMRS_range,
        num_symbols_range=sym_list,
        n_out_syms=N_OUT_SYMS,
    )
    for key, tbl in all_tables.items():
        tbl_tuple = tuple((a, b, c) for a, b, c in tbl)
        if tbl_tuple not in table_to_idx:
            table_to_idx[tbl_tuple] = len(unique_tables)
            unique_tables.append(tbl_tuple)
    single_table = (len(unique_tables) == 1)
    NUM_TABLES   = len(unique_tables)
    TBL_IDX_W   = max(math.ceil(math.log2(NUM_TABLES)), 1) if NUM_TABLES > 1 else 1
    scale    = (1 << FRAC_BITS)
    all_pairs = set()
    for t_idx in range(NUM_TABLES):
        for sym_idx in range(N_OUT_SYMS):
            occ_L, occ_R, alpha_fix = unique_tables[t_idx][sym_idx]
            if occ_L != occ_R:
                all_pairs.add((occ_L, occ_R))
    all_pairs = sorted(all_pairs)
    for (oL, oR) in all_pairs:
        for part in ['re', 'im']:
            area += Est_SUB(Model_ADD, Sub_db, Qu_comp.DWT, Qu_comp.FRAC, Qu_comp.IF_SIGNED, Qu_comp.DWT, Qu_comp.FRAC, Qu_comp.IF_SIGNED, Qu_diff.DWT, Qu_diff.FRAC, 0)
    emission_plan = _build_csd_emission_plan(
        unique_tables=unique_tables,
        NUM_TABLES=NUM_TABLES,
        single_table=single_table,
        N_OUT_SYMS=N_OUT_SYMS,
        Qu_comp=Qu_comp,
        Qu_diff=Qu_diff,
        H_DWT=H_DWT,
        TBL_IDX_W=TBL_IDX_W,
        scale=scale,
    )
    for task in emission_plan:
        ttype = task[0]
        if ttype == 'vlines':
            pass
        elif ttype == 'mod_sub':
            _, Qu_in1, Qu_in2, Qu_out, i1, i2, out = task
            area += Est_SUB(Model_ADD, Sub_db, Qu_in1.DWT, Qu_in1.FRAC, Qu_in1.IF_SIGNED, Qu_in2.DWT, Qu_in2.FRAC, Qu_in2.IF_SIGNED, Qu_out.DWT, Qu_out.FRAC, 0)
        elif ttype == 'mod_add':
            _, Qu_in1, Qu_in2, Qu_out, i1, i2, out = task
            area += Est_ADD(Model_ADD, Qu_in1.DWT, Qu_in1.FRAC, Qu_in1.IF_SIGNED, Qu_in2.DWT, Qu_in2.FRAC, Qu_in2.IF_SIGNED, Qu_out.DWT, Qu_out.FRAC, 0)
        elif ttype == 'mod_delay':
            _, DWT, data_in, data_out = task
            area += Est_Delay(DWT, 1, False)
    return area

def _time_lmmse_effective_occasions(cs, max_occasions, additional_DMRS_range, COEFF_SOURCE):
    """Number of LMMSE coefficient columns that survive synthesis.

    ROM coefficients are hardwired, so a column that is zero for every supported
    (l0, double-DMRS, n_additional_dmrs, n_symbols) combination is optimised
    away; only ``max len(get_pilot_symbol_positions(...))`` columns remain.
    SRAM coefficients are written at runtime and cannot be pruned.
    Verified against the 16 synthesized CORE_TIME_LMMSE_INTERP reports.
    """
    n_max = max(int(max_occasions), 1)
    if COEFF_SOURCE == 'SRAM':
        return n_max
    from lmmse_matrix_gen import get_pilot_symbol_positions
    n_occ = 1
    for l0 in cs.l0_options:
        for dbl in cs.dbl_options:
            for n_add in additional_DMRS_range:
                for n_sym in cs.sym_list:
                    n_occ = max(n_occ, len(get_pilot_symbol_positions(l0, dbl, n_add, n_sym)))
    return min(n_occ, n_max)

def Est_CORE_TIME_LMMSE_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, max_occasions, Qu_H, Qu_COEFF, LMMSE_REAL_COEFF, dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range, W_coeffs, f_d_norm, COEFF_SOURCE):
    area = 0
    H_DWT = 2 * Qu_H.DWT
    H_FRAC = Qu_H.FRAC
    COEFF_DWT = Qu_COEFF.DWT
    cs = expand_config_space(
        dmrs_typeA_pos,
        is_double_dmrs,
        additional_DMRS_range,
        num_symbols_range,
    )
    N_OUT_SYMS = cs.N_OUT_SYMS
    n_add_width = cs.n_add_width
    needs_runtime_l0 = cs.needs_runtime_l0
    needs_runtime_dbl = cs.needs_runtime_dbl
    needs_runtime_nadd = cs.needs_runtime_nadd
    needs_runtime_nsym = cs.needs_runtime_nsym
    COEFF_FRAC = COEFF_DWT - 1
    COMP_DWT = H_DWT // 2           # per-component (real or imag)
    PROD_DWT = COMP_DWT + COEFF_DWT
    PROD_FRAC = H_FRAC + COEFF_FRAC  # input_frac + coeff_frac
    ACC_GUARD = math.ceil(math.log2(max(max_occasions, 1))) if max_occasions > 1 else 0
    ACC_DWT = PROD_DWT + ACC_GUARD
    ACC_FRAC = PROD_FRAC

    QU_PILOT_COMP = QuType(COMP_DWT, H_FRAC, True)
    QU_COEFF = QuType(COEFF_DWT, COEFF_FRAC, True)
    QU_PROD = QuType(PROD_DWT, PROD_FRAC, True)
    QU_ACC = QuType(ACC_DWT, ACC_FRAC, True)
    QU_OUT_COMP = QuType(COMP_DWT, H_FRAC, True)
    MUL_LATENCY = ti_lmmse_multiplier_latency()

    # Number of coefficient columns that actually survive synthesis:
    #   * SRAM coefficients are loaded at runtime -> all max_occasions columns exist
    #   * ROM coefficients are hardwired, so columns that are zero for every
    #     supported (l0, double, n_additional, n_symbols) combination are pruned.
    # Verified against the 16 synthesized CORE_TIME_LMMSE_INTERP reports (16/16).
    N_OCC_COLS = _time_lmmse_effective_occasions(
        cs=cs, max_occasions=max_occasions,
        additional_DMRS_range=additional_DMRS_range, COEFF_SOURCE=COEFF_SOURCE,
    )
    # Calibrated on the 16 synthesized CORE_TIME_LMMSE_INTERP reports:
    #   * the complex multiplier shares logic across its four real products
    #     (measured 0.52x of four independent multipliers);
    #   * ROM coefficients are hardwired constants, so DC turns them into
    #     shift-add networks (measured 0.72x of the generic multiplier model);
    #   * SRAM coefficients are runtime values -> generic multipliers (1.0x).
    MUL_SCALE = 1.0
    if not LMMSE_REAL_COEFF:
        MUL_SCALE *= 0.52
    if COEFF_SOURCE == 'ROM':
        MUL_SCALE *= 0.72
    TREE_DEPTH = math.ceil(math.log2(max(N_OCC_COLS, 1))) if N_OCC_COLS > 1 else 0
    TOTAL_LATENCY = time_lmmse_pipeline_depth(N_OCC_COLS)
    if LMMSE_REAL_COEFF:
        for sym in range(N_OUT_SYMS):
            for j in range(N_OCC_COLS):
                area += Est_MUL(Model_MUL, Model_SU_out, SU_in_db, QU_PILOT_COMP.DWT, QU_PILOT_COMP.FRAC, QU_PILOT_COMP.IF_SIGNED, QU_COEFF.DWT, QU_COEFF.FRAC, QU_COEFF.IF_SIGNED, QU_PROD.DWT, QU_PROD.FRAC, MUL_LATENCY) * 2 * MUL_SCALE
            if N_OCC_COLS != 1:
                area += Est_AT(Model_ADD, N_OCC_COLS, QU_PROD, QU_ACC, TREE_DEPTH) * 2
            area += Est_Delay(QU_OUT_COMP.DWT, 0, False) * 2
            area += Est_Delay(H_DWT, 1, True)
    else:
        QU_CMUL_OUT = QuType(COMP_DWT, COMP_DWT // 2, True)
        for sym in range(N_OUT_SYMS):
            for j in range(N_OCC_COLS):
                area += Est_MUL(Model_MUL, Model_SU_out, SU_in_db, QU_PILOT_COMP.DWT, QU_PILOT_COMP.FRAC, QU_PILOT_COMP.IF_SIGNED, QU_COEFF.DWT, QU_COEFF.FRAC, QU_COEFF.IF_SIGNED, QU_CMUL_OUT.DWT, QU_CMUL_OUT.FRAC, MUL_LATENCY) * 4 * MUL_SCALE
                area += Est_ADD(Model_ADD, QU_CMUL_OUT.DWT, QU_CMUL_OUT.FRAC, QU_CMUL_OUT.IF_SIGNED, QU_CMUL_OUT.DWT, QU_CMUL_OUT.FRAC, QU_CMUL_OUT.IF_SIGNED, QU_CMUL_OUT.DWT, QU_CMUL_OUT.FRAC, 0)
                area += Est_SUB(Model_ADD, Sub_db, QU_CMUL_OUT.DWT, QU_CMUL_OUT.FRAC, QU_CMUL_OUT.IF_SIGNED, QU_CMUL_OUT.DWT, QU_CMUL_OUT.FRAC, QU_CMUL_OUT.IF_SIGNED, QU_CMUL_OUT.DWT, QU_CMUL_OUT.FRAC, 0)
            if N_OCC_COLS != 1:
                for comp_tag in ['re', 'im']:
                    area += Est_AT(Model_ADD, N_OCC_COLS, QU_CMUL_OUT, QU_ACC, TREE_DEPTH)
                area += Est_Delay(QU_OUT_COMP.DWT, 0, False) * 2
            area += Est_Delay(H_DWT, 1, True)
    return area

def Est_TIME_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, antenna_port, max_occasions, max_num_RBs, RB_PARALLELISM, TI_RE_PARALLELISM, Qu_H_interp_f, Qu_H_interp_t, time_interp_method, dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range, LMMSE_REAL_COEFF, Qu_TI_LMMSE_COEFF, n_additional_dmrs_fixed, f_d_norm, W_coeffs, COEFF_SOURCE, SRAM_MACRO_CONFIG, has_pre_fi_buf, FI_RE_PARALLELISM, FI_WINDOW_SIZE, ti_ctrl_graph):
    area = 0
    RE_GROUPS = 12 // TI_RE_PARALLELISM
    SRAM_DEPTH = math.ceil(max_num_RBs / RB_PARALLELISM)
    if not has_pre_fi_buf:
        # The bank inside TIME_INTERP only keeps the occasion banks that some
        # supported runtime configuration can actually select: DC prunes the
        # rest, so the stand-alone bank synthesis is an upper bound.  The
        # effective occasion count uses the same rule as the LMMSE core and the
        # pre-FI register file (SRAM coefficient banks cannot be pruned).
        # Verified against the 26 designs that have both reports: 22 match the
        # rule within 6%, the remaining four are documented outliers.
        _cs_bank = expand_config_space(dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range)
        _occ_bank = _time_lmmse_effective_occasions(
            cs=_cs_bank, max_occasions=max_occasions,
            additional_DMRS_range=additional_DMRS_range,
            COEFF_SOURCE=(COEFF_SOURCE if time_interp_method == 'lmmse' else 'ROM'),
        )
        area += Est_PILOT_SRAM_BANK(max_occasions=_occ_bank, SRAM_DEPTH=SRAM_DEPTH, Qu_H_interp_f=Qu_H_interp_f, TI_RE_PARALLELISM=TI_RE_PARALLELISM, RB_PARALLELISM=RB_PARALLELISM, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG)
    else:
        # Pre-FI occasion register file + read bank-select mux
        # (v_time_interp.py, "Occasion Register File (pre-FI)"):
        #   OCC_REG_DATA_W = RB_PARALLELISM * 12 * H_interp_f_DWT
        #   OCC_REG_DEPTH  = FI_WINDOW_SIZE // RB_PARALLELISM
        #   max_occasions banks + one read register per occasion
        # Banks that no supported runtime configuration ever selects are pruned
        # by DC, so the effective occasion count is the maximum number of pilot
        # occasions over the configuration space (same rule as the LMMSE core).
        # Verified on the 18 synthesized pre-FI TIME_INTERP reports: 14/18 exact,
        # the remaining four within 25%.
        _occ_data_w = RB_PARALLELISM * 12 * (2 * Qu_H_interp_f.DWT)
        _beats = max(FI_WINDOW_SIZE // max(RB_PARALLELISM, 1), 1)
        _cs_pre = expand_config_space(dmrs_typeA_pos, is_double_dmrs, additional_DMRS_range, num_symbols_range)
        _occ_eff = _time_lmmse_effective_occasions(
            cs=_cs_pre, max_occasions=max_occasions,
            additional_DMRS_range=additional_DMRS_range, COEFF_SOURCE='ROM',
        )
        area += 7.84 * _occ_eff * (_beats + 1) * _occ_data_w
        area += 1.15 * _occ_eff * _occ_data_w
        N_BANKS_PRE_FI = RB_PARALLELISM * RE_GROUPS
        if N_BANKS_PRE_FI > 1:
            BANK_SEL_W_PRE_FI = max(math.ceil(math.log2(N_BANKS_PRE_FI)), 1)
            if ti_ctrl_graph is not None and 'occ_bank_sel' in ti_ctrl_graph.build_delay_table():
                _bs_delay = ti_ctrl_graph.build_delay_table()['occ_bank_sel']['delay']
            else:
                _bs_delay = 1
            area += Est_Delay(BANK_SEL_W_PRE_FI, _bs_delay, False)
    for re_lane in range(TI_RE_PARALLELISM):
        if time_interp_method == 'nn':
            area += Est_CORE_TIME_NN_INTERP(max_occasions=max_occasions, Qu_H=Qu_H_interp_f, dmrs_typeA_pos=dmrs_typeA_pos, is_double_dmrs=is_double_dmrs, additional_DMRS_range=additional_DMRS_range, num_symbols_range=num_symbols_range)
        elif time_interp_method == 'linear':
            area += Est_CORE_TIME_LIN_INTERP(Model_ADD, Sub_db, max_occasions=max_occasions, Qu_H=Qu_H_interp_f, dmrs_typeA_pos=dmrs_typeA_pos, is_double_dmrs=is_double_dmrs, additional_DMRS_range=additional_DMRS_range, num_symbols_range=num_symbols_range)
        elif time_interp_method == 'lmmse':
            area += Est_CORE_TIME_LMMSE_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, max_occasions=max_occasions, Qu_H=Qu_H_interp_f, Qu_COEFF=Qu_TI_LMMSE_COEFF, LMMSE_REAL_COEFF=LMMSE_REAL_COEFF, dmrs_typeA_pos=dmrs_typeA_pos, is_double_dmrs=is_double_dmrs, additional_DMRS_range=additional_DMRS_range, num_symbols_range=num_symbols_range, W_coeffs=W_coeffs, f_d_norm=f_d_norm, COEFF_SOURCE=COEFF_SOURCE)
        else:
            raise ValueError(f"Invalid time_interp_method: {time_interp_method}")
    return area

def Est_Top(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, protocol: ProtocolSpec, architecture: ArchitectureConfig, quants: Dict[QuantKey, QuType], arithmetic: ArithmeticConfig, implementation: ImplementationConfig):
    area = 0
    area_CFG_LATCH = 0
    area_CONTROLLER = 0
    area_INIT_GEN = 0
    area_FREQ_INTERP = 0
    area_LS = 0
    area_TIME_INTERP = 0
    area_Y_REDUCE = 0
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
    H_interp_f_DWT = 2 * Qu_H_interp_f.DWT
    H_interp_t_DWT = 2 * Qu_H_interp_t.DWT
    FI_LMMSE_COEFF_DWT = Qu_FI_LMMSE_COEFF.DWT
    FI_LMMSE_COEFF_FRAC = Qu_FI_LMMSE_COEFF.FRAC
    TI_LMMSE_COEFF_DWT = Qu_TI_LMMSE_COEFF.DWT
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
    _fi_fill_beats_orig = max(LMMSE_INTERP_PARALLELISM // max(RB_PARALLELISM, 1), 1) if freq_interp_method == 'lmmse' else 1
    _output_groups = (12 // FI_RE_PARALLELISM) if HAS_PRE_FI_BUF else 1
    _fi_fill_beats = _fi_fill_beats_orig * _output_groups
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
    if HAS_PRE_FI_BUF and freq_interp_method == 'lmmse':
        _pilot_bank_depth = LMMSE_INTERP_PARALLELISM // RB_PARALLELISM
        _pilot_bank_addr_w = max(math.ceil(math.log2(_pilot_bank_depth)), 1)
        _ybuf_data_w = Y_PARALLELISM * 2 * Y.DWT
        _ybuf_re_w = 2 * Y.DWT
    area_CONTROLLER += Est_CONTROLLER(Model_ADD, Sub_db, min_num_RBs=min_num_RBs, max_num_RBs=max_num_RBs, RB_PARALLELISM=RB_PARALLELISM, max_pusch_symbols=max_pusch_symbols, is_double_dmrs=is_double_dmrs, additional_DMRS_range=additional_DMRS_range, dmrs_typeA_pos=dmrs_typeA_pos, num_symbols_range=num_symbols_range, LS_DRAIN_CYCLES=EARLY_LS_DRAIN, TI_PIPELINE_DEPTH=TI_PIPELINE_DEPTH, TI_RE_PARALLELISM=TI_RE_PARALLELISM, HAS_COEFF_SRAM=HAS_COEFF_SRAM, ls_ctrl_graph=ls_ctrl_graph, freq_interp_method=freq_interp_method, max_occasions=max_occasions, counter_width=counter_width, SRAM_ADDR_WIDTH=SRAM_ADDR_WIDTH, Qu_symbol_idx=Qu_symbol_idx, INPUT_MODE=INPUT_MODE, is_enhanced=is_enhanced, dmrs_Type=dmrs_Type, is_ECP=is_ECP, switchable_ports=switchable_ports, ANTENNA_PORTS=ANTENNA_PORTS, has_pre_fi_buf=HAS_PRE_FI_BUF, FI_WINDOW_SIZE=FI_WINDOW_SIZE, FI_CYCLES_PER_OCC=FI_CYCLES_PER_OCC, FI_CYCLES_PER_OCC_SINGLE=FI_CYCLES_PER_OCC_SINGLE, FI_FILL_BEATS=_fi_fill_beats, HAS_TI_GATE=False)[0]
    area += area_CONTROLLER
    # print(area_CONTROLLER)
    area_CFG_LATCH += Est_CFG_LATCH(Qu_slot_idx=Qu_slot_idx, counter_width=counter_width, N_CLK=1, IF_RST_N=True, has_is_double_dmrs=(is_double_dmrs == "Hybrid"), has_is_enhanced=(is_enhanced == "Hybrid"), has_dmrs_type=(dmrs_Type == "Hybrid"), has_typeA_pos=(dmrs_typeA_pos == "Hybrid"), cdm_sel_bits=_cdm_sel_bits, has_is_ECP=(is_ECP == "Hybrid"), n_add_width=_n_add_width_latch, num_ports=_num_ports_latch)
    # print(area_CFG_LATCH * 1.3846)
    area += area_CFG_LATCH * 1.3846
    if switchable_ports:
        area += Est_PORT_ENABLE(antenna_ports=ANTENNA_PORTS, dmrs_Type=dmrs_Type, is_enhanced=is_enhanced, is_double_dmrs=is_double_dmrs, has_ext_enable=True)
    if switchable_ports:
        fdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
        tdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
        area += Est_CDM_CTRL(antenna_ports=ANTENNA_PORTS, dmrs_Type=dmrs_Type)
    elif not switchable_ports and dmrs_Type == 'Hybrid':
        fdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
        tdCDM = {g: 'Hybrid' for g in _cdm_active_groups}
        area += Est_CDM_CTRL(antenna_ports=ANTENNA_PORTS, dmrs_Type=dmrs_Type, has_ports_enable=False)
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
    area_INIT_GEN += Est_C_INIT_GENERATION(Model_MUL, Model_SU_out, SU_in_db, Model_ADD, Sub_db, Qu_symbol_idx=Qu_symbol_idx, Qu_slot_idx=Qu_slot_idx, N_CLK=N_CLK_CINIT, dmrs_Type=dmrs_Type, dmrs_Uplink=dmrs_Uplink, is_ECP=is_ECP, ENABLED_CDM_GROUPS_TYPE1=ENABLED_CDM_GROUPS_TYPE1, ENABLED_CDM_GROUPS_TYPE2=ENABLED_CDM_GROUPS_TYPE2, ENABLED_CDM_GROUPS_TYPE3=ENABLED_CDM_GROUPS_TYPE3)[0]
    area += area_INIT_GEN
    # print(area_INIT_GEN)
    if INPUT_MODE == 'A':
        area_Y_REDUCE = Est_Y_PATH_REDUCE(Qu_Data=Qu_Y_Complex, INPUT_INDEX_LIST=INPUT_INDEX_LIST, OUTPUT_INDEX_LIST=TRUE_INDEX_LIST, HAS_VALID_READY=False)
        area += area_Y_REDUCE
    elif INPUT_MODE == 'B':
        for rb in range(RB_PARALLELISM):
            area_Y_REDUCE = Est_Y_PATH_REDUCE(Qu_Data=Qu_Y_Complex, INPUT_INDEX_LIST=list(range(12)), OUTPUT_INDEX_LIST=required_re_per_rb, HAS_VALID_READY=True)
            area += area_Y_REDUCE
        area +=Est_Y_RB_ALIGN(Qu_Y=Y, RB_PARALLELISM=RB_PARALLELISM, RE_PER_RB=RE_PER_RB)
    # print(area_Y_REDUCE)
    area_LS += Est_LS(Model_ADD, Sub_db, Qu_Y=Y, QU_H_LS=QU_H_LS, QU_MODE_LS=QU_MODE_LS, OF_MODE_LS=OF_MODE_LS, N_CLK_Y_PRE=N_CLK_Y_PRE, N_CLK_DMRS_SEQ=N_CLK_DMRS_SEQ, N_CLK_LS_ROT=N_CLK_LS_ROT, dmrs_Type=dmrs_Type, dmrs_Uplink=dmrs_Uplink, is_ECP=is_ECP, is_enhanced=is_enhanced, is_double_dmrs=is_double_dmrs, antenna_ports=ANTENNA_PORTS, TRUE_INDEX_LIST=TRUE_INDEX_LIST, switchable_ports=switchable_ports, RB_PARALLELISM=RB_PARALLELISM, fdCDM=fdCDM, tdCDM=tdCDM, max_num_RBs=max_num_RBs, HAS_LFSR_ENABLE=True, HAS_LFSR_CTX=(HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'), HAS_AVG_SYM_SWITCH=(HAS_PRE_FI_BUF and freq_interp_method == 'lmmse' and _symbols_per_occasion > 1), N_LFSR_CTX_SLOTS=_ybuf_total_planes, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG, REPLAY_TOKEN_DWT=_replay_token_dwt if (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse') else 0, N_CLK_AVG=ls_timing['N_CLK_AVG'])
    # Calibration factor for the LS subtree.  The tree above models the
    # standalone LS synthesis, while the estimation target is the LS instance
    # inside the TOP (DC prunes logic with real connectivity, so the in-context
    # area is systematically smaller).  Least-squares fit of the LS term alone
    # against the 24 TOP runs: 0.8068 (mean |error| of the LS term 30%, versus
    # 117% with the previous 1.6582 which implicitly compensated the AVERAGING
    # SRAMs that were not modelled at all).
    # Calibration factor for the LS subtree.  The tree above models the
    # stand-alone LS synthesis, but the LS instance inside the TOP is
    # optimised with its real connectivity.  The size of that effect depends
    # on whether fdCDM/tdCDM are runtime-selectable (then the AVERAGING
    # control path is 'Hybrid' and the LS is pruned by 25-55%) or fixed
    # (the model is then accurate to +16%).  Both factors are least-squares
    # fits against the 24 TOP runs, one per group.
    if switchable_ports or dmrs_Type == "Hybrid":
        area += area_LS * 0.74
    else:
        area += area_LS * 1.16
    if _shared_coeff_specs:
        for _spec in _shared_coeff_specs:
            area += Est_COEFF_SRAM(N_OUTPUT=_spec['n_output'], N_PILOTS=_spec['n_pilots'], Qu_COEFF=Qu_FI_LMMSE_COEFF, COEFF_STORAGE='SRAM', is_hybrid=False, rom_data_bank0=None, rom_data_bank1=None, BEAT_MODE=True, N_PILOTS_PER_BEAT=_spec['n_pilots_per_beat'], FILL_BEATS=_spec['fill_beats'])
    _production_layout_by_port = {
        metadata.antenna_port: metadata.canonical_dict()
        for metadata in production_layout_metadata
    }
    for ant_port in ANTENNA_PORTS:
        info = arch_config.get_port_interp_info(ant_port)
        _production_layout = _production_layout_by_port.get(ant_port)
        if freq_interp_method in ('nn', 'linear'):
            area_FREQ_INTERP = Est_FREQ_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, IF_RST_N=False, RB_parallelism=RB_PARALLELISM, Qu_H_LS=QU_H_LS, Qu_H=Qu_H_interp_f, antenna_port=ant_port, RE_INDEX_LIST=info.pilot_re_list, method=freq_interp_method, dmrs_Type=dmrs_Type, pilot_re_compact=info.pilot_re_compact if info.is_dual_type else None, compact_t2_slots=info.compact_t2_slots if info.is_dual_type else None, compact_zero_slots=info.compact_zero_slots if info.is_dual_type else None, pilot_re_t1=info.re_list_type1 if info.is_dual_type else None, pilot_re_t2=info.re_list_type2 if info.is_dual_type else None, has_pre_fi_buf=HAS_PRE_FI_BUF, production_observation_layout=_production_layout)
        elif freq_interp_method == 'lmmse':
            _coeff_shared = bool(_share_cdm_srams)
            area_FREQ_INTERP = Est_FREQ_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, IF_RST_N=False, RB_parallelism=RB_PARALLELISM, Qu_H_LS=QU_H_LS, Qu_H=Qu_H_interp_f, antenna_port=ant_port, RE_INDEX_LIST=info.pilot_re_list, method='lmmse', dmrs_Type=dmrs_Type, LMMSE_P=LMMSE_INTERP_PARALLELISM, Qu_COEFF=Qu_FI_LMMSE_COEFF, REAL_COEFF=FI_LMMSE_REAL_COEFF, tau_rms=FI_LMMSE_tau_rms, snr_linear=FI_LMMSE_snr_linear, COEFF_SOURCE=FI_LMMSE_COEFF_SOURCE, COEFF_SRAM_SHARED=_coeff_shared, channel_model=FI_LMMSE_channel_model, delay_spread=FI_LMMSE_delay_spread, scs=FI_LMMSE_scs, pilot_re_compact=info.pilot_re_compact if info.is_dual_type else None, compact_t2_slots=info.compact_t2_slots if info.is_dual_type else None, compact_zero_slots=info.compact_zero_slots if info.is_dual_type else None, pilot_re_t1=info.re_list_type1 if info.is_dual_type else None, pilot_re_t2=info.re_list_type2 if info.is_dual_type else None, FI_RE_PARALLELISM=FI_RE_PARALLELISM, has_pre_fi_buf=HAS_PRE_FI_BUF, fi_core_graph=build_fi_core_graph(N_PILOTS_PER_RB=len(production_lane_representatives.get(ant_port, info.pilot_re_compact or info.pilot_re_list)), LMMSE_P=LMMSE_INTERP_PARALLELISM, RB_PARALLELISM=RB_PARALLELISM, H_DWT=H_interp_f_DWT // 2, COEFF_DWT=FI_LMMSE_COEFF_DWT, REAL_COEFF=FI_LMMSE_REAL_COEFF, FI_RE_PARALLELISM=FI_RE_PARALLELISM, has_pre_fi_buf=HAS_PRE_FI_BUF,)[0], production_observation_layout=_production_layout)
        # No calibration factor: with the output FxMatch bank now modelled,
        # Est_FREQ_INTERP reproduces the synthesized FI lane directly
        # (the former 1.3744 factor was compensating the missing block).
        area += area_FREQ_INTERP
    # print(area_FREQ_INTERP)
    # print(freq_interp_method)
    if HAS_PRE_FI_BUF:
        if freq_interp_method == 'lmmse':
            _pilot_bank_depth = LMMSE_INTERP_PARALLELISM // RB_PARALLELISM
        for ant_port in ANTENNA_PORTS:
            _info = arch_config.get_port_interp_info(ant_port)
            _descriptor_re = production_lane_representatives.get(ant_port)
            _n_pilots = (
                len(_descriptor_re)
                if _descriptor_re is not None
                else _info.num_pilots_compact
            )
            _ls_buf_dw = _n_pilots * RB_PARALLELISM * COMPLEX_DWT_LS
            _lsbuf_depth = _pilot_bank_depth if freq_interp_method == 'lmmse' else SRAM_DEPTH
            _lsbuf_occ = 1 if freq_interp_method == 'lmmse' else max_occasions
            area += Est_LS_BUF(max_occasions=_lsbuf_occ, SRAM_DEPTH=_lsbuf_depth, DATA_WIDTH=_ls_buf_dw, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG)
    if (HAS_PRE_FI_BUF and freq_interp_method == 'lmmse'):
        area += Est_Y_BUF(max_occasions=max_occasions, symbols_per_occasion=_symbols_per_occasion, SRAM_DEPTH=SRAM_DEPTH, DATA_WIDTH=_ybuf_data_w)
        area += Est_LS_FI_WINDOW_CTRL(max_num_RBs=max_num_RBs, RB_PARALLELISM=RB_PARALLELISM, LMMSE_P=LMMSE_INTERP_PARALLELISM, FI_RE_PARALLELISM=FI_RE_PARALLELISM, max_occasions=max_occasions, symbols_per_occasion=_symbols_per_occasion, LS_DRAIN_CYCLES=_replay_pipe_delay, is_double_dmrs=is_double_dmrs, runtime_n_additional=(len(additional_DMRS_range) > 1))
    for ant_port in ANTENNA_PORTS:
        area_TIME_INTERP = Est_TIME_INTERP(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, antenna_port=ant_port, max_occasions=max_occasions, max_num_RBs=max_num_RBs, RB_PARALLELISM=RB_PARALLELISM, TI_RE_PARALLELISM=TI_RE_PARALLELISM, Qu_H_interp_f=Qu_H_interp_f, Qu_H_interp_t=Qu_H_interp_t, time_interp_method=time_interp_method, dmrs_typeA_pos=dmrs_typeA_pos, is_double_dmrs=is_double_dmrs, additional_DMRS_range=additional_DMRS_range, num_symbols_range=list(range(min_pusch_symbols, max_pusch_symbols + 1)), LMMSE_REAL_COEFF=TI_LMMSE_REAL_COEFF, Qu_TI_LMMSE_COEFF=Qu_TI_LMMSE_COEFF, n_additional_dmrs_fixed=max(additional_DMRS_range), f_d_norm=TI_LMMSE_f_d_norm, W_coeffs=TI_LMMSE_W_coeffs, COEFF_SOURCE=TI_LMMSE_COEFF_SOURCE, SRAM_MACRO_CONFIG=SRAM_MACRO_CONFIG, has_pre_fi_buf=HAS_PRE_FI_BUF, FI_RE_PARALLELISM=FI_RE_PARALLELISM, FI_WINDOW_SIZE=FI_WINDOW_SIZE, ti_ctrl_graph=ti_ctrl_graph)
        area += area_TIME_INTERP
    # print(area_TIME_INTERP)
    # print(time_interp_method)
    # print(HAS_PRE_FI_BUF)
    return area

def _parse_param_value(value: Any) -> Any:
    """Convert the literal-style values used by the ``parameters`` sheet."""

    if pd.isna(value):
        return None
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text in ("", "None", "None (Jakes model)"):
        return None
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return text


def _parse_qu_type(value: Any, field: str) -> QuType:
    """Parse a spreadsheet ``QuType(DWT, FRAC, IF_SIGNED)`` value safely."""

    if isinstance(value, QuType):
        return value
    match = re.fullmatch(
        r"QuType\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(True|False)\s*\)",
        str(value).strip(),
    )
    if not match:
        raise ValueError(f"{field} must use QuType(DWT, FRAC, IF_SIGNED), got {value!r}")
    return QuType(int(match.group(1)), int(match.group(2)), match.group(3) == "True")


def _parse_enum(value: Any, enum_root: Any, field: str) -> Any:
    """Resolve a constrained enum reference such as ``TRN.TCPL``."""

    try:
        group, member = str(value).strip().split(".")
        return getattr(getattr(enum_root, group), member)
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"Invalid {field} enum value: {value!r}") from exc


def _top_inputs_from_row(row: pd.Series) -> tuple[ProtocolSpec, ArchitectureConfig, Dict[QuantKey, QuType], ArithmeticConfig, ImplementationConfig]:
    """Build validated TOP API inputs from one row of ``param.xlsx``."""

    get = lambda name: _parse_param_value(row[name])
    protocol = ProtocolSpec(
        pusch={
            "num_RB_range": (int(get("num_RB_min")), int(get("num_RB_max"))),
            "num_symbols_range": (int(get("num_symbols_min")), int(get("num_symbols_max"))),
            "is_ECP": bool(get("is_ECP")),
        },
        dmrs={
            "dmrs_Uplink": bool(get("dmrs_Uplink")),
            "dmrs_Type": get("dmrs_Type"),
            "is_double_dmrs": bool(get("is_double_dmrs")),
            "is_enhanced": bool(get("is_enhanced")),
            "dmrs_typeA_pos": get("dmrs_typeA_pos"),
            "additional_DMRS_range": get("additional_DMRS_range"),
        },
        antenna_ports=get("antenna_ports"),
        slot_index_format=_parse_qu_type(row["slot_index_format"], "slot_index_format"),
    )
    architecture = ArchitectureConfig(
        rb_parallelism=int(get("rb_parallelism")),
        fi_lmmse_parallelism=int(get("fi_lmmse_parallelism")),
        freq_interp=get("freq_interp"), time_interp=get("time_interp"),
        input_mode=get("input_mode"), switchable_ports=bool(get("switchable_ports")),
        fi_re_parallelism=int(get("fi_re_parallelism")),
        ti_re_parallelism=int(get("ti_re_parallelism")),
        fi_lmmse_real_coeff=bool(get("fi_lmmse_real_coeff")),
        ti_lmmse_real_coeff=bool(get("ti_lmmse_real_coeff")),
        fi_lmmse_coeff_source=get("fi_lmmse_coeff_source"),
        ti_lmmse_coeff_source=get("ti_lmmse_coeff_source"),
    )
    quants = {
        QuantKey.Y: _parse_qu_type(row["Y"], "Y"),
        QuantKey.H_LS: _parse_qu_type(row["H_LS"], "H_LS"),
        QuantKey.H_FI: _parse_qu_type(row["H_FI"], "H_FI"),
        QuantKey.H_TI: _parse_qu_type(row["H_TI"], "H_TI"),
        QuantKey.FI_LMMSE_COEFF: _parse_qu_type(row["FI_LMMSE_COEFF"], "FI_LMMSE_COEFF"),
        QuantKey.TI_LMMSE_COEFF: _parse_qu_type(row["TI_LMMSE_COEFF"], "TI_LMMSE_COEFF"),
    }
    arithmetic = ArithmeticConfig(
        ls_quant_mode=_parse_enum(row["ls_quant_mode"], QuMode, "ls_quant_mode"),
        ls_overflow_mode=_parse_enum(row["ls_overflow_mode"], OfMode, "ls_overflow_mode"),
    )
    implementation = ImplementationConfig(
        ti_lmmse_f_d_norm=float(get("ti_lmmse_f_d_norm")),
        ti_lmmse_w_coeffs=get("ti_lmmse_w_coeffs"),
        fi_lmmse_tau_rms=float(get("fi_lmmse_tau_rms")),
        fi_lmmse_snr_linear=float(get("fi_lmmse_snr_linear")),
        fi_lmmse_channel_model=get("fi_lmmse_channel_model"),
        fi_lmmse_delay_spread=float(get("fi_lmmse_delay_spread")),
        fi_lmmse_scs=float(get("fi_lmmse_scs")),
        sram_macro=get("sram_macro"),
        production_observation_layouts=get("production_observation_layouts"),
    )
    return protocol, architecture, quants, arithmetic, implementation


def main() -> pd.DataFrame:
    """Evaluate the TOP area for every design described in ``param.xlsx``."""

    warnings.filterwarnings("ignore")
    root = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(root, "model")
    SU_in_db = pd.read_excel(os.path.join(model_dir, "SU_in.xlsx"), sheet_name="SU_in")
    Sub_db = pd.read_excel(os.path.join(model_dir, "SU_in.xlsx"), sheet_name="Sub")
    Model_ADD = joblib.load(os.path.join(model_dir, "ADD_area.pkl"))
    Model_MUL = joblib.load(os.path.join(model_dir, "pure_MUL_area.pkl"))
    Model_SU_out = joblib.load(os.path.join(model_dir, "SU_out_FxP_area.pkl"))
    params = pd.read_excel(os.path.join(root, "param.xlsx"), sheet_name="parameters")

    if "area" not in params.columns:
        raise ValueError("param.xlsx 'parameters' sheet must contain an 'area' column")

    results = []
    for _, row in params.dropna(how="all").iterrows():
        design_id = row["design_id"]
        area_marker = row["area"]
        if pd.isna(area_marker) or (isinstance(area_marker, str) and not area_marker.strip()):
            print()
            # print(f"design_id={design_id}: skipped (area is empty)")
            continue
        try:
            inputs = _top_inputs_from_row(row)
            area = Est_Top(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, *inputs)[0]
            results.append({"design_id": design_id, "area": area, "status": "ok"})
            print(area)
        except Exception as exc:
            results.append({"design_id": design_id, "area": np.nan, "status": f"error: {exc}"})
            print(f"design_id={design_id}: error: {exc}")

    result_df = pd.DataFrame(results)
    result_path = os.path.join(root, "param_estimation_results.xlsx")
    result_df.to_excel(result_path, index=False)
    print(f"Results written to {result_path}")
    return result_df


if __name__ == '__main__':
    main()
