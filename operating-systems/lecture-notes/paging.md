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

Page tables are managed by the operating system, and are stored in memory. There is one PTE for each page, ie one PTE per VPN. The page table maps VPNs to PFNs. Each process has its own page table, and the PTBR points to the page table.

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

#### Advantages of Paging

- Easy to allocate physical memory. Allocated from a free list (linked usually) of frames. To allocate, remove
- External fragmentation is eliminated. Pages are fixed size, so no fragmentation.
- Leads naturally to virual memory. Pages can be swapped in and out of memory, and don't need to be entirely in physical memory for a program to run.

#### Disadvantages of Paging

- Can still have internal fragmentation. If a page is not entirely used, there is wasted space.
- Overhead of managing the page table. Page table is stored in memory, and is accessed for every memory access. This can be mitigated by using a TLB (essentially a cache).
- Memory required to hold a page table can be large. Need one PTE/page, and if the page size is small, the page table can be large. ie 32 bit AS with 4 KB pages = $2^20$ PTEs = $1,048,576$ PTEs = 4 MB (using 4 bytes/page). Solution: page the page table.

### Paged Virtual Memory

- The full (used) address space exists on secondary storage (disk) in page-sized blocks
- OS uses main memory as a cache for the disk
- When a page is needed, it is transferred to a free page frame
- If there are no free page frames, the OS must choose a page to evict. If the evicted page is dirty, it must be written to disk. Otherwise, it can just be discarded.
- All transparent to the application/user

### Page Faults

- When a page is evicted, the OS sets the PTE to invalid and records the disk location of the page into a seperate data structure.
- When a process tries to access the now invalid page, an exception is thrown (page fault).
    - After trapping into the kernel on exception, the OS runs the page fault handler
    - The OS looks up the page on disk, and reads it into a free frame
    - The OS updates the page table to point to the new frame
    - The OS restarts the instruction that caused the page fault

### Demand Paging

- Pages are only brought into main memory when they are referenced.
    - only the code/data that is actually used is brought into memory
- Few systems try to anticipate what pages will be used, and instead just bring in pages as they are used
- However, not uncommon to cluster pages that are likely to be used together (ie. code and data pages)
    - OS keeps track of pages that come and go together
    - bring in all pages in the cluster when one is referenced
    - interface may allow programmer or compiler to specify clusters
