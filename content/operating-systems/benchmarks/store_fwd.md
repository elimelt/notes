---
title: Store-to-Load Forwarding Benchmarks
category: Operating Systems
tags:
  - store-forwarding
  - store-buffer
  - memory-ordering
  - microarchitecture
  - performance
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Measures store-to-load forwarding on a modern x86 core, showing that an exactly matching load beats even an independent load, while a partially overlapping load stalls 7x.
sources:
  - title: The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)
    url: https://www.agner.org/optimize/microarchitecture.pdf
    type: docs
---

## Purpose

Measure what store-to-load forwarding is worth, and what it costs when it fails. When a load reads an address that was just written, the CPU can forward the value straight from the store buffer instead of waiting for the store to commit to cache. Forwarding only works when the load lines up with the store. A partial overlap forces a store forwarding stall, where the load waits for the store to reach L1 before it can read.

## Setup

The CPU model and compiler flags were not recorded with these results, so the note is marked needs-review. The cycle conversion below assumes a 3 GHz clock. The runs use the same `./bench` harness as the other notes in this directory.

## Workload

Three store-then-load patterns, run in a tight loop:

```c
// Aligned: store 8 bytes, load same 8 bytes (forwarding works)
*(uint64_t *)(bytes) = i;
sum += *(uint64_t *)(bytes);

// Overlap: store at offset 1, load at offset 0 (forwarding fails)
*(uint64_t *)(bytes + 1) = i;
sum += *(uint64_t *)(bytes);

// Independent: store and load different addresses (no dependency)
array[0] = i;
sum += array[64];
```

## Results

| Pattern | ns/op | vs forwarding |
|---------|-------|---------------|
| `sf_fwd` (aligned) | 0.52 ns | 1.0x |
| `sf_indep` (independent) | 0.70 ns | 1.3x |
| `sf_stall` (overlap) | 3.64 ns | 7.0x |

## Interpretation

The aligned case beats the independent case, 0.52 ns against 0.70 ns, even though the independent load has no dependency at all. Forwarded data comes straight out of the store buffer with no cache lookup, so a load that exactly matches a recent store gets its value faster than an L1 hit.

The overlapping case pays about 3.1 ns extra per operation, roughly 10 cycles at 3 GHz. The store buffer can't forward a value that only partially covers the load, so the CPU waits for the store to commit to L1 and then performs the load from cache. Agner Fog's [microarchitecture manual](https://www.agner.org/optimize/microarchitecture.pdf) documents the exact forwarding rules per CPU family. The common failure cases are a load smaller than the store that isn't aligned to the store's start, a load larger than the store, a load spanning multiple stores, and on some cores mismatched sizes at the same address.

The compiler won't save you from this. It has no model of forwarding stalls, so code like the following can be quietly slow:

```c
struct { char a; int64_t b; } __attribute__((packed)) s;
s.b = value;
use(s.b);  // May stall if 'a' was recently written
```

Packed structs and type-punned byte buffers are where this bites in practice, since they produce loads and stores of different sizes and offsets over the same bytes.

## Reproduction

```bash
./bench sf_fwd 64     # Aligned (forwarding)
./bench sf_stall 64   # Overlapping (stall)
./bench sf_indep 64   # Independent (no dependency)
```

## Sources

- [The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)](https://www.agner.org/optimize/microarchitecture.pdf)

## Related notes

- [[operating-systems/benchmarks/branch|branch prediction]]
- [[operating-systems/benchmarks/false_sharing|false sharing]]
