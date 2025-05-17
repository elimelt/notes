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

A register input shouldn't violate setup or hold time constraints within a clock cycle. With $t_{\text{input}, i}$ being the $i$-th time a register input changes, and $T_clk$ being the clock period, we must have:

$$
t_{h} \leq t_{\text{input}, i} \leq T_{clk} - t_{s} ~ \forall i
$$

So there are two key constraints to keep in mind:

- $t_{\text{input}, i} \geq t_h$: The input must be stable for at least the hold time after the clock edge.
- $t_{\text{input}, i} \leq T_{clk} - t_s$: The input must be stable for at least the setup time before the clock edge.

When considering combinational logic delay, we think about minimizing with respect to the hold time constraint, and maximizing with respect to the setup time constraint. So for hold time we want to find the shortest path through our circuit, and for setup time we want to find the longest path through our circuit.