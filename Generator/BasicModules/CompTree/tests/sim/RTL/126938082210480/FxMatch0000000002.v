 module FxMatch0000000002 (
     i_data, o_data
 );
 input  wire [5-1:0]  i_data; // Input data
 output wire [6-1:0] o_data; // Output data
 //
 wire [6-1:0] i_data_eq;
 assign i_data_eq = {1'b0, i_data};
 wire [7-1:0] o_data_eq;
 // Quantization Stage
 wire [5-1:0]  op_quan; // Quantization output
 wire [6-1:0] i_data_eq_abs;
 wire [5-1:0]  op_quan_abs;
 assign i_data_eq_abs = i_data_eq[6-1] ? ~i_data_eq + 1'b1 : i_data_eq;
 assign op_quan_abs   = i_data_eq_abs[6-1:1];
 assign op_quan       = i_data_eq[6-1] ? ~op_quan_abs + 1'b1 : op_quan_abs;
 // Overflow Stage
 // Pad extra MSB bits with sign bit
 assign o_data_eq = {{2{op_quan[5-1]}}, op_quan};
 wire [6-1:0] o_data_trunc;
 // Drop the auxiliary sign bit
 assign o_data_trunc = o_data_eq[7-2:0];
Delay0000000009  u_0000000001_Delay0000000009(.i_data(o_data_trunc), .o_data(o_data));
 endmodule
