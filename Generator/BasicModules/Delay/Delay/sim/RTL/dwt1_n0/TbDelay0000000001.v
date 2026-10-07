 `timescale 1ns/1ps
 module TbDelay0000000001 ;
 reg [1-1:0] i_data;
 wire [1-1:0] o_data;
Delay0000000001  u_0000000001_Delay0000000001(.i_data(i_data), .o_data(o_data));
 task check;
     input [1-1:0] value;
     begin
         i_data = value;
         #1;
         if (o_data !== value) begin
             $display("Delay mismatch: got=%h expected=%h", o_data, value);
             $fatal(1);
         end
     end
 endtask
 initial begin
     i_data = 1'b0;
     check(1'h0);
     check(1'h1);
     check(1'h1);
     check(1'h0);
     $display("PASS Delay DWT=1 N_CLK=0");
     $finish;
 end
 endmodule
