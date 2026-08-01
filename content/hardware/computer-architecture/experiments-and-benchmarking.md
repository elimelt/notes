---
title: Experiments and Benchmarking in Computer Architecture
category: Computer Architecture
tags:
  - benchmarking
  - methodology
  - reproducibility
  - microarchitecture
  - measurement
date: 2026-08-01
updated: 2026-08-01
status: draft
description: A measurement-record schema for computer-architecture experiments (hardware, software, method, evidence class, results), applied honestly against this repo's existing benchmark notes, most of which are missing the hardware model, compiler flags, or both.
sources:
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
  - title: The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)
    url: https://www.agner.org/optimize/microarchitecture.pdf
    type: docs
---

## Purpose

A benchmark result without its measurement record is a number you can't trust or reproduce. This note defines a minimal schema for recording computer-architecture experiments, whether the evidence is a wall-clock timer, a hardware performance counter, or an RTL simulation waveform, and then applies that schema to this repo's own benchmark notes under `systems/operating-systems/benchmarks/`. Most of them are missing required fields. That's stated here plainly rather than fixed silently, since silently backfilling unrecorded hardware details would violate `.notes/artifacts.yml`'s rule to never invent or reconstruct unrecorded measurements.

## The measurement-record schema

Every benchmark claim in this repo should be traceable to a record with these fields:

```yaml
## schema below: informal, not machine-validated
question: "What is being measured, in one sentence."
hardware:
  cpu_model: string           # e.g. "Intel i9-13900HK" -- exact model, not just vendor
  microarch: string           # e.g. "Raptor Lake" -- helps interpret cycle counts
  core_count: int
  cache_sizes: {l1: str, l2: str, l3: str}
  memory: {size: str, type: str, channels: int, speed: str}
os: string                    # kernel version and relevant sysctls (governor, THP, ASLR)
compiler:
  toolchain: string           # e.g. "gcc 13.2"
  flags: string                # e.g. "-O3 -march=native"
evidence_class: enum           # wall-clock | hardware-counter | rtl-waveform | analytic-model
method:
  repetitions: int
  warmup: bool
  affinity: string             # pinned core(s), NUMA node
  variance_reported: bool      # stddev, min/max spread, or CI
workload:
  description: string
  size_or_shape: string
results:
  raw_or_summary_table: table
  units: string
```

Three evidence classes cover essentially everything in this repo and its likely extensions:

- **Wall-clock**: `clock_gettime` or equivalent around a timed loop. Cheapest to collect, easiest to contaminate with noise (frequency scaling, other processes, page faults).
- **Hardware-counter**: `perf stat`/`perf record` reading model-specific registers (cache misses, branch mispredicts, LLC references). Needs the exact microarchitecture recorded, because counter definitions and even counter availability vary across vendors and generations.
- **RTL-waveform**: cycle-accurate simulation output (from something like Verilator or a vendor simulator) for a specific RTL design at a specific commit, as in [[hardware/computer-architecture/rtl-reading-lab|the RTL reading lab]]. The "hardware" here is the simulated microarchitecture, not a physical chip, and the record needs to say so plus name the simulator and commit.

`evidence_class` matters because it changes what "reproducible" means. A wall-clock number is only reproducible on the same or comparable hardware; a hardware-counter number needs the same microarchitecture family to even be comparable across machines; an RTL-waveform number is reproducible by anyone who checks out the same commit and simulator version, independent of physical hardware entirely.

## Auditing this repo's benchmark notes against the schema

Every benchmark note under `content/systems/operating-systems/benchmarks/` is marked `status: needs-review`, and reading them against the schema above shows exactly why. The table below is an honest accounting, not a criticism of the original notes' content (the interpretation and methodology in each one is careful), just their metadata completeness.

| Note | `cpu_model` | `compiler`+flags | `os`/kernel | `repetitions` | `variance_reported` | Evidence class |
|---|---|---|---|---|---|---|
| [[systems/operating-systems/benchmarks/README\|README (DRAM latency)]] | Recorded (i9-13900HK) | Missing | Missing | Missing | Missing | wall-clock + hardware-counter (`perf`) |
| [[systems/operating-systems/benchmarks/mlp\|mlp]] | Missing | Missing | Missing | Missing | Missing | wall-clock |
| [[systems/operating-systems/benchmarks/tlb\|tlb]] | Missing | Missing | Missing | Missing | Missing | wall-clock |
| [[systems/operating-systems/benchmarks/branch\|branch]] | Missing | Missing | Missing | Missing | Missing | wall-clock (cycle estimate assumes 3 GHz) |
| [[systems/operating-systems/benchmarks/store_fwd\|store_fwd]] | Missing | Missing | Missing | Missing | Missing | wall-clock (cycle estimate assumes 3 GHz) |
| [[systems/operating-systems/benchmarks/bandwidth\|bandwidth]] | Missing | Missing | Missing | Missing | Missing | wall-clock |
| [[systems/operating-systems/benchmarks/reductions\|reductions]] | Missing (only "x86-64 with AVX2") | Recorded (`gcc -O3 -march=native`) | Missing | Missing | Missing | wall-clock + compiled assembly inspection |
| [[systems/operating-systems/benchmarks/false_sharing\|false_sharing]] | Missing | Missing | Missing | Missing | Missing | wall-clock |
| [[systems/performance/streaming_benchmarks/cache_line_efficiency/README\|cache_line_efficiency]] | Partial (24 GB LPDDR5, chip model unrecorded) | Recorded (`clang -O3 ... -march=armv8.5-a+simd`, from Makefile) | Missing | 5 passes, but no per-pass variance | No | wall-clock |

