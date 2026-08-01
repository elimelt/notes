---
title: Out-of-Order and Superscalar Execution
category: Computer Architecture
tags:
  - out-of-order
  - superscalar
  - ilp
  - register-renaming
  - rob
  - issue-queue
  - load-store-queue
  - speculation
  - cpu
date: 2026-08-01
updated: 2026-08-01
status: draft
description: Tomasulo's algorithm, register renaming, the reorder buffer, and load/store queue disambiguation, grounded in BOOM's rename and ROB source and the existing MLP/reduction benchmarks that measure the payoff.
sources:
  - title: riscv-boom (riscv-boom/riscv-boom), commit 97bf536
    url: https://github.com/riscv-boom/riscv-boom/tree/97bf5363d814c460d4e8a3925bb5c08b9e0275e9
    type: source
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
---

## Purpose

A five-stage in-order pipeline (see [[hardware/computer-architecture/pipelining-hazards-branch-prediction|pipelining
and hazards]]) issues and completes instructions strictly in program order, so one stalled instruction
stalls everything behind it even if later instructions are entirely independent. Out-of-order execution
lets independent instructions execute as soon as their operands are ready, regardless of program order,
while still *committing* results in program order so the architectural state stays consistent and
exceptions stay precise. This note derives that machinery from Tomasulo's algorithm through to BOOM's
actual reorder buffer and rename stage, and connects it to the [[systems/operating-systems/benchmarks/mlp|MLP]]
and [[systems/operating-systems/benchmarks/reductions|reduction]] benchmarks that measure why independent
work helps.

## Tomasulo's algorithm, in stages

Tomasulo's original algorithm (IBM 360/91, 1967) solves out-of-order execution with distributed
reservation stations and result buses, predating explicit reorder buffers. The modern pipeline built
on it has six logical stages:

```text
Fetch -> Decode/Rename -> Dispatch -> Issue -> Execute -> Writeback -> Retire (in-order)
```

**Rename** replaces architectural register names with physical register tags, breaking false
dependencies. **Dispatch** allocates a reorder buffer (ROB) entry and an issue-queue (reservation
station) slot. **Issue** happens when an instruction's operands are ready and a functional unit is
free; this is wakeup/select: each cycle, completing instructions broadcast their destination tag,
waiting instructions in the issue queue wake up if they match, and a select policy picks which ready
instructions actually get a functional unit this cycle. **Execute** and **writeback** are
functional-unit-specific. **Retire** commits results to architectural state strictly in program order,
which is what makes it a ROB rather than just a scoreboard.

## Register renaming: false dependencies vs. true dependencies

A true (RAW) dependency is intrinsic to the computation: no renaming scheme can let `add x3, x1, x2`
execute before `x1` and `x2` are known. WAR and WAW dependencies are artifacts of a fixed, finite set
of architectural register names: they exist only because two unrelated computations happen to be
told to write the same name. Renaming maps each architectural destination register to a fresh physical
register from a free list, so two writes to architectural `x1` land in different physical registers
and never actually conflict; only a *read* of `x1` needs to know which physical register currently
holds its value, tracked by a rename map table (RAT).

BOOM's rename map table shows the mechanism directly: reading a rename entry maps architectural
register number to the currently valid physical register, updated on each committed or speculative
rename:

```scala
val map_table = RegInit(VecInit((0 until numLregs) map { i => i.U(pregSz.W) }))
when (io.brupdate.b2.mispredict) {
  // Restore the map table to a branch snapshot.
  map_table := br_snapshots(io.brupdate.b2.uop.br_tag)
} .elsewhen (io.rollback) {
  map_table := com_map_table
} .otherwise {
  map_table := remap_table(plWidth)
}
```

