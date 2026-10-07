 `timescale 1ns/1ps
 module TbAdderTree0000000001 ;
 reg [32-1:0] i_data;
 wire [12-1:0] o_data;
 reg i_clk;
AdderTree0000000001  u_0000000001_AdderTree0000000001(.i_data(i_data), .o_data(o_data), .i_clk(i_clk));
 initial i_clk = 1'b0;
 always #5 i_clk = ~i_clk;
 task check;
     input [32-1:0] value;
     input [12-1:0] expected;
     begin
         @(negedge i_clk);
         i_data = value;
         repeat (1) @(posedge i_clk);
         #1;
         if (o_data !== expected) begin
             $display("AdderTree mismatch: in=%h got=%h expected=%h", value, o_data, expected);
             $fatal(1);
         end
     end
 endtask
 initial begin
     i_data = 32'b0;
     check(32'h4030201, 12'ha);
     check(32'h36251403, 12'h72);
     check(32'hff00ff00, 12'h1fe);
     $display("PASS AdderTree N_INPUTS=4 N_PIPELINES=1");
     $finish;
 end
 endmodule
