 `timescale 1ns/1ps
 module TbAdderTree0000000001 ;
 reg [24-1:0] i_data;
 wire [12-1:0] o_data;
AdderTree0000000001  u_0000000001_AdderTree0000000001(.i_data(i_data), .o_data(o_data));
 task check;
     input [24-1:0] value;
     input [12-1:0] expected;
     begin
         i_data = value;
         #1;
         if (o_data !== expected) begin
             $display("AdderTree mismatch: in=%h got=%h expected=%h", value, o_data, expected);
             $fatal(1);
         end
     end
 endtask
 initial begin
     i_data = 24'b0;
     check(24'h30201, 12'h6);
     check(24'h251403, 12'h3c);
     check(24'hff00, 12'hff);
     $display("PASS AdderTree N_INPUTS=3 N_PIPELINES=0");
     $finish;
 end
 endmodule
