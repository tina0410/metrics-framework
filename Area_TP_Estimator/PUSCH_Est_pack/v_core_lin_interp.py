from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Literal, List, Optional
from collections import defaultdict
from basic_modules import QuType, QuMode, OfMode, ModuleDelay, ModuleAdd, ModuleSub, ModuleFxMatch
from dmrs_config import InterpTopology
from delay_budget import DelayBudget, cost_adder, DEFAULT_BUDGET
from constants import RE_PER_RB


def _lin_pilot_wire(re_k, rb_idx, port_remap):
    """Build the pilot input wire name, applying port_remap if provided."""
    mapped = port_remap[re_k] if (port_remap and re_k in port_remap) else re_k
    return f"pilot_rb{rb_idx}_re{mapped}"


def lin_freq_pipeline_depth(Qu_H_DWT: int) -> int:
    """Pipeline depth of the linear freq interpolation core.

    Gap=5 shift-add chain with pipeline cut after x17:
      Stage 1 (comb): Sub(diff) + Add(x17)  →  pipeline register (N_CLK=1)
      Stage 2 (comb): Add(x51) + Add(H_L + scaled_diff)  →  output register
    Total: 2 clocks.
    """
    return 2


@convert
def ModuleCORE_LIN_INTERP(IF_RST_N: bool, RB_PARALLELISM: int, Qu_H: QuType, pilot_re: List[int], dmrs_Type: int | Literal["Hybrid"], pilot_re_t1: Optional[List[int]] = None, pilot_re_t2: Optional[List[int]] = None, compact_t2_slots: Optional[List[int]] = None, sample_positions: Optional[List[float]] = None, has_next_rb_lowest: bool = False, has_prev_rb_highest: bool = False) -> None:
    """
    RB-level Linear Frequency Interpolation Core.

    Given pilot-position channel estimates, this module fills all 12 RE
    positions per RB using linear interpolation with compile-time-known
    weights.

    **Interior REs** (between two pilots within the same RB):
      - TYPE1 (pilot spacing = 2): simple average ``(H_L + H_R) >>> 1``
      - TYPE2 (pilot spacing = 5): shift-add decomposition of ×(1/5).
        ``diff = H_R - H_L``, ``x17 = diff + (diff<<4)``,
        ``x51 = x17 + (x17<<1)``, ``result = H_L + d*x51/256``.
        Only 2 ``ModuleAdd`` stages for the shared ×51, plus 1 ``ModuleAdd``
        per RE for the final ``H_L + scaled_diff``.  No hardware multiplier.

    **Boundary REs** (below lowest / above highest pilot in current RB):
      - Cross-RB gap = 5 (Type 2): linear interpolation using the same
        shift-add ×51 chain, with ``first_RB``/``last_RB`` NN fallback.
      - Other gaps: nearest-neighbor fallback (same as CORE_NN_INTERP).

    **Fixed Latency**: 2 clock cycles (pipeline cut after x17 in gap=5 chain).

    :param IF_RST_N: True
    :param RB_PARALLELISM: 1
    :param Qu_H: QuType(12, 4, True)
    :param pilot_re: [0, 2, 4, 6, 8, 10]
    :param dmrs_Type: 1
    """

    pilot_re_sorted = sorted(pilot_re)
    if sample_positions is not None:
        if len(sample_positions) != len(pilot_re_sorted):
            raise ValueError("linear sample positions must match unique observation lanes")
        if any(float(position).is_integer() for position in sample_positions):
            raise ValueError("descriptor linear samples must identify averaged-lane centroids")
    lowest_pilot = pilot_re_sorted[0]
    highest_pilot = pilot_re_sorted[-1]

    # Only dual-type Hybrid ports need runtime dmrs_type switching. Hybrid
    # type-specific ports still elaborate as a single fixed pilot topology.
    is_hybrid = (dmrs_Type == "Hybrid" and pilot_re_t1 is not None and pilot_re_t2 is not None)

    DWT = Qu_H.DWT
    FRAC = Qu_H.FRAC
    COMPLEX_DWT = 2 * DWT
    SUM_W = DWT + 1

    # ---- Intermediate QuTypes for shift-add ×51 pipeline (gap=5) ----
    Qu_diff = QuType(DWT + 1, FRAC, True)
    Qu_d_s4 = QuType(DWT + 5, FRAC, True)
    Qu_x17  = QuType(DWT + 6, FRAC, True)
    Qu_x17s1 = QuType(DWT + 7, FRAC, True)
    Qu_x51  = QuType(DWT + 8, FRAC, True)
    Qu_step = QuType(DWT + 8, FRAC + 8, True)

    from v_core_nn_interp import _classify_nn_output

    # =========================================================================
    # Pipeline architecture — linear freq interpolation (depth = 2)
    # =========================================================================
    # Gap=5 shift-add chain with pipeline cut after x17 (N_CLK=1 on x17 adder):
    #   Stage 1: Sub(diff) + Add(x17)  → registered x17
    #   Stage 2: Add(x51) + scaled_add(H_L_q + step)  → output register
    # Gap=2 and pilot pass-through use N_CLK=2 delay for alignment.
    LIN_FREQ_DEPTH = 2

    # =========================================================================
    # Module Port Declaration
    # =========================================================================
    #/ `timescale 1ns / 1ps
    #/ module CORE_LIN_INTERP(
    #/     input clk,
    if IF_RST_N:
        #/ input rst_n,
        pass

    #/ input first_RB,
    #/ input last_RB,
    # Per-lane logical-last-RB flags (RB_PARALLELISM > 1).  The beat-level `last_RB`
    # marks the final beat, but on a partial final beat the logical last RB is the
    # `lane = remainder-1` lane, not necessarily the last physical lane.  These
    # flags gate the right-boundary NN fallback on the correct lane.
    if RB_PARALLELISM > 1:
        lane_last_in = [
            f"lane_last_rb{rb}" for rb in range(RB_PARALLELISM)
        ]
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

    for rb in range(RB_PARALLELISM):
        for k in pilot_re_sorted:
            in_name = f"pilot_rb{rb}_re{k}"
            #/ input [`COMPLEX_DWT`-1:0] `in_name`,
            pass

    out_names: List[str] = []
    for rb in range(RB_PARALLELISM):
        for k in range(RE_PER_RB):
            out_names.append(f"h_lin_rb{rb}_re{k}")

    for idx, on in enumerate(out_names):
        comma = "" if idx == len(out_names) - 1 else ","
        #/ output [`COMPLEX_DWT`-1:0] `on + comma`
        pass
    #/ );

    # =========================================================================
    # Pipeline-delayed boundary control signals (match 2-clk pipeline depth)
    # =========================================================================
    #/ wire first_RB_d;
    dp_first = {'i_data': 'first_RB', 'o_data': 'first_RB_d', 'i_clk': 'clk'}
    if IF_RST_N:
        dp_first['i_rst_n'] = 'rst_n'
    ModuleDelay(DWT=1, N_CLK=2, IF_RST_N=IF_RST_N, PORTS=dp_first)  # type: ignore

    #/ wire last_RB_d;
    dp_last = {'i_data': 'last_RB', 'o_data': 'last_RB_d', 'i_clk': 'clk'}
    if IF_RST_N:
        dp_last['i_rst_n'] = 'rst_n'
    ModuleDelay(DWT=1, N_CLK=2, IF_RST_N=IF_RST_N, PORTS=dp_last)  # type: ignore

    # Per-lane logical-last-RB flag, delayed to match the 2-clk pipeline depth.
    if RB_PARALLELISM > 1:
        ll_d = [f"lane_last_d_rb{rb}" for rb in range(RB_PARALLELISM)]
        #/ wire [`RB_PARALLELISM`-1:0] lane_last_d;
        dp_ll = {'i_data': 'lane_last', 'o_data': 'lane_last_d', 'i_clk': 'clk'}
        if IF_RST_N:
            dp_ll['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=RB_PARALLELISM, N_CLK=2, IF_RST_N=IF_RST_N, PORTS=dp_ll)  # type: ignore
        # emitters to reference bit selects below
        for rb in range(RB_PARALLELISM):
            #/ wire `ll_d[rb]` = lane_last_d[`rb`];
            pass

    # =========================================================================
    # Per-RB Interpolation Logic
    # =========================================================================

    # NOTE: This is only for DMRS Type 2 Linear interpolation.
    def _gen_x51_chain(chain_tag, h_l_r, h_l_i, h_r_r, h_r_i):
        """Generate diff->x17->x51 shift-add x51 chain for real and imag.

        Multiplier-free x51 decomposition (used for Type 2 pilot spacing = 5):
          diff = H_R - H_L                          (comb, Stage 1)
          x17  = diff + (diff << 4) = diff x 17     (registered, Stage 1 → pipe cut)
          x51  = x17  + (x17  << 1) = x17  x 3      (comb, Stage 2)

        Pipeline register after x17 (N_CLK=1) breaks the critical path
        into 2 balanced combinational stages.

        Output wires: x51_{chain_tag}_{r,i}   (available 1 clk after x17)
        """
        for pt, h_l, h_r in [('r', h_l_r, h_r_r), ('i', h_l_i, h_r_i)]:
            diff_n = f"diff_{chain_tag}_{pt}"
            ds4_n = f"ds4_{chain_tag}_{pt}"
            x17_n = f"x17_{chain_tag}_{pt}"
            x17s1_n = f"x17s1_{chain_tag}_{pt}"
            x51_n = f"x51_{chain_tag}_{pt}"

            #/ wire [`Qu_diff.DWT`-1:0] `diff_n`;
            ModuleSub(QU_IN_1=Qu_H, QU_IN_2=Qu_H, QU_OUT=Qu_diff, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': h_r, 'i_data_2': h_l, 'o_data': diff_n})  # type: ignore
            #/ wire [`Qu_d_s4.DWT`-1:0] `ds4_n` = {`diff_n`, 4'b0000};
            #/ wire [`Qu_x17.DWT`-1:0] `x17_n`;
            _x17_p = {'i_data_1': diff_n, 'i_data_2': ds4_n, 'o_data': x17_n, 'i_clk': 'clk'}
            if IF_RST_N:
                _x17_p['i_rst_n'] = 'rst_n'
            ModuleAdd(QU_IN_1=Qu_diff, QU_IN_2=Qu_d_s4, QU_OUT=Qu_x17, N_CLK=1, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=IF_RST_N, PORTS=_x17_p)  # type: ignore
            #/ // x17 is now registered (pipeline cut)
            #/ wire [`Qu_x17s1.DWT`-1:0] `x17s1_n` = {`x17_n`, 1'b0};
            #/ wire [`Qu_x51.DWT`-1:0] `x51_n`;
            ModuleAdd(QU_IN_1=Qu_x17, QU_IN_2=Qu_x17s1, QU_OUT=Qu_x51, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': x17_n, 'i_data_2': x17s1_n, 'o_data': x51_n})  # type: ignore

    # Helper: generate one complete linear interpolation datapath for a
    # specific pilot subset.  For Hybrid mode, called twice with prefixed
    # output wire names and a final dmrs_type MUX selects the output.

    def _gen_lin_datapath(tag, sub_pilot_re, rb, out_pfx, port_remap=None):
        """
        Generate linear interpolation hardware for one pilot subset.
        Output wires: {out_pfx}_re{k} for k in 0..11.
        All pilot inputs come from pilot_rb{rb}_re{k} (union set).
        port_remap: optional dict mapping sub RE → input port RE name.
        """
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

        # ---- Split complex inputs into real / imag (only for this sub-type's pilots) ----
        for k in sp:
            base = _lin_pilot_wire(k, rb, port_remap)
            ri_r = f"{pfx}_pil{k}_r"
            ri_i = f"{pfx}_pil{k}_i"
            #/ wire [`DWT`-1:0] `ri_r` = `base`[`DWT-1`:0];
            #/ wire [`DWT`-1:0] `ri_i` = `base`[`COMPLEX_DWT-1`:`DWT`];

        # ---- Select prev-RB highest pilot (for left boundary) ----
        # For multi-RB, non-first lanes consume the adjacent lower lane in
        # the same clock.  prev_h_pipe below supplies the one register needed
        # to align H_L with the registered x51 difference.  Lane 0/serial
        # operation instead crosses a clock boundary and therefore retains
        # the explicit delay from the final lane of the preceding batch.
        prev_h = f"prev_h_{pfx}"
        cur_h = _lin_pilot_wire(hi, rb, port_remap)
        if has_prev_rb_highest and (RB_PARALLELISM == 1 or rb == 0):
            #/ wire [`COMPLEX_DWT`-1:0] `prev_h` = prev_rb_highest;
            pass
        elif RB_PARALLELISM > 1 and rb > 0:
            prev_h_src = _lin_pilot_wire(hi, rb - 1, port_remap)
            #/ wire [`COMPLEX_DWT`-1:0] `prev_h` = `prev_h_src`;
            pass
        else:
            prev_h_src = _lin_pilot_wire(hi, RB_PARALLELISM - 1, port_remap) if RB_PARALLELISM > 1 else cur_h
            #/ wire [`COMPLEX_DWT`-1:0] `prev_h`;
            dp_ph = {'i_data': prev_h_src, 'o_data': prev_h, 'i_clk': 'clk'}
            if IF_RST_N:
                dp_ph['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_ph)  # type: ignore

        # Pipeline-aligned prev_h: 1 extra clk to match x51 pipeline register
        prev_h_pipe = f"prev_h_pipe_{pfx}"
        #/ wire [`COMPLEX_DWT`-1:0] `prev_h_pipe`;
        dp_php = {'i_data': prev_h, 'o_data': prev_h_pipe, 'i_clk': 'clk'}
        if IF_RST_N:
            dp_php['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_php)  # type: ignore

        # ---- Register current highest for right-boundary stall ----
        reg_h = f"reg_h_{pfx}"
        #/ wire [`COMPLEX_DWT`-1:0] `reg_h`;
        dp_rh = {'i_data': cur_h, 'o_data': reg_h, 'i_clk': 'clk'}
        if IF_RST_N:
            dp_rh['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_rh)  # type: ignore

        # Pipeline-aligned reg_h: 1 extra clk to match x51 pipeline register
        reg_h_pipe = f"reg_h_pipe_{pfx}"
        #/ wire [`COMPLEX_DWT`-1:0] `reg_h_pipe`;
        dp_rhp = {'i_data': reg_h, 'o_data': reg_h_pipe, 'i_clk': 'clk'}
        if IF_RST_N:
            dp_rhp['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_rhp)  # type: ignore

        # ---- Pilot pass-through: register 2 clk for alignment with pipeline depth ----
        for k in sp:
            src = _lin_pilot_wire(k, rb, port_remap)
            reg_p = f"reg_p_{pfx}_re{k}"
            out_w = f"{out_pfx}_re{k}"
            #/ wire [`COMPLEX_DWT`-1:0] `reg_p`;
            dp_p = {'i_data': src, 'o_data': reg_p, 'i_clk': 'clk'}
            if IF_RST_N:
                dp_p['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=COMPLEX_DWT, N_CLK=2, IF_RST_N=IF_RST_N, PORTS=dp_p)  # type: ignore
            #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `reg_p`;

        # ---- Interior REs: linear interpolation ----
        for (lp, rp), re_list in sub_pairs.items():
            gap = rp - lp
            h_l_base_r = f"{pfx}_pil{lp}_r"
            h_l_base_i = f"{pfx}_pil{lp}_i"
            h_r_base_r = f"{pfx}_pil{rp}_r"
            h_r_base_i = f"{pfx}_pil{rp}_i"
            pair_tag = f"{pfx}_p{lp}_{rp}"

            if gap == 2:
                for re_k in re_list:
                    ipfx = f"int_{pfx}_re{re_k}"
                    for pt, h_l, h_r in [('r', h_l_base_r, h_r_base_r), ('i', h_l_base_i, h_r_base_i)]:
                        w = f"{ipfx}_{pt}"
                        #/ wire [`SUM_W`-1:0] `w + '_s'` = {`h_l`[`DWT-1`], `h_l`} + {`h_r`[`DWT-1`], `h_r`};
                        #/ wire [`DWT`-1:0] `w` = `w + '_s'`[`SUM_W`-1:1];
                        pass

                    comb = f"comb_{ipfx}"
                    reg_c = f"reg_{ipfx}"
                    out_w = f"{out_pfx}_re{re_k}"
                    #/ wire [`COMPLEX_DWT`-1:0] `comb` = {`ipfx + '_i'`, `ipfx + '_r'`};
                    #/ wire [`COMPLEX_DWT`-1:0] `reg_c`;
                    dp_i = {'i_data': comb, 'o_data': reg_c, 'i_clk': 'clk'}
                    if IF_RST_N:
                        dp_i['i_rst_n'] = 'rst_n'
                    ModuleDelay(DWT=COMPLEX_DWT, N_CLK=2, IF_RST_N=IF_RST_N, PORTS=dp_i)  # type: ignore
                    #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `reg_c`;

            elif gap == 5:
                # ---- Shift-add ×51 path (gap=5) ----
                #/ // --- shift-add x51 for pair (`lp`, `rp`) ---
                _gen_x51_chain(pair_tag, h_l_base_r, h_l_base_i, h_r_base_r, h_r_base_i)

                # Delay H_L by 1 clk to align with pipelined x51 output
                h_l_q_r = f"h_l_q_{pair_tag}_r"
                h_l_q_i = f"h_l_q_{pair_tag}_i"
                #/ wire [`DWT`-1:0] `h_l_q_r`;
                dp_hlr = {'i_data': h_l_base_r, 'o_data': h_l_q_r, 'i_clk': 'clk'}
                if IF_RST_N:
                    dp_hlr['i_rst_n'] = 'rst_n'
                ModuleDelay(DWT=DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_hlr)  # type: ignore
                #/ wire [`DWT`-1:0] `h_l_q_i`;
                dp_hli = {'i_data': h_l_base_i, 'o_data': h_l_q_i, 'i_clk': 'clk'}
                if IF_RST_N:
                    dp_hli['i_rst_n'] = 'rst_n'
                ModuleDelay(DWT=DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_hli)  # type: ignore

                for re_k in re_list:
                    d = re_k - lp
                    ipfx = f"int_{pfx}_re{re_k}"
                    for pt, h_l in [('r', h_l_q_r), ('i', h_l_q_i)]:
                        x51_n = f"x51_{pair_tag}_{pt}"
                        w = f"{ipfx}_{pt}"
                        _gen_scaled_add(ipfx, pt, h_l, x51_n, d, w)
                        pass

                    comb = f"comb_{ipfx}"
                    reg_c = f"reg_{ipfx}"
                    out_w = f"{out_pfx}_re{re_k}"
                    #/ wire [`COMPLEX_DWT`-1:0] `comb` = {`ipfx + '_i'`, `ipfx + '_r'`};
                    #/ wire [`COMPLEX_DWT`-1:0] `reg_c`;
                    dp_i = {'i_data': comb, 'o_data': reg_c, 'i_clk': 'clk'}
                    if IF_RST_N:
                        dp_i['i_rst_n'] = 'rst_n'
                    ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_i)  # type: ignore
                    #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `reg_c`;
            else:
                # Unsupported gaps use the same deterministic nearest-neighbor
                # fallback documented by this core rather than emitting dangling wires.
                for re_k in re_list:
                    source = lp if (re_k - lp) <= (rp - re_k) else rp
                    src = _lin_pilot_wire(source, rb, port_remap)
                    out_w = f"{out_pfx}_re{re_k}"
                    #/ wire [`COMPLEX_DWT`-1:0] `out_w`;
                    ModuleDelay(DWT=COMPLEX_DWT, N_CLK=2, IF_RST_N=IF_RST_N, PORTS={'i_data': src, 'o_data': out_w, 'i_clk': 'clk', **({'i_rst_n': 'rst_n'} if IF_RST_N else {}),},)  # type: ignore

        # ---- Left-boundary REs ----
        if sub_left:
            reg_lo = f"reg_lo_{pfx}"
            cur_lo = _lin_pilot_wire(lo, rb, port_remap)
            #/ wire [`COMPLEX_DWT`-1:0] `reg_lo`;
            dp_lo = {'i_data': cur_lo, 'o_data': reg_lo, 'i_clk': 'clk'}
            if IF_RST_N:
                dp_lo['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=COMPLEX_DWT, N_CLK=2, IF_RST_N=IF_RST_N, PORTS=dp_lo)  # type: ignore

            if sub_cross_gap == 5:
                #/ wire [`DWT`-1:0] `prev_h + '_r'` = `prev_h`[`DWT-1`:0];
                #/ wire [`DWT`-1:0] `prev_h + '_i'` = `prev_h`[`COMPLEX_DWT-1`:`DWT`];

                lbnd_tag = f"lbnd_{pfx}"
                _gen_x51_chain(lbnd_tag, prev_h + '_r', prev_h + '_i',
                               f"{pfx}_pil{lo}_r", f"{pfx}_pil{lo}_i")

                # Delay prev_h (H_L) by 1 clk to align with pipelined x51
                #/ wire [`DWT`-1:0] `prev_h + '_r_q'` = `prev_h_pipe`[`DWT-1`:0];
                #/ wire [`DWT`-1:0] `prev_h + '_i_q'` = `prev_h_pipe`[`COMPLEX_DWT-1`:`DWT`];

                for re_k in sub_left:
                    d = re_k + RE_PER_RB - hi
                    lpfx = f"lbnd_{pfx}_re{re_k}"
                    for pt in ['r', 'i']:
                        h_l_b = prev_h + f'_{pt}_q'
                        x51_n = f"x51_{lbnd_tag}_{pt}"
                        w = f"{lpfx}_{pt}"
                        _gen_scaled_add(lpfx, pt, h_l_b, x51_n, d, w)

                    comb_lb = f"comb_{lpfx}"
                    reg_lb = f"reg_{lpfx}"
                    out_w = f"{out_pfx}_re{re_k}"
                    #/ wire [`COMPLEX_DWT`-1:0] `comb_lb` = {`lpfx + '_i'`, `lpfx + '_r'`};
                    #/ wire [`COMPLEX_DWT`-1:0] `reg_lb`;
                    dp_lb = {'i_data': comb_lb, 'o_data': reg_lb, 'i_clk': 'clk'}
                    if IF_RST_N:
                        dp_lb['i_rst_n'] = 'rst_n'
                    ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_lb)  # type: ignore
                    if RB_PARALLELISM > 1 and rb > 0:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `reg_lb`;
                        pass
                    else:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = first_RB_d ? `reg_lo` : `reg_lb`;
                        pass
            elif sub_cross_gap == 2:
                # Linear averaging: midpoint of prev-RB highest and cur-RB lowest.
                # For multi-RB non-first lanes, use direct adjacent lane data
                # (no delay) since both are available same clock. The extra pipeline
                # register (N_CLK=2) aligns the output with the 2-clk pipeline depth.
                if RB_PARALLELISM > 1 and rb > 0:
                    prev_lb2 = _lin_pilot_wire(hi, rb - 1, port_remap)
                    _lb2_reg_depth = 2
                else:
                    prev_lb2 = prev_h  # already 1-clk delayed
                    _lb2_reg_depth = 2  # prev_h valid at N, compute at N, reg 2 → N+2
                prev_lb2_r = f"prev_lb2_{pfx}_r"
                prev_lb2_i = f"prev_lb2_{pfx}_i"
                #/ wire [`DWT`-1:0] `prev_lb2_r` = `prev_lb2`[`DWT-1`:0];
                #/ wire [`DWT`-1:0] `prev_lb2_i` = `prev_lb2`[`COMPLEX_DWT-1`:`DWT`];

                for re_k in sub_left:
                    lpfx = f"lbnd_{pfx}_re{re_k}"
                    for pt, h_l, h_r in [('r', prev_lb2_r, f"{pfx}_pil{lo}_r"),
                                          ('i', prev_lb2_i, f"{pfx}_pil{lo}_i")]:
                        w = f"{lpfx}_{pt}"
                        #/ wire [`SUM_W`-1:0] `w + '_s'` = {`h_l`[`DWT-1`], `h_l`} + {`h_r`[`DWT-1`], `h_r`};
                        #/ wire [`DWT`-1:0] `w` = `w + '_s'`[`SUM_W`-1:1];
                        pass

                    comb_lb = f"comb_{lpfx}"
                    reg_lb = f"reg_{lpfx}"
                    out_w = f"{out_pfx}_re{re_k}"
                    #/ wire [`COMPLEX_DWT`-1:0] `comb_lb` = {`lpfx + '_i'`, `lpfx + '_r'`};
                    #/ wire [`COMPLEX_DWT`-1:0] `reg_lb`;
                    dp_lb = {'i_data': comb_lb, 'o_data': reg_lb, 'i_clk': 'clk'}
                    if IF_RST_N:
                        dp_lb['i_rst_n'] = 'rst_n'
                    ModuleDelay(DWT=COMPLEX_DWT, N_CLK=_lb2_reg_depth, IF_RST_N=IF_RST_N, PORTS=dp_lb)  # type: ignore
                    if RB_PARALLELISM > 1 and rb > 0:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `reg_lb`;
                        pass
                    else:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = first_RB_d ? `reg_lo` : `reg_lb`;
                        pass
            else:
                for re_k in sub_left:
                    out_w = f"{out_pfx}_re{re_k}"
                    d_prev = re_k + (RE_PER_RB - hi)
                    d_cur = lo - re_k
                    if d_prev <= d_cur:
                        if RB_PARALLELISM > 1 and rb > 0:
                            #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `prev_h_pipe`;
                            pass
                        else:
                            #/ wire [`COMPLEX_DWT`-1:0] `out_w` = first_RB_d ? `reg_lo` : `prev_h_pipe`;
                            pass
                    else:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `reg_lo`;
                        pass

        # ---- Right-boundary REs ----
        if sub_right:
            # Determine source for next sequential RB's lowest pilot.
            # Non-last lanes: adjacent lane data (same clock), registered
            #   to align with reg_h (1-clk stall timing).
            # Last/only lane: wraps to rb0; next clock provides data via
            #   the stall mechanism (same as RB_PARALLELISM=1).
            if RB_PARALLELISM > 1 and rb < RB_PARALLELISM - 1:
                next_lo_src = _lin_pilot_wire(lo, rb + 1, port_remap)
                next_lo_aligned = f"reg_next_lo_{pfx}"
                #/ wire [`COMPLEX_DWT`-1:0] `next_lo_aligned`;
                dp_nla = {'i_data': next_lo_src, 'o_data': next_lo_aligned, 'i_clk': 'clk'}
                if IF_RST_N:
                    dp_nla['i_rst_n'] = 'rst_n'
                ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_nla)  # type: ignore
            else:
                if has_next_rb_lowest:
                    next_lo_src = "next_rb_lowest"
                else:
                    next_lo_src = _lin_pilot_wire(lo, 0, port_remap)
                next_lo_aligned = next_lo_src  # stall provides alignment

            # Split next-RB lowest pilot into real/imag for interpolation
            next_lo_r = f"next_lo_{pfx}_r"
            next_lo_i = f"next_lo_{pfx}_i"
            #/ wire [`DWT`-1:0] `next_lo_r` = `next_lo_aligned`[`DWT-1`:0];
            #/ wire [`DWT`-1:0] `next_lo_i` = `next_lo_aligned`[`COMPLEX_DWT-1`:`DWT`];

            if sub_cross_gap == 5:
                #/ wire [`DWT`-1:0] `reg_h + '_r'` = `reg_h`[`DWT-1`:0];
                #/ wire [`DWT`-1:0] `reg_h + '_i'` = `reg_h`[`COMPLEX_DWT-1`:`DWT`];

                rbnd_tag = f"rbnd_{pfx}"
                _gen_x51_chain(rbnd_tag, reg_h + '_r', reg_h + '_i',
                               next_lo_r, next_lo_i)

                # Delay reg_h (H_L) by 1 clk to align with pipelined x51
                #/ wire [`DWT`-1:0] `reg_h + '_r_q'` = `reg_h_pipe`[`DWT-1`:0];
                #/ wire [`DWT`-1:0] `reg_h + '_i_q'` = `reg_h_pipe`[`COMPLEX_DWT-1`:`DWT`];

                for re_k in sub_right:
                    d = re_k - hi
                    rpfx = f"rbnd_{pfx}_re{re_k}"
                    for pt in ['r', 'i']:
                        h_l_b = reg_h + f'_{pt}_q'
                        x51_n = f"x51_{rbnd_tag}_{pt}"
                        w = f"{rpfx}_{pt}"
                        _gen_scaled_add(rpfx, pt, h_l_b, x51_n, d, w)

                    comb_rb = f"comb_{rpfx}"
                    out_w = f"{out_pfx}_re{re_k}"
                    #/ wire [`COMPLEX_DWT`-1:0] `comb_rb` = {`rpfx + '_i'`, `rpfx + '_r'`};
                    if RB_PARALLELISM > 1:
                        # Per-lane logical-last fallback: on a partial final beat the
                        # logical last RB is lane `remainder-1`, not RBP-1.
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `ll_d[rb]` ? `reg_h_pipe` : `comb_rb`;
                        pass
                    else:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = last_RB_d ? `reg_h_pipe` : `comb_rb`;
                        pass

            elif sub_cross_gap == 2:
                #/ wire [`DWT`-1:0] `reg_h + '_r'` = `reg_h`[`DWT-1`:0];
                #/ wire [`DWT`-1:0] `reg_h + '_i'` = `reg_h`[`COMPLEX_DWT-1`:`DWT`];

                for re_k in sub_right:
                    rpfx = f"rbnd_{pfx}_re{re_k}"
                    for pt, h_l, h_r in [('r', reg_h + '_r', next_lo_r),
                                          ('i', reg_h + '_i', next_lo_i)]:
                        w = f"{rpfx}_{pt}"
                        #/ wire [`SUM_W`-1:0] `w + '_s'` = {`h_l`[`DWT-1`], `h_l`} + {`h_r`[`DWT-1`], `h_r`};
                        #/ wire [`DWT`-1:0] `w` = `w + '_s'`[`SUM_W`-1:1];
                        pass

                    comb_rb = f"comb_{rpfx}"
                    reg_rb = f"reg_{rpfx}"
                    out_w = f"{out_pfx}_re{re_k}"
                    #/ wire [`COMPLEX_DWT`-1:0] `comb_rb` = {`rpfx + '_i'`, `rpfx + '_r'`};
                    #/ wire [`COMPLEX_DWT`-1:0] `reg_rb`;
                    dp_rb = {'i_data': comb_rb, 'o_data': reg_rb, 'i_clk': 'clk'}
                    if IF_RST_N:
                        dp_rb['i_rst_n'] = 'rst_n'
                    ModuleDelay(DWT=COMPLEX_DWT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=dp_rb)  # type: ignore
                    if RB_PARALLELISM > 1:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `ll_d[rb]` ? `reg_h_pipe` : `reg_rb`;
                        pass
                    else:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = last_RB_d ? `reg_h_pipe` : `reg_rb`;
                        pass
            else:
                # For non-last lanes, next_lo_aligned is already registered (1 clk),
                # so reduce the additional delay by 1.
                _extra_delay = 1 if (RB_PARALLELISM > 1 and rb < RB_PARALLELISM - 1) else 2
                for re_k in sub_right:
                    out_w = f"{out_pfx}_re{re_k}"
                    d_high = re_k - hi
                    d_next = (RE_PER_RB + lo) - re_k
                    if d_high <= d_next:
                        #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `reg_h_pipe`;
                        pass
                    else:
                        # Delay next_lo to match pipeline depth
                        next_lo_reg = f"next_lo_reg_{pfx}_re{re_k}"
                        #/ wire [`COMPLEX_DWT`-1:0] `next_lo_reg`;
                        dp_nl = {'i_data': next_lo_aligned, 'o_data': next_lo_reg, 'i_clk': 'clk'}
                        if IF_RST_N:
                            dp_nl['i_rst_n'] = 'rst_n'
                        ModuleDelay(DWT=COMPLEX_DWT, N_CLK=_extra_delay, IF_RST_N=IF_RST_N, PORTS=dp_nl)  # type: ignore
                        if RB_PARALLELISM > 1:
                            #/ wire [`COMPLEX_DWT`-1:0] `out_w` = `ll_d[rb]` ? `reg_h_pipe` : `next_lo_reg`;
                            pass
                        else:
                            #/ wire [`COMPLEX_DWT`-1:0] `out_w` = last_RB_d ? `reg_h_pipe` : `next_lo_reg`;
                            pass

        # ---- Non-pilot, non-interior, non-boundary REs that aren't covered ----
        # (all 12 should be covered by pilot + immediate + left + right)

    def _gen_scaled_add(prefix, pt, h_l, x51_name, d, out_name):
        """Generate H_L + d * x51 / 256 for distance d from left pilot.

        Linear interpolation for Type 2 DMRS (pilot gap = 5):
          H(k) = H_L + d/5 * (H_R - H_L)

        Since x51 = (H_R - H_L) * 51 (from _gen_x51_chain), and 51/256 ~ 1/5:
          H(k) = H_L + d * x51 / 256

        Distance-specific implementations (multiplier-free):
          d=1: step = x51                   (1/5 ~ 51/256 = 0.199)
          d=2: step = x51 << 1              (2/5 ~ 102/256 = 0.398)
          d=3: step = x51 + (x51 << 1)      (3/5 ~ 153/256 = 0.598)
          d=4: step = x51 << 2              (4/5 ~ 204/256 = 0.797)

        The /256 is implicit via Qu_step's fractional bits (FRAC+8).
        """
        if d == 1:
            step_name = f"step_{prefix}_{pt}"
            #/ wire [`Qu_step.DWT`-1:0] `step_name` = `x51_name`;
            #/ wire [`Qu_H.DWT`-1:0] `out_name`;
            ModuleAdd(QU_IN_1=Qu_H, QU_IN_2=Qu_step, QU_OUT=Qu_H, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': h_l, 'i_data_2': step_name, 'o_data': out_name})  # type: ignore
        elif d == 2:
            Qu_step_d2 = QuType(Qu_step.DWT + 1, Qu_step.FRAC, True)
            step_name = f"step_{prefix}_{pt}"
            #/ wire [`Qu_step_d2.DWT`-1:0] `step_name` = {`x51_name`, 1'b0};
            #/ wire [`Qu_H.DWT`-1:0] `out_name`;
            ModuleAdd(QU_IN_1=Qu_H, QU_IN_2=Qu_step_d2, QU_OUT=Qu_H, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': h_l, 'i_data_2': step_name, 'o_data': out_name})  # type: ignore
        elif d == 3:
            x51s1 = f"x51s1_d3_{prefix}_{pt}"
            Qu_x51s1_d3 = QuType(Qu_x51.DWT + 1, Qu_x51.FRAC, True)
            #/ wire [`Qu_x51s1_d3.DWT`-1:0] `x51s1` = {`x51_name`, 1'b0};
            x51x3 = f"x51x3_{prefix}_{pt}"
            Qu_x51x3 = QuType(Qu_x51.DWT + 2, Qu_x51.FRAC, True)
            #/ wire [`Qu_x51x3.DWT`-1:0] `x51x3`;
            ModuleAdd(QU_IN_1=Qu_x51, QU_IN_2=Qu_x51s1_d3, QU_OUT=Qu_x51x3, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': x51_name, 'i_data_2': x51s1, 'o_data': x51x3})  # type: ignore
            Qu_step_d3 = QuType(Qu_x51x3.DWT, Qu_x51x3.FRAC + 8, True)
            step_name = f"step_{prefix}_{pt}"
            #/ wire [`Qu_step_d3.DWT`-1:0] `step_name` = `x51x3`;
            #/ wire [`Qu_H.DWT`-1:0] `out_name`;
            ModuleAdd(QU_IN_1=Qu_H, QU_IN_2=Qu_step_d3, QU_OUT=Qu_H, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': h_l, 'i_data_2': step_name, 'o_data': out_name})  # type: ignore
        elif d == 4:
            Qu_step_d4 = QuType(Qu_step.DWT + 2, Qu_step.FRAC, True)
            step_name = f"step_{prefix}_{pt}"
            #/ wire [`Qu_step_d4.DWT`-1:0] `step_name` = {`x51_name`, 2'b00};
            #/ wire [`Qu_H.DWT`-1:0] `out_name`;
            ModuleAdd(QU_IN_1=Qu_H, QU_IN_2=Qu_step_d4, QU_OUT=Qu_H, N_CLK=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, PORTS={'i_data_1': h_l, 'i_data_2': step_name, 'o_data': out_name})  # type: ignore

    # --- Main per-RB generation ---
    for rb in range(RB_PARALLELISM):
        #/ // ========== RB slot `rb` ==========

        # Split all union pilots into real/imag (shared by both paths)
        for k in pilot_re_sorted:
            base = f"pilot_rb{rb}_re{k}"
            #/ wire [`DWT`-1:0] `base + '_r'` = `base`[`DWT-1`:0];
            #/ wire [`DWT`-1:0] `base + '_i'` = `base`[`COMPLEX_DWT-1`:`DWT`];

        _use_compact = is_hybrid and compact_t2_slots is not None
        _re_t1: List[int] = []
        _re_t2: List[int] = []

        if is_hybrid:
            assert pilot_re_t1 is not None and pilot_re_t2 is not None
            _re_t1 = sorted(pilot_re_t1)
            _re_t2 = sorted(pilot_re_t2)

        # Build T2 RE → compact port RE mapping
        _t2_port_map = {}
        if is_hybrid and _use_compact:
            assert compact_t2_slots is not None
            for t2_idx, slot in enumerate(compact_t2_slots):
                _t2_port_map[_re_t2[t2_idx]] = pilot_re_sorted[slot]

        if is_hybrid:
            #/ // ---- Type1 linear datapath ----
            _gen_lin_datapath('t1', _re_t1, rb, f"lin_t1_rb{rb}")
            #/ // ---- Type2 linear datapath ----
            _gen_lin_datapath('t2', _re_t2, rb, f"lin_t2_rb{rb}",
                             port_remap=_t2_port_map if _use_compact else None)

            #/ // ---- Hybrid output MUX ----
            for re_k in range(RE_PER_RB):
                out_signal = f"h_lin_rb{rb}_re{re_k}"
                t1_sig = f"lin_t1_rb{rb}_re{re_k}"
                t2_sig = f"lin_t2_rb{rb}_re{re_k}"
                #/ assign `out_signal` = dmrs_type ? `t2_sig` : `t1_sig`;
        else:
            _gen_lin_datapath('', pilot_re_sorted, rb, f"lin_single_rb{rb}")
            for re_k in range(RE_PER_RB):
                out_signal = f"h_lin_rb{rb}_re{re_k}"
                single_sig = f"lin_single_rb{rb}_re{re_k}"
                #/ assign `out_signal` = `single_sig`;

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Example: Type 1 CDM group 0
    ModuleCORE_LIN_INTERP(
        IF_RST_N=True,
        RB_PARALLELISM=1,
        Qu_H=QuType(12, 4, True),
        pilot_re=[0, 2, 4, 6, 8, 10],
        dmrs_Type=1,
    )
