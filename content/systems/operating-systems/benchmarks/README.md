---
title: Measuring Real DRAM Latency
aliases:
  - operating-systems/benchmarks/README
category: Performance Engineering
tags:
  - memory
  - dram
  - sram
  - cache
  - latency
  - benchmarks
  - pointer-chasing
  - memory-hierarchy
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Measures true serial DRAM latency with a pointer-chasing benchmark, explains why naive strided benchmarks understate it, and covers the SRAM and DRAM physics that set the numbers.
sources:
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
---

## Purpose

When you write `int x = array[i]` in C, how long does it actually take? The answer depends on where the data lives in the memory hierarchy. A DRAM access costs orders of magnitude more than a hit in the CPU's SRAM caches, and the naive way of measuring it understates the cost badly. This note measures the true serial DRAM latency on my machine with a pointer-chasing benchmark and explains why the naive numbers lie.

## Setup

Intel i9-13900HK, 96 GB RAM, 25 MB L3 cache, 64-byte cache lines. The compiler and flags were not recorded with these results, which is why the note is marked needs-review. Rough latencies and sizes for this system:

- L1 cache: ~1-4 ns, 48 KB
- L2 cache: ~10-20 ns, 1.3 MB
- L3 cache: ~20-40 ns, 25 MB
- DRAM: ~60-100 ns, 96 GB

The first three levels are SRAM, static RAM. SRAM works on entirely different physical principles than DRAM, and the difference explains most of the latency gap.

## SRAM

SRAM is built from standard digital logic. A basic 6T-SRAM cell uses 6 transistors arranged as cross-coupled inverters. An inverter is a logic gate that outputs the inverse of its input, and cross-coupled means each inverter's output feeds the other's input, which creates a bistable circuit that holds its state.

```text
    VDD
     |
  |--+--|  Cross-coupled
  |     |  inverters (bistable)
--+     +--
  |     |
  |--+--|
     |
    GND

Access transistors connect to bit lines
```

In Verilog, you'd write:

```verilog
module sram #(
    parameter ADDR_WIDTH = 10,  // 1024 words
    parameter DATA_WIDTH = 32
)(
    input wire clk,
    input wire [ADDR_WIDTH-1:0] addr,
    output reg [DATA_WIDTH-1:0] data
);
    reg [DATA_WIDTH-1:0] mem [0:(1<<ADDR_WIDTH)-1];

    always @(posedge clk) begin
        data <= mem[addr];
    end
endmodule
```

Physically, this synthesizes to decoder logic that activates one of 1024 word lines, a memory array of 1024 rows x 32 bits of six-transistor cells, sense amplifiers that detect voltage on the bit lines and amplify it to logic levels, and output drivers for the data bus.

SRAM is static. As long as power is on, the cross-coupled inverters hold their state. Access time is around 0.3-1 ns because the whole read is just transistor switching. The catch is cost. Six transistors per bit eat die area fast, which is why my L1 cache is only 48 KB.

## DRAM

DRAM stores each bit as charge on a capacitor. A DRAM cell is one transistor plus one capacitor (1T1C):

```text
    Bit Line (vertical metal trace)
       |
       |
    [===]  <- Capacitor (tens of femtofarads)
       |
    --+--  <- NMOS access transistor
       |
    Word Line (horizontal polysilicon)
```

Where SRAM is digital, DRAM reads are an analog operation. The capacitor holds a voltage, and capacitors leak charge over time according to their RC time constants. That makes DRAM dynamic. Without a refresh roughly every 64 ms, the data disappears. Drepper's [What Every Programmer Should Know About Memory](https://www.akkadia.org/drepper/cpumemory.pdf) covers the cell design and refresh mechanics in depth.

I don't know the low-level DRAM internals well, since I'm a computer engineer rather than an electrical engineer. The baseline model I use to reason about DRAM performance goes like this:

1. Precharge the bit line
2. Activate the word line (open the access transistor)
3. The capacitor connects to the bit line
4. Charge redistributes between the tiny cell capacitor and the much larger bit line capacitance
5. The result is a tiny voltage swing on the bit line, on the order of 100-200 mV

A sense amplifier, a differential analog circuit, detects this small swing and amplifies it to full logic levels. The sense amplifier also latches the amplified value into the row buffer.

## The row buffer

DRAM cells are arranged in a 2D array, and access happens in two steps:

```text
Step 1: RAS (Row Address Strobe)
  - Activate word line
  - All ~1024-8192 cells in that row dump charge onto bit lines
  - Sense amps detect, amplify, and latch values
  - Row buffer now holds the entire row (~1-8 KB)

Step 2: CAS (Column Address Strobe)
  - Select specific column(s) from row buffer
  - Drive data onto output bus
```

The row buffer is real hardware, a set of SRAM-like latches, one per column. Once a row is open, hitting different columns in that row is fast (~10-15 ns) because you're just reading latches.

