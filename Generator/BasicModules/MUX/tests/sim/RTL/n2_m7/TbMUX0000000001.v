 `timescale 1ns/1ps
 module TbMUX0000000001 ;
 reg [14-1:0] i_data;
 reg [1-1:0] i_sel;
 wire [7-1:0] o_data;
MUX0000000001  u_0000000001_MUX0000000001(.i_data(i_data), .i_sel(i_sel), .o_data(o_data));
 task check;
     input [14-1:0] data_value;
     input [1-1:0] select;
     input [7-1:0] expected;
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
     check(14'h7f, 1'h0, 7'h7f);
     check(14'h7f, 1'h1, 7'h0);
     check(14'h3f80, 1'h0, 7'h0);
     check(14'h3f80, 1'h1, 7'h7f);
     check(14'h1505, 1'h0, 7'h5);
     check(14'h1505, 1'h1, 7'h2a);
     i_data = 14'h1505;
     i_sel = {1{1'bx}};
     #1;
     if (o_data !== 7'b0) $fatal(1, "X selector must choose zero");
     i_sel = {1{1'bz}};
     #1;
     if (o_data !== 7'b0) $fatal(1, "Z selector must choose zero");
     $display("PASS MUX N=2 M=7");
     $finish;
 end
 endmodule
