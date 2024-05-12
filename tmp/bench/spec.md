# SWECCathon Project Spec

## Bench I/O format

### Preamble

```lisp
%d(dimension_in), %s(out_key)
%s(in_key_1), %s(in_key_2), ..., %s(in_key_{dimension_in})
%s(base_1), %s(base_2), ..., %s(base_{dimension_in})
%s(max_1), %s(max_2), ..., %s(max_{dimension_in})
```

### Data

```lisp
%d(in_1), %d(in_2), ..., %d(in_{dimension_in}), %d(out)
%d(in_1), %d(in_2), ..., %d(in_{dimension_in}), %d(out)
...
```

### Input format

```lisp
%d(argc), %s(argv_1), %s(argv_2), ..., %s(argv_{argc})
%d(argc), %s(argv_1), %s(argv_2), ..., %s(argv_{argc})
...
```

## Comp

Compare any number of `.bio` files and generate a benchmarking plot.

```bash
comp [options] <file1> <file2> ...
```

### Comp Options

| Flag | Type | Description | Default |
|------|-------------|---------------------------------------------|---------|
| `-o` | `str` | Output file | "benchmark.png" |

## Gen

Generate a `.input` file

```bash
gen [options]
```

### Gen Options

| Flag | Type | Description | Default |
|------|-------------|---------------------------------------------|---------|
| `-d` | `int` | Dimension of input vectors (number of input keys) | 1 |
| `-b` | `int,`| (CSV string of int) | Base values | "1" |
| `-m` | `int,`| (CSV string of int) | Max values | "10" |
| `-s` | `str` | strategy for generating input | "randint" |
| `-o` | `str` | Output file | "out.bio" |

### Built-in strategies

| Strategy | Description | Compatibility Notes |
|----------|----------------------|
| `randint` | Random integers | requires `b`, `m`, compatible with all `d` |
| `randfloat` | Random floats | requires `b`, `m`, compatible with all `d` |
| `randstr` | Random strings | requires `b`, `m`, compatible with all `d` |
| `randbool` | Random booleans | requires `b`, `m`, compatible with all `d` |
| `drandint` | Distinct Random integers | requires `b`, `m`, compatible with all `d` |
| `drandfloat` | Distinct Random floats | requires `b`, `m`, compatible with all `d` |
| `drandstr` | Distinct Random strings | requires `b`, `m`, need `d = 2` for string length as well |
| `linear` | Linear sequence of integers| requires `b`, `m`, compatible with all `d` |

## Bench

Benchmark a function with a given input file.

```bash
bench [options] <file>
```

### Bench Options

| Flag | Type | Description | Default |
|------|-------------|---------------------------------------------|---------|
| `-d` | `int` | Dimension of input vectors (number of input keys) | 1 |
| `-s` | `str` | Output key | "Time" |
|
| `-i` | `str,` (CSV string of strings) | Input keys | "Size" |
| `-b` | `int,` (CSV string of int) | Base values | "1" |
| `-m` | `int,` (CSV string of int) | Max values | "10" |
| `-inc` | `int,` (CSV string of int) | Increment values | "1" |
| `-o` | `str` | Output file | "out.bio" |

