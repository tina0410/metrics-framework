 module FxMatch0000000001 (
     i_data, o_data
 , i_clk
 , i_rst_n
 );
 input  wire [5-1:0]  i_data; // Input data
 output wire [5-1:0] o_data; // Output data
 input wire i_clk; // Clock
 input wire i_rst_n; // Reset, negative effective
 //
 wire [5-1:0] i_data_eq;
 assign i_data_eq = i_data;
 wire [5-1:0] o_data_eq;
 // Quantization Stage
 assign o_data_eq = i_data_eq[5-1] ? {5{1'b1}} : {5{1'b0}};
 wire [5-1:0] o_data_trunc;
 assign o_data_trunc = o_data_eq;
Delay0000000001  u_0000000001_Delay0000000001(.i_data(o_data_trunc), .o_data(o_data), .i_clk(i_clk), .i_rst_n(i_rst_n));
 endmodule
