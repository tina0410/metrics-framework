 `timescale 1ns/1ps
 module TbMUX0000000001 ;
 reg [65-1:0] i_data;
 reg [3-1:0] i_sel;
 wire [13-1:0] o_data;
MUX0000000001  u_0000000001_MUX0000000001(.i_data(i_data), .i_sel(i_sel), .o_data(o_data));
 task check;
     input [65-1:0] data_value;
     input [3-1:0] select;
     input [13-1:0] expected;
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
     check(65'h1fff, 3'h0, 13'h1fff);
     check(65'h1fff, 3'h1, 13'h0);
     check(65'h1fff, 3'h2, 13'h0);
     check(65'h1fff, 3'h3, 13'h0);
     check(65'h1fff, 3'h4, 13'h0);
     check(65'h3ffe000, 3'h0, 13'h0);
     check(65'h3ffe000, 3'h1, 13'h1fff);
     check(65'h3ffe000, 3'h2, 13'h0);
     check(65'h3ffe000, 3'h3, 13'h0);
     check(65'h3ffe000, 3'h4, 13'h0);
     check(65'h7ffc000000, 3'h0, 13'h0);
     check(65'h7ffc000000, 3'h1, 13'h0);
     check(65'h7ffc000000, 3'h2, 13'h1fff);
     check(65'h7ffc000000, 3'h3, 13'h0);
     check(65'h7ffc000000, 3'h4, 13'h0);
     check(65'hfff8000000000, 3'h0, 13'h0);
     check(65'hfff8000000000, 3'h1, 13'h0);
     check(65'hfff8000000000, 3'h2, 13'h0);
     check(65'hfff8000000000, 3'h3, 13'h1fff);
     check(65'hfff8000000000, 3'h4, 13'h0);
     check(65'h1fff0000000000000, 3'h0, 13'h0);
     check(65'h1fff0000000000000, 3'h1, 13'h0);
     check(65'h1fff0000000000000, 3'h2, 13'h0);
     check(65'h1fff0000000000000, 3'h3, 13'h0);
     check(65'h1fff0000000000000, 3'h4, 13'h1fff);
     check(65'h9903a013c054005, 3'h0, 13'h5);
     check(65'h9903a013c054005, 3'h1, 13'h2a);
     check(65'h9903a013c054005, 3'h2, 13'h4f);
     check(65'h9903a013c054005, 3'h3, 13'h74);
     check(65'h9903a013c054005, 3'h4, 13'h99);
     check(65'h9903a013c054005, 3'h5, 13'h0);
     check(65'h9903a013c054005, 3'h6, 13'h0);
     check(65'h9903a013c054005, 3'h7, 13'h0);
     i_data = 65'h9903a013c054005;
     i_sel = {3{1'bx}};
     #1;
     if (o_data !== 13'b0) $fatal(1, "X selector must choose zero");
     i_sel = {3{1'bz}};
     #1;
     if (o_data !== 13'b0) $fatal(1, "Z selector must choose zero");
     $display("PASS MUX N=5 M=13");
     $finish;
 end
 endmodule
