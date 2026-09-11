 module FxMatch0000000001 (
     i_data, o_data
 );
 input wire [12-1:0] i_data;     // Input data
 output wire [8-1:0] o_data;   // Output data
 //
 wire [13-1:0] i_data_eq;
 assign i_data_eq = {1'b0, i_data};
 wire [9-1:0] o_data_eq;
 // Quantization Stage
 // Perfect LSB match
 wire [13-1:0] op_quan; // Quantization output
 assign op_quan = i_data_eq;
 // Overflow Stage
 // Overflow protection
 assign o_data_eq = op_quan[9-1:0];
 wire [8-1:0] o_data_trunc;
 // Truncate the sign bit for unsigned output
 assign o_data_trunc = o_data_eq[9-2:0];
Delay0000000001  u_0000000001_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
