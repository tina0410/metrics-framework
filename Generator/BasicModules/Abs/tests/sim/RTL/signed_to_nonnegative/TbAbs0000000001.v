 `timescale 1ns/1ps
 module TbAbs0000000001 ;
     reg  [7-1:0] Input_i_data;
     reg  [7-1:0] i_data;
     reg                     clk;
     reg                     i_rst_n;
     wire [6-1:0] o_data;
 // Instantiate the DUT
Abs0000000001  u_0000000001_Abs0000000001(.i_data(i_data), .o_data(o_data), .i_clk(clk), .i_rst_n(i_rst_n));
 initial
 begin
     clk = 0;
      forever #5  clk <= ~clk;
 end
 initial begin
 i_data <= 'b0;
 end
 initial
 begin
     i_rst_n <= 1;
     repeat (1) @(negedge clk);
     i_rst_n <= 0;
     repeat (1) @(negedge clk);
     i_rst_n <= 1;
 end
 reg en;
 initial begin
    en <= 0;
 end
 // Print the header
 integer i_data_dat;   // file handle by $fopen
 integer i_data_st;   // status of $fscanf
 integer iter_group;
 initial begin
 repeat (3) @(posedge clk);
 i_data_dat = $fopen("../../Input_Files/abs_i_data.txt", "r");

 for (iter_group = 0; iter_group < 32; iter_group = iter_group + 1) begin
 if (!$feof(i_data_dat)) begin
 i_data_st = $fscanf(i_data_dat, "%b\n", Input_i_data);
 repeat (1) @(posedge clk);
 i_data <= Input_i_data;
 en <= 1'b1;
 end
 end
 $fclose(i_data_dat);
 end
 ///======== output_data Check ========///
 reg output_data_out_indicator;
 integer iter_output_data;
 integer abs_o_data_dat;
 initial begin
 // wait for enable and clock
 @(posedge en);
 @(posedge clk); // for balance
 repeat (1) @(posedge clk);
 abs_o_data_dat = $fopen("../../Output_Files/abs_o_data.txt", "w");
 output_data_out_indicator = 0;
 for (iter_output_data = 0; iter_output_data < 32; iter_output_data = iter_output_data + 1) begin
 output_data_out_indicator = 0;
 $fdisplay(abs_o_data_dat, "%b", o_data);
 output_data_out_indicator = 1;
 repeat (1) @(posedge clk);
 end
 $fclose(abs_o_data_dat);
 repeat(10) @(posedge clk);
 $finish;
 end
 initial begin
     $dumpfile("wave.vcd");
     $dumpvars(0, TbAbs0000000001);
 end
 endmodule
