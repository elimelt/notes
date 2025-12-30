# TLB and Page Walks

## The Problem

Virtual addresses must be translated to physical addresses. The CPU caches these translations in the **Translation Lookaside Buffer (TLB)**. When the TLB misses, the CPU must walk the page table - a series of dependent memory accesses.

On x86-64 with 4-level paging, a TLB miss requires up to 4 memory accesses to resolve.

## The Benchmark

Access array elements at different strides:
- Small strides: many accesses per page, TLB hits
- Page-sized strides (4KB): one access per page, TLB misses

```c
for (size_t i = 0; i < n; i += stride) {
    sum += array[i];
}
```

## Results (256 MB array)

| Stride | Accesses/page | ns/access | vs sequential |
|--------|---------------|-----------|---------------|
| 8B | 512 | 1.36 ns | 1.0× |
| 64B | 64 | 2.49 ns | 1.8× |
| 512B | 8 | 5.38 ns | 4.0× |
| 4KB | 1 | 12.51 ns | 9.2× |
| 8KB | 0.5 | 13.31 ns | 9.8× |

## Observations

### 1. TLB Miss Penalty: ~10 ns

The jump from 512B stride (5.38 ns) to 4KB stride (12.51 ns) shows the TLB miss cost. At 4KB stride, every access misses the TLB.

### 2. Page Walk is a Pointer Chase

A TLB miss triggers a page table walk - 4 dependent loads through PML4 → PDPT → PD → PT. This is why the penalty is fixed (~10 ns) rather than scaling with stride.

### 3. Hardware Page Walk Cache

Modern CPUs cache intermediate page table entries (page walk cache / paging structure cache). This is why 4KB and 8KB strides show similar latency - upper-level entries are cached.

### 4. TLB Capacity

Typical L1 dTLB: 64-128 entries (covers 256KB-512KB with 4KB pages). L2 TLB: 1024-2048 entries. With 256MB of data at 4KB stride, we access 65K pages - far exceeding TLB capacity.

## Cache vs TLB

| Stride | Cache behavior | TLB behavior |
|--------|---------------|--------------|
| 8B | Hit (prefetcher) | Hit (same page) |
| 64B | Miss (1 line/access) | Hit (64 accesses/page) |
| 512B | Miss | Hit (8 accesses/page) |
| 4KB | Miss | Miss (1 access/page) |

The 64B→512B slowdown is cache misses. The 512B→4KB slowdown is TLB misses.

## Huge Pages

With 2MB huge pages, the TLB covers 512× more memory per entry. Page-strided access would hit TLB until the working set exceeds TLB capacity × 2MB.

## Running

```bash
./bench tlb_seq 256   # Sequential (TLB hits)
./bench tlb_64 256    # Cache line stride
./bench tlb_512 256   # Within-page stride
./bench tlb_4k 256    # Page stride (TLB misses)
./bench tlb_8k 256    # Skip pages
```

