#!/usr/bin/env python3
"""Derive PUSCH CE structural timing without importing the RTL TOP.

The tracked area-estimator package carries the same timing primitives as the
RTL generator.  This helper runs them in an isolated process so ``predict``
does not require the full (and separately distributed) RTL source tree.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AREA_MODEL_ROOT = PROJECT_ROOT / "Area_TP_Estimator" / "PUSCH_Est_pack"
sys.path.insert(0, str(AREA_MODEL_ROOT))

from PyTU import QuType  # noqa: E402
from analyze_timing import analyze_interp_timing, analyze_ls_timing  # noqa: E402
from dmrs_config import DmrsArchConfig, compute_required_re_indices  # noqa: E402


def _qutype(expression: Any, name: str) -> QuType:
    import re

    match = re.fullmatch(
        r"\s*QuType\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(True|False)\s*\)\s*",
        str(expression),
    )
    if match is None:
        raise ValueError(f"invalid {name} QuType expression: {expression!r}")
    return QuType(int(match.group(1)), int(match.group(2)), match.group(3) == "True")


def derive_structural_timing(config: Mapping[str, Any]) -> dict[str, Any]:
    protocol = config["protocol"]
    architecture = config["architecture"]
    quants = config["quantization"]

    rb_parallelism = int(architecture["rb_parallelism"])
    fi_parallelism = int(architecture["fi_lmmse_parallelism"])
    fi_re_parallelism = int(architecture["fi_re_parallelism"])
    ti_re_parallelism = int(architecture["ti_re_parallelism"])
    freq_method = str(architecture["freq_interp"])
    time_method = str(architecture["time_interp"])
    dmrs_type = protocol["dmrs_Type"]
    is_double = protocol["is_double_dmrs"]
    additional = list(protocol["additional_DMRS_range"])
    antenna_ports = list(protocol["antenna_ports"])
    switchable_ports = bool(architecture["switchable_ports"])

    y = _qutype(quants["Y"], "Y")
    h_ls = _qutype(quants["H_LS"], "H_LS")
    h_fi = _qutype(quants["H_FI"], "H_FI")
    fi_coeff = _qutype(quants["FI_LMMSE_COEFF"], "FI_LMMSE_COEFF")

    required_re = compute_required_re_indices(antenna_ports, dmrs_type)
    true_indices = [
        rb * 12 + re_index
        for rb in range(rb_parallelism)
        for re_index in required_re
    ]
    arch_config = DmrsArchConfig(
        antenna_ports=antenna_ports,
        dmrs_Type=dmrs_type,
        TRUE_INDEX_LIST=true_indices,
    )
    active_groups = sorted(
        {pcdmu.group_idx for pcdmu in arch_config.pcdmu_instances}
    )
    dmrs_parallelism = max(
        (pcdmu.max_re_count for pcdmu in arch_config.pcdmu_instances),
        default=12,
    )
    if switchable_ports or dmrs_type == "Hybrid":
        fd_cdm = {group: "Hybrid" for group in active_groups}
        td_cdm = {group: "Hybrid" for group in active_groups}
    else:
        fd_cdm = {
            pcdmu.group_idx: pcdmu.get_fdCDM(dmrs_type)
            for pcdmu in arch_config.pcdmu_instances
        }
        td_cdm = {
            pcdmu.group_idx: pcdmu.get_tdCDM(dmrs_type)
            for pcdmu in arch_config.pcdmu_instances
        }
    cdm_configs = []
    for pcdmu in arch_config.pcdmu_instances:
        group = pcdmu.group_idx
        if pcdmu.has_type1 and pcdmu.has_type2:
            averaging_type = dmrs_type
        elif pcdmu.has_type1:
            averaging_type = 1
        else:
            averaging_type = 2
        cdm_configs.append(
            {
                "group_idx": group,
                "avg_dmrs_type": averaging_type,
                "fdCDM": fd_cdm.get(group, 2),
                "tdCDM": td_cdm.get(group, 1),
            }
        )

    ls_timing = analyze_ls_timing(
        Qu_Y=y,
        QU_H_LS=h_ls,
        MAX_CDM_GROUPS=arch_config.MAX_CDM_GROUPS,
        DMRS_PARALLELISM=dmrs_parallelism,
        dmrs_Type=dmrs_type,
        is_double_dmrs=is_double,
        cdm_group_configs=cdm_configs,
        RB_PARALLELISM=rb_parallelism,
        freq_interp_method=freq_method,
        Qu_H_DWT=h_fi.DWT,
        additional_DMRS_range=additional,
        LMMSE_P=fi_parallelism,
        COEFF_DWT_LMMSE=fi_coeff.DWT,
        REAL_COEFF_LMMSE=bool(architecture["fi_lmmse_real_coeff"]),
        FI_RE_PARALLELISM=fi_re_parallelism,
    )

    max_occasions = 1 + max(additional)
    has_pre_fi_buf = (
        fi_parallelism > 0 and freq_method == "lmmse"
    ) or (
        max_occasions == 1
        and freq_method in ("nn", "linear")
        and time_method in ("nn", "linear")
    )
    interp_timing = analyze_interp_timing(
        freq_interp_method=freq_method,
        time_interp_method=time_method,
        Qu_H_DWT=h_fi.DWT,
        additional_DMRS_range=additional,
        FI_LMMSE_COEFF_DWT=fi_coeff.DWT,
        FI_LMMSE_P=fi_parallelism,
        FI_RB_PARALLELISM=rb_parallelism,
        FI_LMMSE_REAL_COEFF=bool(architecture["fi_lmmse_real_coeff"]),
        FI_RE_PARALLELISM=fi_re_parallelism,
        has_pre_fi_buf=has_pre_fi_buf,
    )

    if freq_method == "lmmse" and has_pre_fi_buf:
        fi_window_size = fi_parallelism
    elif has_pre_fi_buf:
        fi_window_size = rb_parallelism
    else:
        fi_window_size = 1

    if not has_pre_fi_buf:
        fi_cycles = 0
        fi_cycles_single = 0
    elif freq_method != "lmmse":
        fi_cycles = int(interp_timing["freq_depth"]) + 3
        fi_cycles_single = fi_cycles
    else:
        drain_beats = max(fi_parallelism // max(rb_parallelism, 1), 1)
        replay_single = drain_beats + int(ls_timing["pre_fi_pipeline_depth"]) + 6
        replay = replay_single
        if is_double is True or is_double == "Hybrid":
            replay += drain_beats + int(ls_timing["pre_fi_pipeline_depth"]) + 2
        fi_cycles_single = int(interp_timing["freq_depth"]) + drain_beats + replay_single
        fi_cycles = int(interp_timing["freq_depth"]) + drain_beats + replay

    minimum_rbs = int(protocol["num_RB_range"][0])
    safe_head = math.ceil(minimum_rbs / rb_parallelism) - 2
    drain_depth = (
        int(ls_timing["pre_fi_pipeline_depth"])
        if has_pre_fi_buf
        else int(ls_timing["total_pipeline_depth"])
    )
    early_ls_drain = max(drain_depth - safe_head, 1)
    symbol_duration = math.ceil(minimum_rbs / rb_parallelism)
    if safe_head < 0 or early_ls_drain > symbol_duration:
        raise ValueError("generated range violates early LS-drain timing")

    return {
        "rb_parallelism": rb_parallelism,
        "ti_re_parallelism": ti_re_parallelism,
        "early_ls_drain": early_ls_drain,
        "ti_pipeline_depth": int(interp_timing["time_depth"]),
        "has_pre_fi_buf": has_pre_fi_buf,
        "fi_window_size": fi_window_size,
        "fi_cycles_per_occ": fi_cycles,
        "fi_cycles_per_occ_single": fi_cycles_single,
    }


def main() -> int:
    try:
        config = json.load(sys.stdin)
        if not isinstance(config, dict):
            raise ValueError("configuration must be a JSON object")
        sys.stdout.write(json.dumps(derive_structural_timing(config)))
        return 0
    except (KeyError, LookupError, RuntimeError, TypeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
