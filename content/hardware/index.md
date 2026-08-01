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
  - title: NVIDIA Hopper Architecture
    url: https://www.nvidia.com/en-us/data-center/technologies/hopper-architecture/
    type: docs
---

## Purpose

This area is split between three tracks. [[hardware/digital-design/369/combinational-logic|Digital design]] covers logic, state, timing, and HDL workflow. [[hardware/signal-conditioning/lecture-notes/lecture-1|Signal conditioning]] covers the analog side. [[hardware/gpu-architecture|GPU architecture]] applies the digital design primitives to a real, large-scale parallel processor.

The split is useful because the constraints are different. Digital design is mostly about discrete state, timing closure, and implementation. Signal conditioning is about how physical signals get shaped before a digital system can trust them. GPU architecture is about what happens when you replicate and specialize that same digital logic at massive scale to extract data parallelism.

## Sections

- Digital design: [[hardware/digital-design/369/combinational-logic|combinational logic]], [[hardware/digital-design/369/sequential-logic|sequential logic]], [[hardware/digital-design/371/static-timing-analysis|static timing analysis]]
- Signal conditioning: [[hardware/signal-conditioning/lecture-notes/lecture-1|lecture 1]], [[hardware/signal-conditioning/lecture-notes/lecture-2|lecture 2]], [[hardware/signal-conditioning/lecture-notes/lecture-3|lecture 3]]
- GPU architecture: [[hardware/gpu-architecture|GPU Architecture from First Principles]], building SIMT execution up from clocked RTL primitives
