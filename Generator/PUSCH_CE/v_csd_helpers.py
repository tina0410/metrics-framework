###################################################################################################
# Module: v_csd_helpers
# Description: Pure-Python compile-time helpers for CORE_TIME_LIN_INTERP.
#   Contains weight-table builders and CSD shift-and-add emission plan generator.
#   No pytv / @convert dependency -- safe to import freely without Pylance lag.
###################################################################################################
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from v_pilot_symbol_detection import DMRS_POSITION_MAP
from basic_modules import QuType

FRAC_BITS = 8   # fixed-point precision for interpolation weight alpha


# =============================================================================
# Weight computation helpers
# =============================================================================

def _build_lin_weight_table(
    *,
    dmrs_typeA_pos: int,
    is_double_dmrs: bool,
    n_additional_dmrs: int,
    pusch_symbol_length: int,
    n_out_syms: int,
) -> list:
    """
    For each target symbol 0 .. n_out_syms-1, compute (occ_L, occ_R, alpha_fix) where:
      h_out = h[occ_R] + alpha_fix/256 * (h[occ_L] - h[occ_R])
    alpha_fix in [0, 2^FRAC_BITS].  When occ_L == occ_R it is NN fallback.
    """
    symbol_type = 'double' if is_double_dmrs else 'single'
    key = ('A', symbol_type, n_additional_dmrs)
    entries = DMRS_POSITION_MAP.get(key, [])

    pos_raw = [0]
    for dur_range, pos_list in entries:
        if pusch_symbol_length in dur_range:
            pos_raw = pos_list
            break

    l0 = dmrs_typeA_pos
    positions = [l0 if p == 0 else p for p in pos_raw]
    num_occasions = len(positions)

    if is_double_dmrs:
        eff_pos = [p + 0.5 for p in positions]
    else:
        eff_pos = [float(p) for p in positions]

    scale = (1 << FRAC_BITS)
    result = []
    for sym in range(n_out_syms):
        if sym >= pusch_symbol_length:
            result.append((num_occasions - 1, num_occasions - 1, scale))
            continue
        left_occs  = [(i, eff_pos[i]) for i in range(num_occasions) if eff_pos[i] <= sym]
        right_occs = [(i, eff_pos[i]) for i in range(num_occasions) if eff_pos[i] >  sym]
        if not left_occs:
            result.append((0, 0, scale))
        elif not right_occs:
            result.append((num_occasions - 1, num_occasions - 1, scale))
        else:
            j_L_idx, p_L = left_occs[-1]
            j_R_idx, p_R = right_occs[0]
            if p_R == p_L:
                result.append((j_L_idx, j_L_idx, scale))
            else:
                alpha     = (p_R - sym) / (p_R - p_L)
                alpha_fix = round(alpha * scale)
                alpha_fix = max(0, min(scale, alpha_fix))
                result.append((j_L_idx, j_R_idx, alpha_fix))
    return result


def _build_all_lin_tables(
    *,
    dmrs_typeA_pos_options: list,
    is_double_dmrs_options: list,
    additional_DMRS_range: list,
    num_symbols_range: list,
    n_out_syms: int,
) -> dict:
    """Build weight tables for every supported config combo."""
    tables = {}
    for l0 in dmrs_typeA_pos_options:
        for dbl in is_double_dmrs_options:
            for n_add in additional_DMRS_range:
                for n_sym in num_symbols_range:
                    tbl = _build_lin_weight_table(
                        dmrs_typeA_pos=l0,
                        is_double_dmrs=dbl,
                        n_additional_dmrs=n_add,
                        pusch_symbol_length=n_sym,
                        n_out_syms=n_out_syms,
                    )
                    tables[(l0, dbl, n_add, n_sym)] = tbl
    return tables


# =============================================================================
# CSD (Canonical Signed Digit) encoding helpers
# =============================================================================

