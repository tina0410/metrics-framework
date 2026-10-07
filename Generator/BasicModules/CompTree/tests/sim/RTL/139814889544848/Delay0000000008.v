 module Delay0000000008 (
     i_data, o_data
 , i_clk
 );
 // Input and output ports
 input  [4-1:0] i_data;
 output [4-1:0] o_data;
 input i_clk;
 reg [4-1:0] data_d [0:2-1];
 always @(posedge i_clk) begin
     data_d[0] <= i_data;
 end
 always @(posedge i_clk) begin
     data_d[1] <= data_d[0];
 end
 assign o_data = data_d[2-1];
 endmodule
