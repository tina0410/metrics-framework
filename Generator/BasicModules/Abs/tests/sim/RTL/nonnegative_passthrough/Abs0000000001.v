 module Abs0000000001 (
     i_data,
     o_data
 );
 // Input and Output Ports
 input  wire [8-1:0]  i_data;
 output wire [8-1:0] o_data;
 wire [8-1:0] result_fixed;
FxMatch0000000001  u_0000000001_FxMatch0000000001(.i_data(i_data), .o_data(result_fixed));
Delay0000000001  u_0000000002_Delay0000000001(.i_data(result_fixed), .o_data(o_data));
 endmodule
