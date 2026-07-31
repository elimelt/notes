---
title: Virtual Memory and Paging
aliases:
  - operating-systems/lecture-notes/paging
category: Operating Systems
tags:
  - virtual-memory
  - paging
  - fragmentation
  - page-tables
  - address-translation
  - page-replacement
  - working-set
date: 2024-02-07
updated: 2026-07-30
status: evergreen
description: The paging mechanism (page tables, address translation, PTE contents) and the policy side of virtual memory, demand paging, replacement algorithms from FIFO to clock, and the working set model.
sources:
  - title: P. J. Denning, "The Working Set Model for Program Behavior" (CACM, 1968)
    type: paper
  - title: L. A. Belady, R. A. Nelson, and G. S. Shedler, "An Anomaly in Space-Time Characteristics of Certain Programs Running in a Paging Machine" (CACM, 1969)
    type: paper
  - title: Operating systems course lecture notes
    type: lecture
---

Paging maps virtual memory to physical memory in fixed-size units. This note covers the mechanism (page tables, address translation, what lives in a PTE) and the policy side of virtual memory: demand paging, page replacement algorithms, and the working set model.

## Why pages

Dividing memory into fixed-size pages prevents **external fragmentation**, and keeping the allocation unit small limits **internal fragmentation**.

- **external fragmentation**: free memory is broken into pieces too small and scattered to use, even though the total would be enough.
- **internal fragmentation**: a process is allocated more memory than it needs, and the excess goes unused.

Virtual address space divides into *pages*, physical address space into *frames*. The page table maps pages to frames. It lives in memory, and the page table base register (PTBR) points at it. Index it by page number and it gives back a frame number.

From the programmer's perspective, memory is one giant contiguous block, completely independent of the physical memory and hardware underneath.

## Protection

A process cannot name or address another process's memory, since every access goes through its own page table. That is the isolation boundary between processes.

Marking the first page invalid turns NULL pointer dereferences into exceptions.

## Address translation

- The page table provides a layer of indirection.
- A virtual address divides into a **virtual page number (VPN)**, which indexes the page table, and an **offset**.
- The page table entry (PTE) contains the frame number.
- The physical address is the frame number concatenated with the offset.

The OS manages page tables and stores them in memory. There is one PTE per page, i.e. one per VPN. Each process has its own page table, and the PTBR points at the running process's table.

## Shared frames

Multiple processes can map the same frame. Shared libraries and shared memory between processes use this. It also underlies **copy-on-write (COW)**, which makes things like read-only fork and exec cheap.

## Page table entries

Beyond the frame number, PTEs carry:

- **valid bit**: set when the page is in memory, cleared when it isn't. An access to an invalid page causes a page fault.
- **referenced bit**: set by hardware when the page is read or written, cleared by the OS. Used to approximate LRU replacement.
- **dirty/modified bit**: set by hardware when the page is written, cleared by the OS. Used for COW and to skip writeback of clean pages.
- **protection bits**: read/write/execute permissions, enforced in hardware.

## What paging buys and costs

Physical allocation gets easy: grab a frame off the free list (usually a linked list). External fragmentation disappears, since every unit is the same fixed size. And paging leads naturally to virtual memory, because pages can swap in and out and a program doesn't need to be fully resident to run.

The costs: internal fragmentation remains when a page is only partly used. Every memory access also touches the page table, which a TLB mitigates. And the page table itself can get large. One PTE per page in a 32-bit address space with 4 KB pages is $2^{20}$ PTEs, about 4 MB at 4 bytes per PTE. Multi-level page tables fix this; see [[systems/operating-systems/lecture-notes/page-faults|page faults]].

## Paged virtual memory

- The full used address space lives on secondary storage (disk) in page-sized blocks.
- The OS uses main memory as a cache for the disk.
- When a page is needed, it gets transferred into a free page frame.
- With no free frames, the OS must evict a page. A dirty page gets written to disk first; a clean page can just be discarded.
- All of it is transparent to the application.

## Page faults

