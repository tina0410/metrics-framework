 module FxMatch0000000003 (
     i_data, o_data
 );
 input  wire [8-1:0]  i_data; // Input data
 output wire [9-1:0] o_data; // Output data
 //
 wire [9-1:0] i_data_eq;
 assign i_data_eq = {1'b0, i_data};
 wire [10-1:0] o_data_eq;
 // Quantization Stage
 // Perfect LSB match
 wire [9-1:0] op_quan; // Quantization output
 assign op_quan = i_data_eq;
 // Overflow Stage
 // Pad extra MSB bits with sign bit
 assign o_data_eq = {{1{op_quan[9-1]}}, op_quan};
 wire [9-1:0] o_data_trunc;
 // Drop the auxiliary sign bit
 assign o_data_trunc = o_data_eq[10-2:0];
Delay0000000001  u_0000000003_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
