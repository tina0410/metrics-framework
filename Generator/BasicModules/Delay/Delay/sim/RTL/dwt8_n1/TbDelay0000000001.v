 `timescale 1ns/1ps
 module TbDelay0000000001 ;
 reg [8-1:0] i_data;
 wire [8-1:0] o_data;
 reg i_clk;
 reg i_rst_n;
Delay0000000001  u_0000000001_Delay0000000001(.i_data(i_data), .o_data(o_data), .i_clk(i_clk), .i_rst_n(i_rst_n));
 initial i_clk = 1'b0;
 always #5 i_clk = ~i_clk;
 task check;
     input [8-1:0] value;
     begin
         @(negedge i_clk);
         i_data = value;
         repeat (1) @(posedge i_clk);
         #1;
         if (o_data !== value) begin
             $display("Delay mismatch: got=%h expected=%h", o_data, value);
             $fatal(1);
         end
     end
 endtask
 initial begin
     i_data = 8'b0;
     i_rst_n = 1'b0;
     #2;
     if (o_data !== 8'b0) $fatal(1, "reset did not clear Delay output");
     i_rst_n = 1'b1;
     check(8'h0);
     check(8'h1);
     check(8'hff);
     check(8'h5a);
     $display("PASS Delay DWT=8 N_CLK=1");
     $finish;
 end
 endmodule
