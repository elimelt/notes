---
title: Caches, Virtual Memory, and Memory Systems
aliases:
  - hardware/computer-architecture/caches-virtual-memory
category: Computer Architecture
tags:
  - cache
  - tlb
  - virtual-memory
  - page-tables
  - prefetching
  - mlp
  - dram
  - memory-controller
  - memory-hierarchy
date: 2026-08-01
status: draft
description: A load-to-DRAM model of the memory system - cache indexing and replacement, MSHRs and nonblocking misses, TLB and page-walk mechanics, prefetching, and DRAM row buffers, grounded in Rocket Chip source and the repo's own benchmark measurements.
sources:
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
  - title: "rocket-chip: TLB.scala"
    url: https://github.com/chipsalliance/rocket-chip/blob/master/src/main/scala/rocket/TLB.scala
    type: source
  - title: "rocket-chip: NBDcache.scala (MSHR, MSHRFile)"
    url: https://github.com/chipsalliance/rocket-chip/blob/master/src/main/scala/rocket/NBDcache.scala
    type: source
---

## Purpose

Trace what happens between `int x = array[i]` and the value landing in a register: cache indexing and replacement, what a miss costs, how many misses a core can have outstanding at once, how a virtual address becomes a physical one, and why DRAM latency is not one number. Each mechanism below is tied to a real measurement already in this repo or to a real hardware implementation, not to a textbook diagram.

## Core idea: an address is three fields

A physical address splits into **tag**, **index**, and **offset**. For a cache with $2^s$ sets, $B$-byte lines, and associativity $A$:

- **offset** ($\log_2 B$ bits): which byte within the line.
- **index** ($s$ bits): which set. Only the index picks the set; the tag disambiguates which of the $A$ lines in that set holds the data.
- **tag** (remaining bits): compared against every way in the indexed set in parallel.

Associativity is a trade: direct-mapped ($A=1$) is fast and simple but two addresses that alias to the same index thrash each other out; fully associative ($A = $ number of lines) never thrashes on index collisions but needs a comparator per line. Real L1s split the difference at 4- to 8-way set associative.

