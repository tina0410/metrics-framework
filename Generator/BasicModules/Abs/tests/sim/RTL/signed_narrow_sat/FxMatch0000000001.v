 module FxMatch0000000001 (
     i_data, o_data
 );
 input  wire [8-1:0]  i_data; // Input data
 output wire [5-1:0] o_data; // Output data
 //
 wire [9-1:0] i_data_eq;
 assign i_data_eq = {1'b0, i_data};
 wire [5-1:0] o_data_eq;
 // Quantization Stage
 wire [8-1:0] op_quan; // Quantization output
 wire [9:0]  i_data_eq_fill;
 assign i_data_eq_fill = {i_data_eq[9-1] , i_data_eq};
 assign op_quan = (i_data_eq_fill[1:0] >= 2'b10)
 ? (i_data_eq_fill[9:2] + 1'b1)
 : i_data_eq_fill[9:2];
 // Overflow Stage
 // Overflow protection
 assign o_data_eq = (op_quan[8-1:5] != {3{op_quan[5-1]}})
 ? (op_quan[8-1] ? 5'b10000 : 5'b01111)
 : op_quan[5-1:0];
 wire [5-1:0] o_data_trunc;
 assign o_data_trunc = o_data_eq;
Delay0000000001  u_0000000001_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
