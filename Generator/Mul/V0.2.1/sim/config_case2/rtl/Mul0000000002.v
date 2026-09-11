 module Mul0000000002 (
 i_data_1, i_data_2, o_data
 );
 input wire [3:0] i_data_1;
 input wire [4:0] i_data_2;
 output wire [7:0] o_data;
 wire [3:0] data_1;
 wire [4:0] data_2;
 assign data_1 = i_data_1;
 assign data_2 = i_data_2;
 wire [3:0] data_1_abs;
 wire [4:0] data_2_abs;
 wire [8:0] data_mul_ures;
 assign data_1_abs =  data_1;
 assign data_2_abs =  data_2;
 assign data_mul_ures = data_1_abs * data_2_abs;
 wire res_sign;
 wire [9:0] data_mul_res;
 assign res_sign = 1'b0;
 assign data_mul_res = {1'b0, data_mul_ures};
 wire [7:0] result_fixed;
FxMatch0000000002  u_0000000001_FxMatch0000000002(.i_data(data_mul_res), .o_data(result_fixed));
Delay0000000004  u_0000000001_Delay0000000004(.i_data(result_fixed), .o_data(o_data));
 endmodule
