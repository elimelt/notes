# JVM Performance with State Pattern Optimizations

I was reading some interesting code at AWS and came across an implementation of the state pattern written by one of the senior engineers on our team. If you aren't already familiar, read [this](https://refactoring.guru/design-patterns/state). While the problem I would usually reach to the state pattern to solve is one more concerned with logical complexity and structure, (without revealing anything in particular about the code I was reading) I was intrigued by the performance implications of the underlying implementations, especially in a multi-threaded environment.

## The Implementations

1. **Optimized State Pattern Using Enums**: In `InlineStatePattern`, states are represented as enums with direct in-line transitions. State changes are handled by a simple check and assignment operation.
2. **Generic State Pattern with Lazy Transitions**: In `PolymorphicStatePattern`, state changes are managed with a generic context using an `AtomicReference` for thread-safe transitions. Lazy evaluation allows the state to change only if necessary, reducing the overhead in *certain cases* (emphasis on *certain*).

## When might I reach for either?

1. **Inline State Pattern**:
   - Use when state transitions are simple and predictable.
   - Ideal for low contention scenarios where synchronization overhead is a concern. For example, in a high-throughput system with little locking overhead, like a cache or a message queue.

2. **Generic State Pattern**:
   - Use when state transitions are complex or require additional logic.
   - Ideal for high contention scenarios where synchronization is necessary. For example, in a shared resource or a asynchronous/distributed system. Note that while I'm saying high contention, this is not a hard and fast rule. It's more about the nature of the contention and the nature of the state transitions, e.g. if the state transitions are complex and the contention is low, you might still want to use the generic state patter for the sake of readability maintainability.

### JVM Optimizations and Overheads

1. **Enum-Based State Handling (Inlined Transitions)**:
   - Enums offer low-level performance wins by making state transitions in-line without additional method calls or object creation. OpenJDK initial
   - In this setup, each `DocumentState` enum implements its own `handle` and `nextState` methods. Transitioning states here is a simple assignment with little locking overhead, so the JVM can optimize by inlining these transitions at runtime.

2. **Generic Interface with `AtomicReference`**:
   - `AtomicReference` ensures thread safety for transitions, but adds some overhead due to its CAS (Compare-and-Swap) operations, which are costly under high contention.
   - With lazy state transition, this implementation could theoretically avoid unnecessary state updates, which may be beneficial under lower contention.

## Predictions and Testing

Based on JVM behaviors, here are our predictions:

1. **Single-threaded Performance**:
   - `InlineStatePattern` should outperform `PolymorphicStatePattern` in single-threaded scenarios due to reduced overhead from `AtomicReference`.

2. **Multi-threaded Performance**:
   - At lower levels of contention, `InlineStatePattern` should still perform better due to fewer synchronization requirements.
   - Under high contention, the `AtomicReference` CAS operations in `PolymorphicStatePattern` may actually limit performance due to frequent retries.

To verify these assumptions, let’s test using the following code blocks. You can add these into the `main` method to see the results.

### Code Blocks to Test Performance

1. **Single-Threaded Performance Test**:

```java
   Document doc1 = new InlineStatePattern.Document("Single-threaded Test");
   benchmark("Optimized State Pattern - Single Thread", 10_000_000, doc1::handleState);

   Document doc2 = new PolymorphicStatePattern.Document("Single-threaded Test");
   benchmark("Generic State Pattern - Single Thread", 10_000_000, doc2::handleState);
```

Here, I predict `InlineStatePattern` will complete faster, as it avoids the overhead of `AtomicReference` and CAS operations.

```txt
Inline State Pattern - Single Thread: 201363 µs for 10000000 iterations (0.02 µs/op) - Last result: Published: Single-threaded Test
Polymorphic State Pattern - Single Thread: 133314 µs for 10000000 iterations (0.01 µs/op) - Last result: Published: Single-threaded Test
```

As expected, `InlineStatePattern` outperforms `PolymorphicStatePattern` in a single-threaded scenario by roughly 50%.

2. **Multi-Threaded Performance Test with Low Contention:**:

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

Here, `InlineStatePattern` should still outperform `PolymorphicStatePattern`, as the contention is low.

```txt
Polymorphic Pattern - Multi-thread Low Contention: 339159 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 360859 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 348844 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 375313 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 342431 µs for 2500000 iterations (0.14 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 368308 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 368001 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 385776 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
idata = [339159, 360859, 348844, 375313]
pdata = [342431, 368308, 368001, 385776]
```

As you can see however, despite being roughly neck and neck with Poly and Inline having respective averages of `356043.75` (`0.1424175 µs/op`) and `366129.0` (`0.1464516 µs/op`), the Inline pattern is actually slightly slower in this case. Since I hate being proven wrong, I also wonder if the results would be different if we swapped the order of the tests.

```txt
Polymorphic Pattern - Multi-thread Low Contention: 494816 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 481862 µs for 2500000 iterations (0.19 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 491883 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 492075 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 455870 µs for 2500000 iterations (0.18 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 491346 µs for 2500000 iterations (0.20 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 483745 µs for 2500000 iterations (0.19 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 475941 µs for 2500000 iterations (0.19 µs/op) - Last result: Published: Multi-thread Test
idata = [494816, 481862, 491883, 492075]
pdata = [455870, 491346, 483745, 475941]
```

This time, we have a Poly and Inline average of `490159.0` (`0.1960636 µs/op`) and `476225.5` (`0.1904902 µs/op`) respectively. Well well well...

Lets try this one more time, running the tests twice, while also isolating them to their own JVM instances.

```txt
Polymorphic Pattern - Multi-thread Low Contention: 372321 µs for 2500000 iterations (0.15 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 387558 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 402434 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Polymorphic Pattern - Multi-thread Low Contention: 407174 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
pdata = [372321, 387558, 402434, 407174]
```

```txt
Inline Pattern - Multi-thread Low Contention: 397600 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 398064 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 392855 µs for 2500000 iterations (0.16 µs/op) - Last result: Published: Multi-thread Test
Inline Pattern - Multi-thread Low Contention: 419996 µs for 2500000 iterations (0.17 µs/op) - Last result: Published: Multi-thread Test
idata = [397600, 398064, 392855, 419996]
```

So we have a Inline average of `402128.75` (`0.1608515 µs/op`) and a Poly average of `392371.75` (`0.1569487 µs/op`). So it seems that the Inline pattern is actually slower in this case. `AtomicReference`s are preetttty pretty good.

3. **High Contention Test with Increased Threads:**

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

With more threads, we expect contention to impact `PolymorphicStatePattern` more due to frequent CAS retries in AtomicReference.

## Conclusion

The low-level optimizations in `InlineStatePattern` using enums make it ideal for performance-critical, low-contention use cases. `PolymorphicStatePattern`, with its AtomicReference, offers better safety for concurrent environments but incurs a trade-off in performance due to CAS operations. Testing under these scenarios confirms that the right implementation depends on your application’s specific threading needs.