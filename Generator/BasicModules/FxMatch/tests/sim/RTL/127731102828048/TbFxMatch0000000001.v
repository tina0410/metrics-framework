 `timescale 1ns/1ps
 module TbFxMatch0000000001 ;
 // Inputs
 reg [5-1:0] Input_i_data;
 reg [5-1:0] i_data;
 reg i_clk;
 reg i_rst_n;
 // Outputs
 wire [5-1:0] o_data;
 // Instantiate the DUT
 // Instantiate the DUT, requires kwargs
FxMatch0000000001  u_0000000001_FxMatch0000000001(.i_data(i_data), .o_data(o_data), .i_clk(i_clk), .i_rst_n(i_rst_n));
 // Drive clk signal
 initial
 begin
     i_clk = 0;
      forever #5  i_clk <= ~i_clk;
 end
 // Initialize Inputs
 initial begin
 i_data <= 'b0;
 end
 // Drive rst signal
 initial
 begin
     i_rst_n <= 1;
     repeat (1) @(negedge i_clk);
     i_rst_n <= 0;
     repeat (1) @(negedge i_clk);
     i_rst_n <= 1;
 end


 // Drive input signal with 100 inputs using mode A2
 reg en;
 initial begin
    en <= 0;
 end
 // Print the header
 integer i_data_dat;   // file handle by $fopen
 integer i_data_st;   // status of $fscanf
 integer iter_group;
 initial begin
 repeat (30) @(posedge i_clk);
 i_data_dat = $fopen("../../Input_Files/fxmatch_i_data.txt", "r");

 for (iter_group = 0; iter_group < 100; iter_group = iter_group + 1) begin
 if (!$feof(i_data_dat)) begin
 i_data_st = $fscanf(i_data_dat, "%b\n", Input_i_data);
 repeat (1) @(posedge i_clk);
 i_data <= Input_i_data;
 en <= 1'b1;
 end
 end
 $fclose(i_data_dat);
 end
 // Dump output signal using mode A
 ///======== output_data Check ========///
 reg output_data_out_indicator;
 integer iter_output_data;
 integer fxmatch_o_data_dat;
 initial begin
 // wait for enable and clock
 @(posedge en);
 @(posedge i_clk); // for balance
 repeat (4) @(posedge i_clk);
 fxmatch_o_data_dat = $fopen("../../Output_Files/fxmatch_o_data.txt", "w");
 output_data_out_indicator = 0;
 for (iter_output_data = 0; iter_output_data < 100; iter_output_data = iter_output_data + 1) begin
 output_data_out_indicator = 0;
 $fdisplay(fxmatch_o_data_dat, "%b", o_data);
 output_data_out_indicator = 1;
 repeat (1) @(posedge i_clk);
 end
 $fclose(fxmatch_o_data_dat);
 repeat(100) @(posedge i_clk);
 $finish;
 end
 // Dump the wave.vcd file
 initial begin
     $dumpfile("wave.vcd");
     $dumpvars(0, TbFxMatch0000000001);
 end
 endmodule
