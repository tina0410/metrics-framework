"""
XOR-Tree Logic Generator for Fast LFSR State Jumping (Infinite Sequence Support)

This module implements a generator for parallel XOR-tree logic that calculates
the future sequence of a Linear Feedback Shift Register (LFSR) starting from
a specific future time offset (N_taps).

Unlike simple state jumping, this version supports generating an arbitrary 
number of output bits (N_bits) by iteratively advancing the transition matrix.
This allows generating a parallel bus of 100+ bits even if the LFSR state 
size is small (e.g., 31 bits).

Logic derivation:
    Bit[i] corresponds to the LSB (Row 0) of the state at time (t + N_taps + i).
    
    Let M be the single-step matrix.
    Logic_Mask_0 = Row_0( M^(N_taps) )
    Logic_Mask_1 = Row_0( M^(N_taps+1) )
    ...

Example Usage (31-bit LFSR):
    >>> rows = [ ... ] # Define LFSR structure
    >>> # Generate logic for 64 consecutive bits starting from offset 1600
    >>> ModuleXOR_TREE(LFSR=rows, N_taps=1600, N_bits=64, ...)
"""

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import os, sys
from os.path import dirname

sys.path.append(dirname(__file__))
from basic_modules import ModuleDelay

def build_balanced_xor(signals: list[str]) -> str:
    """
    Build a balanced binary XOR tree expression.

    This guarantees logarithmic logic depth and stable timing.
    """
    if len(signals) == 1:
        return signals[0]
    mid = len(signals) // 2
    left = build_balanced_xor(signals[:mid])
    right = build_balanced_xor(signals[mid:])
    return f"({left} ^ {right})"


def popcount(n):
    """Return number of set bits in integer n."""
    return bin(n).count('1')


class GF2Matrix:
    """
    GF(2) matrix model for a square binary matrix.
    Each row is stored as an integer bitmask.
    """
    def __init__(self, size=31, rows=None):
        self.size = size
        self.rows = rows if rows else [0] * size

    @staticmethod
    def identity(size=31):
        """Return identity matrix."""
        return GF2Matrix(size, [(1 << i) for i in range(size)])

    def multiply(self, other):
        """Matrix multiplication in GF(2). self * other"""
        new_rows = [0] * self.size
        for r in range(self.size):
            acc = 0
            row_map = self.rows[r]
            for k in range(self.size):
                if (row_map >> k) & 1:
                    acc ^= other.rows[k]
            new_rows[r] = acc
        return GF2Matrix(self.size, new_rows)

    def power(self, n):
        """Fast exponentiation: self^n in GF(2)."""
        res = GF2Matrix.identity(self.size)
        base = GF2Matrix(self.size, list(self.rows))
        while n > 0:
            if n & 1:
                res = res.multiply(base)
            base = base.multiply(base)
            n >>= 1
        return res

    def apply(self, vec_val):
        """Apply matrix to vector (integer bitmask)."""
        res = 0
        for r in range(self.size):
            if popcount(self.rows[r] & vec_val) & 1:
                res |= (1 << r)
        return res

    def display(self) -> list[str]:
        return [f"{self.rows[r]:0{self.size}b}" for r in range(self.size)]


