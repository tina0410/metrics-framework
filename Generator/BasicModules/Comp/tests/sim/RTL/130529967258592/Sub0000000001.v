 `timescale 1ns / 1ps
 module Sub0000000001 (
     i_data_1,
     i_data_2,
     o_data
 );
 // Input and Output Ports
 input  wire [7-1:0] i_data_1;
 input  wire [6-1:0] i_data_2;
 output wire [11-1:0]  o_data;
 wire [7-1:0] data_1;
 wire [6-1:0] data_2;
 assign data_1 = i_data_1;
 assign data_2 = i_data_2;
 wire [6:0] data_2_minus;
 assign data_2_minus = ~{data_2[6-1], data_2} + 1'b1;
 wire [11-1:0] data_1_fixed;
 wire [11-1:0] data_2_fixed;
FxMatch0000000003  u_0000000001_FxMatch0000000003(.i_data(data_1), .o_data(data_1_fixed));
FxMatch0000000004  u_0000000001_FxMatch0000000004(.i_data(data_2_minus), .o_data(data_2_fixed));
 wire [11-1:0] result_unfixed;
 wire [11-1:0] result_fixed;
 assign result_unfixed = data_1_fixed + data_2_fixed;
FxMatch0000000005  u_0000000001_FxMatch0000000005(.i_data(result_unfixed), .o_data(result_fixed));
Delay0000000002  u_0000000004_Delay0000000002(.i_data(result_fixed), .o_data(o_data));
 endmodule
