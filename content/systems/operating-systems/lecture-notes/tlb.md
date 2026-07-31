---
title: Translation Lookaside Buffer (TLB)
aliases:
  - operating-systems/lecture-notes/tlb
category: Operating Systems
tags:
  - virtual-memory
  - paging
  - address-translation
  - tlb
  - mmu
  - page-tables
  - context-switch
date: 2024-02-16
updated: 2026-07-30
status: evergreen
description: How the TLB caches virtual-to-physical translations, hardware vs software miss handling, why context switches flush it, and the tricks page tables enable, shared libraries, memory-mapped files, and soft faults.
sources:
  - title: Operating systems course lecture notes
    type: lecture
---

The TLB caches translations from virtual page numbers to physical page numbers so that most memory accesses never touch the page table. It is a small hardware cache of page table entries, and it exists because paging otherwise turns every memory access into two.

## Mapping

The usual cache design space applies:

- **Direct mapped**: each virtual page number can live in exactly one TLB slot. Simplest and fastest to look up, and the most prone to conflicts.
- **Fully associative**: a translation can live in any slot, and the hardware searches every slot in parallel on each access. Most flexible, hardest to build big.
- **N-way set associative**: the compromise. The TLB divides into sets, and a translation can live in any slot within its set.

TLBs hold few entries compared to data caches, and misses cost a page table walk, so real TLBs tend toward full or high associativity.

## Managing the TLB

The TLB handles almost all address translations, and the page table only sees the misses. On a miss, the translation comes from the page table and gets inserted into the TLB, usually evicting some other entry.

Who handles the miss splits two ways:

- Hardware, via the MMU, as on x86. The hardware knows where the page table sits in memory and walks it itself. The OS maintains the page table, and it must keep it in the hardware-defined format.
- Software-loaded TLBs, where the OS does it. A TLB miss traps to the OS like a page fault. The OS finds the page table entry, loads it into the TLB, and restarts the instruction that missed. The handler has to be very fast since it runs on every miss, so the CPU's ISA includes special instructions for loading TLB entries.

### Context switching

The OS has to keep the TLB and the page table consistent, so when the page table changes it invalidates the affected TLB entries. When a process is switched in, the OS must invalidate or flush the entire TLB, and the flood of misses that follows is a big part of context switch overhead. Including the PID in the TLB lookup avoids the flush by making the TLB safely shared between processes.

## Functionality built on page tables

- **Memory protection**: each PTE carries protection bits specifying access rights for the page, so violations get caught at the hardware level, which is much faster than catching them in software.
- **Shared memory**: multiple processes can map the same physical page. Shared libraries and shared memory use this, and copy-on-write builds on it.

### Loading shared libraries

The OS loads a shared library once and maps the same physical pages into the address space of every process that uses it, transparently to the user. The library doesn't have to land at the same virtual address in every process, but the OS tries to make that happen, and as a rule of thumb each library has a preferred virtual address location, which makes loading easier. After a while there may not be room to give every library its preferred spot, so libraries need to be dynamically relocatable.

### Memory-mapped files

Forget reads and writes; map the file into the address space instead. A store to a mapped address becomes a write to the file. Depending on the OS and the caching policy (write-through vs write-back), the file gets updated immediately or later. Many applications use this because it is an efficient way to read and write files.

#### Soft page faults

A soft fault is a fault on a page that is actually in memory, with the PTE deliberately marked invalid. Resolving one is cheap since no disk I/O is involved. It works anywhere you want the OS woken up when a page gets referenced, a debugger watchpoint for instance. Windows uses soft faults in its page replacement strategy; see [[systems/operating-systems/lecture-notes/windows-memory-management|Windows memory management]].

## Related notes

- [[systems/operating-systems/lecture-notes/paging|paging]]
- [[systems/operating-systems/lecture-notes/page-faults|page faults]]
- [[systems/operating-systems/benchmarks/tlb|TLB benchmarks]]
