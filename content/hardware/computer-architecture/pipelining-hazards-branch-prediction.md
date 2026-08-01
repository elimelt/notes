---
title: Pipelining, Hazards, and Branch Prediction
category: Computer Architecture
tags:
  - pipelining
  - hazards
  - forwarding
  - branch-prediction
  - speculation
  - btb
  - cpu
date: 2026-08-01
updated: 2026-08-01
status: draft
description: A five-stage RV32I pipeline, the RAW/WAR/WAW/structural/control hazard taxonomy, forwarding and stall logic, and BTB/RAS-based branch prediction grounded in CVA6's frontend and a measured misprediction penalty.
sources:
  - title: The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)
    url: https://www.agner.org/optimize/microarchitecture.pdf
    type: docs
  - title: CVA6 (openhwgroup/cva6), commit e4184b6
    url: https://github.com/openhwgroup/cva6/tree/e4184b665b7c777224688e8973167c8c5842762a
    type: source
---

## Purpose

A sequential datapath becomes a pipeline by overlapping instructions across stages instead of
finishing each one before the next starts. That overlap is free performance only until two
instructions in flight at once touch the same resource or depend on each other; then correctness and
throughput become the same problem. This note derives the hazard taxonomy for a five-stage RV32I
pipeline, the forwarding and stall logic that resolves data hazards, and the branch prediction
machinery (BTB, RAS) that turns control hazards from a full-pipeline stall into a low-probability
misprediction cost. It continues from [[hardware/computer-architecture/isa-datapath-control|ISA,
datapath, and control]] and precedes [[hardware/computer-architecture/out-of-order-execution|out-of-order
execution]], where renaming removes most of the hazards derived here.

## Five-stage RV32I pipeline

Split the multicycle datapath's stages (IF, ID, EX, MEM, WB) into pipeline stages, each with its own
pipeline register holding the instruction's state as it moves forward:

```text
IF  ->  ID  ->  EX  ->  MEM  ->  WB
[IF/ID] [ID/EX] [EX/MEM] [MEM/WB]
```

At steady state, five instructions are in flight simultaneously, one per stage, and one instruction
completes (or would complete, absent hazards) every cycle: CPI approaches 1 instead of the
multicycle design's 4-5. Each pipeline register carries forward everything later stages need: the
instruction's opcode/control signals, register values, computed addresses, and a valid bit so a
bubble (inserted due to a stall or flush) doesn't accidentally act like a real instruction. The clock
period is bounded by the slowest single stage rather than the slowest whole instruction, same as the
multicycle design, but now every stage's hardware is active on every cycle instead of idle 4/5 of the
time.

## Hazard taxonomy

**Structural hazards**: two instructions in different stages need the same hardware in the same
cycle. A single shared memory port for both instruction fetch and data access is the classic case;
splitting instruction and data memories (I$/D$) removes it. The register file is read (ID) and written
(WB) by different instructions in the same cycle; this resolves cheaply because register file reads
and writes are usually built to not conflict (write-first or read-old-value-before-write semantics in
the same cycle), rather than by stalling.

**Data hazards**: three orderings matter, of which only one appears in a simple in-order pipeline.

| Hazard | Meaning | Appears in-order? |
|---|---|---|
| RAW (read-after-write) | Consumer reads a value the producer hasn't written yet | Yes, the only one that occurs |
| WAR (write-after-read) | A later instruction writes before an earlier one reads | No; in-order issue means reads always precede later writes |
| WAW (write-after-write) | Two instructions write the same register out of order | No; in-order issue writes in program order |

RAW is the only structural concern in-order because instructions issue and retire in program order; WAR
and WAW require some instruction to *finish* before an earlier one, which cannot happen without
reordering. This is precisely what changes once [[hardware/computer-architecture/out-of-order-execution|out-of-order
execution]] lets instructions complete out of program order: WAR and WAW reappear and have to be
solved by register renaming instead of forwarding/stalling.

**Control hazards**: the fetch stage needs to know the next PC before it knows whether the current
instruction is a taken branch. Every cycle spent not knowing is either a stall (wait until the branch
resolves) or a guess (fetch speculatively and flush if wrong).

