 `timescale 1ns/1ps
 module TbAdderTree0000000001 ;
 reg [56-1:0] i_data;
 wire [12-1:0] o_data;
 reg i_clk;
 reg i_rst_n;
AdderTree0000000001  u_0000000001_AdderTree0000000001(.i_data(i_data), .o_data(o_data), .i_clk(i_clk), .i_rst_n(i_rst_n));
 initial i_clk = 1'b0;
 always #5 i_clk = ~i_clk;
 task check;
     input [56-1:0] value;
     input [12-1:0] expected;
     begin
         @(negedge i_clk);
         i_data = value;
         repeat (4) @(posedge i_clk);
         #1;
         if (o_data !== expected) begin
             $display("AdderTree mismatch: in=%h got=%h expected=%h", value, o_data, expected);
             $fatal(1);
         end
     end
 endtask
 initial begin
     i_data = 56'b0;
     i_rst_n = 1'b0;
     #2;
     i_rst_n = 1'b1;
     check(56'h7060504030201, 12'h1c);
     check(56'h69584736251403, 12'h17a);
     check(56'hff00ff00ff00, 12'h2fd);
     $display("PASS AdderTree N_INPUTS=7 N_PIPELINES=4");
     $finish;
 end
 endmodule
