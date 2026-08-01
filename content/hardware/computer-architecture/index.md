---
title: A Working Map of Computer Architecture
category: Computer Architecture
tags:
  - computer-architecture
  - microarchitecture
  - isa
  - rtl
  - benchmarking
date: 2026-08-01
updated: 2026-08-01
status: draft
description: A navigable map of the computer architecture notes, organized as a graph of questions and experiments rather than a linear course sequence, spanning ISA/datapath, pipelining, and out-of-order execution.
sources:
  - title: The RISC-V Instruction Set Manual, Volume I - Unprivileged ISA
    url: https://riscv.github.io/riscv-isa-manual/snapshot/spec/
    type: docs
  - title: CVA6 (openhwgroup/cva6)
    url: https://github.com/openhwgroup/cva6
    type: source
  - title: riscv-boom (riscv-boom/riscv-boom)
    url: https://github.com/riscv-boom/riscv-boom
    type: source
---

## Purpose

This is the narrative spine for a university-level Computer Architecture I/II treatment, organized as
a graph of questions and experiments rather than a folder hierarchy to walk top to bottom. Each linked
note is a self-contained island: a derivation, a real-source reading, or a measured benchmark. Enter
through whichever view matches what you already have in hand: a performance symptom, an RTL question,
or an ISA detail.

The transformation this whole area studies: a program is written against an ISA (an abstract contract
of registers, memory, and instructions), the ISA is implemented by a microarchitecture (pipelines,
caches, predictors, out-of-order machinery), the microarchitecture is described in RTL (SystemVerilog,
Chisel), and RTL becomes gates through synthesis. Measurement runs the other direction: benchmarks and
hardware counters on real silicon are the ground truth that the architectural model has to explain.

## Entry points

- **Have a performance symptom** (a benchmark is slower than expected): start at
  [[systems/operating-systems/benchmarks/branch|branch misprediction]],
  [[systems/operating-systems/benchmarks/mlp|memory-level parallelism]], or
  [[systems/operating-systems/benchmarks/store_fwd|store-to-load forwarding]], then follow the "why"
  link into [[hardware/computer-architecture/pipelining-hazards-branch-prediction|pipelining]] or
  [[hardware/computer-architecture/out-of-order-execution|out-of-order execution]].
- **Have an ISA question** (what does this instruction encode, how does a load actually execute):
  start at [[hardware/computer-architecture/isa-datapath-control|ISA, datapath, and control]].
