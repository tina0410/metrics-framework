 module Delay0000000001 (
     i_data, o_data
 , i_clk
 , i_rst_n
 );
 // Input and output ports
 input  [8-1:0] i_data;
 output [8-1:0] o_data;
 input i_clk;
 input i_rst_n;
 reg [8-1:0] data_d [0:1-1];
 always @(posedge i_clk, negedge i_rst_n) begin
     if (~i_rst_n) begin
         data_d[0] <= 8'b0;
     end
     else begin
         data_d[0] <= i_data;
     end
 end
 assign o_data = data_d[1-1];
 endmodule
