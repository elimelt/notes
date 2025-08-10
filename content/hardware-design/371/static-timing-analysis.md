---
title: Static Timing Analysis
category: Hardware
tags: timing analysis, verilog, systemverilog, clock domain crossing, metastability
description: How should you reason about timing in hardware? What are the key thresholds for signal integrity?
---

# Static Timing Analysis

## Sequential Timing Constraints

- $t_s$ (**Setup Time**): The minimum time before the clock edge that the data input must be stable. This is to ensure that the data is latched correctly by the flip-flop.
- $t_h$ (**Hold Time**): The minimum time after the clock edge that the data input must remain stable. This is to ensure that the data is not changed before it is latched by the flip-flop.
- $t_{co}$ (**Clock-to-Q Delay**): The time it takes for the output of the flip-flop to change after the clock edge. This is the time it takes for the data to propagate through the flip-flop.

```txt
            T (clk edge)
            |
            |
  +---------+------------+
  |     reg must be      |
  |     stable during    |
  |     this time        |
T - t_s                T + t_h
```


A register input shouldn't violate setup or hold time constraints within a clock cycle. With $t_{\text{input}, i}$ being the $i$-th time a register input changes, and $T_clk$ being the clock period, we must have:

$$
t_{h} \leq t_{\text{input}, i} \leq T_{clk} - t_{s} ~ \forall i
$$

So there are two key constraints to keep in mind:

- $t_{\text{input}, i} \geq t_h$: The input must be stable for at least the hold time after the clock edge.
- $t_{\text{input}, i} \leq T_{clk} - t_s$: The input must be stable for at least the setup time before the clock edge.

When considering combinational logic delay, we think about minimizing with respect to the hold time constraint, and maximizing with respect to the setup time constraint. So for hold time we want to find the shortest path through our circuit, and for setup time we want to find the longest path through our circuit.

For example, if you are given $t_{co}$, $t_{h}$, $t_{s}$, and $T_{clk}$, you can calculate the range of tolerable delays for components on a path between two registers, or the input signal's delay after clock edge to change, or some variation on these. In order to do this, you identify the longest and shortest paths through the circuit that concern your component/between the two registers, and then write out the inequalities.

## In Practice

Static timing analysis usually happens twice in the FPGA design process: once after synthesis (static analysis of the RTL), and once after place and route (static analysis of the netlist).

### Circuit Path Categorization

- **Data paths** are between inputs, sequential elements, and outputs
- **Clock paths** are from device ports or internally-generated clocks to the clock pins of sequential elements
- **Asynchronous paths** are between inputs and asynchronous set and clear pins of sequential elements

