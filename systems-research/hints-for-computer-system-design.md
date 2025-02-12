---
title: Hints for Computer System Design
category: System Design
tags: systems, scaling, review, paper, caching
description: A review of the paper "Hints for Computer System Design" by Butler Lampson.
---


# [source](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17.pdf)

###### Hints for Computer System Design

---

### Key Insights

#### Caching

Store $\[f, x, f(x)\]$ tuples in a cache.

If $f$ isn't a pure function, invalidate with the following:

$$
f(x + \Delta) = g(x, \Delta, f(x))
$$

For example, $x$ is an `int[]`, $\Delta$ is a write $(i, v)$, and $f$ is a function `int sum(int[] x)`. Then $g(x, \Delta, f(x))$ is `f(x) + v - x[i]`.

Caches should ideally have adaptive sizes.

A classic example is the caching in hardware that uses $\[Fetch, \text{address}, \text{content of address}\]$ tuples. Similarly, virtual memory uses $\[Page, \text{address}, \text{content of address}\]$ tuples.

However, more complicated applications of caching exist. In real-time systems, you're often trying to cache the state of a system given small changes corresponding to events. The key here is to try and invalidate as few entries as possible in response to events.


### Lecture Review Notes

#### Why is system design hard?

- external interface isn't well defined
    - requirements aren't clear
    - Things are often not well-designed
- The measure of success is not very clear
    - Many different ways to interact with a system
    - Many systems, even in production, have bugs

#### Throw one away

- Always be prepared to discard your prototype
- Throw ideas at the wall and go with what sticks

#### Interface Design

Conflicting requirements:
- Simple
- Complete
- Efficient

In a way it's a lot like PL design; exposing new abstractions, objects and operations, manipulating them, etc.

KISS; Do one thing at a time and do it well.

- Don't over-promise
- Get it right, but beware the dangers of abstractions (especially performance)
- Make it fast rather than general and complete. You should keep scope small so that it's easy to optimize, and also to compose with other systems/components
- Procedure args let you keep it general but extendable
    - C function pointers, C++ functions
    - `LD_PRELOAD` trick: override calls by providing a wrapper that calls the original function, but with some extra functionality
- Leave it to the client (check Exokernel paper)
    - Unix pipes
- Keep interfaces stable
    - Counterexample LLVM
- Keep a place to stand
    - Virtualization!!!

#### Implementation

Plan to throw one away - learn from prototyping

Keep secrets - impl details hidden from clients. Can be tradeoff for performance optimizations

Handle normal and worst cases separately

- Might be OK to crash a few processes if it means the system can recover
- Caches in processors are optimized for common case (principle of locality)
- Paging in virtual memory is optimized for common case (principle of locality)

#### Efficiency

- Split resources
    - Faster to allocate a new resource than to wait for one to be freed
    - Heterogeneous systems
        - Specialized hardware like FPGA or GPU to run specialized tasks
        - E.G. Google's TPU, Microsoft Azure FPGAs
- Use static analysis

#### Reliability
- Log updates
    - Can recover
    - Append only is efficient
    - Can be used for replication
- Atomic transactions
    - E.G. ACID

#### Takeaways

- Most successful systems are built with particular themes, many of which are discussed in this paper
- When reading papers, look for what you can apply, and ignore irrelevant details.
- Hints can be added, e.g. approximation vs precision

### Further Reading

- MicroLog
- https://github.com/DPDK/dpdk
