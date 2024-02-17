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

#### More functionality to the PTEs:

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

### Page Replacement

- When you read in a page, you either use an existing free frame, or you evict a page.

#### Page Replacement Algorithms

- pick one that won't be used for a while
- pick one that hasn't been modified (so we don't have to write it to disk)
- OS typically keeps a pool of free pages so that allocations don't need to evict.
- OS also tries to keep clean pages around so that they can be evicted without writing to disk.

##### Belady's Optimal Algorithm

- Replace the page that will not be used for the longest time in the future
- Impossible to implement in practice, but useful for comparing other algorithms

##### FIFO

- Replace the page that has been in memory the longest
- Simple to implement, but not always the best
- Can cause **Belady's Anomaly**: increasing the number of frames can increase the number of page faults

##### LRU

- Replace the page that has not been used for the longest time
- Requires keeping track of the time of the last reference for each page

##### Approximate LRU

- Keep counter for each page
- At some regular interval, for each page:
    - if ref bit == 1, increment counter
    - if ref bit == 0, zero counter
    - zero ref bit
- counter contains the number of intervals since the last reference to the page. page with the largest counter is least recently used

##### LRU Clock

- Keep a circular list of pages
- Each page has a reference bit
- When a page is referenced, set the reference bit to 1
- When a page is evicted, if the reference bit is 1, set it to 0 and move to the next page. If the reference bit is 0, evict the page
- Essentially a clock hand that moves around the list, and evicts the page that the hand is pointing to
- Low overhead if plenty of memory
- As memory increases, accuracy decreases. Can use multiple hands to increase accuracy.

### How do you load a program?

- Create descriptor/process control block (PCB)
- Create page table
- Put address space image on disk in page-sized blocks
- Build page table
    - All PTE valid bits set to 0
    - Some data structure stores disk location of each page
    - When process starts executing, the OS sets the PTBR to point to the page table

### Locality

- **Temporal locality**: if a memory location is accessed, it is likely to be accessed again soon
- **Spatial locality**: if a memory location is accessed, it is likely that nearby memory locations will be accessed soon

Locality means paging can be infrequent, and the OS can bring in multiple pages at once. This assumes that:

- Once you bring in a page, you will use it many times
- On average, you will use the pages you bring in



### Local vs Global Page Replacement

Local page replacement means that each process has its own set of pages that it is replacing. Global page replacement means that the OS can choose any page to replace, regardless of which process it belongs to. Linux uses global page replacement.

This is typically implemented by keeping a pool of free pages, and when a page is needed, the OS can choose any page to evict. This is useful because it allows the OS to make better decisions about which pages to evict, and can reduce the number of page faults.

#### Working Set Model

- $t$: time
- $w$: working set window (measured in page refs)
- a page is in the working set (WS) only if it was referenced in the
last w references

$$
WS(t,w) = \{\text{pages P such that P was referenced in the time
interval } (t, t-w)\}
$$

$|WT(t, w)|$ is the number of pages in the working set at time $t$, and varies with time. During a time interval with particularly bad locality, the working set can be very large.

- The working set of a process is the set of pages that the process is currently using
- The working set window is the number of page references that are considered to be in the working set.
- Typically, the working set is the set of pages that have been referenced in the last $n$ references, where $n$ is the working set window.

The goal is to reduce page faults by keeping the working set in memory. **Thrashing** is when a process is spending more time paging than executing, and keeping the working set in memory can help prevent thrashing.

### Hard vs Soft Page Faults

- **Hard page fault**: when a page is not in memory, and the OS must read it from disk/backend storage
- **Soft page fault**: when a page is not in memory, but the OS can find it in the page file, and bring it into memory without reading from the backend storage