 `timescale 1ns/1ps
 module TbCompTree0000000001 ;
 // Inputs
 reg [155-1:0] Input_i_data;
 reg [155-1:0] i_data;
 reg clk;
 reg i_rst_n;
 // Outputs
 wire [6-1:0] o_gval;
 wire [5-1:0] o_gidx;
 // Input ready and Output ready Indicators
 reg Input_rdy;
 reg Output_rdy;
 // Instantiate the DUT
 // Instantiate the DUT
CompTree0000000001  u_0000000001_CompTree0000000001(.i_data(i_data), .o_gval(o_gval), .o_gidx(o_gidx), .i_rst_n(i_rst_n), .i_clk(clk));
 // Drive clk signal
 initial
 begin
     clk = 0;
      forever #5  clk <= ~clk;
 end
 // Initialize Inputs
 initial begin
 i_data <= 'b0;
 end
 // Drive rst signal
 initial
 begin
     i_rst_n <= 1;
     repeat (1) @(negedge clk);
     i_rst_n <= 0;
     repeat (1) @(negedge clk);
     i_rst_n <= 1;
 end
 // Drive input signal
 reg en;
 initial begin
    en <= 0;
 end
 // Print the header
 integer i_data_dat;   // file handle by $fopen
 integer i_data_st;   // status of $fscanf
 integer iter_group;
 initial begin
 repeat (30) @(posedge clk);
 i_data_dat = $fopen("../../Input_Files/CompTree_i_data.txt", "r");

 for (iter_group = 0; iter_group < 220; iter_group = iter_group + 1) begin
 if (!$feof(i_data_dat)) begin
 i_data_st = $fscanf(i_data_dat, "%b\n", Input_i_data);
 repeat (1) @(posedge clk);
 i_data <= Input_i_data;
 en <= 1'b1;
 end
 end
 $fclose(i_data_dat);
 end
 // Dump output signal
 ///======== output_data Check ========///
 reg output_data_out_indicator;
 integer iter_output_data;
 integer CompTree_o_gval_dat;
 integer CompTree_o_gidx_dat;
 initial begin
 // wait for enable and clock
 @(posedge en);
 @(posedge clk); // for balance
 repeat (10) @(posedge clk);
 CompTree_o_gval_dat = $fopen("../../Output_Files/CompTree_o_gval.txt", "w");
 CompTree_o_gidx_dat = $fopen("../../Output_Files/CompTree_o_gidx.txt", "w");
 output_data_out_indicator = 0;
 for (iter_output_data = 0; iter_output_data < 100; iter_output_data = iter_output_data + 1) begin
 output_data_out_indicator = 0;
 $fdisplay(CompTree_o_gval_dat, "%b", o_gval);
 $fdisplay(CompTree_o_gidx_dat, "%b", o_gidx);
 output_data_out_indicator = 1;
 repeat (1) @(posedge clk);
 end
 $fclose(CompTree_o_gval_dat);
 $fclose(CompTree_o_gidx_dat);
 repeat(100) @(posedge clk);
 $finish;
 end
 initial begin
     $dumpfile("wave.vcd");
     $dumpvars(0, TbCompTree0000000001);
 end
 endmodule
