 module Comp0000000001 (
 i_data_1
 ,i_data_2
 ,o_gidx
 ,o_lidx
 ,o_eidx
 ,o_gval
 ,o_lval
 ,i_rst_n
 ,i_clk
);
 // Input and Output Ports
 input wire [7-1:0] i_data_1;
 input wire [5-1:0] i_data_2;
 input wire i_clk;
 input wire i_rst_n;
 wire [7-1:0] data_1;
 wire [5-1:0] data_2;
 assign data_1 = i_data_1;
 assign data_2 = i_data_2;
 output wire o_gidx;
 output wire o_lidx;
 output wire o_eidx;
 output wire [8-1:0] o_gval;
 output wire [8-1:0] o_lval;
 // FxMatch for Output Fix
 wire [8-1:0] data_1_fixed;
 wire [8-1:0] data_2_fixed;
FxMatch0000000001  u_0000000001_FxMatch0000000001(.i_data(data_1), .o_data(data_1_fixed));
FxMatch0000000002  u_0000000001_FxMatch0000000002(.i_data(data_2), .o_data(data_2_fixed));
 wire [11-1:0] comp_result;
Sub0000000001  u_0000000001_Sub0000000001(.i_data_1(data_1), .i_data_2(data_2), .o_data(comp_result));
 // Signed Value Comparison
 wire greater_sign;
 assign greater_sign = (comp_result[11-1] == 1'b0 && comp_result != {11{1'b0}} ) ? 1'b1 : 1'b0;
Delay0000000003  u_0000000001_Delay0000000003(.i_data(greater_sign), .o_data(o_gidx), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire lesser_sign;
 assign lesser_sign = (comp_result[11-1] == 1'b1) ? 1'b1 : 1'b0;
Delay0000000003  u_0000000002_Delay0000000003(.i_data(lesser_sign), .o_data(o_lidx), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire equal_sign;
 assign equal_sign = (comp_result == 0) ? 1'b1 : 1'b0;
Delay0000000003  u_0000000003_Delay0000000003(.i_data(equal_sign), .o_data(o_eidx), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire [8-1:0] greater_value;
 assign greater_value = ((comp_result[11-1] == 1'b0) && (comp_result != {11{1'b0}})) ? data_1_fixed : data_2_fixed;
Delay0000000004  u_0000000001_Delay0000000004(.i_data(greater_value), .o_data(o_gval), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire [8-1:0] smaller_value;
 assign smaller_value = (comp_result[11-1] == 1'b1) ? data_1_fixed : data_2_fixed;
Delay0000000004  u_0000000002_Delay0000000004(.i_data(smaller_value), .o_data(o_lval), .i_clk(i_clk), .i_rst_n(i_rst_n));
 endmodule