**Write policy** is a separate axis from associativity. *Write-back* caches dirty data locally and write it out only on eviction; *write-through* pushes every store to the next level immediately. *Write-allocate* pulls a line into cache on a write miss before writing it (paired with write-back, since you'll write the freshly dirtied line again soon); *no-write-allocate* writes straight through to the next level on a miss and leaves nothing cached. Rocket's L1 data cache is write-back with write-allocate for cacheable addresses, visible in the `MSHR` state machine below, which drives an `AcquireBlock` (fetch-for-ownership) on a tag miss.

## MSHRs and non-blocking misses

A blocking cache stalls the whole pipeline on any miss. A **non-blocking cache** tracks each in-flight miss in a **Miss Status Holding Register (MSHR)** and keeps issuing new requests underneath older misses that haven't returned yet. The MSHR count is a hard ceiling on memory-level parallelism (MLP): once every MSHR is occupied, the next miss stalls no matter how many outstanding requests the memory system could otherwise absorb.

Rocket's `MSHRFile` allocates one `MSHR` module per outstanding block miss and arbitrates their `TLBundleA` requests onto the outer memory bus:

<augment_code_snippet path="rocket-chip: src/main/scala/rocket/NBDcache.scala" mode="EXCERPT">
````scala
class MSHR(id: Int)(implicit edge: TLEdgeOut, p: Parameters) extends L1HellaCacheModule()(p) {
  val s_invalid :: s_wb_req :: s_wb_resp :: s_meta_clear ::
      s_refill_req :: s_refill_resp :: s_meta_write_req ::
      s_meta_write_resp :: s_drain_rpq :: Nil = Enum(9)
  val sec_rdy = idx_match && (state.isOneOf(states_before_refill) ||
    (state.isOneOf(s_refill_req, s_refill_resp) && !cmd_requires_second_acquire && !refill_done))
````
</augment_code_snippet>

Two things stand out. First, `sec_rdy` is a *secondary miss* check: a second request to the same in-flight block does not allocate a new MSHR, it queues onto the existing one (`rpq`, the replay queue) and is satisfied when the first miss returns. This is why hitting the same cache line repeatedly while it is still being fetched is nearly free. Second, `MSHRFile` arbitrates all MSHRs' outgoing requests with `TLArbiter.lowestFromSeq`, so the number of *simultaneously outstanding, distinct* block misses is bounded by `cfg.nMSHRs`, a build-time parameter.

This ceiling is directly measurable. [[systems/operating-systems/benchmarks/mlp|the MLP benchmark]] runs $N$ independent pointer chases and finds throughput scaling almost linearly up to 8 chains (92.6 ns/access at 1 chain down to 15.6 ns at 8, a 5.9x speedup) but only reaching 10.4x at 16 chains, converging to the same ~7-8 ns/access floor as fully-independent random access. That floor is the point where MSHR capacity, memory-controller queue depth, and DRAM bank-conflict probability jointly saturate — adding more independent misses stops helping because there's nowhere left in the pipeline to hold them.

## Address translation

A **TLB** caches virtual-to-physical translations so most loads skip the page table. Rocket's `TLB` module encodes the lookup as three separate structures rather than one flat array: a set-associative array for normal 4 KB pages (with *sectored* entries, where several adjacent PTEs share one tag to amortize tag storage), a small fully-associative array just for superpages, and (when PMP granularity is finer than a page) one dedicated entry for the sub-page permission checker:

<augment_code_snippet path="rocket-chip: src/main/scala/rocket/TLB.scala" mode="EXCERPT">
````scala
val sectored_entries = Reg(Vec(cfg.nSets, Vec(cfg.nWays / cfg.nSectors,
  new TLBEntry(cfg.nSectors, false, false))))
val superpage_entries = Reg(Vec(cfg.nSuperpageEntries, new TLBEntry(1, true, true)))
val s_ready :: s_request :: s_wait :: s_wait_invalidate :: Nil = Enum(4)
````
</augment_code_snippet>

On a miss the TLB moves `s_ready -> s_request -> s_wait`, sending the faulting VPN to the page-table walker (PTW, RISC-V's hardware page walker) and stalling the requesting pipeline until `io.ptw.resp` fires. `SFENCE.VMA` is handled as its own transient path (`s_wait_invalidate`) because a fence arriving mid-refill has to invalidate the entry that's about to land rather than let it commit stale.

[[systems/operating-systems/benchmarks/tlb|The TLB benchmark]] isolates the walk cost directly by sweeping access stride over a 256 MB array so every access falls on a fresh page once stride reaches 4 KB:

| Stride | Accesses/page | ns/access | Cache behavior | TLB behavior |
|--------|---------------|-----------|-----------------|--------------|
| 64 B | 64 | 2.49 ns | miss (new line) | hit |
| 512 B | 8 | 5.38 ns | miss | hit |
| 4 KB | 1 | 12.51 ns | miss | miss |

Both 512 B and 4 KB strides miss the data cache on every access, so the jump from 5.38 ns to 12.51 ns isolates the page-walk cost at roughly 7 ns. A 4-level x86-64 walk is up to four dependent loads (PML4 → PDPT → PD → PT), which would cost several DRAM round trips in the worst case; the measured 7 ns instead reflects that the upper page-table levels are themselves small and hot, cached in the same hierarchy as data, so a linear scan's walk usually only misses on the leaf PTE. Huge pages attack the same cost from the other side: a 2 MB page covers 512x the address range per TLB entry, so a workload with this access pattern would keep hitting the TLB until its footprint passed (TLB entries) x 2 MB instead of x 4 KB.

## AMAT and where the average lies

**Average Memory Access Time** is the standard first-order model:

$$\text{AMAT} = t_{L1} + m_{L1}\left(t_{L2} + m_{L2}\left(t_{L3} + m_{L3} \cdot t_{DRAM}\right)\right)$$

where $t_i$ is the hit time at level $i$ and $m_i$ is the miss rate *given a lookup reaches that level*. Plugging in this repo's measured single-machine numbers ([[systems/operating-systems/benchmarks/README|DRAM latency benchmark]]: L1 ~2 ns, L2 ~15 ns, L3 ~30 ns, DRAM ~97 ns for the pointer-chase floor) with illustrative miss rates $m_{L1}=0.05$, $m_{L2}=0.3$, $m_{L3}=0.5$:

$$\text{AMAT} = 2 + 0.05\left(15 + 0.3\left(30 + 0.5 \cdot 97\right)\right) = 2 + 0.05(15 + 23.55) = 3.93 \text{ ns}$$

AMAT assumes each miss is served serially and that its cost is a fixed constant — both assumptions the repo's own benchmarks falsify. The [[systems/operating-systems/benchmarks/README|DRAM latency note]] shows sequential access at 1.35 ns/access next to *pointer-chase* access at 97.4 ns/access, despite both eventually reaching DRAM on a large array: the hardware prefetcher detects the stride-1 pattern and turns nearly every access into a hit before AMAT's "miss cost" term would ever apply. And the [[systems/operating-systems/benchmarks/mlp|MLP benchmark]] shows that even genuine DRAM misses aren't independent, fixed-latency events once several are outstanding — 8 concurrent chains pay 15.6 ns/access, not 8x92.6 ns. AMAT is a useful single-thread, single-request accounting identity; it silently assumes away both prefetching and miss-level parallelism, which is exactly what determines real throughput on any core built after about 1995.

## DRAM: row buffers and why access has two costs

DRAM cells sit in a 2D array; each access opens a **row** (activating a word line, dumping the whole row's charge onto sense amplifiers that latch it into the **row buffer**, on the order of 1-8 KB) and then reads a **column** out of that buffer. A **row-buffer hit** — a second access to an already-open row — only pays the column access, ~10-15 ns in the [[systems/operating-systems/benchmarks/README|DRAM benchmark]]'s numbers. A **row-buffer miss** pays precharge (~15 ns) to close the old row, activation (~15 ns) to open the new one, then the column access, landing around 40-50 ns. Random pointer-chasing hits a mix of both and the measured 97.4 ns average sits above even the row-miss estimate, which the note attributes to memory-controller queueing and the specific pattern denying the controller any chance to schedule for row locality. Memory controllers exploit this by reordering requests to cluster same-row accesses (row-buffer scheduling) — the [[systems/operating-systems/benchmarks/bandwidth|bandwidth benchmark]]'s scaling from 24.9 GB/s at one thread to 63.7 GB/s at eight is partly this effect: more outstanding requests give the controller more opportunities to find row-buffer locality it couldn't see from a single stream.

## Prefetching: covering latency you can predict

Hardware prefetchers detect sequential and constant-stride access and fetch ahead speculatively; they do nothing for pointer chases because the next address doesn't exist until the current load returns. [[systems/operating-systems/benchmarks/prefetch|The prefetch benchmark]] shows software prefetch distance mattering even when the hardware prefetcher is already active on sequential access: an explicit `__builtin_prefetch` 64 elements ahead beats the hardware-only baseline 2.5x (0.54 ns vs 1.37 ns/access), because the hardware prefetcher stays conservative about run-ahead distance to avoid cache pollution on patterns it hasn't confirmed, while software with known future indices can fetch aggressively. For random access with computable future indices the win is smaller (about 1.3x) because the baseline is already close to bandwidth-bound from MLP — once bandwidth, not per-request latency, is the limit, prefetching can only reorder when requests land, not reduce their number.

## Edge cases and limits

- **Sectored TLB entries and superpages create ambiguity, not just capacity pressure.** Rocket's `TLB.hit` explicitly checks for `multipleHits` (two entries matching the same VPN, possible when a superpage and a regular mapping overlap) and flushes the whole TLB rather than picking one, since picking wrong would be a silent correctness bug.
- **AMAT breaks down whenever accesses aren't independent identically-costed events** — it has no term for prefetch coverage, MSHR-limited concurrency, or row-buffer state, all three of which this repo has separately measured swings of 2-70x from.
- **Write-allocate amplifies the cost of write-only workloads** that never re-read the line: pulling the whole block in on a write miss wastes the fetch if nothing downstream ever reads it. No-write-allocate is the right policy exactly there, and mixed policies (write-allocate for the data cache, no-write-allocate for streaming stores) exist for this reason.

## Sources

- [What Every Programmer Should Know About Memory (Drepper)](https://www.akkadia.org/drepper/cpumemory.pdf)
- [rocket-chip: TLB.scala](https://github.com/chipsalliance/rocket-chip/blob/master/src/main/scala/rocket/TLB.scala)
- [rocket-chip: NBDcache.scala](https://github.com/chipsalliance/rocket-chip/blob/master/src/main/scala/rocket/NBDcache.scala)

## Related notes

- [[systems/operating-systems/benchmarks/README|measuring real DRAM latency]]
- [[systems/operating-systems/benchmarks/mlp|memory-level parallelism]]
- [[systems/operating-systems/benchmarks/tlb|TLB and page walk benchmarks]]
- [[systems/operating-systems/benchmarks/prefetch|software prefetching benchmarks]]
- [[systems/operating-systems/benchmarks/bandwidth|memory bandwidth benchmarks]]
- [[systems/operating-systems/lecture-notes/paging|virtual memory and paging]]
- [[systems/operating-systems/lecture-notes/tlb|TLB (lecture notes)]]
- [[hardware/computer-architecture/multiprocessors-cache-coherence|multiprocessors, cache coherence, and memory consistency]]
