---
title: Multiprocessors, Cache Coherence, and Memory Consistency
aliases:
  - hardware/computer-architecture/multiprocessors-cache-coherence
category: Computer Architecture
tags:
  - multiprocessor
  - cache-coherence
  - memory-consistency
  - mesi
  - atomics
  - fences
  - litmus-tests
  - false-sharing
  - synchronization
date: 2026-08-01
status: draft
description: Coherence and consistency kept as separate axes - a MESI directory protocol traced through gem5's Ruby SLICC source, RVWMO preserved program order and two litmus tests, and the false-sharing benchmark's ping-pong explained state by state.
sources:
  - title: RVWMO Memory Consistency Model (RISC-V unprivileged ISA manual)
    url: https://github.com/riscv/riscv-isa-manual/blob/main/src/unpriv/rvwmo.adoc
    type: spec
  - title: "gem5: MESI_Two_Level-L1cache.sm"
    url: https://github.com/gem5/gem5/blob/stable/src/mem/ruby/protocol/MESI_Two_Level-L1cache.sm
    type: source
  - title: "rocket-chip: tilelink/Arbiter.scala"
    url: https://github.com/chipsalliance/rocket-chip/blob/master/src/main/scala/tilelink/Arbiter.scala
    type: source
---

## Purpose

**Coherence** and **consistency** answer different questions, and conflating them is the single most common confusion in this area. Coherence asks: for a *single memory location*, do all cores eventually agree on the order of writes to it? Consistency asks: across *multiple locations*, what orderings can a program observe at all? A machine can have perfect coherence and still let two cores disagree about the order two different variables were written. This note derives a directory-based MESI protocol against real gem5 SLICC source, then RVWMO's ordering rules against two litmus tests, and ties both to the [[systems/operating-systems/benchmarks/false_sharing|false-sharing benchmark]] already measured in this repo.

## Coherence: single-location agreement

A coherent system guarantees, for every memory location: (1) a core's own reads and writes to that location appear in program order to itself, (2) if core A writes and core B later reads (with enough time between them), B sees A's value, and (3) writes to the same location are seen in the same order by every core (**write serialization**). Nothing here says anything about *different* locations — that's consistency's job, covered below.

### Directory MESI, traced through gem5

**MESI** gives each cached line one of four states: **M**odified (dirty, sole owner, may write silently), **E**xclusive (clean, sole owner, may write without asking anyone), **S**hared (clean, possibly cached elsewhere, must ask before writing), **I**nvalid (not present). A **directory** protocol tracks, per line, which cores currently hold a copy and in what state, so a writer only has to message the directory and the directory forwards invalidations to the actual sharers — no core has to broadcast to every other core (that's *snooping*, the alternative that doesn't scale past a shared bus).

gem5's `MESI_Two_Level-L1cache.sm` SLICC source names states exactly this way, plus the transient states a real implementation needs while a request is in flight:

