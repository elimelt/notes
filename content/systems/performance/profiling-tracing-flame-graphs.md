---
title: Profiling, Tracing, and Flame Graphs
category: Performance Engineering
tags:
  - profiling
  - tracing
  - flame graphs
  - observability
  - performance debugging
date: 2026-08-01
status: draft
description: The practical measurement layer under the performance models, covering profiling vs tracing vs metrics, sampling mechanics and overhead, how to read flame graphs correctly, a minimal perf workflow, and the standard measurement traps.
sources:
  - title: Gregg, Flame Graphs
    url: https://www.brendangregg.com/flamegraphs.html
    type: docs
  - title: Gregg (2016), The Flame Graph, ACM Queue
    url: https://queue.acm.org/detail.cfm?id=2927301
    type: paper
  - title: Gregg, Linux perf Examples
    url: https://www.brendangregg.com/perf.html
    type: docs
---

## Purpose

The bridge between the abstract models in this section and a live system: how to find out where time actually goes. The three tool families answer different questions, and most wasted investigation time comes from using the wrong one — a CPU profile of an I/O-bound program faithfully reports that the program is idle.

## Three kinds of measurement

- **Metrics/counters** count events over an interval — CPU utilization, cache misses, requests per second. Near-zero overhead, always on, and the right starting point. Gregg's **USE method** structures the first pass: for every resource (CPU, memory, disk, NIC), check Utilization, Saturation, and Errors before touching a profiler, so the profile is aimed at the resource that is actually the bottleneck.
- **Profiling** samples state at a fixed rate — typically the stack of whatever is on-CPU, at 99 Hz — and aggregates. Statistical, cheap, safe in production. Answers "where does the time go?"
- **Tracing** records every occurrence of chosen events with timestamps — syscalls, scheduler switches, function calls. Complete, but the cost scales with event rate; per-function tracing of a hot process can perturb it beyond usefulness. Answers "what exactly happened, and in what order?" — required for latency outliers and rare events, where a sampler almost never looks at the right moment.