@convert
def ModuleXOR_TREE(LFSR: list[int], N_taps: int, N_bits: int, N_CLK: int, IF_RST_N: bool) -> None:
    """
    Generate a combinational XOR-tree followed by optional pipeline delays.

    Each output bit `o_data[i]` represents the LSB of the LFSR sequence 
    at time step `t + N_taps + i`.

    The selection mask is derived by iteratively advancing the GF(2) matrix.
    
    :param LFSR: [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 134217728, 268435456, 536870912, 1073741824, 9]
    List of integers representing the LFSR transition matrix rows.
    :type LFSR: list[int]
    :param N_taps: 1600
    Number of taps to advance the LFSR.
    :type N_taps: int
    :param N_bits: 32
    Number of LSBs to output in the result (should be <= len(LFSR)). For example, for a 31-bit LFSR in state 0-30, set `N_bits=12` and `N_taps= 1600` to get the 12 LSBs of the advanced state, which corresponds to state 1600~1611.
    :type N_bits: int
    :param N_CLK: 2
    Number of pipeline stages to insert after the XOR tree.
    :type N_CLK: int
    :param IF_RST_N: False
     Whether the pipeline stages have asynchronous reset.
    :type IF_RST_N: bool
    """
    
    # 1. Initialize Matrices
    # M_step: The single-step transition matrix S(t+1) = M * S(t)
    M_step = GF2Matrix(size=len(LFSR), rows=LFSR)
    
    # M_curr: The matrix accumulated to the current calculation point.
    # Initially points to S(t + N_taps) = M^N_taps * S(t)
    M_curr = M_step.power(N_taps)
    
    # Logic Width (Number of input bits from the LFSR state)
    state_width = len(LFSR)

    #/ `timescale 1ns / 1ps
    #/ module XOR_TREE(
    if N_CLK > 0:
        #/ input wire i_clk,
        if IF_RST_N:
            #/ input wire i_rst_n,
            pass

    #/ input  wire [`state_width`-1:0] i_data,
    #/ output wire [`N_bits`-1:0]      o_data
    #/ );
    #/ // XOR tree intermediate signals
    for i in range(N_bits):
        bit_res = f"xor_tree_out_{i}_res"
        #/ wire `bit_res`;

        # Get the mask for the LSB (Row 0) of the current time step
        # Row 0 determines the output bit of a standard LFSR
        mask_int = M_curr.rows[0]
        mask_str = f"{mask_int:0{state_width}b}"
        
        # Identify which input bits participate in the XOR sum
        src_bits = [j for j, b in enumerate(reversed(mask_str)) if b == '1']
        sigs = [f"i_data[{j}]" for j in src_bits]

        if len(sigs) == 0:
            #/ assign `bit_res` = 1'b0;
            pass
        elif len(sigs) == 1:
            #/ assign `bit_res` = i_data[`src_bits[0]`];
            pass
        else:
            xor_expr = build_balanced_xor(sigs)
            #/ assign `bit_res` = `xor_expr`;
            pass
        
        # Advance the matrix by one time step for the next bit
        # M(t+n+1) = M_step * M(t+n)
        if i < N_bits - 1: # Optimization: Don't compute for the last iteration
            M_curr = M_step.multiply(M_curr)

    #/ // Output vector assembly
    #/ wire [`N_bits`-1:0] o_data_comb;
    for i in range(N_bits):
        bit_res = f"xor_tree_out_{i}_res"
        #/ assign o_data_comb[`i`] = `bit_res`;
        pass

    #/ // Optional pipeline delay
    if N_CLK > 0:
        if IF_RST_N:
            ModuleDelay(DWT=N_bits, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS={'i_data': 'o_data_comb', 'o_data': 'o_data', 'i_clk': 'i_clk', 'i_rst_n': 'i_rst_n'})
        else:
            ModuleDelay(DWT=N_bits, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS={'i_data': 'o_data_comb', 'o_data': 'o_data', 'i_clk': 'i_clk'})
    else:
        #/ assign o_data = o_data_comb;
        pass
    #/ endmodule
    pass

if __name__ == "__main__":
    # Example: Calculate X1 logic for a very large output width
    x1_rows = [0] * 31
    for i in range(30):
        x1_rows[i] = (1 << (i + 1))
    x1_rows[30] = (1 << 3) | (1 << 0)
    
    # We can now request 64 bits (or more) from a 31-bit LFSR
    # This generates logic for sequence [1600, 1601, ..., 1663]
    ModuleXOR_TREE(LFSR=x1_rows, N_taps=1600, N_bits=64, N_CLK=0, IF_RST_N=False)
