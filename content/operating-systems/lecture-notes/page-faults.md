---
title: How the Operating System Handles Page Faults
category: Operating Systems
tags:
  - page-faults
  - virtual-memory
  - page-replacement
  - page-tables
  - multi-level-page-tables
date: 2024-02-16
updated: 2026-07-30
status: evergreen
description: What the page fault handler does step by step (locating the page on disk, finding or evicting a frame, fixing the PTE), and the two big costs of paging, extra memory references and page table size, with multi-level page tables as the fix.
sources:
  - title: Operating systems course lecture notes
    type: lecture
---

This note walks through what the OS does when a page fault fires, then covers the two big costs paging introduces, extra memory references and page table size, and the structures that mitigate them.

## Handling a page fault

On a fault, an interrupt drops the CPU into the page fault handler, which:

- finds a page frame to load the new page into, evicting another page if it has to
- reads the page in; if I/O is needed, it starts the I/O and lets another process run
- fixes up the PTE: marks it valid, clears the referenced and modified bits, sets the protection bits appropriately, and points it at the page frame
- puts the process back on the ready queue

### Finding the page on disk

- the processor makes the process ID and the faulting virtual address available to the page fault handler
- the process ID gets you to the base of the page table
- the VPN portion of the virtual address gets you to the PTE
- a data structure analogous to the page table (an array with one entry per page in the address space) holds each page's disk address
- from there it's just a matter of I/O
- the target page frame must stay available for the whole operation

### Finding or creating a page frame

Run the page replacement algorithm. The candidate frame is either free, assigned but unmodified ("clean"), or assigned and modified ("dirty").

- Free: use it directly.
- Assigned and clean: find the PTE, which may belong to a different process, and mark it invalid. The disk address must stay available so the page can be reloaded later.
- Assigned and dirty: find the PTE (again, possibly another process's), mark it invalid, and write the page out.

The OS may speculatively maintain lists of clean and dirty frames selected for replacement, and may speculatively clean the dirty ones by writing them to disk ahead of time.

## Costs of paging

### Memory reference overhead

Every memory access becomes two references: one to the page table and one to the actual memory. A TLB, which is a hardware cache of page table entries, absorbs most of the page table lookups. See [[operating-systems/lecture-notes/tlb|translation lookaside buffers]].

### Page table size

You need one PTE per page of virtual address space. Work it out for a 32-bit address space with 4 KB pages and 4-byte PTEs:

$$
\frac{2^{32}}{2^{12}} = 2^{20} \text{ PTEs}, \qquad 2^{20} \times 4 \text{ B} = 4 \text{ MB per page table}
$$

Operating systems typically keep a separate page table per process, so 25 processes cost 100 MB in page tables. Stretch the address space to 48 bits with the same page and PTE sizes and a flat table needs $2^{36}$ PTEs, which is $2^{38}$ bytes, 256 GB per process.

#### Old solution: page the page table

Keep the "system" page table in physical memory and the "user" page table in virtual memory, so the page table itself can page out. This is no longer done in practice.

#### Current solution: multi-level page tables

Add another level of indirection, a page table of page tables. This works because address spaces are sparsely populated in practice, so a flat table wastes a PTE on every unmapped page while a multi-level table only materializes the pieces that are actually used. Modern operating systems use this.

##### Two-level page tables

The virtual address splits into three parts: a master page number, a secondary page number, and an offset. The master page table maps the master page number to a secondary page table. The secondary page table maps the secondary page number to a page frame number. The PFN plus the offset yields the physical address.

#### Other alternatives

- Hashed page tables. The VPN is used as a hash, and collisions resolve through a linked list at the hash index whose elements carry the VPN along with the PFN.
- Inverted page tables. One entry per page frame, holding the VPN and the PID of the owning process. This really cuts the space down, but searching is hard. The IBM PC/RT actually did it.

## Related notes

- [[operating-systems/lecture-notes/paging|paging]]
- [[operating-systems/lecture-notes/tlb|translation lookaside buffers]]
