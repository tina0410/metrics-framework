 `timescale 1ns/1ps
 module TbDelay0000000001 ;
 reg [16-1:0] i_data;
 wire [16-1:0] o_data;
 reg i_clk;
Delay0000000001  u_0000000001_Delay0000000001(.i_data(i_data), .o_data(o_data), .i_clk(i_clk));
 initial i_clk = 1'b0;
 always #5 i_clk = ~i_clk;
 task check;
     input [16-1:0] value;
     begin
         @(negedge i_clk);
         i_data = value;
         repeat (4) @(posedge i_clk);
         #1;
         if (o_data !== value) begin
             $display("Delay mismatch: got=%h expected=%h", o_data, value);
             $fatal(1);
         end
     end
 endtask
 initial begin
     i_data = 16'b0;
     check(16'h0);
     check(16'h1);
     check(16'hffff);
     check(16'h5a);
     $display("PASS Delay DWT=16 N_CLK=4");
     $finish;
 end
 endmodule
