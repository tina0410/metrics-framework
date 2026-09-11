`timescale 1ns/1ps
module tb_mul_latency;
  localparam integer N_PIPELINE = 1;
  reg clk = 0;
  reg rst_n = 0;
  reg valid_i = 0;
  reg [5:0] data_i_1 = 0;
  reg [5:0] data_i_2 = 0;
  wire [8:0] dut_o;
  wire [8:0] reference_o;
  reg [N_PIPELINE-1:0] valid_pipe = 0;
  reg [8:0] expected_pipe [0:N_PIPELINE-1];
  integer cycle = 0;
  integer input_cycle = -1;
  integer first_output_cycle = -1;
  integer previous_output_cycle = -1;
  integer output_count = 0;
  integer i;

  Mul0000000001 dut(
    .i_data_1(data_i_1), .i_data_2(data_i_2), .o_data(dut_o),
    .i_clk(clk)
  );
  Mul0000000002 reference_mul(
    .i_data_1(data_i_1), .i_data_2(data_i_2), .o_data(reference_o)
  );
  always #5 clk = ~clk;

  always @(posedge clk) begin
    if (!rst_n) begin
      cycle = 0;
      valid_pipe <= 0;
      for (i = 0; i < N_PIPELINE; i = i + 1)
        expected_pipe[i] <= 0;
    end else begin
      cycle = cycle + 1;
      if (valid_i && input_cycle < 0)
        input_cycle = cycle;
      if (valid_pipe[N_PIPELINE-1]) begin
        if (dut_o !== expected_pipe[N_PIPELINE-1]) begin
          $display("MUL_DATA_MISMATCH expected=%0d actual=%0d", expected_pipe[N_PIPELINE-1], dut_o);
          $fatal(1);
        end
        if (first_output_cycle < 0)
          first_output_cycle = cycle;
        if (output_count == 2) begin
          $display("MUL_LATENCY cycles=%0d interval=%0d", first_output_cycle - input_cycle, cycle - previous_output_cycle);
          $finish;
        end
        previous_output_cycle = cycle;
        output_count = output_count + 1;
      end
      valid_pipe[0] <= valid_i;
      expected_pipe[0] <= reference_o;
      for (i = 1; i < N_PIPELINE; i = i + 1) begin
        valid_pipe[i] <= valid_pipe[i-1];
        expected_pipe[i] <= expected_pipe[i-1];
      end
    end
  end

  initial begin
    repeat (2) @(posedge clk);
    @(negedge clk); rst_n = 1;
    @(negedge clk); valid_i = 1; data_i_1 = 2; data_i_2 = 3;
    @(negedge clk); data_i_1 = 3; data_i_2 = 4;
    @(negedge clk); data_i_1 = 5; data_i_2 = 6;
    @(negedge clk); valid_i = 0;
    repeat (9) @(posedge clk);
    $fatal(1, "MUL latency simulation timed out");
  end
endmodule
