 `timescale 1ns / 1ps
 module MUX0000000001 (
     i_data,
     i_sel,
     o_data
 );
 input  wire [32-1:0] i_data;
 input  wire [2-1:0]       i_sel;
 output reg  [8-1:0]           o_data;

 always @(*) begin
     case (i_sel)
         2'd0: o_data = i_data[0 +: 8];
         2'd1: o_data = i_data[8 +: 8];
         2'd2: o_data = i_data[16 +: 8];
         2'd3: o_data = i_data[24 +: 8];
         default: o_data = 8'b0;
     endcase
 end
 endmodule
