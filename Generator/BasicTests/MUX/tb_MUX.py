# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Verithon testbench generator for arbitrary-N/arbitrary-M MUX.

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from Generator.BasicModules.MUX import ModuleMUX, mux_select_width


@convert
def ModuleTbMUX(N_INPUTS, DWT):
    SEL_DWT = mux_select_width(N_INPUTS)
    PACKED_DWT = N_INPUTS * DWT
    DATA_MASK = (1 << DWT) - 1

    #/ `timescale 1ns/1ps
    #/ module TbMUX;
    #/ reg [`PACKED_DWT`-1:0] i_data;
    #/ reg [`SEL_DWT`-1:0] i_sel;
    #/ wire [`DWT`-1:0] o_data;

    ModuleMUX(N_INPUTS=N_INPUTS, DWT=DWT, PORTS={"i_data": "i_data", "i_sel": "i_sel", "o_data": "o_data"})

    #/ task check;
    #/     input [`PACKED_DWT`-1:0] data_value;
    #/     input [`SEL_DWT`-1:0] select;
    #/     input [`DWT`-1:0] expected;
    #/     begin
    #/         i_data = data_value;
    #/         i_sel = select;
    #/         #1;
    #/         if (o_data !== expected) begin
    #/             $display("MUX mismatch: data=%h sel=%h got=%h expected=%h", data_value, select, o_data, expected);
    #/             $fatal(1);
    #/         end
    #/     end
    #/ endtask

    #/ initial begin
    # Every lane is independently selected with all other lanes cleared.
    for hot_lane in range(N_INPUTS):
        packed = DATA_MASK << (hot_lane * DWT)
        packed_hex = format(packed, "x")
        for select in range(N_INPUTS):
            expected = DATA_MASK if select == hot_lane else 0
            select_hex = format(select, "x")
            expected_hex = format(expected, "x")
            #/     check(`PACKED_DWT`'h`packed_hex`, `SEL_DWT`'h`select_hex`, `DWT`'h`expected_hex`);

    # Non-symmetric packed data proves the documented LSB-first lane order.
    packed = sum((((index * 37) + 5) & DATA_MASK) << (index * DWT) for index in range(N_INPUTS))
    packed_hex = format(packed, "x")
    for select in range(N_INPUTS):
        expected = (packed >> (select * DWT)) & DATA_MASK
        select_hex = format(select, "x")
        expected_hex = format(expected, "x")
        #/     check(`PACKED_DWT`'h`packed_hex`, `SEL_DWT`'h`select_hex`, `DWT`'h`expected_hex`);

    # All representable selector values outside N must select the zero default.
    for select in range(N_INPUTS, 1 << SEL_DWT):
        select_hex = format(select, "x")
        #/     check(`PACKED_DWT`'h`packed_hex`, `SEL_DWT`'h`select_hex`, `DWT`'h0);
    if N_INPUTS == 1:
        #/     check(`PACKED_DWT`'h`packed_hex`, 1'b1, `DWT`'h0);
        pass

    #/     i_data = `PACKED_DWT`'h`packed_hex`;
    #/     i_sel = {`SEL_DWT`{1'bx}};
    #/     #1;
    #/     if (o_data !== `DWT`'b0) $fatal(1, "X selector must choose zero");
    #/     i_sel = {`SEL_DWT`{1'bz}};
    #/     #1;
    #/     if (o_data !== `DWT`'b0) $fatal(1, "Z selector must choose zero");
    #/     $display("PASS MUX N=`N_INPUTS` M=`DWT`");
    #/     $finish;
    #/ end
    #/ endmodule
