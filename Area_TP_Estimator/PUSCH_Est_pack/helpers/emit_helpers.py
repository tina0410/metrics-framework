###################################################################################################
# Module Name: emit_helpers
# Description: Pure Python helpers for generating Verilog port/wire declaration strings.
#   Returns lists of strings to be emitted inside @convert functions via:
#     for line in result:
#         #/ `line`
#         pass
#
# Author: Auto-generated (refactoring)
# Date: 2026.3.15
# Version: V0.1.0
###################################################################################################
from typing import List, Optional


def emit_port_list(
    names: List[str],
    dwt_expr: str,
    direction: str = 'output',
    last_has_comma: bool = False,
) -> List[str]:
    """Generate Verilog port declaration lines for a list of signal names.

    Each returned string is a raw Verilog line (without ``#/`` prefix).
    Commas are inserted between entries; the last entry omits the comma
    unless *last_has_comma* is True.

    Usage inside an @convert function::

        for line in emit_port_list(port_names, f'{DWT}-1:0', 'output'):
            #/ `line`
            pass

    Parameters
    ----------
    names : list of str
        Signal names.
    dwt_expr : str
        Bit-range expression, e.g. ``'23'`` for ``[23:0]`` or ``'DWT-1'``
        for ``[DWT-1:0]``.  Pass ``''`` for 1-bit ports.
    direction : str
        ``'input'``, ``'output'``, or ``'wire'``.
    last_has_comma : bool
        If True, the last entry also ends with a comma (useful when more
        ports follow after this block).

    Returns
    -------
    list of str
        Verilog lines ready for ``#/ `line` `` emission.
    """
    lines: List[str] = []
    width_part = f" [{dwt_expr}:0]" if dwt_expr else ""
    for idx, name in enumerate(names):
        is_last = (idx == len(names) - 1)
        comma = "" if (is_last and not last_has_comma) else ","
        lines.append(f"{direction}{width_part} {name}{comma}")
    return lines


def wire_declare(name: str, dwt_expr: str) -> str:
    """Generate a single ``wire [DWT-1:0] name;`` declaration string.

    Parameters
    ----------
    name : str
        Signal name.
    dwt_expr : str
        Bit-range expression (e.g. ``'24-1'``).  Pass ``''`` for 1-bit.

    Returns
    -------
    str
        Verilog wire declaration line.
    """
    if dwt_expr:
        return f"wire [{dwt_expr}:0] {name};"
    return f"wire {name};"


def wire_declare_many(names: List[str], dwt_expr: str) -> List[str]:
    """Generate wire declarations for multiple signals (same width).

    Returns
    -------
    list of str
        Verilog wire declaration lines.
    """
    return [wire_declare(n, dwt_expr) for n in names]
