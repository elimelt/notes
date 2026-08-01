---
title: Amdahl, Gustafson, and Scalability Limits
category: Performance Engineering
tags:
  - amdahl
  - gustafson
  - scalability
  - speedup
  - parallel performance
date: 2026-08-01
status: draft
description: The laws that bound parallel speedup - Amdahl's fixed-problem ceiling, Gustafson's scaled-problem rebuttal, and the contention and coherency terms that make real systems scale worse than either predicts, with computed tables.
sources:
  - title: Amdahl (1967), Validity of the Single Processor Approach
    url: https://dl.acm.org/doi/10.1145/1465482.1465560
    type: paper
  - title: Gustafson (1988), Reevaluating Amdahl's Law
    url: https://dl.acm.org/doi/10.1145/42411.42415
    type: paper
  - title: Brown (2000), Amdahl's Law and Parallel Speedup (USENIX ALS)
    url: https://www.usenix.org/legacy/publications/library/proceedings/als00/2000papers/papers/full_papers/brownrobert/brownrobert_html/node3.html
    type: paper
  - title: Gunther, The Universal Scalability Law
    url: http://www.perfdynamics.com/Manifesto/USLscalability.html
    type: docs
---

## Purpose

These are the laws that make parallel-scaling claims falsifiable: given a measured speedup curve, they say whether the workload is limited by serial work, by communication, or by nothing yet. The numeric tables below are computed directly from the formulas (script run in the repo venv). This note is the model layer under measurement notes like [[systems/operating-systems/benchmarks/reductions|the reductions benchmark]], which is an Amdahl story in miniature.

## Amdahl's law

Fix the problem. Split execution time into a fraction $p$ that parallelizes perfectly and a fraction $1-p$ that does not. On $N$ processors:

$$
S(N) = \frac{1}{(1-p) + p/N},
\qquad
\lim_{N \to \infty} S(N) = \frac{1}{1-p}.
$$

The derivation is one line — the parallel part shrinks by $N$, the serial part does not — but the consequence is brutal because the serial term dominates as $N$ grows:

| $p$ | $S(8)$ | $S(64)$ | $S(1024)$ | ceiling $1/(1-p)$ |
| --- | --- | --- | --- | --- |
| 0.50 | 1.78 | 1.97 | 2.00 | 2 |
| 0.90 | 4.71 | 8.77 | 9.91 | 10 |
| 0.95 | 5.93 | 15.42 | 19.64 | 20 |
| 0.99 | 7.48 | 39.26 | 91.18 | 100 |
| 0.999 | 7.94 | 60.21 | 506.18 | 1000 |