def _csd_encode(value: int) -> list:
    """
    Encode *value* into Canonical Signed Digit form.
    Returns list of (sign, bit_position) for non-zero digits.
    CSD guarantees no two consecutive non-zero digits.

    Example: _csd_encode(51) -> [(-1,0), (+1,2), (-1,4), (+1,6)]
             since -1 + 4 - 16 + 64 = 51
    """
    if value == 0:
        return []
    digits = []
    v, i = value, 0
    while v != 0:
        if v & 1:
            if (v & 3) == 3:
                digits.append((-1, i)); v += 1
            else:
                digits.append((+1, i)); v -= 1
        v >>= 1
        i += 1
    return digits


def _csd_build_chain(diff_name: str, Qu_diff, alpha_fix: int, prefix: str):
    """
    Build CSD shift-and-add op-list for ``alpha_fix * diff``.

    Returns (ops, result_name, Qu_result).
    Each op is a tuple with type tag as first element:
      ('shift', wire_name, src, shift_amt, Qu_wire)
      ('neg',   wire_name, src, Qu_src, Qu_out)
      ('add',   wire_name, in1, Qu_in1, in2, Qu_in2, Qu_out)
      ('sub',   wire_name, in1, Qu_in1, in2, Qu_in2, Qu_out)
    """
    if alpha_fix == 0:
        return [], None, None
    digits = _csd_encode(alpha_fix)
    if not digits:
        return [], None, None

    ops = []
    prev_name, prev_qu = None, None

    for step_idx, (sign, bit_pos) in enumerate(digits):
        shifted_name = f"{prefix}_sh{bit_pos}"
        shifted_dwt  = Qu_diff.DWT + bit_pos
        Qu_shifted   = QuType(shifted_dwt, Qu_diff.FRAC, Qu_diff.IF_SIGNED)
        ops.append(('shift', shifted_name, diff_name, bit_pos, Qu_shifted))

        if prev_name is None:
            if sign == -1:
                neg_name = f"{prefix}_neg{step_idx}"
                Qu_neg   = QuType(shifted_dwt + 1, Qu_diff.FRAC, True)
                ops.append(('neg', neg_name, shifted_name, Qu_shifted, Qu_neg))
                prev_name, prev_qu = neg_name, Qu_neg
            else:
                prev_name, prev_qu = shifted_name, Qu_shifted
        else:
            acc_name = f"{prefix}_acc{step_idx}"
            acc_dwt  = max(prev_qu.DWT, Qu_shifted.DWT) + 1
            Qu_acc   = QuType(acc_dwt, Qu_diff.FRAC, True)
            if sign == +1:
                ops.append(('add', acc_name, prev_name, prev_qu, shifted_name, Qu_shifted, Qu_acc))
            else:
                ops.append(('sub', acc_name, prev_name, prev_qu, shifted_name, Qu_shifted, Qu_acc))
            prev_name, prev_qu = acc_name, Qu_acc

    Qu_result = QuType(prev_qu.DWT, prev_qu.FRAC + FRAC_BITS, prev_qu.IF_SIGNED)
    return ops, prev_name, Qu_result


# =============================================================================
# Emission plan builder  (Layers 2+3)
# =============================================================================

