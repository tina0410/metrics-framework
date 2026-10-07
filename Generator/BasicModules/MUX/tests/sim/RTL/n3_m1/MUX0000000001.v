 `timescale 1ns / 1ps
 module MUX0000000001 (
     i_data,
     i_sel,
     o_data
 );
 input  wire [3-1:0] i_data;
 input  wire [2-1:0]       i_sel;
 output reg  [1-1:0]           o_data;

 always @(*) begin
     case (i_sel)
         2'd0: o_data = i_data[0 +: 1];
         2'd1: o_data = i_data[1 +: 1];
         2'd2: o_data = i_data[2 +: 1];
         default: o_data = 1'b0;
     endcase
 end
 endmodule
