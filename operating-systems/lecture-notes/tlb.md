# Translation Lookaside Buffer (TLB)

Translates virtual page numbers to physical page numbers. It is a small, fully associative cache of page table entries implemented in hardware to improve the speed of address translation and decrease the number of memory accesses.

## Associative and Direct Mapping

- **Direct Mapping**: Each entry in the TLB corresponds to a unique entry in the page table. This is the simplest and most common implementation of the TLB. It is also the fastest, but it is also the most limited in terms of the number of entries it can hold.
- **Fully Associative**: Each entry in the TLB can correspond to any entry in the page table. This is the most flexible, but also the slowest. It means that the TLB must be searched for every memory access.
- **N-way Set Associative**: A compromise between the two. The TLB is divided into a number of sets, and each entry in the TLB can correspond to any entry in the page table within its set.

## Managing TLBs

- Address translation mostly handled by TLB
    - Over 99% of address translations are handled by the TLB, but the remaining 1% are handled by the page table.
    - In case of a miss, translation is done by the page table and the result is stored in the TLB. Often this results in an eviction.
- Hardware (MMU) in x86 systems
    - Knows where oage table is in memory. OS maintains page table, but hardware does the translation and accesses the page table.
    - Page table is stored in a hardware-depended format, and the OS must maintain it in this format.
- Software loaded TLB (OS)
    - TLB miss is handled like a page fault (trap to OS)
    - OS finds the page table entry, loads it into the TLB, and restarts the instruction that caused the miss.
    - Must be very fast (20-1000 cycles), so CPU ISA has special instructions to load TLB entries.

### Context Switching

The OS **needs** to ensure TLB and page table are consistent. This is done by invalidating the TLB when the page table changes. When a process is switched, the OS must invalidate/flush the entire TLB, which is a big part of the overhead of context switching (since there will be many TLB misses subsequently). You can also use the PID as part of the TLB lookup to make the TLB "global" (ie. shared between processes). 

## Functionality Enhanced by Page Tables

- **Memory Protection**: Each page table entry has a protection bit that specifies the access rights for the page. This is used to prevent unauthorized access to memory. This has the effect of catching errors at the hardware level, which is much faster than catching them at the software level.
- **Shared Memory**: Multiple processes can share the same physical page. This is useful for shared libraries and shared memory, and is also used in copy-on-write optimization.

### Loading Shared Libraries

- Shared libraries are loaded into memory by the OS, and the same physical page is mapped into the address space of multiple processes. This is done by the OS, and is transparent to the user.
- It doesn't *have* to be loaded into the same virtual address, but the OS tries to do this. As a rule of thumb, each library has a preferred virtual address location, which makes loading shared libraries easier.
- Adter a while, might run out of address space to share all libraries. Need to be able to dynamicallly relocate them.

### Memory Mapped Files

Forget about doing reads/writes. Instead, map the file into the address space. Any time you write to the address space, it writes to the file. Depending on the OS and cache type (write-through vs write-back), the file may be written to immediately or later. This is a very efficient way to read/write files, and is used in many applications.

#### Soft Page Faults

Fault on a page that are actually in memory, but the PTE was marked as invalid. Resolving soft faults is relatively cheap. This can be used whenever you need to wake up the OS to do something on reference to a page (for instance, a debugger watch point). Windows uses soft faults in its page replacement strategy.