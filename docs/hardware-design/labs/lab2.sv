/* Top-level module that defines the I/Os for the DE1-SoC board
 * and the circuit behavior.
 */
module lab2 (
  output logic [6:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5,
  output logic [9:0] LEDR,
  input  logic [3:0] KEY,
  input  logic [9:0] SW
  );

  // Default values, turns off the HEX displays
  assign HEX0 = 7'b1111111;
  assign HEX1 = 7'b1111111;
  assign HEX2 = 7'b1111111;
  assign HEX3 = 7'b1111111;
  assign HEX4 = 7'b1111111;
  assign HEX5 = 7'b1111111;
	
  // Logic to check if SW3-SW0 match your bottom digit,
  // and SW7-SW4 match the next.
  // Result should drive LEDR0.
  logic d1, d2;
  
  two t1(.out(d1), .i0(SW[0]), .i1(SW[1]), .i2(SW[2]), .i3(SW[3]));
  two t2(.out(d2), .i0(SW[4]), .i1(SW[5]), .i2(SW[6]), .i3(SW[7]));
	
  assign LEDR[0] = d2 & d1;
endmodule  // lab2
