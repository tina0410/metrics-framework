###################################################################################################
# Module Name: config_space
# Description: Pure Python helper for expanding DMRS configuration space parameters
#   shared by time-domain interpolation cores (NN, Linear, LMMSE).
#   Eliminates ~30-50 lines of duplicated parameter parsing in each core.
#
# Author: Auto-generated (refactoring)
# Date: 2026.3.15
# Version: V0.1.0
###################################################################################################
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class ConfigSpace:
    """Expanded DMRS configuration space for time-domain interpolation cores.

    All fields are derived from the user-facing parameters
    ``dmrs_typeA_pos``, ``is_double_dmrs``, ``additional_DMRS_range``,
    and ``num_symbols_range``.
    """
    # Compile-time option lists
    l0_options: List[int]
    """Possible DMRS TypeA starting symbol positions (e.g. [2], [3], or [2,3])."""

    dbl_options: List[bool]
    """Possible double-DMRS settings (e.g. [False], [True], or [False, True])."""

    sym_list: List[int]
    """All supported PUSCH symbol lengths (contiguous range)."""

    N_OUT_SYMS: int
    """Maximum output symbol count = max(num_symbols_range)."""

    n_add_max: int
    """Maximum additional DMRS count."""

    n_add_width: int
    """Bit-width to encode n_additional_dmrs (ceil(log2(n_add_max + 1)))."""

    # Runtime selection flags
    needs_runtime_l0: bool
    """True when dmrs_typeA_pos is 'Hybrid' → 1-bit runtime selector needed."""

    needs_runtime_dbl: bool
    """True when is_double_dmrs is 'Hybrid' → 1-bit runtime selector needed."""

    needs_runtime_nadd: bool
    """True when additional_DMRS_range has more than one value."""

    needs_runtime_nsym: bool
    """True when num_symbols_range spans more than one value."""


def expand_config_space(
    dmrs_typeA_pos: str,
    is_double_dmrs: bool | str,
    additional_DMRS_range: List[int],
    num_symbols_range: List[int],
) -> ConfigSpace:
    """Expand DMRS configuration parameters into a ``ConfigSpace``.

    This function replaces the repeated ~30-line preamble present in
    ``v_core_time_nn_interp.py``, ``v_core_time_lin_interp.py``, and
    similar modules.

    Parameters
    ----------
    dmrs_typeA_pos : str
        ``'pos2'``, ``'pos3'``, or ``'Hybrid'``.
    is_double_dmrs : bool | str
        ``True``, ``False``, or ``'Hybrid'``.
    additional_DMRS_range : list of int
        Supported additional DMRS counts (e.g. ``[0, 2]``).
    num_symbols_range : list of int
        Supported PUSCH symbol lengths (e.g. ``[4, 14]`` meaning 4..14).

    Returns
    -------
    ConfigSpace
    """
    # ---- l0_options ----
    if dmrs_typeA_pos == 'pos2':
        l0_options = [2]
    elif dmrs_typeA_pos == 'pos3':
        l0_options = [3]
    elif dmrs_typeA_pos == 'Hybrid':
        l0_options = [2, 3]
    else:
        raise ValueError(f"Invalid dmrs_typeA_pos: {dmrs_typeA_pos}")

    # ---- dbl_options ----
    if is_double_dmrs == "Hybrid":
        dbl_options = [False, True]
    elif is_double_dmrs:
        dbl_options = [True]
    else:
        dbl_options = [False]

    # ---- Symbol range ----
    min_sym = num_symbols_range[0]
    max_sym = num_symbols_range[-1]
    N_OUT_SYMS = max_sym
    sym_list = list(range(min_sym, max_sym + 1))

    # ---- Additional DMRS encoding ----
    n_add_max = max(additional_DMRS_range)
    n_add_width = max(math.ceil(math.log2(n_add_max + 1)), 1) if n_add_max > 0 else 1

    # ---- Runtime selection flags ----
    needs_runtime_l0 = (dmrs_typeA_pos == 'Hybrid')
    needs_runtime_dbl = (is_double_dmrs == "Hybrid")
    needs_runtime_nadd = (len(additional_DMRS_range) > 1)
    needs_runtime_nsym = (len(sym_list) > 1)

    return ConfigSpace(
        l0_options=l0_options,
        dbl_options=dbl_options,
        sym_list=sym_list,
        N_OUT_SYMS=N_OUT_SYMS,
        n_add_max=n_add_max,
        n_add_width=n_add_width,
        needs_runtime_l0=needs_runtime_l0,
        needs_runtime_dbl=needs_runtime_dbl,
        needs_runtime_nadd=needs_runtime_nadd,
        needs_runtime_nsym=needs_runtime_nsym,
    )
