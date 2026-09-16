###################################################################################################
# Module Name: MUX
# Description: Parameterized N-to-1, M-bit combinational multiplexer.
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Dependency Modules: None
###################################################################################################
from pytv.Converter import convert


def mux_select_width(n_inputs: int) -> int:
    """Return the selector width for an ``n_inputs``-to-1 multiplexer."""
    if not isinstance(n_inputs, int) or isinstance(n_inputs, bool):
        raise TypeError("N_INPUTS must be an integer.")
    if n_inputs < 1:
        raise ValueError("N_INPUTS must be positive.")
    return max(1, (n_inputs - 1).bit_length())


@convert
def ModuleMUX(N_INPUTS: int | None = None, DWT: int | None = None, N: int | None = None, M: int | None = None):
    """Generate an N-to-1 M-bit combinational multiplexer.

    ``N_INPUTS``/``DWT`` are the canonical parameter names. ``N``/``M`` are
    accepted aliases. Input lane 0 occupies the least-significant ``DWT``
    bits of ``i_data``. An unused, unknown, or high-impedance selector value
    drives ``o_data`` to zero.
    """
    if N_INPUTS is None:
        N_INPUTS = N
    elif N is not None and N != N_INPUTS:
        raise ValueError("N and N_INPUTS must match when both are provided.")

    if DWT is None:
        DWT = M
    elif M is not None and M != DWT:
        raise ValueError("M and DWT must match when both are provided.")

    if not isinstance(N_INPUTS, int) or isinstance(N_INPUTS, bool):
        raise TypeError("N_INPUTS (N) must be an integer.")
    if not isinstance(DWT, int) or isinstance(DWT, bool):
        raise TypeError("DWT (M) must be an integer.")
    if N_INPUTS < 1:
        raise ValueError("N_INPUTS (N) must be positive.")
    if DWT < 1:
        raise ValueError("DWT (M) must be positive.")

    SEL_DWT = mux_select_width(N_INPUTS)

    #/ `timescale 1ns / 1ps
    #/ module MUX(
    #/     i_data,
    #/     i_sel,
    #/     o_data
    #/ );
    #/ input  wire [`N_INPUTS*DWT`-1:0] i_data;
    #/ input  wire [`SEL_DWT`-1:0]       i_sel;
    #/ output reg  [`DWT`-1:0]           o_data;
    #/
    #/ always @(*) begin
    #/     case (i_sel)
    for index in range(N_INPUTS):
        #/         `SEL_DWT`'d`index`: o_data = i_data[`index*DWT` +: `DWT`];
        pass
    #/         default: o_data = `DWT`'b0;
    #/     endcase
    #/ end
    #/ endmodule


# Preserve the repository's CamelCase naming style as a convenience alias.
ModuleMux = ModuleMUX

__all__ = ["ModuleMUX", "ModuleMux", "mux_select_width"]
