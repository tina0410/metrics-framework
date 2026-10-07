 `timescale 1ns/1ps
 module TbComp0000000001 ;
 // Inputs
 reg [7-1:0] Input_i_data_1;
 reg [5 -1:0] Input_i_data_2;
 reg [7-1:0] i_data_1;
 reg [5 -1:0] i_data_2;
 reg clk;
 reg i_rst_n;
 // Outputs
 wire o_gidx;
 wire o_lidx;
 wire o_eidx;
 wire [8-1:0] o_gval;
 wire [8-1:0] o_lval;
 // Input ready and Output ready Indicators
 reg Input_rdy;
 reg Output_rdy;
 // Instantiate the DUT
 // Instantiate the DUT
Comp0000000001  u_0000000001_Comp0000000001(.i_data_1(i_data_1), .i_data_2(i_data_2), .o_gidx(o_gidx), .o_lidx(o_lidx), .o_eidx(o_eidx), .o_gval(o_gval), .o_lval(o_lval), .i_rst_n(i_rst_n), .i_clk(clk));
 // Drive clk signal
 initial
 begin
     clk = 0;
      forever #5  clk <= ~clk;
 end
 // Initialize Inputs
 initial begin
 i_data_1 <= 'b0;
 i_data_2 <= 'b0;
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
 integer i_data_1_dat;   // file handle by $fopen
 integer i_data_1_st;   // status of $fscanf
 integer i_data_2_dat;   // file handle by $fopen
 integer i_data_2_st;   // status of $fscanf
 integer iter_group;
 initial begin
 repeat (30) @(posedge clk);
 i_data_1_dat = $fopen("../../Input_Files/Comp_i_data_1.txt", "r");
 i_data_2_dat = $fopen("../../Input_Files/Comp_i_data_2.txt", "r");

 for (iter_group = 0; iter_group < 100; iter_group = iter_group + 1) begin
 if (!$feof(i_data_1_dat) && !$feof(i_data_2_dat)) begin
 i_data_1_st = $fscanf(i_data_1_dat, "%b\n", Input_i_data_1);
 i_data_2_st = $fscanf(i_data_2_dat, "%b\n", Input_i_data_2);
 repeat (1) @(posedge clk);
 i_data_1 <= Input_i_data_1;
 i_data_2 <= Input_i_data_2;
 en <= 1'b1;
 end
 end
 $fclose(i_data_1_dat);
 $fclose(i_data_2_dat);
 end
 // Dump output signal
 ///======== output_data Check ========///
 reg output_data_out_indicator;
 integer iter_output_data;
 integer Comp_o_gidx_dat;
 integer Comp_o_lidx_dat;
 integer Comp_o_eidx_dat;
 integer Comp_o_gval_dat;
 integer Comp_o_lval_dat;
 initial begin
 // wait for enable and clock
 @(posedge en);
 @(posedge clk); // for balance
 repeat (4) @(posedge clk);
 Comp_o_gidx_dat = $fopen("../../Output_Files/Comp_o_gidx.txt", "w");
 Comp_o_lidx_dat = $fopen("../../Output_Files/Comp_o_lidx.txt", "w");
 Comp_o_eidx_dat = $fopen("../../Output_Files/Comp_o_eidx.txt", "w");
 Comp_o_gval_dat = $fopen("../../Output_Files/Comp_o_gval.txt", "w");
 Comp_o_lval_dat = $fopen("../../Output_Files/Comp_o_lval.txt", "w");
 output_data_out_indicator = 0;
 for (iter_output_data = 0; iter_output_data < 100; iter_output_data = iter_output_data + 1) begin
 output_data_out_indicator = 0;
 $fdisplay(Comp_o_gidx_dat, "%b", o_gidx);
 $fdisplay(Comp_o_lidx_dat, "%b", o_lidx);
 $fdisplay(Comp_o_eidx_dat, "%b", o_eidx);
 $fdisplay(Comp_o_gval_dat, "%b", o_gval);
 $fdisplay(Comp_o_lval_dat, "%b", o_lval);
 output_data_out_indicator = 1;
 repeat (1) @(posedge clk);
 end
 $fclose(Comp_o_gidx_dat);
 $fclose(Comp_o_lidx_dat);
 $fclose(Comp_o_eidx_dat);
 $fclose(Comp_o_gval_dat);
 $fclose(Comp_o_lval_dat);
 repeat(100) @(posedge clk);
 $finish;
 end
 initial begin
     $dumpfile("wave.vcd");
     $dumpvars(0, TbComp0000000001);
 end
 endmodule
