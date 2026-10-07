 module FxMatch0000000003 (
     i_data, o_data
 );
 input  wire [8-1:0]  i_data; // Input data
 output wire [12-1:0] o_data; // Output data
 //
 wire [8-1:0] i_data_eq;
 assign i_data_eq = i_data;
 wire [12-1:0] o_data_eq;
 // Quantization Stage
 // Pad extra LSB bits with 0
 wire [11-1:0] op_quan; // Quantization output
 assign op_quan = {i_data_eq, {3{1'b0}}};
 // Overflow Stage
 // Pad extra MSB bits with sign bit
 assign o_data_eq = {{1{op_quan[11-1]}}, op_quan};
 wire [12-1:0] o_data_trunc;
 assign o_data_trunc = o_data_eq;
Delay0000000002  u_0000000001_Delay0000000002(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