Accessing a closed row takes the slow path. Precharge closes the current row (~15 ns), RAS opens the new row and waits for sensing (~15 ns), then CAS does the column access (~10 ns). Call it 40-50 ns for the full row operation, versus 10-15 ns when the row is already open and you only pay the CAS.

## Physical constraints

Why does this take so long? Two effects dominate.

Wire delay. Signals travel at roughly 2/3 the speed of light in a conductor. On a 3 GHz CPU, light in vacuum covers about 10 cm per clock cycle, and the DRAM chips sit several centimeters from the CPU over motherboard traces. The round-trip signal propagation alone is on the order of 5-10 ns.

Capacitor charging. The cell capacitor is tiny and takes time to charge and discharge. Worse, activating a word line connects every cell in the row, thousands of capacitors, to bit lines at once, and all those sense amplifiers must stabilize before the data is valid. How long exactly? I'm not sure, and I refuse to do the math.

## First attempt, and why it failed

I wrote a simple benchmark to compare sequential and strided access:

```c
// Sequential access
for (size_t i = 0; i < n; i++) {
    sum += array[i];
}

// Strided access (every 1024th element)
for (size_t i = 0; i < n; i += 1024) {
    sum += array[i];
}
```

Running on a 64 MB array, larger than my 25 MB L3:

```text
Sequential:  1.50 ns/access
Stride 1024: 13.18 ns/access
```

A difference, sure, but both numbers were suspiciously low for DRAM. The `perf` counters showed the strided version missing L3 constantly:

```text
LLC-load-misses: 80.52% of all L3 accesses
```

So the loads were reaching DRAM, yet each one appeared to take only 13 ns. Something was hiding the true latency. The culprit is memory-level parallelism. My loop does this:

```c
sum += array[i];      // Load request sent
sum += array[i+1024]; // Another load sent before first completes
// ... multiple loads in flight ...
```

The loads are independent. The CPU never needs the result of one to start the next, so its load/store unit keeps a queue of outstanding requests and can hold around 10-12 loads in flight at once. If each DRAM access takes 100 ns but 10 are in flight, results arrive every 10 ns on average. It's pipelining, applied to memory requests. I measure this effect directly in [[systems/operating-systems/benchmarks/mlp|memory-level parallelism]].

## Pointer chasing

To measure true serial latency, each load must depend on the previous one. Pointer chasing does this. Build a linked list where each element holds the index of the next, in randomized order:

```c
// Setup: create randomized pointer chain
// array[i] contains the index of the next element
for (size_t i = 0; i < n - 1; i++) {
    array[indices[i]] = indices[i + 1];
}

// Chase pointers - each load depends on the previous
size_t index = 0;
for (size_t i = 0; i < n; i++) {
    index = array[index];  // Must wait for this load
}
```

The CPU can't start loading `array[index]` until it knows `index`. Every load carries a true data dependency on the previous one, so nothing overlaps.

## Results

Three benchmarks on a 4 GB array, well beyond cache size:

| Benchmark | ns/access | LLC Misses | Explanation |
|-----------|-----------|------------|-------------|
| Sequential | 1.35 | 98% | Hardware prefetcher brings data into cache before needed |
| Random (parallel) | 7.90 | 99% | Hitting DRAM but MLP hides latency (~10 loads in flight) |
| Pointer Chase | 97.40 | 99% | True serial DRAM latency, no parallelism possible |

## Why sequential is so fast

The hardware prefetcher detects the stride-1 pattern and speculatively fetches cache lines ahead of the program. The `perf` counts make this obvious:

```text
Sequential:    1.3M LLC loads    (for 537M accesses)
Random:        1.07B LLC loads   (for 537M accesses)
```

With sequential access, only about 0.2% of accesses ever reach L3. The prefetcher pulls lines into L1 and L2 before the load instruction even executes. Each 64-byte line covers 8 adjacent `uint64_t` values, and the prefetcher tracks multiple concurrent streams with strides up to a few KB.

## Reading the 97 ns number

My guess is that 97 ns is an average across row buffer hits and misses. A row buffer hit might land around 50-60 ns end to end, while a miss that has to precharge the old row and activate a new one could run 100-120 ns. Random pointer chasing hits a mix of both, and the memory controller can't optimize for row locality when it can't predict the access pattern. I hesitate to pin it down further without writing more benchmarks.

## Reproduction

```bash
make
./run_benchmarks.sh 4096  # 4096 MB array
```

## Sources

- [What Every Programmer Should Know About Memory (Drepper)](https://www.akkadia.org/drepper/cpumemory.pdf)

## Related notes

- [[systems/operating-systems/benchmarks/mlp|memory-level parallelism]]
- [[systems/operating-systems/benchmarks/bandwidth|memory bandwidth]]
- [[systems/operating-systems/benchmarks/tlb|TLB and page walks]]
