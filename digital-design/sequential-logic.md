---
title: Sequential Logic (SL)
category: hardware
tags: sequential logic, digital systems, finite state machines, flip-flops, clock signals
description: Explains the concept of sequential logic in digital systems and its applications.
---

# Sequential Logic (SL)

Whereas in *combinational logic*, you have outputs which are direct functions of their inputs, with sequential logic the presence of *feedback* gives circuits the ability to store state. This is the basis for memory and computation in digital systems.

This helps control the flow of information through blocks of combinational logic, usually synchronizing with a clock signal. One of the major use cases of sequential logic is in **Finite State Machines (FSM)**. Without SL, the output of a combinational circuit would change instantly with every change in input, which can lead to unpredictable behavior within intermediate states, leading to unexpected outputs.

## Positive Edge-Triggered D-type Flip-Flop

On the rising edge of the clock signal, input is sampled and transferred to the output signal. At all other times, changes in the input are ignored and the previously samples value is retained. This essentially has the effect of *synchronizing* the input signal with the clock signal, or rather quantizing changes in the input signal to only fall on the rising edge of the clock signal.

## Registers

A `n` bit register is composed of `n` flip-flops. Registers have the addition of a `reset` signal, which sets the register to a known state if it is high during a clock trigger.

## Flip-Flop Timing

- **Setup Time**: how long the input needs to be stable *before* the clock trigger for a proper read
- **Hold Time**: how long the input needs to be stable *after* the clock trigger for a proper read
- **"Clock-to-Q Delay"**: how long it takes the output to changed after a clock trigger

Let $t_{input, i}$ be the time it takes for the input of a register to change for the $i$-th time in a single clock cycle, measured from the clock signal. Then we need...

$$
t_{hold} \le t_{input, i} \le t_{period} - t_{setup}
$$

### Minimum Delay

If the shortest path to a register input is too short, then $t_{hold}$ could be violated, meaning the input could change before the state is "locked in". We have...

- `min_delay = min(clk_to_q + min_cl_delay, min_cl_delay)`
- `min_delay >= t_hold`

### Maximum Clock Frequency

The maximum frequency you can run your clock at is limited by the amount of time needed to get a correct next state to your registers. We must have...

`max_delay = max(clock_to_q + max_cl_delay, max_cl_delay)`

Then, `min_period = max_delay + t_setup`, and `max_freq = 1/min_period`.