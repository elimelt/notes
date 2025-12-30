# Branch Prediction

## The Problem

Modern CPUs speculatively execute past branches before knowing the outcome. When the prediction is wrong, the pipeline flushes - typically 15-20 cycles wasted.

## The Benchmark

Conditionally sum array elements:

```c
for (size_t i = 0; i < n; i++) {
    if (array[i] < threshold)
        sum += array[i];
}
```

Three variants:
- **Sorted**: First half below threshold, second half above. Predictor learns the pattern.
- **Random**: 50% probability per element. Predictor wrong ~50% of the time.
- **Branchless**: Use bit manipulation instead of a branch.

## Results (64 MB array)

| Variant | ns/element | vs sorted |
|---------|------------|-----------|
| `br_sort` (sorted) | 0.85 ns | 1.0× |
| `br_less` (branchless) | 1.41 ns | 1.7× |
| `br_rand` (random) | 2.75 ns | 3.2× |

## Observations

### 1. Misprediction Penalty: ~2 ns / ~6 cycles

Random data causes ~50% misprediction. The 1.9 ns difference (2.75 - 0.85) amortized over 50% mispredictions suggests ~4 ns per misprediction, or ~12 cycles at 3 GHz.

### 2. Branchless Trades ALU for Predictability

The branchless version:

```c
uint64_t mask = -(array[i] < threshold);  // 0 or 0xFFFFFFFFFFFFFFFF
sum += array[i] & mask;
```

More instructions, but no branch. Faster than mispredicted branches, slower than predicted ones.

### 3. When to Use Branchless

- **Predictable data** (sorted, patterns): Use branches
- **Unpredictable data** (random, hashed): Use branchless
- **Mixed**: Profile and measure

### 4. Modern Compilers

GCC/Clang may auto-convert branches to conditional moves (`cmov`) with `-O3`. Check the assembly if results seem off.

## Branch Predictor Basics

Modern predictors use:
- **Local history**: Pattern of recent outcomes for this branch
- **Global history**: Pattern of recent branches (any branch)
- **Hybrid**: Combines both with neural-network-like structures (TAGE)

Predictors can learn patterns like "taken 3×, not taken 1×, repeat". They fail on truly random data.

## Running

```bash
./bench br_sort 64   # Predictable (sorted)
./bench br_rand 64   # Unpredictable (random)
./bench br_less 64   # Branchless (mask)
```

