---
title: Hardware
category: Hardware
tags:
  - hardware
  - digital design
  - timing
  - signals
  - computer-architecture
date: 2026-07-31
updated: 2026-08-01
status: evergreen
description: Map of the hardware notes, spanning digital design, signal-conditioning lecture notes, and computer architecture.
sources:
  - title: The RISC-V Instruction Set Manual
    url: https://riscv.github.io/riscv-isa-manual/snapshot/spec/
    type: spec
---

## Purpose

This area is split between three tracks. [[hardware/digital-design/369/combinational-logic|Digital design]] covers logic, state, timing, and HDL workflow. [[hardware/signal-conditioning/lecture-notes/lecture-1|Signal conditioning]] covers the analog side. [[hardware/computer-architecture/index|Computer architecture]] covers the ISA-to-microarchitecture-to-RTL stack that sits on top of digital design.

The split is useful because the constraints are different. Digital design is mostly about discrete state, timing closure, and implementation. Signal conditioning is about how physical signals get shaped before a digital system can trust them. Computer architecture is about the abstractions (ISA, pipeline, out-of-order execution) that let digital design build something a compiler can target.

## Sections

- Digital design: [[hardware/digital-design/369/combinational-logic|combinational logic]], [[hardware/digital-design/369/sequential-logic|sequential logic]], [[hardware/digital-design/371/static-timing-analysis|static timing analysis]]
- Signal conditioning: [[hardware/signal-conditioning/lecture-notes/lecture-1|lecture 1]], [[hardware/signal-conditioning/lecture-notes/lecture-2|lecture 2]], [[hardware/signal-conditioning/lecture-notes/lecture-3|lecture 3]]
- Computer architecture: [[hardware/computer-architecture/index|map]], [[hardware/computer-architecture/isa-datapath-control|ISA/datapath/control]], [[hardware/computer-architecture/pipelining-hazards-branch-prediction|pipelining and hazards]], [[hardware/computer-architecture/out-of-order-execution|out-of-order execution]], [[hardware/computer-architecture/simd-vectors-gpus-accelerators|SIMD to SIMT]], [[hardware/computer-architecture/rtl-reading-lab|RTL reading lab]], [[hardware/computer-architecture/experiments-and-benchmarking|experiments and benchmarking]]