## Forwarding and stalls

A RAW hazard on an ALU-only dependency chain (`add x1, x2, x3` followed immediately by `sub x4, x1,
x5`) does not need a stall if the producer's result is available before the consumer's normal register
read would happen. Forwarding paths route the EX/MEM and MEM/WB pipeline register values back into the
EX stage's ALU inputs, bypassing the register file entirely for back-to-back dependent instructions.
Forwarding control compares the destination register of instructions ahead in the pipeline against the
source registers of the instruction currently in EX, selecting the freshest matching value (EX/MEM
over MEM/WB, since EX/MEM is one cycle newer).

The one RAW case forwarding cannot fix is the **load-use hazard**: a load's result isn't available
until the end of MEM, one stage later than an ALU result at the end of EX. If the very next instruction
needs that loaded value, forwarding has nothing to forward yet, so the pipeline must insert one bubble
(stall for 1 cycle) so the load reaches MEM before the dependent instruction reaches EX. Hazard
detection compares the load's destination register (in ID/EX) against the source registers of the
instruction behind it (in IF/ID); on a match, it freezes the PC and IF/ID register for one cycle and
injects a bubble into ID/EX.

```text
lw   x1, 0(x2)     IF ID EX MEM WB
add  x3, x1, x4       IF ID -- EX MEM WB   <- one stall cycle (ID repeated) before EX can use x1
```

## Control hazards, speculation, and the BTB

Stalling on every branch until it resolves in EX (or later) costs one bubble per branch, which is
expensive when 1 in 5 instructions is a branch. The alternative is to predict the next fetch address
and flush on misprediction. A **branch target buffer (BTB)** caches, indexed by PC, the target address
the branch went to last time; if this fetch's PC hits in the BTB, the frontend speculatively fetches
from the cached target instead of `PC+4`. A **direction predictor** (not always present alongside a
BTB in small cores) separately predicts taken/not-taken so a BTB hit doesn't automatically mean
"speculate the branch is taken."

CVA6's BTB is exactly this cache, indexed by a slice of the virtual PC, storing a valid bit and target
address, updated only when a branch resolves and turns out to have been taken:

```systemverilog
assign index = vpc_i[PREDICTION_BITS-1:ROW_ADDR_BITS+OFFSET];
if (btb_update_i.valid && !debug_mode_i) begin
  btb_d[update_pc][update_row_index].valid = 1'b1;
  btb_d[update_pc][update_row_index].target_address = btb_update_i.target_address;
end
```

