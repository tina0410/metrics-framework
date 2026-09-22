from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Literal, List, Optional, Tuple
from basic_modules import QuType, QuMode, OfMode, ModuleDelay, ModuleFxMatch
from delay_budget import DelayBudget, COST_MUX_2TO1, DEFAULT_BUDGET
from constants import RE_PER_RB


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


def _nn_pilot_wire(re_k, rb, port_remap):
    """Build the pilot input wire name, applying port_remap if provided."""
    mapped = port_remap[re_k] if (port_remap and re_k in port_remap) else re_k
    return f"pilot_rb{rb}_re{mapped}"


def nn_freq_pipeline_depth() -> int:
    """Pipeline depth of the NN freq interpolation core (always 1)."""
    return 1


@convert
def ModuleCORE_NN_INTERP(IF_RST_N: bool, RB_PARALLELISM: int, Qu_H: QuType, pilot_re: List[int], dmrs_Type: int | Literal["Hybrid"], pilot_re_t1: Optional[List[int]] = None, pilot_re_t2: Optional[List[int]] = None, compact_t2_slots: Optional[List[int]] = None, sample_positions: Optional[List[float]] = None, has_next_rb_lowest: bool = False, has_prev_rb_highest: bool = False) -> None:
    """
    RB-level Nearest-Neighbor Frequency Interpolation Core.

    Given pilot-position channel estimates at the input, this module fills
    all 12 RE positions per RB using nearest-neighbor assignment.

    **Output Timing**:
      - Pilots and interior REs (those between the lowest and highest pilot,
        or equal-distance assigned) are output **immediately** (same clock).
      - Right-boundary REs (above the highest pilot in the current RB) are
        **stalled by 1 clock**, output when the next RB's lowest-pilot data
        arrives.  The stalled REs are then assigned to whichever is closer:
        current RB's highest pilot or next RB's lowest pilot.
      - Left-boundary REs (below the lowest pilot) are output using the
        **registered** highest pilot from the previous RB (1-clock delay).
        On ``first_RB``, these REs use the current RB's lowest pilot instead
        (extrapolation fallback).

    **Fixed Latency**: 1 clock cycle for all output REs, since:
      - Immediate REs: registered at output for alignment.
      - Left-boundary: use registered prev-RB data → naturally 1 clk.
      - Right-boundary: wait for next clock's input → 1 clk stall.

    **Example (DMRS Type 2, CDM group 0, pilots = [0, 1, 6, 7])**::

        Input clock N:   pilots at RE {0, 1, 6, 7} for RB_n
        Same clock:      RE 2,3 ← RE 1;  RE 4,5 ← RE 6  (immediate)
        Stall RE 8,9 ← RE 7;  RE 10,11 wait for next RB's RE 0
        Input clock N+1: pilots at RE {0, 1, 6, 7} for RB_{n+1}
        Output RE 10,11 of RB_n ← closer of (RB_n RE 7, RB_{n+1} RE 0)
        And simultaneously output RB_{n+1}'s immediate REs

    **Example (DMRS Type 1, CDM group 0, pilots = [0, 2, 4, 6, 8, 10])**::

        Pilots at even REs; each odd RE is equidistant from neighbours.
        All interior odd REs (1,3,5,7,9) assigned to left neighbour.
        RE 11 is right-boundary → stall, assigned from closer of
        (current RE 10, next RB RE 0).
        No left-boundary REs (RE 0 is a pilot).

    :param IF_RST_N: True
        Whether to include async reset.
    :type IF_RST_N: bool
    :param RB_PARALLELISM: 1
        Number of RBs processed per clock cycle.
    :type RB_PARALLELISM: int
    :param Qu_H: QuType(12, 4, True)
        Quantization type of channel estimates (input and output).
    :type Qu_H: QuType
    :param pilot_re: [0, 2, 4, 6, 8, 10]
        Sorted pilot RE indices within one RB.
    :type pilot_re: List[int]
    :param dmrs_Type: 1
        DMRS type (1, 2, or "Hybrid"). Affects boundary handling.
    :type dmrs_Type: int | Literal["Hybrid"]
    """

    pilot_re_sorted = sorted(pilot_re)
    if sample_positions is not None:
        if len(sample_positions) != len(pilot_re_sorted):
            raise ValueError("NN sample positions must match unique observation lanes")
        descriptor_source = {
            output_re: min(
                range(len(sample_positions)),
                key=lambda index: (abs(float(sample_positions[index]) - output_re), index),
            )
            for output_re in range(RE_PER_RB)
        }
    else:
        descriptor_source = None
    N_PILOTS = len(pilot_re_sorted)

    # Only dual-type Hybrid ports need runtime dmrs_type switching. Hybrid
    # type-specific ports still elaborate as a single fixed pilot topology.
    is_hybrid = (dmrs_Type == "Hybrid" and pilot_re_t1 is not None and pilot_re_t2 is not None)

    _use_compact = is_hybrid and compact_t2_slots is not None

    _re_t1: List[int] = []
    _re_t2: List[int] = []
    lowest_pilot_t1 = pilot_re_sorted[0]
    highest_pilot_t1 = pilot_re_sorted[-1]
    lowest_pilot_t2 = pilot_re_sorted[0]
    highest_pilot_t2 = pilot_re_sorted[-1]
    if is_hybrid:
        assert pilot_re_t1 is not None and pilot_re_t2 is not None
        _re_t1 = sorted(pilot_re_t1)
        _re_t2 = sorted(pilot_re_t2)

    # Build T2 RE → compact port RE mapping for _gen_nn_datapath
    _t2_port_map = {}
    if is_hybrid and _use_compact:
        assert compact_t2_slots is not None
        for t2_idx, slot in enumerate(compact_t2_slots):
            _t2_port_map[_re_t2[t2_idx]] = pilot_re_sorted[slot]

    if is_hybrid:
        pilot_re_t1 = _re_t1
        pilot_re_t2 = _re_t2

        nn_class_t1 = _classify_nn_output(pilot_re_t1)
        nn_class_t2 = _classify_nn_output(pilot_re_t2)

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

        nn_class = (
            _classify_assignment(
                _nn_assignment_map_positions(pilot_re_sorted, sample_positions)
            )
            if sample_positions is not None
            else _classify_nn_output(pilot_re_sorted)
        )
        immediate_list = nn_class['immediate']
        left_bnd_list = nn_class['left_boundary']
        right_bnd_list = nn_class['right_boundary']

    # Pilot index lookup: pilot_re_k → position in input vector
    pilot_idx_map = {re_k: i for i, re_k in enumerate(pilot_re_sorted)}

    # Complex data width
    COMPLEX_DWT = 2 * Qu_H.DWT

    # =========================================================================
    # DelayBudget analysis — NN freq interpolation
    # =========================================================================
    # NN is MUX-only (cost ≈ 0) + 1 output register → fixed depth = 1.
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    budget.add_comb(COST_MUX_2TO1, tag="nn_mux_select")
    budget.add_register(1, tag="output_reg")
    NN_FREQ_DEPTH = budget.pipeline_depth  # == 1

    # =========================================================================
    # Module Port Declaration
    # =========================================================================

    #/ `timescale 1ns / 1ps
    #/ module CORE_NN_INTERP(
    #/     input clk,
    if IF_RST_N:
        #/ input rst_n,
        pass

    #/ input first_RB,
    #/ input last_RB,
    if RB_PARALLELISM > 1:
        #/ input [`RB_PARALLELISM`-1:0] lane_last,
        pass

    if has_next_rb_lowest:
        #/ input [`COMPLEX_DWT`-1:0] next_rb_lowest,
        pass

    if has_prev_rb_highest:
        #/ input [`COMPLEX_DWT`-1:0] prev_rb_highest,
        pass

    if is_hybrid:
        #/ input dmrs_type,
        pass

    # Per RB: pilot inputs (complex)
    for rb in range(RB_PARALLELISM):
        for k in pilot_re_sorted:
            in_name = f"pilot_rb{rb}_re{k}"
            #/ input [`COMPLEX_DWT`-1:0] `in_name`,
            pass

    # Per RB: RE_PER_RB (12) RE outputs (complex)
    out_names: List[str] = []
    for rb in range(RB_PARALLELISM):
        for k in range(RE_PER_RB):
            out_names.append(f"h_nn_rb{rb}_re{k}")

    for idx, on in enumerate(out_names):
        comma = "" if idx == len(out_names) - 1 else ","
        #/ output [`COMPLEX_DWT`-1:0] `on + comma`
        pass
    #/ );

    # =========================================================================
    # Pipeline-delayed boundary control signals (match 1-clk registered data)
    # =========================================================================
    #/ wire first_RB_d;
    dp_first = {'i_data': 'first_RB', 'o_data': 'first_RB_d', 'i_clk': 'clk'}
    if IF_RST_N:
        dp_first['i_rst_n'] = 'rst_n'
    ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_first)  # type: ignore

    #/ wire last_RB_d;
    dp_last = {'i_data': 'last_RB', 'o_data': 'last_RB_d', 'i_clk': 'clk'}
    if IF_RST_N:
        dp_last['i_rst_n'] = 'rst_n'
    ModuleDelay(DWT=1, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_last)  # type: ignore

    # Per-lane logical-last-RB flag, delayed 1 clk to match the NN pipeline depth.
    # On a partial final beat the logical last RB is `lane = remainder-1`, not
    # necessarily the last physical lane; this gates the right-boundary fallback
    # on the correct lane.
    if RB_PARALLELISM > 1:
        ll_d = [f"lane_last_d_rb{rb}" for rb in range(RB_PARALLELISM)]
        #/ wire [`RB_PARALLELISM`-1:0] lane_last_d;
        dp_ll = {'i_data': 'lane_last', 'o_data': 'lane_last_d', 'i_clk': 'clk'}
        if IF_RST_N:
            dp_ll['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=RB_PARALLELISM, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_ll)  # type: ignore
        for rb in range(RB_PARALLELISM):
            #/ wire `ll_d[rb]` = lane_last_d[`rb`];
            pass

    # =========================================================================
    # Per-RB NN Interpolation Logic
    # =========================================================================
    # Helper to generate one NN datapath for a specific pilot subset.
    # For Hybrid mode this is called twice (t1 and t2) with output MUX.
    # For single-type, called once and wired directly to outputs.

    def _gen_nn_datapath(tag, sub_pilot_re, sub_lowest, sub_highest, rb, output_prefix, port_remap=None, assignment_override=None):
        """
        Generate NN interpolation wiring for a single pilot subset within one RB.
        All output wires are named {output_prefix}_re{k}.
        Pilot inputs come from the union set: pilot_rb{rb}_re{k}.
        port_remap: optional dict mapping sub RE → input port RE name.
        """
        sub_nn = (
            _classify_assignment(assignment_override)
            if assignment_override is not None
            else _classify_nn_output(sub_pilot_re)
        )
        sub_imm = sub_nn['immediate']
        sub_left = sub_nn['left_boundary']
        sub_right = sub_nn['right_boundary']

        pfx = f"{tag}_rb{rb}" if tag else f"rb{rb}"

        # Register prev-RB highest pilot for left-boundary.
        # For multi-RB: non-first lanes get prev data from the adjacent
        # lower lane (same clock, 1 clk delay). First/only lane wraps to
        # last lane (previous clock, 2 clk delay).
        prev_h = f"prev_highest_{pfx}"
        cur_h = _nn_pilot_wire(sub_highest, rb, port_remap)
        if has_prev_rb_highest and (RB_PARALLELISM == 1 or rb == 0):
            #/ wire [`COMPLEX_DWT`-1:0] `prev_h` = prev_rb_highest;
            pass
        elif RB_PARALLELISM > 1 and rb > 0:
            _m_h = port_remap.get(sub_highest, sub_highest) if port_remap else sub_highest
            prev_h_src = f"pilot_rb{rb - 1}_re{_m_h}"
            prev_h_delay = 1
            #/ wire [`COMPLEX_DWT`-1:0] `prev_h`;
            d_ph = {'i_data': prev_h_src, 'o_data': prev_h, 'i_clk': 'clk'}
            if IF_RST_N:
                d_ph['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=COMPLEX_DWT, N_CLK=prev_h_delay, IF_RST_N=IF_RST_N, PORTS=d_ph)  # type: ignore
        else:
            _m_h = port_remap.get(sub_highest, sub_highest) if port_remap else sub_highest
            prev_h_src = f"pilot_rb{RB_PARALLELISM - 1}_re{_m_h}" if RB_PARALLELISM > 1 else cur_h
            prev_h_delay = 2
            #/ wire [`COMPLEX_DWT`-1:0] `prev_h`;
            d_ph = {'i_data': prev_h_src, 'o_data': prev_h, 'i_clk': 'clk'}
            if IF_RST_N:
                d_ph['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=COMPLEX_DWT, N_CLK=prev_h_delay, IF_RST_N=IF_RST_N, PORTS=d_ph)  # type: ignore

        # Register highest pilot for right-boundary stall
        reg_h = f"reg_highest_{pfx}"
        #/ wire [`COMPLEX_DWT`-1:0] `reg_h`;
        d_rh = {'i_data': cur_h, 'o_data': reg_h, 'i_clk': 'clk'}
        if IF_RST_N:
            d_rh['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=d_rh)  # type: ignore

        # Immediate outputs (registered for 1-clk alignment)
        for re_k, src_k in sub_imm:
            src_sig = _nn_pilot_wire(src_k, rb, port_remap)
            reg_name = f"reg_imm_{pfx}_re{re_k}"
            out_name = f"{output_prefix}_re{re_k}"
            #/ wire [`COMPLEX_DWT`-1:0] `reg_name`;
            d_imm = {'i_data': src_sig, 'o_data': reg_name, 'i_clk': 'clk'}
            if IF_RST_N:
                d_imm['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=d_imm)  # type: ignore
            #/ wire [`COMPLEX_DWT`-1:0] `out_name` = `reg_name`;

        # Left-boundary outputs
        cur_l = _nn_pilot_wire(sub_lowest, rb, port_remap)
        if sub_left:
            reg_l = f"reg_lowest_{pfx}"
            #/ wire [`COMPLEX_DWT`-1:0] `reg_l`;
            d_rl = {'i_data': cur_l, 'o_data': reg_l, 'i_clk': 'clk'}
            if IF_RST_N:
                d_rl['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=d_rl)  # type: ignore

            for re_k in sub_left:
                out_name = f"{output_prefix}_re{re_k}"
                d_prev = re_k + (RE_PER_RB - sub_highest)
                d_cur = sub_lowest - re_k
                if d_prev <= d_cur:
                    if RB_PARALLELISM > 1 and rb > 0:
                        # Previous lane always available; no first_RB fallback
                        #/ wire [`COMPLEX_DWT`-1:0] `out_name` = `prev_h`;
                        pass
                    else:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_name` = first_RB_d ? `reg_l` : `prev_h`;
                        pass
                else:
                    #/ wire [`COMPLEX_DWT`-1:0] `out_name` = `reg_l`;
                    pass

        # Right-boundary outputs
        if sub_right:
            # Determine source for next sequential RB's lowest pilot.
            # Non-last lanes: adjacent lane provides data from the same clock,
            #   but must be registered (1 clk) to align with reg_h timing.
            # Last/only lane: wraps to rb0; next clock's input provides data
            #   via the stall mechanism (same as RB_PARALLELISM=1).
            if RB_PARALLELISM > 1 and rb < RB_PARALLELISM - 1:
                _m_l = port_remap.get(sub_lowest, sub_lowest) if port_remap else sub_lowest
                next_l_src = f"pilot_rb{rb + 1}_re{_m_l}"
                next_l = f"reg_next_l_{pfx}"
                #/ wire [`COMPLEX_DWT`-1:0] `next_l`;
                d_nl = {'i_data': next_l_src, 'o_data': next_l, 'i_clk': 'clk'}
                if IF_RST_N:
                    d_nl['i_rst_n'] = 'rst_n'
                ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=d_nl)  # type: ignore
            else:
                _m_l = port_remap.get(sub_lowest, sub_lowest) if port_remap else sub_lowest
                if has_next_rb_lowest:
                    next_l = "next_rb_lowest"
                else:
                    next_l = f"pilot_rb0_re{_m_l}"
            for re_k in sub_right:
                out_name = f"{output_prefix}_re{re_k}"
                d_high = re_k - sub_highest
                d_next = (12 + sub_lowest) - re_k
                if d_high <= d_next:
                    #/ wire [`COMPLEX_DWT`-1:0] `out_name` = `reg_h`;
                    pass
                else:
                    if RB_PARALLELISM > 1 and rb < RB_PARALLELISM - 1:
                        # Adjacent physical lane provides next-RB data for this
                        # lane's right boundary, UNLESS this lane is itself the
                        # logical last RB (partial final beat) — then fall back to
                        # the current RB's highest pilot instead of reading an
                        # invalid (padded) neighbour.
                        #/ wire [`COMPLEX_DWT`-1:0] `out_name` = `ll_d[rb]` ? `reg_h` : `next_l`;
                        pass
                    else:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_name` = last_RB_d ? `reg_h` : `next_l`;
                        pass

    # --- Main per-RB generation ---
    for rb in range(RB_PARALLELISM):
        #/ // ========== RB slot `rb` ==========

        if is_hybrid:
            #/ // ---- Type1 NN datapath ----
            _gen_nn_datapath('t1', pilot_re_t1, lowest_pilot_t1, highest_pilot_t1, rb, f"nn_t1_rb{rb}")
            #/ // ---- Type2 NN datapath ----
            _gen_nn_datapath('t2', pilot_re_t2, lowest_pilot_t2, highest_pilot_t2, rb, f"nn_t2_rb{rb}", port_remap=_t2_port_map if _use_compact else None)

            # MUX: select output based on runtime dmrs_type
            #/ // ---- Hybrid output MUX ----
            for re_k in range(RE_PER_RB):
                out_signal = f"h_nn_rb{rb}_re{re_k}"
                t1_sig = f"nn_t1_rb{rb}_re{re_k}"
                t2_sig = f"nn_t2_rb{rb}_re{re_k}"
                
                # dmrs_type: 0 = t1, 1 = t2
                #/ assign `out_signal` = dmrs_type ? `t2_sig` : `t1_sig`;
        else:
            # Single type: generate one NN datapath, wire directly to outputs
            _gen_nn_datapath('', pilot_re_sorted, lowest_pilot, highest_pilot, rb, f"nn_single_rb{rb}", assignment_override=(_nn_assignment_map_positions(pilot_re_sorted, sample_positions) if sample_positions is not None else None),)
            for re_k in range(RE_PER_RB):
                out_signal = f"h_nn_rb{rb}_re{re_k}"
                single_sig = f"nn_single_rb{rb}_re{re_k}"
                #/ assign `out_signal` = `single_sig`;

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Example: Type 2 CDM Group 0
    ModuleCORE_NN_INTERP(
        IF_RST_N=True,
        RB_PARALLELISM=1,
        Qu_H=QuType(12, 4, True),
        pilot_re=[0, 1, 6, 7],
        dmrs_Type=2,
    )
