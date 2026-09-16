# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
"""Python reference model used by the MUX RTL testbench template."""


def pack_lanes(values: list[int], width: int) -> int:
    mask = (1 << width) - 1
    return sum((value & mask) << (index * width) for index, value in enumerate(values))


def mux_expected(packed: int, select: int, n_inputs: int, width: int) -> int:
    if not 0 <= select < n_inputs:
        return 0
    return (packed >> (select * width)) & ((1 << width) - 1)
