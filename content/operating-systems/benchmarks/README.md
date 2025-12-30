# Measuring Real DRAM Latency

When you write `int x = array[i]` in C, how long does it actually take? The answer depends on where the data lives in your system's memory hierarchy. Accessing data in DRAM, the legit RAM that you have probably touched/nervously forced into sockets (if you've built a computer), is orders of magnitude slower than accessing data in the CPU's caches (SRAM, e.g. L1, L2, L3)

## The Memory Hierarchy

Modern CPUs have multiple levels of storage, each with different speeds. The system I'm testing on looks like this:

- **L1 cache**: ~1-4 ns, 48 KB
- **L2 cache**: ~10-20 ns, 1.3 MB  
- **L3 cache**: ~20-40 ns, 25 MB
- **DRAM**: ~60-100 ns, 96 GB

The first three are SRAM - static RAM. SRAM is fundamentally different from DRAM, in that it both functions and is built differently, using entirely different physical mechanisms/principles than DRAM.

## SRAM

SRAM is built from standard digital logic. A basic SRAM cell (6T-SRAM) uses 6 transistors arranged as \*cross-coupled \*\*inverters:

```
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

Physically, this synthesizes to:
1. **Decoder logic**: Activates one of 1024 word lines based on address
2. **Memory array**: 1024 rows x 32 bits = 32,768 six-transistor cells
3. **Sense amplifiers**: Detect voltage on bit lines and amplify to logic levels
4. **Output drivers**: Drive the data bus

Perhaps mose importantly, SRAM is **static**; as long as power is on, the cross-coupled inverters hold their state. Access time is ~0.3-1 ns because it's just transistor switching.

However, 6 transistors per bit makes SRAM expensive in die area. My L1 cache is only 48 KB 😞

\* cross-coupled means the output of one inverter feeds back into the other, creating a stable state.

\*\* inverters are logic gates that output the inverse of their input

## DRAM

DRAM stores each bit as **charge on a capacitor**. A DRAM cell is just one transistor plus one capacitor (1T1C):

```
    Bit Line (vertical metal trace)
       |
       |
    [===]  ← Capacitor (~50 fF, holds ~30,000 electrons)
       |
    --+--  ← NMOS access transistor
       |
    Word Line (horizontal polysilicon)
```

Like I mentioned earlier, DRAM and SRAM are funamentally different because DRAM is an analog circuit, while SRAM is digital. The capacitor holds a voltage, but capacitors leak charge over time according to RC time constants. Therefore DRAM is **dynamic**; without periodic refresh (every \~64ms), the data disappears.

I don't actually know that much about the low-level internals/implementation of DRAM, because I'm a computer engineer, not an electrical engineer. That being said, there *is* at least a baseline understanding I use to reason about DRAM performance from the perspective of a computer engineer. 

It works like this:

1. Precharge bit line
2. Activate word line (open transistor)
3. Capacitor connects to bit line
4. Charge redistributes between tiny capacitor (50 fF) and large bit line (~500 fF)
5. This creates a tiny voltage swing: \~100-200 mV

A **sense amplifier** (differential analog circuit) detects this small voltage and amplifies it to full logic levels. The sense amplifier also latches the amplified value into what's called the **row buffer**.

## The Row Buffer

DRAM cells are arranged in a 2D array. To access data:

```
Step 1: RAS (Row Address Strobe)
  - Activate word line
  - All ~1024-8192 cells in that row dump charge onto bit lines
  - Sense amps detect, amplify, and latch values
  - Row buffer now holds the entire row (~1-8 KB)
  
Step 2: CAS (Column Address Strobe)  
  - Select specific column(s) from row buffer
  - Drive data onto output bus
