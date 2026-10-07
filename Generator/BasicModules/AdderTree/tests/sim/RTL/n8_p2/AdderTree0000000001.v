 `timescale 1ns / 1ps
 module AdderTree0000000001 (
     i_data,
     o_data
 , i_clk
 );
 // Input and Output Ports
 input                          wire [64-1:0] i_data;
 output wire [12-1:0] o_data;
 input wire i_clk;
 wire [64-1:0] data0;
 assign data0 = i_data;
 wire [36-1:0] data1;
Add0000000001  u_0000000001_Add0000000001(.i_data_1(data0[1*8-1:0*8]), .i_data_2(data0[2*8-1:1*8]), .o_data(data1[1*9-1:0*9]));
Add0000000001  u_0000000002_Add0000000001(.i_data_1(data0[3*8-1:2*8]), .i_data_2(data0[4*8-1:3*8]), .o_data(data1[2*9-1:1*9]));
Add0000000001  u_0000000003_Add0000000001(.i_data_1(data0[5*8-1:4*8]), .i_data_2(data0[6*8-1:5*8]), .o_data(data1[3*9-1:2*9]));
Add0000000001  u_0000000004_Add0000000001(.i_data_1(data0[7*8-1:6*8]), .i_data_2(data0[8*8-1:7*8]), .o_data(data1[4*9-1:3*9]));
 wire [20-1:0] data2;
Add0000000002  u_0000000001_Add0000000002(.i_data_1(data1[1*9-1:0*9]), .i_data_2(data1[2*9-1:1*9]), .o_data(data2[1*10-1:0*10]), .i_clk(i_clk));
Add0000000002  u_0000000002_Add0000000002(.i_data_1(data1[3*9-1:2*9]), .i_data_2(data1[4*9-1:3*9]), .o_data(data2[2*10-1:1*10]), .i_clk(i_clk));
 wire [12-1:0] data3;
Add0000000003  u_0000000001_Add0000000003(.i_data_1(data2[1*10-1:0*10]), .i_data_2(data2[2*10-1:1*10]), .o_data(data3[1*12-1:0*12]), .i_clk(i_clk));
 assign o_data = data3;
 endmodule
