#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
compiler=${CC:-cc}
iterations=${1:-20000000}
samples=${2:-21}

if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo "This benchmark requires Linux on x86-64." >&2
  exit 2
fi
if ! command -v taskset >/dev/null 2>&1; then
  echo "taskset is required to pin the benchmark to one logical CPU." >&2
  exit 2
fi

allowed_list=$(awk '/^Cpus_allowed_list:/ { print $2 }' /proc/self/status)
first_range=${allowed_list%%,*}
default_cpu=${first_range%%-*}
cpu=${CPU:-$default_cpu}
if [[ ! $cpu =~ ^[0-9]+$ ]]; then
  echo "CPU must name one logical CPU from the allowed affinity set." >&2
  exit 2
fi

binary=$(mktemp "${TMPDIR:-/tmp}/store_fwd_bench.XXXXXX")
trap 'rm -f -- "$binary"' EXIT

recorded_flags='-O3 -std=gnu11 -Wall -Wextra -Wpedantic'
"$compiler" -O3 -std=gnu11 -Wall -Wextra -Wpedantic \
  "-DSTORE_FWD_BUILD_FLAGS=\"$recorded_flags\"" \
  "$script_dir/store_fwd_bench.c" -o "$binary"

printf 'measured_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'source_sha256=%s\n' "$(sha256sum "$script_dir/store_fwd_bench.c" | awk '{ print $1 }')"
taskset --cpu-list "$cpu" "$binary" "$iterations" "$samples"
