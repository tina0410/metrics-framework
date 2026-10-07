 module Abs0000000001 (
     i_data,
     o_data
 );
 // Input and Output Ports
 input  wire [8-1:0]  i_data;
 output wire [8-1:0] o_data;
 wire [8-1:0] result_fixed;
 wire [8-1:0] data_abs;
 assign data_abs = i_data[8-1] ? (~i_data + 1'b1) : i_data;
FxMatch0000000001  u_0000000001_FxMatch0000000001(.i_data(data_abs), .o_data(result_fixed));
Delay0000000001  u_0000000002_Delay0000000001(.i_data(result_fixed), .o_data(o_data));
 endmodule
