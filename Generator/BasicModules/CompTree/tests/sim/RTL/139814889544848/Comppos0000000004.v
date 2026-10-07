 module Comppos0000000004 (
     i_data_1, i_data_2, i_data_gpos_1, i_data_gpos_2
     , o_gval
     , o_gidx
     , i_clk
     , i_rst_n
 );
 input wire [5-1:0] i_data_1;
 input wire [5-1:0] i_data_2;
 input wire [4-1:0] i_data_gpos_1;
 input wire [4-1:0] i_data_gpos_2;
 output wire [6-1:0] o_gval;
 output wire [4:0] o_gidx;
 input wire i_clk;
 input wire i_rst_n;
 wire choose_first;
 assign choose_first = i_data_1 > i_data_2;
 wire [5-1:0] greater_value_raw;
 wire [6-1:0] greater_value_fixed;
 assign greater_value_raw = choose_first ? i_data_1 : i_data_2;
FxMatch0000000002  u_0000000001_FxMatch0000000002(.i_data(greater_value_raw), .o_data(greater_value_fixed));
Delay000000000A  u_0000000001_Delay000000000A(.i_data(greater_value_fixed), .o_data(o_gval), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire [5-1:0] greater_position;
 assign greater_position = choose_first ? {1'b1, i_data_gpos_1} : {1'b0, i_data_gpos_2};
Delay0000000003  u_0000000004_Delay0000000003(.i_data(greater_position), .o_data(o_gidx), .i_clk(i_clk), .i_rst_n(i_rst_n));
 endmodule