When the OS evicts a page, it marks the PTE invalid and records the page's disk location in a separate data structure. A later access to that page throws an exception, and after trapping into the kernel the OS runs the page fault handler, which looks up the page on disk, reads it into a free frame, updates the page table, and restarts the instruction that faulted. Details in [[systems/operating-systems/lecture-notes/page-faults|page faults]].

### Hard vs soft page faults

- **Hard page fault**: the page is not in memory, and the OS must read it from disk or other backing storage.
- **Soft page fault**: the page is actually still in memory, so the OS can map it back in without touching backing storage.

## Demand paging

Pages come into main memory only when they are referenced, so only the code and data that actually get used take up memory. Few systems try to anticipate which pages will be needed. Clustering is common though. The OS keeps track of pages that come and go together and brings in the whole cluster when one of them is referenced, and some interfaces let the programmer or compiler specify the clusters.

## Page replacement

Reading in a page either uses an existing free frame or evicts something. Good eviction targets are pages that won't be used for a while and pages that haven't been modified, since clean pages don't need to be written back. The OS typically keeps a pool of free pages so allocations don't have to evict, and tries to keep clean pages around for cheap eviction.

### Belady's optimal algorithm

Replace the page that will not be used for the longest time in the future. Impossible to implement in practice, but useful as a yardstick for other algorithms.

### FIFO

Replace the page that has been in memory the longest. Simple to implement. It also suffers from **Belady's anomaly**: increasing the number of frames can increase the number of page faults.

### LRU

Replace the page that has not been used for the longest time. Doing this exactly requires recording the time of the last reference to every page on every access, which costs too much, so systems approximate it.

### Approximate LRU

Keep a counter for each page. At some regular interval, for each page:

- if the reference bit is 0, increment the counter
- if the reference bit is 1, zero the counter
- zero the reference bit

The counter then holds the number of intervals since the last reference to the page, and the page with the largest counter is the least recently used.

### LRU clock

Keep the pages in a circular list, each with a reference bit that gets set when the page is referenced. To evict, sweep a clock hand around the list. A page with its bit set gets the bit cleared and the hand moves on; a page with its bit clear gets evicted. Overhead is low when memory is plentiful. As memory grows the accuracy drops, and multiple hands can compensate.

## Loading a program

- Create the descriptor / process control block (PCB).
- Create the page table.
- Put the address space image on disk in page-sized blocks.
- Build the page table with every PTE valid bit set to 0, and record each page's disk location in a separate data structure.
- When the process starts executing, point the PTBR at its page table.

Demand paging pulls the pages in from there.

## Locality

- **Temporal locality**: a memory location accessed now is likely to be accessed again soon.
- **Spatial locality**: locations near an accessed location are likely to be accessed soon.

Locality is why paging can be infrequent and why the OS can profitably bring in multiple pages at once. It assumes that a page brought in gets used many times, and that on average you use the pages you bring in.

## Local vs global replacement

Local replacement means each process evicts only from its own set of pages. Global replacement lets the OS evict any page, regardless of which process owns it. Linux replaces globally.

Global replacement is typically implemented with a shared pool of free pages, and it lets the OS put memory where it does the most good, which can reduce the total number of page faults.

## Working set model

Denning's working set model defines:

- $t$: time
- $w$: the working set window, measured in page references

A page is in the working set only if it was referenced in the last $w$ references:

$$
WS(t,w) = \{\text{pages } P \text{ such that } P \text{ was referenced in the interval } (t-w, t]\}
$$

$|WS(t, w)|$ is the number of pages in the working set at time $t$, and it varies over time. During a stretch of particularly bad locality, the working set can get very large.

The goal is to reduce page faults by keeping each process's working set in memory. **Thrashing** is when a process spends more time paging than executing, and keeping working sets resident is the defense against it.

## Related notes

- [[systems/operating-systems/lecture-notes/page-faults|page faults]]
- [[systems/operating-systems/lecture-notes/tlb|translation lookaside buffers]]
- [[systems/operating-systems/lecture-notes/windows-memory-management|Windows memory management]]
