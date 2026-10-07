 module FxMatch0000000001 (
     i_data, o_data
 );
 input  wire [7-1:0]  i_data; // Input data
 output wire [6-1:0] o_data; // Output data
 //
 wire [8-1:0] i_data_eq;
 assign i_data_eq = {1'b0, i_data};
 wire [7-1:0] o_data_eq;
 // Quantization Stage
 wire [8-1:0] op_quan; // Quantization output
 wire [8:0]  i_data_eq_fill;
 assign i_data_eq_fill = {i_data_eq[8-1] , i_data_eq};
 assign op_quan = (i_data_eq_fill[0:0] > 1'b1)
 ? (i_data_eq_fill[8:1] + 1'b1)
 : (
     ((i_data_eq_fill[0:0] == 1'b1) && (i_data_eq_fill[8-1]))
     ? (i_data_eq_fill[8:1] + 1'b1)
     : i_data_eq_fill[8:1]
 );
 // Overflow Stage
 // Overflow protection
 assign o_data_eq = (op_quan[8-1:7] != {1{op_quan[7-1]}})
 ? 7'b0
 : op_quan[7-1:0];
 wire [6-1:0] o_data_trunc;
 // Clamp a negative result before dropping the auxiliary sign bit
 assign o_data_trunc = o_data_eq[7-1] ? 6'b0 : o_data_eq[7-2:0];
Delay0000000001  u_0000000001_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