A 95%-parallel program never exceeds 20x, and at 64 cores it has already burned three quarters of its budget on the serial 5%. Historical footnote: [Amdahl's 1967 paper](https://dl.acm.org/doi/10.1145/1465482.1465560) contains no formula — it is a two-and-a-half-page argument against parallel machines, estimating that data-management housekeeping consumed ~40% of executed instructions and would not parallelize. The algebra was formalized by later commentators.

**Reading the serial fraction honestly.** $1-p$ is not "lines of code outside the parallel loop." It is everything whose cost fails to shrink with $N$: lock acquisition and barriers, load imbalance (the barrier waits for the slowest worker), the fork/join and result-merge phases, and — critically on multicore — shared memory bandwidth. A saturated memory bus behaves exactly like serial work: for a bandwidth-bound kernel, speedup caps at (aggregate bandwidth) / (single-core bandwidth demand) no matter how many cores exist. When a measured curve flattens earlier than the code's visible structure suggests, the effective serial fraction is telling you about one of these hidden components, and fitting $1/((1-p)+p/N)$ to the measurements recovers it.

## Gustafson's law

[Gustafson (1988)](https://dl.acm.org/doi/10.1145/42411.42415) attacked the fixed-problem assumption: in practice, buying a 1024-node machine means running a 1024-node-sized problem. Fix the *time* instead, let the parallel work grow with $N$, and ask how much more got done. If the scaled run spends fraction $s = 1 - p'$ of its time in serial work, the same job on one processor would have taken $s + p'N$, so the scaled speedup is

$$
S(N) = s + p'N = N - (1-p')(N-1),
$$

linear in $N$ with slope $p'$ — no ceiling. With $p' = 0.99$ and $N = 1024$: 1014x, against Amdahl's 91x for the same fractions. This was not hypothetical: Gustafson's team at Sandia reported 1016-1021x scaled speedups on a 1024-processor hypercube across three real applications, the results that ended the "Amdahl says parallelism is futile" era.

The two laws answer different questions rather than contradicting each other. **Strong scaling** (Amdahl): same problem, more processors, lower latency — the right lens when the problem size is fixed by external requirements, e.g. serving one request faster. **Weak scaling** (Gustafson): more processors, proportionally bigger problem, same wall-clock — the right lens for batch and simulation workloads where fidelity or dataset size soaks up capacity. Misapplied lenses produce nonsense in both directions: quoting weak-scaling numbers for a latency problem overstates what more hardware buys, and quoting Amdahl at a throughput problem understates it.

## Where both laws are too optimistic

Both laws assume the parallel fraction costs nothing to coordinate. Add an overhead term $T_o(N)$ that *grows* with $N$ ([Brown 2000](https://www.usenix.org/legacy/publications/library/proceedings/als00/2000papers/papers/full_papers/brownrobert/brownrobert_html/node3.html)):

$$
S(N) = \frac{T_s + T_p}{T_s + T_o(N) + T_p/N}.
$$

If $T_o$ is all-to-all communication, $T_o \propto N^2$ per step and the curve peaks at finite $N$, then declines. Gunther's [Universal Scalability Law](http://www.perfdynamics.com/Manifesto/USLscalability.html) packages this into two fittable parameters:

$$
S(N) = \frac{N}{1 + \sigma(N-1) + \kappa N(N-1)},
$$

where $\sigma$ is contention (queueing for a shared resource; $\kappa = 0$ reduces the model to Amdahl's shape) and $\kappa$ is coherency (pairwise cost of keeping $N$ parties consistent: cache-line ping-pong, lock handoffs, consensus chatter — hence the $N(N-1)$). The $\kappa$ term is what Amdahl and Gustafson cannot express: **retrograde scaling**, throughput that falls when capacity is added, with the peak at $N_{opt} = \sqrt{(1-\sigma)/\kappa}$. Computed example with $\sigma = 0.02$, $\kappa = 10^{-4}$:

| $N$ | 8 | 32 | 64 | 99 | 200 | 350 |
| --- | --- | --- | --- | --- | --- | --- |
| $S(N)$ | 7.0 | 18.6 | 24.0 | **25.2** | 22.3 | 17.3 |

Peak 25.2x at $N_{opt} = \sqrt{0.98/10^{-4}} \approx 99$, and 350 processors are 30% *slower* than 99. Fitting these three parameters to a measured scaling curve is the practical procedure: $\sigma$ names your serialization, a nonzero $\kappa$ names your crosstalk, and $N_{opt}$ tells you where to stop buying hardware.

```python
import numpy as np

def amdahl(p, N):    return 1 / ((1 - p) + p / N)
def gustafson(p, N): return N - (1 - p) * (N - 1)
def usl(N, sigma, kappa):
    return N / (1 + sigma * (N - 1) + kappa * N * (N - 1))

N = np.array([8, 32, 64, 99, 200, 350])
print(np.round(amdahl(0.95, N), 2))       # [ 5.93 12.55 15.42 16.78 18.26 18.97]
print(np.round(usl(N, 0.02, 1e-4), 1))    # [ 7.  18.6 24.  25.2 22.3 17.3]
```

Note the contrast in the two printed rows: the Amdahl curve with $p = 0.95$ climbs monotonically toward its ceiling of 20, while the USL curve with a small $\kappa$ turns over and falls.

## Using the laws

- **Estimate before parallelizing.** Profile the serial share first; if 20% of runtime is unparallelizable, the ceiling is 5x and a heroic 64-core port is wasted effort compared to attacking the serial 20%.
- **Diagnose from the curve's shape.** Flattening toward an asymptote is Amdahl-type serialization ($\sigma$); a peak followed by decline is coherency ($\kappa$) — more parallelism will actively hurt, and the fix is reducing sharing (partitioning, per-core state, batching updates), not tuning the parallel code.
- **State which scaling regime a benchmark ran.** "Linear to 1024 nodes" under weak scaling and under strong scaling are claims of very different strength; published speedup numbers are meaningless without this label.
- **Watch the denominator.** Speedup is relative to the best *serial* implementation; a parallel program that scales beautifully over its own 1-thread mode may still lose to tuned serial code — Amdahl arguments silently assume the $N=1$ baseline is worth speeding up.

The queueing-side view of the same saturation phenomena — what happens to latency rather than throughput as load approaches capacity — is in [[systems/performance/latency-throughput-and-utilization|Latency, Throughput, and Utilization]] and [[systems/operating-systems/v2-concurrency/7-queueing-theory|Queueing Theory]].

## Sources

- [Amdahl (1967), Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities](https://dl.acm.org/doi/10.1145/1465482.1465560)
- [Gustafson (1988), Reevaluating Amdahl's Law, CACM 31(5)](https://dl.acm.org/doi/10.1145/42411.42415)
- [Brown (2000), Amdahl's Law and Parallel Speedup, USENIX ALS](https://www.usenix.org/legacy/publications/library/proceedings/als00/2000papers/papers/full_papers/brownrobert/brownrobert_html/node3.html)
- [Gunther, USL Scalability Manifesto](http://www.perfdynamics.com/Manifesto/USLscalability.html)

## Related notes

- [[systems/performance/latency-throughput-and-utilization|Latency, Throughput, and Utilization]]
- [[systems/operating-systems/v2-concurrency/7-queueing-theory|Queueing Theory]]
- [[systems/performance/streaming|Streaming Data]]
- [[systems/operating-systems/benchmarks/reductions|Reductions Benchmark]]