The sampling-versus-instrumentation trade is overhead versus completeness. Sampling at 99 Hz costs a fixed ~100 stack walks per second per CPU regardless of workload; instrumenting every function call costs per *event*, which on a hot path can be more work than the function itself. The odd 99 Hz is deliberate: sampling at exactly 100 Hz risks lockstep with timer-driven activity, systematically hitting the same code and biasing the profile; a prime-ish off-frequency decorrelates ([Gregg's perf page](https://www.brendangregg.com/perf.html) uses `-F 99` throughout).

## Flame graphs

A flame graph renders a set of sampled stacks so that visual area equals time ([Gregg 2016, ACM Queue](https://queue.acm.org/detail.cfm?id=2927301)). Rules of the picture:

- Each box is a function present in some stacks; the y-axis is stack depth, callers below callees.
- Box **width** is the fraction of samples containing that frame — total time in the function and everything it called.
- The **x-axis is alphabetical, not time**. Identical stacks merge regardless of when they occurred; left-to-right order means nothing.
- The **top edge** is what was actually executing on-CPU when samples fired. Everything below is ancestry explaining why.

Reading one correctly means resisting the widest-box instinct. A wide frame near the bottom (`main`, an event loop) is just ancestry. The actionable signal is a wide *plateau along the top edge* — a function burning CPU itself — or a wide frame whose children fan out into many narrow flames, meaning its descendants collectively dominate and the fix is at the parent's call rate, not in any child. Gregg's origin story is the cautionary tale: a MySQL CPU regression where `perf report`'s top entry was a status command at ~3% of samples; the flame graph made it obvious the real cost sat under `JOIN::exec`, and the eventual fix recovered 40% CPU. The interactive SVGs support click-to-zoom and search with cumulative-percentage readout, which replaces squinting.

Variants worth knowing: **differential** flame graphs (color = change versus a baseline profile, for regression hunts), **off-CPU** flame graphs (sample or trace *blocked* time instead of running time — the complement that catches I/O, lock waits, and scheduler delay), and icicle (inverted) layout for merging from leaves instead of roots.

## A minimal workflow

System-wide CPU investigation on Linux with `perf` and the [FlameGraph scripts](https://www.brendangregg.com/flamegraphs.html):

```bash
perf stat -a -- sleep 10             # step 0: counters first - is this even
                                     #   a CPU problem? IPC, branch misses
perf record -F 99 -a -g -- sleep 30  # step 1: sample all CPUs at 99 Hz
                                     #   for 30 s, with call stacks
perf script | ./stackcollapse-perf.pl \
            | ./flamegraph.pl > cpu.svg   # step 2: fold and render
```

`perf stat`'s counter summary calibrates expectations before any profile: instructions per cycle near the machine's ceiling means the code is compute-bound and the flame graph will point at real algorithmic cost, while IPC of 0.2 means stalls (memory, branches) and the *widest frame is not where the fix is* — the cycles are being spent waiting inside it, and `perf stat -d`'s cache-miss counters are the follow-up. For blocked time, the eBPF tools are the modern path: `profile(8)` samples on-CPU stacks in-kernel, and `offcputime(8)` aggregates off-CPU durations with stacks, feeding the same folded-stack format.

Two prerequisites break silently. Stack walks need frame pointers, and most distros compile with `-fomit-frame-pointer`; broken profiles show implausibly shallow or fragmented stacks ("grass"), and the fixes are rebuilding with `-fno-omit-frame-pointer`, or `--call-graph dwarf` / `--call-graph lbr` at record time. JIT runtimes (Java, Node) need symbol maps (`perf-map-agent`, `-XX:+PreserveFramePointer`) or every frame is an anonymous address.

## Measurement traps

- **Observer effect.** Every tool costs something; tracing hot events can cost enough to change the behavior under study (Gregg measured ~9% throughput loss tracing scheduler events on a busy MySQL with perf, versus ~6% doing in-kernel aggregation with eBPF). Start with sampling, escalate to tracing narrowly, and measure the tool's impact on the metric you care about.
- **Wrong resource.** An on-CPU profile of a blocked program shows the idle path, correctly and uselessly. If utilization counters say the CPU is not the bottleneck, profile off-CPU time or the saturated device instead.
- **Cold start and warmup.** JIT compilation, cold caches, and unpopulated buffer pools dominate early samples. Profile steady state unless startup *is* the target, and let benchmarks warm up before the measured window.
- **Coordinated omission.** A load generator that waits for each response before sending the next silently drops the latency that would have been observed during stalls — the benchmark self-censors exactly when the system misbehaves. Fixed-schedule (open-loop) load generation and recording intended-start-to-completion latency avoid it. This is the measurement-side counterpart of the percentile arguments in [[systems/performance/tail-latency-percentiles|Tail Latency and Percentiles]].
- **Averaged mixtures.** A profile summed over day and night traffic, or over two request classes, can show a blend no single request experiences — the same failure as averaging latency distributions. Segment before profiling when workloads differ.
- **Missing symbols and truncated stacks** produce confidently wrong pictures rather than errors; treat a profile with unresolved frames or grass-like fragments as broken tooling, not as data.

The benchmark suites under [[systems/operating-systems/benchmarks/README|the OS benchmarks]] are the controlled-environment counterpart of these tools: same counters, no production noise.

## Related notes

- [[systems/performance/latency-throughput-and-utilization|Latency, Throughput, and Utilization]]
- [[systems/performance/tail-latency-percentiles|Tail Latency, Percentiles, and Queueing Distributions]]
- [[systems/operating-systems/benchmarks/README|OS Benchmarks]]
- [[ml/serving-systems/gpu-basics|GPU Basics]]

## Sources

- [Gregg, Flame Graphs](https://www.brendangregg.com/flamegraphs.html)
- [Gregg (2016), The Flame Graph, ACM Queue 14(2)](https://queue.acm.org/detail.cfm?id=2927301)
- [Gregg, Linux perf Examples](https://www.brendangregg.com/perf.html)
- [Gregg, Off-CPU Analysis](https://www.brendangregg.com/offcpuanalysis.html)
