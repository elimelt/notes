# Store-to-Load Forwarding

## The Problem

When a load reads from an address that was just written, the CPU can forward the data directly from the store buffer instead of waiting for the store to commit to cache. This is **store-to-load forwarding**.

However, forwarding only works when the load exactly matches the store. Partial overlaps cause a **store forwarding stall** - the CPU must wait for the store to commit before loading.

## The Benchmark

Three patterns:

```c
// Aligned: store 8 bytes, load same 8 bytes (forwarding works)
*(uint64_t *)(bytes) = i;
sum += *(uint64_t *)(bytes);

// Overlap: store at offset 1, load at offset 0 (forwarding fails)
*(uint64_t *)(bytes + 1) = i;
sum += *(uint64_t *)(bytes);

// Independent: store and load different addresses (no dependency)
array[0] = i;
sum += array[64];
```

## Results (64 MB array)

| Pattern | ns/op | vs forwarding |
|---------|-------|---------------|
| `sf_fwd` (aligned) | 0.52 ns | 1.0× |
| `sf_indep` (independent) | 0.70 ns | 1.3× |
| `sf_stall` (overlap) | 3.64 ns | 7.0× |

## Observations

### 1. Forwarding is Faster Than Independent

The aligned case (0.52 ns) beats the independent case (0.70 ns). Store-forwarding provides data faster than even an L1 cache hit because:
- No cache lookup needed
- Data comes directly from store buffer
- Zero latency dependency

### 2. Overlap Stall: ~3 ns Penalty

When the load partially overlaps the store, the CPU cannot forward. It must:
1. Wait for the store to commit to L1 cache
2. Then perform the load from cache

This adds ~3 ns (roughly 10 cycles at 3 GHz).

### 3. When Forwarding Fails

Store-forwarding fails when:
- Load is smaller than store and not aligned to store start
- Load is larger than store
- Load spans multiple stores
- Store and load have different sizes at same address (sometimes)

### 4. Compiler Implications

The compiler doesn't know about store-forwarding stalls. Code like:

```c
struct { char a; int64_t b; } __attribute__((packed)) s;
s.b = value;
use(s.b);  // May stall if 'a' was recently written
```

Can cause unexpected slowdowns.

## Running

```bash
./bench sf_fwd 64     # Aligned (forwarding)
./bench sf_stall 64   # Overlapping (stall)
./bench sf_indep 64   # Independent (no dependency)
```

