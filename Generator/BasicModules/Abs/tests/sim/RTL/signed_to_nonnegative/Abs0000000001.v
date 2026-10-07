 module Abs0000000001 (
     i_data,
     o_data
     ,i_clk
     ,i_rst_n
 );
 // Input and Output Ports
 input  wire [7-1:0]  i_data;
 output wire [6-1:0] o_data;
 input wire i_clk;
 input wire i_rst_n;
 wire [6-1:0] result_fixed;
 wire [7-1:0] data_abs;
 assign data_abs = i_data[7-1] ? (~i_data + 1'b1) : i_data;
FxMatch0000000001  u_0000000001_FxMatch0000000001(.i_data(data_abs), .o_data(result_fixed));
Delay0000000002  u_0000000001_Delay0000000002(.i_data(result_fixed), .o_data(o_data), .i_clk(i_clk), .i_rst_n(i_rst_n));
 endmodule
