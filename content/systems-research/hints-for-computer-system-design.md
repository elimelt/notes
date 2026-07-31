---
title: Hints for Computer System Design
category: System Design
tags:
  - systems
  - scaling
  - review
  - paper
  - caching
date: 2025-01-06
updated: 2026-07-30
status: evergreen
description: Notes on Lampson's hints paper plus lecture discussion, with a worked treatment of his caching formulation and the interface, implementation, efficiency, and reliability hints.
sources:
  - title: Hints for Computer System Design (SOSP 1983)
    url: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17.pdf
    type: paper
---

## Purpose

Notes on Butler Lampson's hints paper, combining my own reading with lecture discussion. The caching section gets the most depth because Lampson's formulation generalizes further than the usual presentation of caching.

## Citation

- [Hints for Computer System Design](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17.pdf), Butler Lampson, SOSP 1983.

## Caching, Lampson's way

Store $[f, x, f(x)]$ tuples in a cache. The cache maps a function and its argument to a memoized result.

If $f$ isn't a pure function, you need a way to update cached entries when the input changes. Lampson frames invalidation as finding a cheap update function $g$ such that

$$
f(x + \Delta) = g(x, \Delta, f(x))
$$

For example, let $x$ be an `int[]`, let $\Delta$ be a write $(i, v)$, and let $f$ be `int sum(int[] x)`. Then $g(x, \Delta, f(x))$ is `f(x) + v - x[i]`. You never recompute the sum from scratch; you patch the cached value.

Hardware caching fits the same shape with $[Fetch, \text{address}, \text{content of address}]$ tuples, and virtual memory with $[Page, \text{address}, \text{content of address}]$ tuples. More complicated applications exist too. Real-time systems often cache the state of a system under small event-driven changes, and the goal is to invalidate as few entries as possible per event. Caches should ideally have adaptive sizes.

## Why is system design hard?

The external interface isn't well defined. Requirements aren't clear, and the things you build against are often not well designed themselves. The measure of success is also murky, since there are many ways to interact with a system, and many production systems ship with bugs anyway.

## Interface design

An interface wants to be simple, complete, and efficient at the same time, and those requirements conflict. Designing one is a lot like language design, since you expose abstractions and operations that clients then build on.

The hints that stuck with me:

- Do one thing at a time and do it well. Don't over-promise.
- Get it right, but beware the dangers of abstractions, especially their performance cost.
- Make it fast rather than general and complete. Small scope keeps a component easy to optimize and easy to compose with other systems.
- Procedure arguments keep an interface general but extendable. C function pointers and C++ callables are the everyday version. The `LD_PRELOAD` trick is another: override a call by providing a wrapper that adds functionality and then calls the original.
- Leave it to the client. Unix pipes do this, and the [[systems-research/exokernel|Exokernel]] takes it to the extreme.
- Keep interfaces stable. LLVM's churn is the counterexample.
- Keep a place to stand. Virtualization is the canonical example.

## Implementation

Plan to throw one away; you learn from the prototype, so be prepared to discard it. Keep secrets, meaning implementation details hidden from clients, while knowing that secrecy can trade off against performance optimizations.

Handle normal and worst cases separately. It might be fine to crash a few processes if the system as a whole can recover. Processor caches and virtual memory paging both optimize for the common case that locality predicts.

## Efficiency

Split resources. Allocating a fresh resource is faster than waiting for one to be freed, and dedicating specialized hardware to specialized tasks follows the same logic. FPGAs and GPUs running dedicated workloads, like Google's TPU or Microsoft Azure's FPGAs, are the modern version. Static analysis helps find the rest.

## Reliability

Log updates. A log gives you recovery after a crash. Because it is append-only it is also cheap to write, and the same log doubles as a replication mechanism. Atomic transactions, in the ACID sense, build on that foundation.

## Takeaways

Most successful systems repeat a small set of themes, many of which this paper names. When reading papers, look for what you can apply and ignore irrelevant details. The hints also extend; approximation versus precision is one axis Lampson leaves room for.

## Further reading

- [DPDK](https://github.com/DPDK/dpdk), kernel-bypass networking that follows the "leave it to the client" hint
- MicroLog

## Sources

- [Hints for Computer System Design](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17.pdf)

## Related notes

- [[systems-research/end-to-end-arguments-in-sys-design|End-to-End Arguments in System Design]]
- [[systems-research/locality-principle|The Locality Principle]]
