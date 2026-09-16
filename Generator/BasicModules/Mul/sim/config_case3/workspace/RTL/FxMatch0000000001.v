 module FxMatch0000000001 (
     i_data, o_data
 );
 input wire [10-1:0] i_data;     // Input data
 output wire [9-1:0] o_data;   // Output data
 //
 wire [11-1:0] i_data_eq;
 assign i_data_eq = {1'b0, i_data};
 wire [10-1:0] o_data_eq;
 // Quantization Stage
 // Pad extra LSB bits with 0
 wire [12-1:0] op_quan; // Quantization output
 assign op_quan = {i_data_eq, {1{1'b0}}};
 // Overflow Stage
 // Overflow protection
 assign o_data_eq = op_quan[10-1:0];
 wire [9-1:0] o_data_trunc;
 // Truncate the sign bit for unsigned output
 assign o_data_trunc = o_data_eq[10-2:0];
Delay0000000001  u_0000000001_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
