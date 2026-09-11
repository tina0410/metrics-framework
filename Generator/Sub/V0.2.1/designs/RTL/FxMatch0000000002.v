 module FxMatch0000000002 (
     i_data, o_data
 );
 input wire [9-1:0] i_data;     // Input data
 output wire [10-1:0] o_data;   // Output data
 //
 wire [9-1:0] i_data_eq;
 assign i_data_eq = i_data;
 wire [10-1:0] o_data_eq;
 // Quantization Stage
 // Perfect LSB match
 wire [9-1:0] op_quan; // Quantization output
 assign op_quan = i_data_eq;
 // Overflow Stage
 // Pad extra MSB bits with sign bit
 assign o_data_eq = {{1{op_quan[9-1]}}, op_quan};
 wire [10-1:0] o_data_trunc;
 assign o_data_trunc = o_data_eq;
Delay0000000001  u_0000000002_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
