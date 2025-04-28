module lab2_tb();
  logic [6:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5;
  logic [9:0] LEDR;
  logic [3:0] KEY;
  logic [9:0] SW;

  // instantiate device under test
  lab2 dut (.HEX0, .HEX1, .HEX2, .HEX3, .HEX4, .HEX5, .KEY, .LEDR, .SW);

  // test input sequence - try all combinations of inputs
  integer i;
  initial begin
    SW[9] = 1'b0;
    SW[8] = 1'b0;
    for(i = 0; i <256; i++) begin
      SW[7:0] = i; #10;
    end
  end
endmodule  // lab2_tb
