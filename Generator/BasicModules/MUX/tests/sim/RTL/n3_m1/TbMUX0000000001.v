 `timescale 1ns/1ps
 module TbMUX0000000001 ;
 reg [3-1:0] i_data;
 reg [2-1:0] i_sel;
 wire [1-1:0] o_data;
MUX0000000001  u_0000000001_MUX0000000001(.i_data(i_data), .i_sel(i_sel), .o_data(o_data));
 task check;
     input [3-1:0] data_value;
     input [2-1:0] select;
     input [1-1:0] expected;
     begin
         i_data = data_value;
         i_sel = select;
         #1;
         if (o_data !== expected) begin
             $display("MUX mismatch: data=%h sel=%h got=%h expected=%h", data_value, select, o_data, expected);
             $fatal(1);
         end
     end
 endtask
 initial begin
     check(3'h1, 2'h0, 1'h1);
     check(3'h1, 2'h1, 1'h0);
     check(3'h1, 2'h2, 1'h0);
     check(3'h2, 2'h0, 1'h0);
     check(3'h2, 2'h1, 1'h1);
     check(3'h2, 2'h2, 1'h0);
     check(3'h4, 2'h0, 1'h0);
     check(3'h4, 2'h1, 1'h0);
     check(3'h4, 2'h2, 1'h1);
     check(3'h5, 2'h0, 1'h1);
     check(3'h5, 2'h1, 1'h0);
     check(3'h5, 2'h2, 1'h1);
     check(3'h5, 2'h3, 1'h0);
     i_data = 3'h5;
     i_sel = {2{1'bx}};
     #1;
     if (o_data !== 1'b0) $fatal(1, "X selector must choose zero");
     i_sel = {2{1'bz}};
     #1;
     if (o_data !== 1'b0) $fatal(1, "Z selector must choose zero");
     $display("PASS MUX N=3 M=1");
     $finish;
 end
 endmodule
