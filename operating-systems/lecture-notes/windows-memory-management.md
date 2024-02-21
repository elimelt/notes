# Windows Memory Management

Pages have one of the following states defined in the **page frame number (PFN) database**:

- **Active**: The page is in use and its contents are valid.
- **Transition**: The page is being moved from disk to memory or from memory to disk.
- **Free**: The page is not in use. It should be contained in the free list.
- **Zeroed**: The page is filled with zeros. This is used to support demand paging by maintaining a list of zeroed pages.
- **Standby**: The page is not in use, but its contents are valid.
- **Modified**: The page is in use and its contents are valid, but it has been modified since it was last read from disk.
- **Modified no-write**: The page is in use and its contents are valid, but it has been modified since it was last read from disk and cannot be written to disk. This was used to support transactional memory.
- **Rom**: The page is read-only memory.
- **Bad**: The page is defective and cannot be used.

Windows uses a mixture of local and global page replacement, and maintains an LRU list of pages on top of a FIFO list. The LRU list is used to select pages for replacement (working set), and the FIFO list (standby list) is used to select pages for trimming. The LRU list is maintained by the memory manager, and the FIFO list is maintained by the cache manager.


## A Major Problem with Page Replacement in Early Windows

Using a **working set** model for page replacement, when a user's process goes idle for long periods of time, all of the pages used by the process are removed from memory. Background processes like antivirus and indexing services exacerbate this problem. When the user returns to the process, it must wait for the pages to be read back into memory from disk.

## An Interesting Exam Question from 2013

Examine how long it takes a user mode program writing to an array of integers using various access patterns. Assume the entire array fits into memory, and that the system is idle besides this program. The **Stride** is the number of elements between each access. The array is a constant size of `PGSIZE` (4096 bytes).

```cpp
int access(int* arr, int size, int stride);
```