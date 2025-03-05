---
title: The Locality Principle
category: Systems
tags: os, operating-system, systems, multicore, kernel
description: A review of the paper The Locality Principle, where the authors argue that the OS should be designed to exploit the locality of reference in modern workloads.
---

###### [Paper Title](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/asplos2016.pdf)

---

### What is the Problem?

Early implementations of virtual memory were plagued by poor performance due to thrashing, when the system spends more time swapping pages in and out of memory than executing the actual program. This is caused by a larger "working set" than the available physical memory, leading to repeated page faults and throughput collapse.

### Summary

The author details the history of virtual memory and the development and evolution of the working set model for managing memory. While studying this, the author discovered a natural pattern in the behavior of modern workloads: working sets tend to be related by some measure of locality. This property is generally applicable and can therefore be exploited to improve the performance of many systems.

### Key Insights

- Systems, particularly those that interact with some external storage, naturally exhibit patterns in locality that can be exploited to improve performance.
- When working sets grow too large, one way to cope is to queue up requests and and control admission to the working set.

### Notable Design Details/Strengths

- The working set model ($W(t,T)$) abstractly defines a process's memory needs as the set of pages referenced in the time interval of length T preceding time t, giving a good theoretical basis for understanding memory behavior.
- The feedback control mechanism for limiting multiprogramming level prevents thrashing by refusing to activate programs whose working sets wouldn't fit in available memory.

### Limitations/Weaknesses

- The original working set model requires a fixed $T$ (essentially an LRU cache of size $T$), which is not always ideal for all workloads.
- Some workloads differ in nature from the traditional working set model, e.g. a job running over a massive file that is read sequentially.

### Summary of Key Results

- Virtual memory became a viable and relatively predictable technology.
- The locality principle has been successfully applied to many many domains and systems/

### Open Questions

- Can malicious actors exploit systems that design for the common case of locality, somehow executing a DOS attack?
- Is designing a system for high throughput sequential reads directly at odds with designing for locality? Or can the two be targeted simultaneously?