- **Have an RTL module in front of you** (a decoder, a BTB, a reorder buffer): the same three notes
  below pin real source snippets to commits from [CVA6](https://github.com/openhwgroup/cva6),
  [Rocket Chip](https://github.com/chipsalliance/rocket-chip), and [BOOM](https://github.com/riscv-boom/riscv-boom),
  so you can jump from mechanism to implementation directly.
- **Have a multicore anomaly**: not yet covered in this map; the load/store queue and memory
  disambiguation discussion in [[hardware/computer-architecture/out-of-order-execution|out-of-order
  execution]] is the single-core prerequisite for coherence and consistency questions.

## The three narrative branches

| Note | Type | What it answers |
|---|---|---|
| [[hardware/computer-architecture/isa-datapath-control\|ISA, datapath, and control]] | Narrative + source reading | How does RV32I encoding become a working single-cycle/multicycle processor? |
| [[hardware/computer-architecture/pipelining-hazards-branch-prediction\|Pipelining, hazards, and branch prediction]] | Narrative + source reading + benchmark | Why does overlapping instructions require forwarding, stalls, and speculation, and what does a misprediction actually cost? |
| [[hardware/computer-architecture/out-of-order-execution\|Out-of-order and superscalar execution]] | Narrative + source reading + benchmark | How do real cores extract ILP beyond in-order issue, and why do the MLP/reduction benchmarks look the way they do? |

Each is a narrative first: it derives the mechanism from first principles, the way a course would. Each
then grounds the mechanism in real RTL (a specific file, pinned to a commit SHA) and, where a
mechanism is directly measurable, in an existing benchmark note rather than a claim asserted without
evidence.

## Coverage matrix

Mapping this graph onto typical Computer Architecture I/II course outcomes:

| Course outcome | Covered by | Evidence type |
|---|---|---|
| Instruction encoding and decoding | [[hardware/computer-architecture/isa-datapath-control\|ISA note]] | Derivation + CVA6 decoder source |
| Single-cycle / multicycle datapath design | [[hardware/computer-architecture/isa-datapath-control\|ISA note]] | Derivation + CVA6 register file source |
| CPI and clock period tradeoffs | [[hardware/computer-architecture/isa-datapath-control\|ISA note]], [[hardware/computer-architecture/pipelining-hazards-branch-prediction\|pipelining note]] | Derivation + worked CPI models |
| Pipeline hazards (structural, data, control) | [[hardware/computer-architecture/pipelining-hazards-branch-prediction\|pipelining note]] | Derivation |
| Forwarding and stall logic | [[hardware/computer-architecture/pipelining-hazards-branch-prediction\|pipelining note]] | Derivation |
| Branch prediction (BTB, RAS) | [[hardware/computer-architecture/pipelining-hazards-branch-prediction\|pipelining note]] | CVA6 BTB/RAS source + Agner Fog's measured penalties across microarchitectures |
| Branch misprediction cost, measured | [[systems/operating-systems/benchmarks/branch\|branch benchmark]] | Real-hardware measurement (~11 cycles/misprediction) |
| Tomasulo's algorithm, register renaming | [[hardware/computer-architecture/out-of-order-execution\|OoO note]] | Derivation + BOOM rename-maptable source |
| Reorder buffer, precise exceptions | [[hardware/computer-architecture/out-of-order-execution\|OoO note]] | Derivation + BOOM ROB source |
| Load/store queue, memory disambiguation | [[hardware/computer-architecture/out-of-order-execution\|OoO note]] | Derivation + Drepper's ordering discussion |
| ILP extraction, measured | [[systems/operating-systems/benchmarks/mlp\|MLP benchmark]], [[systems/operating-systems/benchmarks/reductions\|reductions benchmark]] | Real-hardware measurement |
| Store-to-load forwarding | [[systems/operating-systems/benchmarks/store_fwd\|store-forwarding benchmark]] | Real-hardware measurement |

Coherence, interconnects, vector/accelerator ISAs, and an RTL implementation lab (a working RV32I core
with a testbench) are natural next branches but are not yet written; this table only claims what
exists today.

## What's measured vs. simulated vs. inferred from source vs. conceptual

- **Measured on real hardware**: the [[systems/operating-systems/benchmarks/branch|branch]],
  [[systems/operating-systems/benchmarks/mlp|MLP]], and [[systems/operating-systems/benchmarks/store_fwd|store-forwarding]]
  benchmarks. These are ground truth for one specific (unrecorded, hence `needs-review`) CPU, not a
  general claim about all out-of-order cores.
- **Inferred from source, not simulated or measured**: every RTL snippet pinned to a commit SHA (CVA6
  decoder/ALU/BTB/RAS, BOOM rename/ROB). These show *what a real implementation does*, not how fast it
  is; timing and area claims about them would need synthesis or simulation this map does not yet have.
- **Purely conceptual / derived**: the CPI models, the hazard taxonomy, and Tomasulo's algorithm as
  presented are textbook derivations, cross-checked against source and measurement where a link exists
  but not independently re-derived from a simulator run.
- **Not yet present in this map**: gem5/ChampSim simulation results, a from-scratch RV32I RTL build
  with its own testbench, and ISA extensions beyond RV32I (M/F/D/V, privileged spec).

## Sources

- [The RISC-V Instruction Set Manual, Volume I](https://riscv.github.io/riscv-isa-manual/snapshot/spec/)
- [CVA6 source](https://github.com/openhwgroup/cva6)
- [riscv-boom source](https://github.com/riscv-boom/riscv-boom)

## Related notes

- [[hardware/computer-architecture/isa-datapath-control|Instruction sets, datapaths, and control]]
- [[hardware/computer-architecture/pipelining-hazards-branch-prediction|Pipelining, hazards, and branch prediction]]
- [[hardware/computer-architecture/out-of-order-execution|Out-of-order and superscalar execution]]
- [[hardware/index|Hardware]]
- [[systems/operating-systems/benchmarks/README|Operating systems benchmarks]]
