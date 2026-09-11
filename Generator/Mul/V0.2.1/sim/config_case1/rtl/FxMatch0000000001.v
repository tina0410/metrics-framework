 module FxMatch0000000001 (
     i_data, o_data
 );
 input wire [9-1:0] i_data;     // Input data
 output wire [7-1:0] o_data;   // Output data
 //
 wire [9-1:0] i_data_eq;
 assign i_data_eq = i_data;
 wire [7-1:0] o_data_eq;
 // Quantization Stage
 wire [8-1:0] op_quan; // Quantization output
 assign op_quan = i_data_eq[9-1:1];
 // Overflow Stage
 // Overflow protection
 assign o_data_eq = op_quan[7-1:0];
 wire [7-1:0] o_data_trunc;
 assign o_data_trunc = o_data_eq;
Delay0000000001  u_0000000001_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
