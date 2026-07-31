---
title: JVM Performance with State Pattern Optimizations
category: Performance Engineering
tags:
  - jvm
  - state-pattern
  - performance-optimization
  - multithreading
  - atomic-reference
  - benchmarks
date: 2024-12-08
updated: 2026-07-30
status: needs-review
description: Compares an enum-based inline state pattern against a polymorphic state pattern using AtomicReference on the JVM, with single-threaded and multi-threaded timing runs. Hardware, JVM version, and the full benchmark harness were not recorded.
sources:
  - title: "State pattern (Refactoring Guru)"
    url: https://refactoring.guru/design-patterns/state
    type: docs
---

## Purpose

I was reading some interesting code at AWS and came across an implementation of the state pattern written by one of the senior engineers on our team. If you aren't already familiar, read [Refactoring Guru's state pattern page](https://refactoring.guru/design-patterns/state). The problem I would usually reach for the state pattern to solve is about logical complexity and structure, and (without revealing anything in particular about the code I was reading) I got curious about the performance of the underlying implementations, especially with multiple threads. This note records the two implementations I compared and the timing runs.

A caveat on the measurements up front. I didn't record the hardware, OS, or JVM version these ran on, and the `benchmark` helper plus the two pattern classes aren't reproduced here, so treat the numbers as one anecdote rather than a reproducible result. The relative comparisons within a single run are still informative because both implementations ran in the same environment.

## The implementations

1. **Inline state pattern using enums.** In `InlineStatePattern`, states are enums with direct in-line transitions. A state change is a check and an assignment.
2. **Polymorphic state pattern with lazy transitions.** In `PolymorphicStatePattern`, a generic context holds the current state in an `AtomicReference` for thread-safe transitions. Lazy evaluation lets the state change only when necessary, which can reduce overhead in *certain cases* (emphasis on *certain*).

## When might I reach for either?

Reach for the inline pattern when transitions are simple and predictable and you care about synchronization overhead, for example a high-throughput component like a cache or a message queue with little locking.

Reach for the polymorphic pattern when transitions are complex or need additional logic, or when concurrent access requires the safety of `AtomicReference`. Contention level is a rough guide rather than a hard rule. Even with low contention, complex transitions can justify the polymorphic version purely for readability and maintainability.

## JVM costs of each approach

The enum version keeps each transition to an assignment with no extra method dispatch or object creation. Each `DocumentState` enum implements its own `handle` and `nextState` methods, and the transition is simple enough that the JIT can inline it at runtime.

The `AtomicReference` version pays for thread safety with compare-and-swap (CAS) operations. Under high contention, failed CAS attempts retry, which costs cycles. With lazy state transitions, this implementation can skip unnecessary state updates, which may help when contention is low.

## Predictions

1. **Single-threaded.** `InlineStatePattern` should win by avoiding `AtomicReference` overhead.
2. **Multi-threaded.** At low contention, `InlineStatePattern` should still win on fewer synchronization requirements. Under high contention, CAS retries in `PolymorphicStatePattern` may limit its performance.

## Results

### Single-threaded

```java
Document doc1 = new InlineStatePattern.Document("Single-threaded Test");
benchmark("Optimized State Pattern - Single Thread", 10_000_000, doc1::handleState);

Document doc2 = new PolymorphicStatePattern.Document("Single-threaded Test");
benchmark("Generic State Pattern - Single Thread", 10_000_000, doc2::handleState);
```

```txt
Inline State Pattern - Single Thread: 201363 µs for 10000000 iterations (0.02 µs/op) - Last result: Published: Single-threaded Test
Polymorphic State Pattern - Single Thread: 133314 µs for 10000000 iterations (0.01 µs/op) - Last result: Published: Single-threaded Test
```

My prediction failed. The polymorphic version finished 10M iterations in 133 ms against 201 ms for the inline version, so an uncontended `AtomicReference` cost less here than whatever the inline version paid per transition. A single-shot loop like this is also at the mercy of JIT warmup and run ordering, which the low-contention runs below demonstrate.

### Multi-threaded, low contention

```java
Document sharedDoc1 = new InlineStatePattern.Document("Multi-thread Test");
Thread[] threads1 = new Thread[4];
for (int i = 0; i < threads1.length; i++) {
    threads1[i] = new Thread(() -> {
        benchmark("Optimized Pattern - Multi-thread Low Contention", 2_500_000, sharedDoc1::handleState);
    });
    threads1[i].start();
}

Document sharedDoc2 = new PolymorphicStatePattern.Document("Multi-thread Test");
Thread[] threads2 = new Thread[4];
for (int i = 0; i < threads2.length; i++) {
    threads2[i] = new Thread(() -> {
        benchmark("Generic Pattern - Multi-thread Low Contention", 2_500_000, sharedDoc2::handleState);
    });
    threads2[i].start();
}
```

First run, both tests in one JVM:

```txt
Polymorphic Pattern - Multi-thread Low Contention: 339159 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 360859 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 348844 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 375313 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 342431 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 368308 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 368001 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 385776 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
```

Roughly neck and neck, with per-thread averages of 356043.75 µs (0.1424 µs/op) for polymorphic and 366129.0 µs (0.1465 µs/op) for inline. The inline pattern came out slightly slower. Since I hate being proven wrong, I wondered whether run order was the culprit, so I swapped the order of the tests:

```txt
Polymorphic Pattern - Multi-thread Low Contention: 494816 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 481862 µs for 2500000 iterations (0.19 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 491883 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 492075 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 455870 µs for 2500000 iterations (0.18 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 491346 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 483745 µs for 2500000 iterations (0.19 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 475941 µs for 2500000 iterations (0.19 µs/op) - Last result: Published: Multi-thread Test
```

This time the averages were 490159.0 µs (0.1961 µs/op) polymorphic and 476225.5 µs (0.1905 µs/op) inline, so the winner flipped with the ordering. Well well well.

To take ordering out of the picture I ran each test in its own JVM instance:

```txt
Polymorphic Pattern - Multi-thread Low Contention: 372321 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 387558 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 402434 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 407174 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
```

```txt
Inline Pattern - Multi-thread Low Contention: 397600 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 398064 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 392855 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 419996 µs for 2500000 iterations (0.17 µs/op) - Last result: Published: Multi-thread Test
```

Isolated, the averages were 392371.75 µs (0.1569 µs/op) polymorphic and 402128.75 µs (0.1609 µs/op) inline. The inline pattern lost again, by about 2%. `AtomicReference`s are preetttty pretty good.

### High contention

```java
Document highContDoc1 = new InlineStatePattern.Document("High Contention Test");
Document highContDoc2 = new PolymorphicStatePattern.Document("High Contention Test");

for (int i = 0; i < 8; i++) {
    new Thread(() -> {
        benchmark("Optimized Pattern - High Contention", 1_250_000, highContDoc1::handleState);
    }).start();
}

for (int i = 0; i < 8; i++) {
    new Thread(() -> {
        benchmark("Generic Pattern - High Contention", 1_250_000, highContDoc2::handleState);
    }).start();
}
```

The prediction was that CAS retries would hurt `PolymorphicStatePattern` as thread count rises. I never recorded the output of this run, so the high-contention question stays open.

## What the numbers say

The measurements contradict the intuition I started with. The polymorphic pattern with `AtomicReference` matched or beat the enum-based inline pattern in every run where I kept the output: 34% faster single-threaded, and 2% to 3% faster at 4 threads in the isolated-JVM runs. The differences in the low-contention runs are close to the run-to-run noise, as the order-swap experiment shows, so the honest summary is that the two implementations cost about the same at this contention level and the safety of `AtomicReference` came essentially for free. Picking between them on maintainability grounds looks like the right call until a profiler says otherwise. A proper rematch would use JMH, record the JVM and hardware, and include the high-contention run.
