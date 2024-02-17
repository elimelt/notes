# Page Fautls

## How does the OS handle a page fault?

On fault, an interrupt causes the CPU to jump to the page fault handler:

- find or create (evict another page) a page frame to load the new page into
- read it in. if I/O needed, start I/O and let another process run
- fix up PTE by marking it as "valid", set "referenced" and "modified" bits to false, set protection bits appropriately, point to correct page frame
- add process to ready queue

### Finding the page on disk

- processor makes process ID and faulting virtual address available to page fault handler
- process ID gets you to the base of the page table
- VPN portion of VA gets you to the PTE
- data structure analogous to page table (an array with an entry for each page in the address space) contains disk address of page
- at this point, it's just a simple matter of I/O
- must be positive that the target page frame remains available!

### Find or create a page frame

- run page replacement algorithm
- free page frame
- assigned but unmodified ("clean") page frame
- assigned and modified ("dirty") page frame
- assigned but "clean"
  - find PTE (may be a different process!)
  - mark as invalid (disk address must be available for subsequent reload)
- assigned and "dirty"
    - find PTE (may be a different process!)
    - mark as invalid
    - write it out
- OS may speculatively maintain lists of clean and dirty frames selected for replacement
    - May also speculatively clean the dirty pages (by writing them to
disk)


## Issues with Page Faults

### Memory reference overhead

There are 2 references to memory for every memory access: one to the page table, and one to the actual memory. This can be mitigated by using a TLB (Translation Lookaside Buffer), which is essentially a cache for the page table.

### Memory required to hold a page table can be large

- need one PTE per page in the virtual address space
- 32 bit AS with 4KB pages = 220 PTEs = 1,048,576 PTEs. 4 bytes/PTE = 4MB per page table
    - OS's typically have separate page tables per process
    - 25 processes = 100MB of page tables
- 48 bit AS, same assumptions, 64GB per page table!

#### Old Solution: Paging the page table

Can be solved by paging the page table! (ie. have a page table for the page table). Keep the "system" page table in physical memory, and the "user" page table in virtual memory. This is no longer done in practice.

#### New Solution: Multi-level page tables

Simply add another level of indirection. Instead of having a single page table, have a page table of page tables. This works well because the page table is sparsely populated in practice, so it is a waste to have a PTE mapped for every page in the address space.

**This is the solution used in modern operating systems.**

##### Two-level page table

- VA has 3 parts:
    - master page number, secondary page number, offset
- master PT maps master PN to secondary PT
- secondary PT maps secondary PN to page frame number
- offset and PFN yield physical address

#### Other Alternatives

- Hashed page tables
    - VPN used as a hash
    - collision resolved because elements in linked list at the hash index include the VPN as well as the PFN
- Inverted page tables (really reduces space)
    - one entry per page frame
    - includes the VPN and the PID of the process
    - hard to search (but IBM PC/RT actually did it)