<augment_code_snippet path="gem5: src/mem/ruby/protocol/MESI_Two_Level-L1cache.sm" mode="EXCERPT">
````text
state_declaration(State, desc="Cache states", default="L1Cache_State_I") {
  NP, AccessPermission:Invalid, desc="Not present in either cache";
  I, AccessPermission:Invalid, desc="a L1 cache entry Idle";
  S, AccessPermission:Read_Only, desc="a L1 cache entry Shared";
  E, AccessPermission:Read_Only, desc="a L1 cache entry Exclusive";
  M, AccessPermission:Read_Write, desc="a L1 cache entry Modified";
  IS, AccessPermission:Busy, desc="L1 idle, issued GETS, have not seen response yet";
  IM, AccessPermission:Busy, desc="L1 idle, issued GETX, have not seen response yet";
````
</augment_code_snippet>

The transient states (`IS`, `IM`, `M_I`, ...) exist because a real protocol is not instantaneous: between issuing a `GETX` (get-exclusive) request and receiving data, the line is neither fully invalid nor fully modified, and the state machine has to define what happens if a forwarded request from another core (`Fwd_GETX`, `Fwd_GETS`) arrives during that window. This is the **invalidation race**: two cores can want the same line at once, and the directory has to serialize their requests into some order, whichever wins first blocking the other until it retries. Looking at the actual transitions:

<augment_code_snippet path="gem5: src/mem/ruby/protocol/MESI_Two_Level-L1cache.sm" mode="EXCERPT">
````text
transition(E, Fwd_GETX, I) {
  forward_eviction_to_cpu;
  d_sendDataToRequestor;
  l_popRequestQueue;
}
transition(E, {Fwd_GETS, Fwd_GET_INSTR}, S) {
  d_sendDataToRequestor;
  d2_sendDataToL2;
  l_popRequestQueue;
}
````
</augment_code_snippet>

A core holding a line **E**xclusive downgrades to **I** if another core wants to write it (`Fwd_GETX`), the requester takes full ownership and the old holder loses its copy entirely, but only downgrades to **S** on a read request (`Fwd_GETS`), keeping a shared clean copy while also forwarding data to both the requester and the L2 (`d2_sendDataToL2`), since L2 needs an up-to-date copy once no core holds exclusive/modified state. **Silent eviction** is visible too: `E` can be silently dropped without notifying anyone because the copy was clean and no one else has claimed it, whereas `M` (dirty) must write back before eviction (`g_issuePUTX`, sending data to L2), the entire reason write-back caches need eviction protocols and write-through caches don't.

### Snooping vs. directory

**Snooping**: every cache watches every request on a shared bus and reacts (invalidate, supply data) without a directory. It needs no extra storage but doesn't scale, since the bus itself becomes the bottleneck as core count grows — every request is seen by every cache whether or not it cares.

**Directory**: a directory entry per line tracks exact sharers, so messages go point-to-point instead of broadcast. The cost is directory storage (bits per line per potential sharer, or a sharer list) and one more hop of indirection (core → directory → sharers, instead of core → bus). This is why directory protocols dominate past a handful of cores and snooping survives only in small-bus SMPs.

## Consistency: cross-location ordering, via RVWMO

RVWMO defines a total **global memory order** over every hart's loads and stores, constrained by **preserved program order (PPO)**: same-hart operation $a$ must precede $b$ in the global order if $a$ precedes $b$ in program order *and* one of several conditions holds — overlapping addresses, an explicit fence, an acquire/release annotation, or a syntactic dependency (address, data, or control) from $a$ to $b$. Crucially, PPO does **not** require ordering between a store and a *later*, non-dependent load to a different address — that gap is what store buffers exploit, and it's exactly what a fence closes.

### Litmus test: store buffering (SB)

Two harts, `x` and `y` both start at 0:

```text
Hart 0:              Hart 1:
sw x0, 0(x_addr)     sw x0, 0(y_addr)   # store 1 to y
lw a0, 0(y_addr)     lw a1, 0(x_addr)   # load x into a1
```

Under RVWMO, `a0 = 0, a1 = 0` is a **legal** outcome, because neither hart's store-then-load pair has any address, data, or control dependency between them, and there is no fence. Each hart's own store can sit in a per-hart store buffer, invisible to the other hart, while its load to the *other* variable proceeds and returns the old value — this is precisely the store-buffer-forwarding behavior in [[systems/operating-systems/benchmarks/store_fwd|the store-forwarding benchmark]], generalized across cores instead of within one core's pipeline. Inserting a `fence rw, rw` (or `fence.tso`) between each hart's store and load forbids this outcome, because rule 4 of PPO (an explicit fence orders $a$ before $b$) then puts the store ahead of the load in the global order on both harts, which is inconsistent with both loads returning 0.

### Litmus test: message passing (MP)

```text
Hart 0:                    Hart 1:
sw a1, 0(data_addr)        lw a0, 0(flag_addr)   # spin until a0 == 1
fence w, w                 fence r, r
sw x1, 0(flag_addr)        lw a1, 0(data_addr)
```

Here the fences make it **illegal** for hart 1 to observe `flag == 1` but `data == 0`. `fence w, w` on hart 0 orders the write to `data` before the write to `flag` in PPO (rule 4); `fence r, r` on hart 1 orders the read of `flag` before the read of `data`. Combined with the load value axiom (a load returns the value of the store latest in global order among stores preceding it in that order or in program order), once hart 1 observes `flag == 1` it has observed a point in global order after hart 0's fenced store to `flag`, which itself is after the fenced store to `data` — so the read of `data` cannot return the stale value. Without the fences, RVWMO permits `flag == 1, data == 0`: this is the same reordering hazard that makes lock-free publish/subscribe code without explicit barriers unsafe on any weakly-ordered ISA, RISC-V included.

## False sharing: coherence traffic without any real conflict

[[systems/operating-systems/benchmarks/false_sharing|The false-sharing benchmark]] packs 8 threads' independent counters into a single 64-byte cache line and measures an 8.5x slowdown (57.8 ms vs 6.8 ms padded) purely from coherence traffic. Reading it against the MESI transitions above: `counters[0]++` requires the line in **M** state on core 0 (a store needs write permission, i.e., MESI's read-modify-write access check `onAccess`). When core 1 then writes `counters[1]` — a different byte, same line — the directory sees a `GETX` and must invalidate core 0's **M** copy (the `M, Fwd_GETX -> I` transition, which also flushes the dirty data to whoever's tracking it). Core 0's next increment misses entirely and re-fetches, taking the line back to **M** and forcing core 1's next increment to fault the same way. Coherence is doing exactly what it's supposed to — no two cores are seeing stale data, write serialization holds — but the *granularity* of the protocol (whole 64-byte lines, not individual bytes) turns logically independent writes into a physical ownership fight. Padding each counter to its own line removes the ownership contention entirely: each core's `M` state is never contested since no other core's writes ever land in that line. `perf c2c` detects this directly by sampling cache-to-cache transfers, which is why the benchmark note recommends it for finding false sharing in the wild.

