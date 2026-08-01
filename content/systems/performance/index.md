---
title: Performance Engineering
category: Performance Engineering
tags:
  - performance engineering
  - latency
  - throughput
  - bandwidth
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the performance notes, with emphasis on bottleneck models and measurements.
---

## Purpose

The performance section is small, so it should carry the basic mental model as well as the case studies. Start with [[systems/performance/latency-throughput-and-utilization|latency, throughput, and utilization]]. It gives the queueing and bottleneck vocabulary that the other notes assume.

Then read [[systems/performance/streaming|streaming data]] for a concrete bandwidth-bound workload and [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|cache-line efficiency benchmark]] for a direct measurement of how access pattern changes throughput.

## Notes

- Foundations: [[systems/performance/latency-throughput-and-utilization|latency, throughput, and utilization]], [[systems/performance/tail-latency-percentiles|tail latency, percentiles, and queueing distributions]], [[systems/performance/amdahl-gustafson-scalability|Amdahl, Gustafson, and scalability limits]]
- Bandwidth and streaming: [[systems/performance/streaming|streaming data]], [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|cache-line efficiency benchmark]]
- Case study: [[systems/performance/efficiently-implementing-state-pattern-JVM|efficiently implementing the state pattern on the JVM]]
