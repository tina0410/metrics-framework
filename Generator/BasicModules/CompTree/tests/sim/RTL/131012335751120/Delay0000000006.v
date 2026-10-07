 module Delay0000000006 (
     i_data, o_data
 , i_clk
 , i_rst_n
 );
 // Input and output ports
 input  [3-1:0] i_data;
 output [3-1:0] o_data;
 input i_clk;
 input i_rst_n;
 reg [3-1:0] data_d [0:2-1];
 always @(posedge i_clk) begin
     data_d[0] <= i_data;
 end
 always @(posedge i_clk, negedge i_rst_n) begin
     if (~i_rst_n) begin
         data_d[1] <= 3'b0;
     end
     else begin
         data_d[1] <= data_d[0];
     end
 end
 assign o_data = data_d[2-1];
 endmodule