def _build_csd_emission_plan(
    *,
    unique_tables: list,
    NUM_TABLES: int,
    single_table: bool,
    N_OUT_SYMS: int,
    Qu_comp,
    Qu_diff,
    H_DWT: int,
    TBL_IDX_W: int,
    scale: int,
) -> list:
    """
    Pre-compute the entire Verilog emission plan for Layers 2+3 of
    CORE_TIME_LIN_INTERP.  Returns a flat list of task tuples:

      ('vlines', [str, ...]) -- Verilog lines; emitted one-per-line via ``#/ `line` ``
      ('mod_sub', Qu_in1, Qu_in2, Qu_out, i1, i2, out) -- ModuleSub N_CLK=0
      ('mod_add', Qu_in1, Qu_in2, Qu_out, i1, i2, out) -- ModuleAdd N_CLK=0
      ('mod_delay', H_DWT, data_in, data_out)           -- ModuleDelay N_CLK=1

    All QuType objects are computed here; the @convert dispatcher only needs
    to call the correct basic_module function for the add/sub/delay tasks.
    """
    plan: list = []
    COMP_DWT = Qu_comp.DWT

    def vl(*lines: str) -> None:
        plan.append(('vlines', list(lines)))

    def emit_csd_ops(ops: list, pfx: str) -> None:
        """Append plan entries for all ops in a CSD chain."""
        for op in ops:
            if op[0] == 'shift':
                _, wire_name, src, shift_amt, Qu_w = op
                if shift_amt == 0:
                    vl(f"wire [{Qu_w.DWT}-1:0] {wire_name} = {src};")
                else:
                    vl(f"wire [{Qu_w.DWT}-1:0] {wire_name} = {{{src}, {shift_amt}'b0}};")
            elif op[0] == 'neg':
                _, wire_name, src_n, Qu_src, Qu_out = op
                zero_name = f"{pfx}_z"
                vl(
                    f"wire signed [{Qu_src.DWT}-1:0] {zero_name} = {Qu_src.DWT}'sb0;",
                    f"wire [{Qu_out.DWT}-1:0] {wire_name};",
                )
                plan.append(('mod_sub', Qu_src, Qu_src, Qu_out, zero_name, src_n, wire_name))
            elif op[0] == 'add':
                _, wire_name, in1, Qu_in1, in2, Qu_in2, Qu_out = op
                vl(f"wire [{Qu_out.DWT}-1:0] {wire_name};")
                plan.append(('mod_add', Qu_in1, Qu_in2, Qu_out, in1, in2, wire_name))
            elif op[0] == 'sub':
                _, wire_name, in1, Qu_in1, in2, Qu_in2, Qu_out = op
                vl(f"wire [{Qu_out.DWT}-1:0] {wire_name};")
                plan.append(('mod_sub', Qu_in1, Qu_in2, Qu_out, in1, in2, wire_name))

    def emit_variant(occ_L: int, occ_R: int, alpha_fix: int, tag: str) -> str:
        """Append plan entries for one interpolation variant. Returns var_comb name."""
        if alpha_fix == scale:
            var_comb = f"{tag}_comb"
            vl(f"wire [{H_DWT}-1:0] {var_comb} = h_pilot_occ{occ_L};")
            return var_comb
        if alpha_fix == 0:
            var_comb = f"{tag}_comb"
            vl(f"wire [{H_DWT}-1:0] {var_comb} = h_pilot_occ{occ_R};")
            return var_comb

        for part in ['re', 'im']:
            diff_name = f"diff_{occ_L}_{occ_R}_{part}"
            pfx = f"{tag}_{part}"
            ops, csd_result_name, Qu_csd = _csd_build_chain(diff_name, Qu_diff, alpha_fix, pfx)
            emit_csd_ops(ops, pfx)
            hR_name    = f"occ{occ_R}_{part}"
            final_name = f"{tag}_f_{part}"
            vl(f"wire [{COMP_DWT}-1:0] {final_name};")
            plan.append(('mod_add', Qu_comp, Qu_csd, Qu_comp, hR_name, csd_result_name, final_name))

        var_comb = f"{tag}_comb"
        vl(f"wire [{H_DWT}-1:0] {var_comb} = {{{tag}_f_im, {tag}_f_re}};")
        return var_comb

    # ---- Per-symbol emission ----
    for sym in range(N_OUT_SYMS):
        weights_per_table = [unique_tables[t][sym] for t in range(NUM_TABLES)]
        all_nn = all(w[2] == scale and w[0] == w[1] for w in weights_per_table)

        if all_nn:
            occ = weights_per_table[0][0]
            if single_table or len(set(w[0] for w in weights_per_table)) == 1:
                nn_comb = f"nn_comb_s{sym}"
                nn_reg  = f"nn_reg_s{sym}"
                vl(
                    f"// sym{sym}: NN fallback -- occasion {occ}",
                    f"wire [{H_DWT}-1:0] {nn_comb} = h_pilot_occ{occ};",
                    f"wire [{H_DWT}-1:0] {nn_reg};",
                )
                plan.append(('mod_delay', H_DWT, nn_comb, nn_reg))
                vl(f"assign h_time_sym{sym} = {nn_reg};", "")
            else:
                occ_per_table = [w[0] for w in weights_per_table]
                mux_name = f"nn_mux_s{sym}"
                nn_reg   = f"nn_reg_s{sym}"
                lines = [
                    f"// sym{sym}: NN fallback -- runtime occasion select",
                    f"reg [{H_DWT}-1:0] {mux_name};",
                    f"always @(*) begin",
                    f"  case (tbl_idx)",
                ]
                for t_idx, o in enumerate(occ_per_table):
                    lines.append(f"  {TBL_IDX_W}'d{t_idx}: {mux_name} = h_pilot_occ{o};")
                lines += [
                    f"  default: {mux_name} = h_pilot_occ0;",
                    f"  endcase",
                    f"end",
                    f"wire [{H_DWT}-1:0] {nn_reg};",
                ]
                vl(*lines)
                plan.append(('mod_delay', H_DWT, mux_name, nn_reg))
                vl(f"assign h_time_sym{sym} = {nn_reg};", "")

        else:
            unique_configs: dict = {}
            for t_idx_w, (occ_L_w, occ_R_w, alpha_fix_w) in enumerate(weights_per_table):
                cfg_key = (occ_L_w, occ_R_w, alpha_fix_w)
                if cfg_key not in unique_configs:
                    unique_configs[cfg_key] = []
                unique_configs[cfg_key].append(t_idx_w)

            need_mux = (not single_table) and (len(unique_configs) > 1)

            if not need_mux:
                occ_L, occ_R, alpha_fix = weights_per_table[0]
                tag = f"s{sym}"
                vl(f"// sym{sym}: linear occ{occ_L}<->occ{occ_R} alpha={alpha_fix}/{scale}")
                result_comb = emit_variant(occ_L, occ_R, alpha_fix, tag)
                result_reg  = f"reg_s{sym}"
                vl(f"wire [{H_DWT}-1:0] {result_reg};")
                plan.append(('mod_delay', H_DWT, result_comb, result_reg))
                vl(f"assign h_time_sym{sym} = {result_reg};", "")
            else:
                vl(f"// sym{sym}: {len(unique_configs)} variants -- runtime MUX")
                variant_regs = []
                for v_idx, ((occ_L, occ_R, alpha_fix), tbl_indices) in enumerate(unique_configs.items()):
                    tag      = f"v{v_idx}_s{sym}"
                    var_comb = emit_variant(occ_L, occ_R, alpha_fix, tag)
                    var_reg  = f"v{v_idx}_reg_s{sym}"
                    vl(f"wire [{H_DWT}-1:0] {var_reg};")
                    plan.append(('mod_delay', H_DWT, var_comb, var_reg))
                    variant_regs.append((v_idx, tbl_indices, var_reg))

                tbl_idx_d   = f"tbl_idx_d_s{sym}"
                mux_name    = f"mux_s{sym}"
                default_reg = variant_regs[0][2]
                mux_lines = [
                    f"reg [{TBL_IDX_W}-1:0] {tbl_idx_d};",
                    f"always @(posedge clk) {tbl_idx_d} <= tbl_idx;",
                    f"reg [{H_DWT}-1:0] {mux_name};",
                    f"always @(*) begin",
                    f"  {mux_name} = {default_reg};",
                    f"  case ({tbl_idx_d})",
                ]
                for v_idx, tbl_indices, var_reg in variant_regs:
                    for t_idx in tbl_indices:
                        mux_lines.append(f"  {TBL_IDX_W}'d{t_idx}: {mux_name} = {var_reg};")
                mux_lines += [f"  default: {mux_name} = {default_reg};", f"  endcase", f"end"]
                vl(*mux_lines)
                vl(f"assign h_time_sym{sym} = {mux_name};", "")

    return plan
