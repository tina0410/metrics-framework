# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
"""Python reference model used by the Delay RTL testbench template."""


def delay_expected(samples: list[int], n_clk: int) -> list[int]:
    if n_clk < 0:
        raise ValueError("n_clk must be non-negative")
    if n_clk == 0:
        return list(samples)
    return ([0] * n_clk + list(samples))[: len(samples)]
