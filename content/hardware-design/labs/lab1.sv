/* Top-level module that defines the I/Os for the DE1-SoC board
 * and the circuit behavior.
 */
module lab1 (
  // define ports
  output logic [6:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5,
  output logic [9:0] LEDR,
  input  logic [3:0] KEY,
  input  logic [9:0] SW
  );

  /////////////////////////////////
  // TASK 2
  /////////////////////////////////

  // set LEDR0 to 0/GND and LEDR1 to 1/VDD
  assign LEDR[0] = 1'b0;
  assign LEDR[1] = 1'b1;

  // connect SW2 to LEDR2 and KEY3 to LEDR3
  assign LEDR[2] = SW[2];
  assign LEDR[3] = KEY[3];

  /////////////////////////////////
  // TASK 3
  /////////////////////////////////

  // TODO: connect an inverter between SW2 and LEDR4


  // TODO: connect a 2nd inverter between LEDR4 and LEDR5


  // TODO: connect a 2-input NOR gate between two unused SW and an unused LEDR


  /////////////////////////////////
  // NO CHANGES NEEDED
  /////////////////////////////////

  // instantiate a mux2_1 module for you to play with
  mux2_1 m(.out(LEDR[9]), .i0(SW[7]), .i1(SW[8]), .sel(SW[9]));

  // turns off the HEX displays (covered and used later in the course)
  assign HEX0 = '1;
  assign HEX1 = '1;
  assign HEX2 = '1;
  assign HEX3 = '1;
  assign HEX4 = '1;
  assign HEX5 = '1;

endmodule  // lab1