(from [BOOM `src/main/scala/v4/exu/rename/rename-maptable.scala`](https://github.com/riscv-boom/riscv-boom/blob/97bf5363d814c460d4e8a3925bb5c08b9e0275e9/src/main/scala/v4/exu/rename/rename-maptable.scala), commit `97bf536`)

The free-list side of renaming allocates a physical register for every instruction that writes a
result and reclaims one when the physical register it's replacing is no longer needed by any
in-flight or committed instruction (i.e., once the *next* writer of that same architectural register
commits). This reclamation point is exactly what caps how many renames can be in flight: the physical
register file must be large enough to hold both the committed architectural state and every
speculative in-flight write.

## Reorder buffer

The ROB is a circular buffer of in-flight instructions in program order, one entry per instruction from
dispatch until retirement. Each entry records enough to (a) commit the result to architectural state
when it's this instruction's turn, and (b) detect and report an exception at the correct point in
program order even though execution happened out of order. Retirement walks the ROB head in program
order, committing each entry once it's marked complete, and stops at the first incomplete or excepting
entry; this is what makes exceptions precise: the architectural state visible at any point corresponds
exactly to instructions that have retired, in order, with no visibility into speculative or in-flight
work beyond that point.

BOOM's ROB tracks per-entry busy/exception state and drives retirement off the ROB head:

```scala
val rob_val       = RegInit(VecInit(Seq.fill(numRobRows){false.B}))
val rob_bsy       = Reg(Vec(numRobRows, Bool()))
val rob_exception = Reg(Vec(numRobRows, Bool()))
// ...
can_commit(w) := rob_val(rob_head) && !(rob_bsy(rob_head)) && !io.csr_stall &&
  !io.brupdate.b2.mispredict && !io.trace_stall
```

(from [BOOM `src/main/scala/v4/exu/rob.scala`](https://github.com/riscv-boom/riscv-boom/blob/97bf5363d814c460d4e8a3925bb5c08b9e0275e9/src/main/scala/v4/exu/rob.scala), commit `97bf536`)

On a branch misprediction or exception, the ROB entries younger than the offending instruction are
squashed (their physical registers freed back to the freelist, their RAT entries rolled back to a
checkpoint), which is the out-of-order analog of flushing the pipeline registers in the in-order
design from [[hardware/computer-architecture/pipelining-hazards-branch-prediction|pipelining and
hazards]], except now there may be hundreds of in-flight instructions to unwind instead of two or
three.

## Load/store queue and memory disambiguation

Loads and stores cannot simply issue out of order like ALU ops, because a load might alias a store
that hasn't computed its address yet. The load/store queue (LSQ) tracks in-flight memory ops in
program order and resolves two questions per load: does an older, unresolved store's address possibly
overlap this load (if so, stall or speculate), and if an older store's address *is* known and matches,
forward that store's value directly instead of reading memory (store-to-load forwarding, matching the
mechanism in [[systems/operating-systems/benchmarks/store_fwd|the store-forwarding benchmark]]).
Speculative memory disambiguation, guessing a load doesn't alias any pending store and later
verifying, trades a rollback penalty on misspeculation for not stalling every load behind every
in-flight store.

This is the microarchitectural version of the ordering concerns Drepper's memory paper raises about
concurrent access: [What Every Programmer Should Know About Memory](https://www.akkadia.org/drepper/cpumemory.pdf)
discusses out-of-order stores and loads needing careful ordering guarantees for correctness on
multiprocessors, which is exactly what the LSQ enforces locally within one core before any cross-core
coherence protocol gets involved.

## Wakeup/select and issue width

Every cycle, the issue queue broadcasts the tags of instructions that just finished execution;
waiting entries compare their source-operand tags against the broadcast and mark themselves ready
(wakeup). Among all ready entries, a select policy, often oldest-first for fairness and to avoid
starving instructions stuck behind a long-latency operation, picks up to (issue width) instructions
per cycle, limited by the number of functional units and read ports available. Widening issue width
increases the peak ILP the core can exploit but scales the wakeup/select logic worse than linearly
(broadcast compares grow with the product of issue-queue size and issue width), which is a large part
of why very wide superscalar designs are hard to clock as fast as narrower ones.

## Comparing in-order, scoreboard, and out-of-order on real workloads

The existing benchmarks in this repository measure exactly the mechanisms above, on real out-of-order
hardware, without needing a simulator:

- [[systems/operating-systems/benchmarks/reductions|Parallel reductions]]: a single-accumulator
  reduction has a serial RAW dependency chain on the accumulator; breaking it into 8 independent
  accumulators only buys 1.3x at large array sizes because the bottleneck shifts to memory bandwidth,
  not the ALU/issue width, a case where the out-of-order engine already has enough ILP exposed by the
  compiler's auto-vectorization, and adding more independent work has nothing left to overlap against.
- [[systems/operating-systems/benchmarks/mlp|Memory-level parallelism]]: independent pointer chains
  scale from 92.6 ns/access (1 chain) to 8.9 ns/access (16 chains), a 10.4x speedup, because the LSQ
  and MSHRs can hold roughly 10-12 independent outstanding misses at once; this ceiling *is* a
  measurement of the load queue's effective depth on that core, not a property of DRAM.
- [[systems/operating-systems/benchmarks/store_fwd|Store-to-load forwarding]]: an aligned load that
  exactly matches a recent store (0.52 ns) beats even an independent, non-conflicting load (0.70 ns),
  because a forwarding hit skips the cache lookup entirely, direct evidence the LSQ's forwarding path
  is a distinct, faster path than the normal load pipeline this note derives above.

A simple scoreboard (single in-order issue, but allowing out-of-order completion with WAR/WAW hazard
tracking, as in the CDC 6600) sits between these: it can let a long-latency instruction fall behind
without stalling everything, but it still issues in program order, so it cannot start a later
independent instruction ahead of an earlier one still waiting on an operand the way full out-of-order
issue can. The MLP benchmark's near-linear scaling up to 8 chains would not appear with only a
scoreboard's in-order issue, because only one load can be waiting to issue at a time.

## Precise exceptions and recovery as architectural obligations

Precise exceptions are not just an implementation nicety: the ISA guarantees that after a trap, all
instructions before the faulting one have fully committed and none after it have any visible effect,
so a handler can inspect and resume architectural state unambiguously. Out-of-order execution makes
this hard to deliver for free, because by the time an exception is detected, later instructions may
have already executed (out of order) and written speculative results. The ROB is precisely the
structure that makes precise exceptions affordable: exceptions are recorded per-entry at execution
time but only *acted on* at retirement, in program order, so speculative execution past an exception
point is simply discarded rather than ever becoming visible. The same recovery path handles branch
mispredictions, interrupts, and memory-ordering fences (which stall retirement, not issue, until
prior memory ops are globally visible).

## Edge cases or limits

Register renaming is bounded by the physical register file size; running out of free physical
registers stalls rename (and therefore dispatch) even though the issue queue and ROB might have room,
which is a common bottleneck in workloads with many live values. Speculative memory disambiguation
that mispredicts costs a pipeline-flush-like recovery, similar in kind to (but usually narrower in
scope than) a branch misprediction. ROB size caps how far ahead of a stalled instruction the core can
look for independent work; a long-latency miss (e.g., an L3/DRAM load) can fill the ROB and stall
dispatch even with abundant ILP further down the instruction stream, which is exactly the situation
[[systems/operating-systems/benchmarks/mlp|the MLP benchmark]]'s multi-chain results are implicitly
bounded by.

## Sources

- [riscv-boom source, commit 97bf536](https://github.com/riscv-boom/riscv-boom/tree/97bf5363d814c460d4e8a3925bb5c08b9e0275e9)
- [What Every Programmer Should Know About Memory (Ulrich Drepper)](https://www.akkadia.org/drepper/cpumemory.pdf)
- [[systems/operating-systems/benchmarks/mlp|Memory-level parallelism benchmarks]]
- [[systems/operating-systems/benchmarks/reductions|Parallel reductions benchmarks]]
- [[systems/operating-systems/benchmarks/store_fwd|Store-to-load forwarding benchmarks]]

## Related notes

- [[hardware/computer-architecture/index|A working map of computer architecture]]
- [[hardware/computer-architecture/pipelining-hazards-branch-prediction|Pipelining, hazards, and branch prediction]]
- [[hardware/computer-architecture/isa-datapath-control|Instruction sets, datapaths, and control]]
- [[systems/operating-systems/benchmarks/mlp|Memory-level parallelism benchmarks]]
- [[systems/operating-systems/benchmarks/reductions|Parallel reductions benchmarks]]