```

The row buffer is actual hardware - a set of SRAM-like latches (one per column). Once a row is open, accessing different columns in that row is fast (~10-15 ns) because you're just reading from latches.

Accessing a on the slow path requires:
1. **Precharge**: Close current row (~15 ns)
2. **RAS**: Open new row, wait for sensing (~15 ns)
3. **CAS**: Column access (~10 ns)

Total: ~40-50 ns for the row operation, vs ~10-15 ns if the row is already open (meaning you just did a CAS)

## Physical Constraints

Why does this take so long?

**Wire delay**: Signals travel at roughly 2/3 the speed of light in silicon. On a 3 GHz CPU, if light travels ~6 cm per clock cycle, and DRAM chips are several centimeters away from the CPU connected by traces on the motherboard, then just the round-trip signal propagation is ~5-10 ns.

**Capacitor charging**: The DRAM cell capacitor is small (~50 fF) and takes time to charge/discharge. Likewise, when you activate a word line, you're simultaneously connecting ~1024-8192 capacitors to bit lines. All those sense amplifiers must stabilize before data is valid. How much time does this take? I'm not sure, and I refuse to do the math.

## Initial Benchmark Attempt

I wrote a simple benchmark to measure sequential vs strided access:

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

Running on a 64 MB array (larger than my 25 MB L3 cache):

```
Sequential:  1.50 ns/access
Stride 1024: 13.18 ns/access
```

This showed a difference, but both numbers were suspiciously low for DRAM access. Looking at `perf` counters:

```
LLC-load-misses: 80.52% of all L3 accesses
```

The strided version was missing L3 and going to DRAM, yet only taking 13 ns. Something was hiding the true latency. Modern CPUs can have ~10-12 outstanding memory requests in flight simultaneously. When my loop does:

```c
sum += array[i];      // Load request sent
sum += array[i+1024]; // Another load sent before first completes
// ... multiple loads in flight ...
```

The loads are independent - the CPU doesn't need the result of one to start the next. This **memory-level parallelism (MLP)** hides latency. If each DRAM access takes 100 ns but I have 10 in flight, I get results every ~10 ns on average.

The CPU's load/store unit has a queue of pending memory operations. As long as there are no data dependencies, it can issue new loads while waiting for old ones to complete. Like pipelining, but for memory operations across multiple clock cycles.

## No MLP: Pointer Chasing

To measure true serial latency, each load must depend on the previous one. The solution is pointer chasing - create a linked list where each element points to the next:

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

The CPU can't start `array[index]` until it knows what `index` is. Each load has a true data dependency on the previous one, preventing the CPU from issuing them in parallel.

## Results

I implemented three benchmarks and ran them on a 4 GB array (well beyond cache size):

**System:** Intel i9-13900HK, 96 GB RAM, 25 MB L3 cache, 64-byte cache lines

| Benchmark | ns/access | LLC Misses | Explanation |
|-----------|-----------|------------|-------------|
| Sequential | 1.35 | 98% | Hardware prefetcher brings data into cache before needed |
| Random (parallel) | 7.90 | 99% | Hitting DRAM but MLP hides latency (~10 loads in flight) |
| Pointer Chase | **97.40** | 99% | True serial DRAM latency - no parallelism possible |

## Why Sequential is So Fast

Modern CPUs have hardware prefetchers that detect access patterns. When they see sequential access (stride of 1), they speculatively fetch cache lines ahead of the program. The `perf` stats show this clearly:

```
Sequential:    1.3M LLC loads    (for 537M accesses)
Random:        1.07B LLC loads   (for 537M accesses)
```

With sequential access, only ~0.2% of accesses reach L3 - almost everything is prefetched into L1/L2. The prefetcher is effectively predicting the future, bringing cache lines into L1 before the load instruction even executes.

Cache lines are 64 bytes on my system, so each prefetch brings in 8 adjacent `uint64_t` values. The prefetcher tracks multiple concurrent streams and can detect strides up to a few KB.

## My guess for the 97 ns latency

This is actually an average across row buffer hits and misses. A row buffer hit (data in already-open row) might be ~50-60 ns, while a row buffer miss (must precharge old row, activate new one) could be ~100-120 ns.

My random pointer chasing likely hits a mix of both, averaging to ~97 ns. The memory controller doesn't know our access pattern, so it can't optimize for row locality.

That all being said, I hesitate to guess exactly without writing more benchmarks.

## Code

To run:
```bash
make
./run_benchmarks.sh 4096  # 4096 MB array
```