(from [CVA6 `core/frontend/btb.sv`](https://github.com/openhwgroup/cva6/blob/e4184b665b7c777224688e8973167c8c5842762a/core/frontend/btb.sv), commit `e4184b6`)

Indexing by a PC slice rather than the full PC means two branches at different addresses can alias to
the same BTB entry (the ANTIALIAS_BITS parameter in the same file exists specifically to push this
probability down). This is a direct hardware instance of the aliasing tradeoff every direct-mapped
cache-like structure makes: more entries or wider tags reduce aliasing at an area cost.

## Return address stack

Indirect returns (`ret`, i.e. `jalr x0, 0(ra)`) are a special case: the target is whatever address was
most recently pushed by the matching call, so a BTB (which only remembers the *last* target for a
given PC) mispredicts any function called from more than one call site. A **return address stack
(RAS)** is a small hardware stack: pushed on `call`, popped on `return`, giving the correct target as
long as calls and returns nest properly.

```systemverilog
if (push_i) begin
  stack_d[0].ra = data_i;
  stack_d[0].valid = 1'b1;
  stack_d[DEPTH-1:1] = stack_q[DEPTH-2:0];
end
if (pop_i) begin
  stack_d[DEPTH-2:0] = stack_q[DEPTH-1:1];
end
```

(from [CVA6 `core/frontend/ras.sv`](https://github.com/openhwgroup/cva6/blob/e4184b665b7c777224688e8973167c8c5842762a/core/frontend/ras.sv), commit `e4184b6`)

A RAS depth of only a handful of entries covers the common case; recursion deeper than the stack, or
longjmp-style non-local control flow, overflows it and falls back to whatever the BTB alone predicts.

## Misprediction recovery

On a misprediction (branch resolves in EX with a different direction or target than fetch guessed),
every instruction fetched after the branch, sitting in IF, ID, and possibly EX, is wrong and must be
squashed: their valid bits are cleared (turned into bubbles) as the correct-path fetch restarts from
the resolved target. The number of cycles wasted equals roughly the distance in the pipeline between
fetch and the stage that resolves the branch: a 5-stage pipeline that resolves branches in EX loses 2
bubbles (the two instructions fetched into IF and ID on the wrong path).

Agner Fog's [microarchitecture manual](https://www.agner.org/optimize/microarchitecture.pdf) documents
this scaling across two decades of x86 cores: the Pentium Pro/II/III "usually costs between 10 and 20
clock cycles" due to a long pipeline, the Pentium 4's inability to cancel bogus µops before retirement
pushed recovery to "rarely less than 24 clock cycles, and typically around 45 µops," and Sandy Bridge
measured "15 clock cycles or more," attributed partly to caching decoded µops so cached branches skip
the full front-end redecode on the recovery path. The pattern is consistent: misprediction penalty
tracks pipeline depth from fetch to branch resolution, and processors that resolve branches earlier
(or speculate less aggressively) pay less per miss.

The [[systems/operating-systems/benchmarks/branch|branch prediction benchmark]] measures this
end-to-end on real hardware rather than reading it off a manual: feeding a conditional sum a sorted
array (predictable) versus a random array (unpredictable) isolates the misprediction cost as the
difference in throughput, landing at roughly 11 cycles per misprediction at 3 GHz on that machine,
consistent with modern out-of-order cores, which can overlap part of the recovery with independent
work, something a simple 5-stage in-order pipeline like the one in this note cannot do at all.

## Worked example: CPI with hazards

For instruction mix with fraction $f_{lu}$ load-use dependent pairs (1-cycle stall each) and fraction
$f_{br}$ branches with misprediction rate $p$ and $k$-cycle recovery penalty:

$$\text{CPI} = 1 + f_{lu} \cdot 1 + f_{br} \cdot p \cdot k$$

With $f_{lu} = 0.10$, $f_{br} = 0.20$, $p = 0.10$ (a mediocre predictor), $k = 2$ (5-stage, resolve in
EX): CPI $= 1 + 0.10 + 0.20 \times 0.10 \times 2 = 1.14$. Doubling the misprediction penalty to $k=4$
(a deeper pipeline resolving branches later) raises CPI to $1.18$ for the same predictor accuracy.
That is the reason deeper pipelines invest more heavily in prediction accuracy: the penalty per miss scales
with depth, so acceptable overall CPI demands the miss rate fall proportionally.

## Edge cases or limits

Forwarding and stall logic as described here assumes a single in-order issue pipeline; adding a second
issue port (superscalar, in-order) reintroduces structural hazards between the two lanes (two branches
per cycle, register file port contention) that this note's single-issue model sidesteps. Aliasing in
the BTB (two live branches mapping to the same index) causes destructive interference that looks like
misprediction but is really an eviction; deeper caches (2-way BTBs, or the aliasing bits CVA6 reserves)
trade area for lower alias rates rather than eliminating them. A RAS overflowed by deep recursion
degrades to whatever the BTB alone predicts for the return address, typically wrong until the RAS is
back in range.

## Sources

- [The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)](https://www.agner.org/optimize/microarchitecture.pdf)
- [CVA6 source, commit e4184b6](https://github.com/openhwgroup/cva6/tree/e4184b665b7c777224688e8973167c8c5842762a)
- [[systems/operating-systems/benchmarks/branch|Branch prediction benchmark]]

## Related notes

- [[hardware/computer-architecture/index|A working map of computer architecture]]
- [[hardware/computer-architecture/isa-datapath-control|Instruction sets, datapaths, and control]]
- [[hardware/computer-architecture/out-of-order-execution|Out-of-order and superscalar execution]]
- [[systems/operating-systems/benchmarks/branch|Branch prediction benchmarks]]
- [[systems/operating-systems/benchmarks/store_fwd|Store-to-load forwarding benchmarks]]
