 `timescale 1ns / 1ps
 module AdderTree0000000001 (
     i_data,
     o_data
 );
 // Input and Output Ports
 input                          wire [24-1:0] i_data;
 output wire [12-1:0] o_data;
 wire [24-1:0] data0;
 assign data0 = i_data;
 wire [18-1:0] data1;
Add0000000001  u_0000000001_Add0000000001(.i_data_1(data0[1*8-1:0*8]), .i_data_2(data0[2*8-1:1*8]), .o_data(data1[1*9-1:0*9]));
 wire [8-1:0] remainder_l1;
FxMatch0000000003  u_0000000001_FxMatch0000000003(.i_data(data0[3*8-1:2*8]), .o_data(data1[2*9-1:1*9]));
 wire [12-1:0] data2;
Add0000000002  u_0000000001_Add0000000002(.i_data_1(data1[1*9-1:0*9]), .i_data_2(data1[2*9-1:1*9]), .o_data(data2[1*12-1:0*12]));
 assign o_data = data2;
 endmodule
