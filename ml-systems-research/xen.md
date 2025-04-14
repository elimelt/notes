---
title: Xen and the Art of Virtualization
category: Systems
tags: virtualization, hypervisor, xen, operating system, systems
description: Paper review of Xen and the Art of Virtualization
---

###### [Xen and the Art of Virtualization](https://www.cl.cam.ac.uk/research/srg/netos/papers/2003-xensosp.pdf)

---

### What is the Problem?

Full virtualization, where you completely emulate the underlying hardware of a machine to run a guest OS, is not a very good solution. In particular, it is much slower due to overhead, and it doesn't guest OSes to access hardware features from the host OS.

### Summary

Xen is a hypervisor that allows multiple OSes to run on the same hardware through **paravirtualization**. This means that the guest OSes are modified to be aware of the hypervisor, and they can make calls to the hypervisor to access hardware features. It implements efficient mechanisms for memory management, scheduling, event delivery, and I/O that exist in the hypervisor, which are then used to delegate resources to the guest OSes. To this end, it achieves many performance improvements over traditional full virtualization systems on their port **XenoLinux**.

### Key Insights

- Guest OSes benefit from being hypervisor-aware, both for correctness (clocks, paging), and performance (fast handlers).
- Paravirtualization provides huge performance improvements over full virtualization, but requires modifying the guest OSes. Xen was still able to minimize the amount of source code that needed to be changed by using a simple and clean interface that can easily be ported to new OSes.

### Notable Design Details/Strengths

- Requires minimal changes to the guest OSes; only need to "port" new guest OSes, which involves modifying the OS to be aware of the hypervisor
- Very low overhead in terms of latency and throughput for most operations, since emulation is not needed in many cases

### Limitations/Weaknesses

- Guest OSes still need to be modified, making adoption more difficult for new OSes
- Doesn't support SMP on guest OSes, meaning some workloads are still far more efficient on native hardware

### Summary of Key Results

- Performance very close to native linux for many workloads, and even when it is not, it is still much better than full virtualization
- Many concurrent guest OSes can run with little memory imprint resulting from the hypervisor.

### Open Questions

- Is there a way to automatically/programmatically port guest OSes to be hypervisor-aware? Is there some way we could make implementing a new OS conform to an interface that complies with the hypervisor automatically?
- Has there been any work in detecting "hot spots" for routines that that are called a lot, for which we could automatically register a fast handler in the hypervisor?
