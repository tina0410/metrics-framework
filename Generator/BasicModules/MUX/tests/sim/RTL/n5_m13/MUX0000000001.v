 `timescale 1ns / 1ps
 module MUX0000000001 (
     i_data,
     i_sel,
     o_data
 );
 input  wire [65-1:0] i_data;
 input  wire [3-1:0]       i_sel;
 output reg  [13-1:0]           o_data;

 always @(*) begin
     case (i_sel)
         3'd0: o_data = i_data[0 +: 13];
         3'd1: o_data = i_data[13 +: 13];
         3'd2: o_data = i_data[26 +: 13];
         3'd3: o_data = i_data[39 +: 13];
         3'd4: o_data = i_data[52 +: 13];
         default: o_data = 13'b0;
     endcase
 end
 endmodule