Two patterns stand out. First, every note is missing OS/kernel details and repetition/variance policy entirely; none say whether the CPU frequency governor was pinned, whether the process was core-affinitized, or whether the reported number is a mean, median, or single run. Second, the notes that get closest to complete (`reductions`, `cache_line_efficiency`) are exactly the ones that recorded compiler flags from a Makefile that still exists, which suggests the missing fields elsewhere were dropped because the harness's build configuration wasn't captured at measurement time, not because they didn't matter.

None of this invalidates the qualitative conclusions those notes draw (MLP scaling, TLB miss cost, branch misprediction penalty) since the relative comparisons hold regardless of the exact CPU model. It does mean the absolute numbers (92.6 ns per pointer-chase access, 0.85 ns per branchy element) can't be reproduced or checked against a different machine's numbers without knowing what machine produced them. Per `.notes/artifacts.yml`, the fix is not to guess the missing fields retroactively; it's to record them going forward and mark old notes `needs-review` until someone reruns the harness with full metadata, which is exactly the status they already carry.

## What a complete record looks like

The `cache_line_efficiency` benchmark comes closest, so it's worth extracting what it does right as the template for new benchmarks:

```yaml
question: "How much of peak memory bandwidth is achieved for sequential
           partial-line, sequential full-line, and random access?"
hardware:
  cpu_model: "unrecorded (Apple Silicon-class laptop)"  # <- still a gap
  memory: {size: "24 GB", type: "LPDDR5", channels: "unrecorded"}
compiler:
  toolchain: "clang"
  flags: "-O3 -Wall -std=c11 -march=armv8.5-a+simd"
evidence_class: wall-clock
method:
  repetitions: 5
  warmup: true  # buffer touched with memset before timing
  variance_reported: false  # <- gap: only the average of 5 passes is kept
workload:
  description: "1 GB buffer, three access patterns (seq8, seq64, rand8)"
  size_or_shape: "1 GB, 64 B cache lines"
results:
  raw_or_summary_table: "seq8 ~1/8 peak, seq64 ~55 GB/s, rand8 ~70 MB/s"
  units: "GB/s"
```

Even this benchmark's biggest gap, no per-pass variance, is fixable without rerunning anything expensive: report min/max or stddev across the 5 passes instead of collapsing straight to the mean, since 5 samples is enough to say something about noise but the current note discards that information.

## Applying this to RTL evidence

The RTL-waveform evidence class needs one more field the schema above doesn't spell out for the wall-clock and hardware-counter cases: the exact commit SHA of the RTL under test, plus the simulator and its version, because "cycles to execute this trace" is only meaningful pinned to both. [[hardware/computer-architecture/rtl-reading-lab|The RTL reading lab]] pins every excerpt to a commit SHA for exactly this reason, even though it doesn't run simulations itself; any future benchmark note built on those cores (say, comparing branch misprediction recovery cycles between BOOM and XiangShan via waveform traces) should inherit that same commit-pinning discipline plus the simulator name and flags used to build the design.

## Edge cases and limits

This schema is deliberately informal (YAML-shaped prose, not a JSON Schema with a validator), because `.notes/` has no tooling to enforce measurement-record structure yet. It's a checklist for the author to run through before publishing a benchmark note, not a machine-checked contract. A future version could plausibly become a real schema file under `.notes/`, alongside `frontmatter.yml`, `content.yml`, and `prose.yml`, and get referenced from `AGENTS.md`'s benchmark-note workflow, but that's a repo-infrastructure change outside the scope of this note.

The schema also doesn't fully cover comparative benchmarking across systems with different ISAs (say, comparing an x86 result to a result from RVV hardware), since cycle counts and even the meaning of "one operation" diverge across ISAs in ways a single `hardware.cpu_model` field can't capture. That's a gap worth returning to once such a comparison is actually attempted rather than speculatively designed for now.

## Sources

- [What Every Programmer Should Know About Memory (Drepper)](https://www.akkadia.org/drepper/cpumemory.pdf)
- [The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)](https://www.agner.org/optimize/microarchitecture.pdf)

## Related notes

- [[hardware/computer-architecture/rtl-reading-lab|Open-Source CPU RTL Reading Lab]]
- [[hardware/computer-architecture/simd-vectors-gpus-accelerators|From SIMD to SIMT]]
- [[systems/operating-systems/benchmarks/README|Measuring Real DRAM Latency]]
- [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|Cache Line Efficiency Benchmark]]
- [[ml/serving-systems/roofline-reference|Modeling and Scaling Performance with Roofline]]
