 `timescale 1ns/1ps
 module TbMUX0000000001 ;
 reg [32-1:0] i_data;
 reg [2-1:0] i_sel;
 wire [8-1:0] o_data;
MUX0000000001  u_0000000001_MUX0000000001(.i_data(i_data), .i_sel(i_sel), .o_data(o_data));
 task check;
     input [32-1:0] data_value;
     input [2-1:0] select;
     input [8-1:0] expected;
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
     check(32'hff, 2'h0, 8'hff);
     check(32'hff, 2'h1, 8'h0);
     check(32'hff, 2'h2, 8'h0);
     check(32'hff, 2'h3, 8'h0);
     check(32'hff00, 2'h0, 8'h0);
     check(32'hff00, 2'h1, 8'hff);
     check(32'hff00, 2'h2, 8'h0);
     check(32'hff00, 2'h3, 8'h0);
     check(32'hff0000, 2'h0, 8'h0);
     check(32'hff0000, 2'h1, 8'h0);
     check(32'hff0000, 2'h2, 8'hff);
     check(32'hff0000, 2'h3, 8'h0);
     check(32'hff000000, 2'h0, 8'h0);
     check(32'hff000000, 2'h1, 8'h0);
     check(32'hff000000, 2'h2, 8'h0);
     check(32'hff000000, 2'h3, 8'hff);
     check(32'h744f2a05, 2'h0, 8'h5);
     check(32'h744f2a05, 2'h1, 8'h2a);
     check(32'h744f2a05, 2'h2, 8'h4f);
     check(32'h744f2a05, 2'h3, 8'h74);
     i_data = 32'h744f2a05;
     i_sel = {2{1'bx}};
     #1;
     if (o_data !== 8'b0) $fatal(1, "X selector must choose zero");
     i_sel = {2{1'bz}};
     #1;
     if (o_data !== 8'b0) $fatal(1, "Z selector must choose zero");
     $display("PASS MUX N=4 M=8");
     $finish;
 end
 endmodule
