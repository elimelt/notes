# Virtual Memory and Paging

Use pages to map virtual memory to physical memory. This prevents **external fragmentation** by dividing memory into fixed-size pages, and **internal fragmentation** by making the units of allocation smaller.

### Fragmentation

- **external fragmentation**: when free memory is broken into small pieces, but the memory is not being used because it is not contiguous.
- **internal fragmentation**: when a process is allocated more memory than it needs, and the extra memory is not being used.

Virtual address space is divided into *pages*, and physical address space is divided into *frames*. The page table maps pages to frames. The page table is stored in memory, and the page table base register (PTBR) points to the page table. The page table is indexed by the page number, and the value at that index is the frame number.

From the programmers perspective, memory is a giant contiguous block, completely independent of the physical memory and hardware.

### Protection

One processes cannot "name" or address the memory of another process. This provides protection between processes.

Set the first page to be invalid so that if a process tries to access it (NULL pointer), it will cause an exception.

### Address Translation

- Page table provides layer of indirection
- Virtual address is divided into **virtual page number (vpn)**, which is an index into the page table, and **offset**
- The page table entry (PTE) contains the frame number
- The physical address is the frame number concatenated with the offset

Page tables are managed by the operating system, and are stored in memory. There is one PTE for each page, ie one PTE per VPN. The page table maps VPNs to PFNs.

### Shared Frames

Multiple processes can share the same frame. This is useful for shared libraries, and for shared memory between processes. Can also be used when implementing **copy-on-write (COW)** to optimize things like read-only fork, or exec.

### Page Table Entries

More functionality to the PTEs:

- Protection by setting read/write/execute bits
- Page table entry can point to nothing, causing a page fault
- Accounting information for if the PTE is used, dirty bit, reference bit, etc.

- **valid bit**: if the page is in memory. set when the page is in memory, cleared when the page is not in memory. Used for page faults.
- **referenced bit**: if the page has been referenced before. set when page is read or written to. cleared by the OS but set by the hardware. Used for LRU replacement.
- **dirty/modified bit**: page has been modified. set when page is written to. cleared by the OS but set by the hardware. Used for COW.
- **protection bits**: read/write/execute permissions

More out there.


https://calendar.google.com/calendar/u/1/r?cid=cs.washington.edu_kaujd7jilnokn62oukhdms0n8c%40group.calendar.google.com&authuser=3

https://mailman.cs.washington.edu/mailman/listinfo/uw-networks

https://mailman.cs.washington.edu/mailman/listinfo/uw-systems