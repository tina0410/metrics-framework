 module Comp0000000001 (
 i_data_1
 ,i_data_2
 ,o_gidx
 ,o_gval
 ,i_rst_n
 ,i_clk
);
 // Input and Output Ports
 input wire [5-1:0] i_data_1;
 input wire [5-1:0] i_data_2;
 input wire i_clk;
 input wire i_rst_n;
 wire [5-1:0] data_1;
 wire [5-1:0] data_2;
 assign data_1 = i_data_1;
 assign data_2 = i_data_2;
 output wire o_gidx;
 output wire [5-1:0] o_gval;
 // FxMatch for Output Fix
 wire [5-1:0] data_1_fixed;
 wire [5-1:0] data_2_fixed;
FxMatch0000000001  u_0000000001_FxMatch0000000001(.i_data(data_1), .o_data(data_1_fixed));
FxMatch0000000001  u_0000000002_FxMatch0000000001(.i_data(data_2), .o_data(data_2_fixed));
 // Unsigned Value Comparison
 wire greater_sign;
 assign greater_sign = (data_1 > data_2) ? 1'b1 : 1'b0;
Delay0000000002  u_0000000001_Delay0000000002(.i_data(greater_sign), .o_data(o_gidx), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire [5-1:0] greater_value;
 assign greater_value = (data_1 > data_2) ? data_1_fixed : data_2_fixed;
Delay0000000003  u_0000000001_Delay0000000003(.i_data(greater_value), .o_data(o_gval), .i_clk(i_clk), .i_rst_n(i_rst_n));
 endmodule
