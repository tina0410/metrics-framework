 module CompTree0000000001 (
  i_data
 ,o_gidx
 ,o_gval
, i_rst_n
, i_clk
);
 // Input and Output Ports
 input wire [155-1:0] i_data;
 output [5-1:0] o_gidx;
 output [6-1:0] o_gval;
 input wire i_clk;
 input wire i_rst_n;
 wire [155-1:0] data0;
 assign data0 = i_data;
 wire [80-1:0] gval_l1;
 wire [16-1:0] gidx_l1;
Comp0000000001  u_0000000001_Comp0000000001(.i_data_2(data0[1*5-1:0*5]), .i_data_1(data0[2*5-1:1*5]), .o_gval(gval_l1[1*5-1:0*5]), .o_gidx(gidx_l1[1*1-1:0*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000002_Comp0000000001(.i_data_2(data0[3*5-1:2*5]), .i_data_1(data0[4*5-1:3*5]), .o_gval(gval_l1[2*5-1:1*5]), .o_gidx(gidx_l1[2*1-1:1*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000003_Comp0000000001(.i_data_2(data0[5*5-1:4*5]), .i_data_1(data0[6*5-1:5*5]), .o_gval(gval_l1[3*5-1:2*5]), .o_gidx(gidx_l1[3*1-1:2*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000004_Comp0000000001(.i_data_2(data0[7*5-1:6*5]), .i_data_1(data0[8*5-1:7*5]), .o_gval(gval_l1[4*5-1:3*5]), .o_gidx(gidx_l1[4*1-1:3*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000005_Comp0000000001(.i_data_2(data0[9*5-1:8*5]), .i_data_1(data0[10*5-1:9*5]), .o_gval(gval_l1[5*5-1:4*5]), .o_gidx(gidx_l1[5*1-1:4*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000006_Comp0000000001(.i_data_2(data0[11*5-1:10*5]), .i_data_1(data0[12*5-1:11*5]), .o_gval(gval_l1[6*5-1:5*5]), .o_gidx(gidx_l1[6*1-1:5*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000007_Comp0000000001(.i_data_2(data0[13*5-1:12*5]), .i_data_1(data0[14*5-1:13*5]), .o_gval(gval_l1[7*5-1:6*5]), .o_gidx(gidx_l1[7*1-1:6*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000008_Comp0000000001(.i_data_2(data0[15*5-1:14*5]), .i_data_1(data0[16*5-1:15*5]), .o_gval(gval_l1[8*5-1:7*5]), .o_gidx(gidx_l1[8*1-1:7*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_0000000009_Comp0000000001(.i_data_2(data0[17*5-1:16*5]), .i_data_1(data0[18*5-1:17*5]), .o_gval(gval_l1[9*5-1:8*5]), .o_gidx(gidx_l1[9*1-1:8*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_000000000A_Comp0000000001(.i_data_2(data0[19*5-1:18*5]), .i_data_1(data0[20*5-1:19*5]), .o_gval(gval_l1[10*5-1:9*5]), .o_gidx(gidx_l1[10*1-1:9*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_000000000B_Comp0000000001(.i_data_2(data0[21*5-1:20*5]), .i_data_1(data0[22*5-1:21*5]), .o_gval(gval_l1[11*5-1:10*5]), .o_gidx(gidx_l1[11*1-1:10*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_000000000C_Comp0000000001(.i_data_2(data0[23*5-1:22*5]), .i_data_1(data0[24*5-1:23*5]), .o_gval(gval_l1[12*5-1:11*5]), .o_gidx(gidx_l1[12*1-1:11*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_000000000D_Comp0000000001(.i_data_2(data0[25*5-1:24*5]), .i_data_1(data0[26*5-1:25*5]), .o_gval(gval_l1[13*5-1:12*5]), .o_gidx(gidx_l1[13*1-1:12*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_000000000E_Comp0000000001(.i_data_2(data0[27*5-1:26*5]), .i_data_1(data0[28*5-1:27*5]), .o_gval(gval_l1[14*5-1:13*5]), .o_gidx(gidx_l1[14*1-1:13*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comp0000000001  u_000000000F_Comp0000000001(.i_data_2(data0[29*5-1:28*5]), .i_data_1(data0[30*5-1:29*5]), .o_gval(gval_l1[15*5-1:14*5]), .o_gidx(gidx_l1[15*1-1:14*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire [5-1:0] remainder_val_l1;
 wire [1-1:0] remainder_pos_l1;
 assign remainder_pos_l1 = 1'b0;
Delay0000000002  u_0000000002_Delay0000000002(.i_data(remainder_pos_l1), .o_data(gidx_l1[16*1-1:15*1]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Delay0000000003  u_0000000002_Delay0000000003(.i_data(data0[31*5-1:30*5]), .o_data(remainder_val_l1), .i_clk(i_clk), .i_rst_n(i_rst_n));
FxMatch0000000001  u_0000000003_FxMatch0000000001(.i_data(remainder_val_l1), .o_data(gval_l1[16*5-1:15*5]));
 wire [40-1:0] gval_l2;
 wire [16-1:0] gidx_l2;
Comppos0000000001  u_0000000001_Comppos0000000001(.i_data_2(gval_l1[1*5-1:0*5]), .i_data_1(gval_l1[2*5-1:1*5]), .i_data_gpos_2(gidx_l1[1*1-1:0*1]), .i_data_gpos_1(gidx_l1[2*1-1:1*1]), .o_gval(gval_l2[1*5-1:0*5]), .o_gidx(gidx_l2[1*2-1:0*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000001  u_0000000002_Comppos0000000001(.i_data_2(gval_l1[3*5-1:2*5]), .i_data_1(gval_l1[4*5-1:3*5]), .i_data_gpos_2(gidx_l1[3*1-1:2*1]), .i_data_gpos_1(gidx_l1[4*1-1:3*1]), .o_gval(gval_l2[2*5-1:1*5]), .o_gidx(gidx_l2[2*2-1:1*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000001  u_0000000003_Comppos0000000001(.i_data_2(gval_l1[5*5-1:4*5]), .i_data_1(gval_l1[6*5-1:5*5]), .i_data_gpos_2(gidx_l1[5*1-1:4*1]), .i_data_gpos_1(gidx_l1[6*1-1:5*1]), .o_gval(gval_l2[3*5-1:2*5]), .o_gidx(gidx_l2[3*2-1:2*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000001  u_0000000004_Comppos0000000001(.i_data_2(gval_l1[7*5-1:6*5]), .i_data_1(gval_l1[8*5-1:7*5]), .i_data_gpos_2(gidx_l1[7*1-1:6*1]), .i_data_gpos_1(gidx_l1[8*1-1:7*1]), .o_gval(gval_l2[4*5-1:3*5]), .o_gidx(gidx_l2[4*2-1:3*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000001  u_0000000005_Comppos0000000001(.i_data_2(gval_l1[9*5-1:8*5]), .i_data_1(gval_l1[10*5-1:9*5]), .i_data_gpos_2(gidx_l1[9*1-1:8*1]), .i_data_gpos_1(gidx_l1[10*1-1:9*1]), .o_gval(gval_l2[5*5-1:4*5]), .o_gidx(gidx_l2[5*2-1:4*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000001  u_0000000006_Comppos0000000001(.i_data_2(gval_l1[11*5-1:10*5]), .i_data_1(gval_l1[12*5-1:11*5]), .i_data_gpos_2(gidx_l1[11*1-1:10*1]), .i_data_gpos_1(gidx_l1[12*1-1:11*1]), .o_gval(gval_l2[6*5-1:5*5]), .o_gidx(gidx_l2[6*2-1:5*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000001  u_0000000007_Comppos0000000001(.i_data_2(gval_l1[13*5-1:12*5]), .i_data_1(gval_l1[14*5-1:13*5]), .i_data_gpos_2(gidx_l1[13*1-1:12*1]), .i_data_gpos_1(gidx_l1[14*1-1:13*1]), .o_gval(gval_l2[7*5-1:6*5]), .o_gidx(gidx_l2[7*2-1:6*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000001  u_0000000008_Comppos0000000001(.i_data_2(gval_l1[15*5-1:14*5]), .i_data_1(gval_l1[16*5-1:15*5]), .i_data_gpos_2(gidx_l1[15*1-1:14*1]), .i_data_gpos_1(gidx_l1[16*1-1:15*1]), .o_gval(gval_l2[8*5-1:7*5]), .o_gidx(gidx_l2[8*2-1:7*2]), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire [20-1:0] gval_l3;
 wire [12-1:0] gidx_l3;
Comppos0000000002  u_0000000001_Comppos0000000002(.i_data_2(gval_l2[1*5-1:0*5]), .i_data_1(gval_l2[2*5-1:1*5]), .i_data_gpos_2(gidx_l2[1*2-1:0*2]), .i_data_gpos_1(gidx_l2[2*2-1:1*2]), .o_gval(gval_l3[1*5-1:0*5]), .o_gidx(gidx_l3[1*3-1:0*3]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000002  u_0000000002_Comppos0000000002(.i_data_2(gval_l2[3*5-1:2*5]), .i_data_1(gval_l2[4*5-1:3*5]), .i_data_gpos_2(gidx_l2[3*2-1:2*2]), .i_data_gpos_1(gidx_l2[4*2-1:3*2]), .o_gval(gval_l3[2*5-1:1*5]), .o_gidx(gidx_l3[2*3-1:1*3]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000002  u_0000000003_Comppos0000000002(.i_data_2(gval_l2[5*5-1:4*5]), .i_data_1(gval_l2[6*5-1:5*5]), .i_data_gpos_2(gidx_l2[5*2-1:4*2]), .i_data_gpos_1(gidx_l2[6*2-1:5*2]), .o_gval(gval_l3[3*5-1:2*5]), .o_gidx(gidx_l3[3*3-1:2*3]), .i_clk(i_clk), .i_rst_n(i_rst_n));
Comppos0000000002  u_0000000004_Comppos0000000002(.i_data_2(gval_l2[7*5-1:6*5]), .i_data_1(gval_l2[8*5-1:7*5]), .i_data_gpos_2(gidx_l2[7*2-1:6*2]), .i_data_gpos_1(gidx_l2[8*2-1:7*2]), .o_gval(gval_l3[4*5-1:3*5]), .o_gidx(gidx_l3[4*3-1:3*3]), .i_clk(i_clk), .i_rst_n(i_rst_n));
 wire [10-1:0] gval_l4;
 wire [8-1:0] gidx_l4;
Comppos0000000003  u_0000000001_Comppos0000000003(.i_data_2(gval_l3[1*5-1:0*5]), .i_data_1(gval_l3[2*5-1:1*5]), .i_data_gpos_2(gidx_l3[1*3-1:0*3]), .i_data_gpos_1(gidx_l3[2*3-1:1*3]), .o_gval(gval_l4[1*5-1:0*5]), .o_gidx(gidx_l4[1*4-1:0*4]), .i_clk(i_clk));
Comppos0000000003  u_0000000002_Comppos0000000003(.i_data_2(gval_l3[3*5-1:2*5]), .i_data_1(gval_l3[4*5-1:3*5]), .i_data_gpos_2(gidx_l3[3*3-1:2*3]), .i_data_gpos_1(gidx_l3[4*3-1:3*3]), .o_gval(gval_l4[2*5-1:1*5]), .o_gidx(gidx_l4[2*4-1:1*4]), .i_clk(i_clk));
 wire [6-1:0] gval_l5;
 wire [5-1:0] gidx_l5;
Comppos0000000004  u_0000000001_Comppos0000000004(.i_data_2(gval_l4[1*5-1:0*5]), .i_data_1(gval_l4[2*5-1:1*5]), .i_data_gpos_2(gidx_l4[1*4-1:0*4]), .i_data_gpos_1(gidx_l4[2*4-1:1*4]), .o_gval(gval_l5[1*6-1:0*6]), .o_gidx(gidx_l5[1*5-1:0*5]), .i_clk(i_clk), .i_rst_n(i_rst_n));
 assign o_gval = gval_l5;
 assign o_gidx = gidx_l5;
 endmodule
