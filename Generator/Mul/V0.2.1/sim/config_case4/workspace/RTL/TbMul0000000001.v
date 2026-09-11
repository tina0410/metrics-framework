 `timescale 1ns/1ps
 module TbMul0000000001 ;
 // Inputs
 reg [5-1:0] Input_i_data_1;
 reg [6 -1:0] Input_i_data_2;
 reg [5-1:0] i_data_1;
 reg [6 -1:0] i_data_2;
 reg clk;
 reg en;
 reg i_rst_n;
 // Outputs
 wire [8-1:0] o_data;
 // Input ready and Output ready Indicators
 reg Input_rdy;
 reg Output_rdy;
 // Instantiate the DUT
 // Instantiate the DUT
Mul0000000001  u_0000000001_Mul0000000001(.i_data_1(i_data_1), .i_data_2(i_data_2), .o_data(o_data), .i_clk(clk));
 // Drive clk signal
 initial
 begin
     clk = 0;
      forever #2.5  clk <= ~clk;
 end
 // Initialize Inputs
 initial begin
 i_data_1 <= 'b0;
 i_data_2 <= 'b0;
 end
 // Enable signal
 initial begin
 en <= 0;
 repeat (3) @(posedge clk);
 en <= 1;
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
 // Drive input ready and output ready signal
 integer Input_rdy_iter;
 initial begin
 Input_rdy <= 0;
 repeat (1) @(posedge en);
 Input_rdy <= 1;
 for (Input_rdy_iter=0; Input_rdy_iter<36; Input_rdy_iter=Input_rdy_iter+1) begin
     # (2.5) Input_rdy <= ~ Input_rdy;
 end
 end
 integer Output_rdy_iter;
 initial begin
 Output_rdy <= 0;
 repeat(1) @(posedge en);
 repeat (1) @(posedge clk); // wait for 1 cycles
 Output_rdy <= 1;
 for (Output_rdy_iter=0; Output_rdy_iter<36; Output_rdy_iter=Output_rdy_iter+1) begin
     # (2.5) Output_rdy <= ~ Output_rdy;
 end
 repeat(30) @(posedge clk);
 $finish;
 end
 // Drive input signal
 integer i_data_1_dat, i_data_1_st;
 initial begin
 repeat (2) @(posedge clk);
 i_data_1_dat = $fopen("../Input_Files/Mul_i_data_1.txt", "r");
 while (!$feof(i_data_1_dat)) begin
     i_data_1_st = $fscanf(i_data_1_dat, "%b\n", Input_i_data_1);
      repeat(1) @(posedge Input_rdy);
     i_data_1 <= Input_i_data_1;
 end
 $fclose(i_data_1_dat);
 end
 integer i_data_2_dat, i_data_2_st;
 initial begin
 repeat (2) @(posedge clk);
 i_data_2_dat = $fopen("../Input_Files/Mul_i_data_2.txt", "r");
 while (!$feof(i_data_2_dat)) begin
     i_data_2_st = $fscanf(i_data_2_dat, "%b\n", Input_i_data_2);
      repeat(1) @(posedge Input_rdy);
     i_data_2 <= Input_i_data_2;
 end
 $fclose(i_data_2_dat);
 end
 // Dump output signal
 integer o_data_dat;
 integer o_data_iter;
 initial begin
 repeat (2) @(posedge clk);
 o_data_dat = $fopen("../Output_Files/Mul_o_data.txt", "w");
 for (o_data_iter=0; o_data_iter<8; o_data_iter=o_data_iter+1) begin
     repeat(1) @(posedge Output_rdy);
     repeat(1) @(negedge clk);
     $fdisplay(o_data_dat, "%b", o_data);
 end
 $fclose(o_data_dat);
 end
 initial begin
     $dumpfile("wave.vcd");
     $dumpvars(0, TbMul0000000001);
 end
 endmodule
