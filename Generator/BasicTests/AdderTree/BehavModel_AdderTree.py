# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
"""Python reference model used by the AdderTree RTL testbench template."""


def pack_lanes(values: list[int], width: int) -> int:
    mask = (1 << width) - 1
    return sum((value & mask) << (index * width) for index, value in enumerate(values))


def adder_tree_expected(values: list[int], output_width: int) -> int:
    return sum(values) & ((1 << output_width) - 1)
