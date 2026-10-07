 module Delay0000000001 (
     i_data, o_data
 , i_clk
 );
 // Input and output ports
 input  [16-1:0] i_data;
 output [16-1:0] o_data;
 input i_clk;
 reg [16-1:0] data_d [0:4-1];
 always @(posedge i_clk) begin
     data_d[0] <= i_data;
 end
 always @(posedge i_clk) begin
     data_d[1] <= data_d[0];
 end
 always @(posedge i_clk) begin
     data_d[2] <= data_d[1];
 end
 always @(posedge i_clk) begin
     data_d[3] <= data_d[2];
 end
 assign o_data = data_d[4-1];
 endmodule
