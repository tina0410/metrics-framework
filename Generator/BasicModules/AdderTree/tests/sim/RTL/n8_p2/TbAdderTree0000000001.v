 `timescale 1ns/1ps
 module TbAdderTree0000000001 ;
 reg [64-1:0] i_data;
 wire [12-1:0] o_data;
 reg i_clk;
AdderTree0000000001  u_0000000001_AdderTree0000000001(.i_data(i_data), .o_data(o_data), .i_clk(i_clk));
 initial i_clk = 1'b0;
 always #5 i_clk = ~i_clk;
 task check;
     input [64-1:0] value;
     input [12-1:0] expected;
     begin
         @(negedge i_clk);
         i_data = value;
         repeat (2) @(posedge i_clk);
         #1;
         if (o_data !== expected) begin
             $display("AdderTree mismatch: in=%h got=%h expected=%h", value, o_data, expected);
             $fatal(1);
         end
     end
 endtask
 initial begin
     i_data = 64'b0;
     check(64'h807060504030201, 12'h24);
     check(64'h7a69584736251403, 12'h1f4);
     check(64'hff00ff00ff00ff00, 12'h3fc);
     $display("PASS AdderTree N_INPUTS=8 N_PIPELINES=2");
     $finish;
 end
 endmodule
