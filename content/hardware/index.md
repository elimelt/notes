---
title: Hardware
category: Hardware
tags:
  - hardware
  - digital design
  - timing
  - signals
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Map of the hardware notes, split between digital design material and signal-conditioning lecture notes.
sources:
  - title: The RISC-V Instruction Set Manual
    url: https://riscv.github.io/riscv-isa-manual/snapshot/spec/
    type: spec
---

## Purpose

This area is split between two tracks. [[hardware/digital-design/369/combinational-logic|Digital design]] covers logic, state, timing, and HDL workflow. [[hardware/signal-conditioning/lecture-notes/lecture-1|Signal conditioning]] covers the analog side.

The split is useful because the constraints are different. Digital design is mostly about discrete state, timing closure, and implementation. Signal conditioning is about how physical signals get shaped before a digital system can trust them.

## Sections

- Digital design: [[hardware/digital-design/369/combinational-logic|combinational logic]], [[hardware/digital-design/369/sequential-logic|sequential logic]], [[hardware/digital-design/371/static-timing-analysis|static timing analysis]]
- Signal conditioning: [[hardware/signal-conditioning/lecture-notes/lecture-1|lecture 1]], [[hardware/signal-conditioning/lecture-notes/lecture-2|lecture 2]], [[hardware/signal-conditioning/lecture-notes/lecture-3|lecture 3]]
- Computer architecture: [[hardware/computer-architecture/simd-vectors-gpus-accelerators|SIMD to SIMT]], [[hardware/computer-architecture/rtl-reading-lab|RTL reading lab]], [[hardware/computer-architecture/experiments-and-benchmarking|experiments and benchmarking]]