## Edge cases and limits

- **Coherence says nothing about atomicity across two locations.** A protocol can be perfectly coherent per-line and still let a thread observe half of a two-word update — that needs a consistency-model or lock-based guarantee, not a coherence one.
- **RCpc vs RCsc acquire/release annotations change which litmus outcomes are legal.** RVWMO's PPO rules 5-7 treat acquire and release annotations as directional fences (acquire orders itself before *later* ops, release orders *earlier* ops before itself) rather than full fences, which is weaker than `fence rw, rw` and cheaper on hardware that supports it natively.
- **Directory size is a real resource, not free metadata.** A directory tracking full sharer bit-vectors costs $O(\text{cores})$ bits per line; coarser encodings (limited pointers, coarse vectors) trade precision for storage and can force spurious invalidations when the encoding can't represent the exact sharer set.

## Sources

- [RVWMO Memory Consistency Model](https://github.com/riscv/riscv-isa-manual/blob/main/src/unpriv/rvwmo.adoc)
- [gem5: MESI_Two_Level-L1cache.sm](https://github.com/gem5/gem5/blob/stable/src/mem/ruby/protocol/MESI_Two_Level-L1cache.sm)

## Related notes

- [[systems/operating-systems/benchmarks/false_sharing|false sharing benchmarks]]
- [[systems/operating-systems/benchmarks/store_fwd|store-to-load forwarding benchmarks]]
- [[systems/distributed-systems/consistency|distributed systems consistency models]]
- [[systems/distributed-systems/distributed-cache-coherence|distributed cache coherence]]
- [[hardware/computer-architecture/caches-virtual-memory|caches, virtual memory, and memory systems]]
- [[hardware/computer-architecture/interconnects-noc-dma|interconnects, NoCs, DMA, and memory controllers]]
