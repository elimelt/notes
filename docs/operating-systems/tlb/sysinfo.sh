#!/bin/bash
echo "=== CPU Info ==="
sysctl machdep.cpu.brand_string
sysctl machdep.cpu.core_count
sysctl machdep.cpu.thread_count

echo -e "\n=== Cache Hierarchy ==="
echo "L1 Data Cache:  $(sysctl -n hw.l1dcachesize) bytes"
echo "L1 Inst Cache:  $(sysctl -n hw.l1icachesize) bytes"
echo "L2 Cache:       $(sysctl -n hw.l2cachesize) bytes"
if sysctl hw.l3cachesize &>/dev/null; then
    echo "L3 Cache:       $(sysctl -n hw.l3cachesize) bytes"
fi
echo "Cache Line:     $(sysctl -n hw.cachelinesize) bytes"

echo -e "\n=== Memory Info ==="
echo "Page Size:      $(sysctl -n hw.pagesize) bytes"
echo "Total RAM:      $(echo "$(sysctl -n hw.memsize) / 1024 / 1024 / 1024" | bc) GB"

echo -e "\n=== TLB Info (if available) ==="
sysctl -a 2>/dev/null | grep -i tlb || echo "TLB info not exposed via sysctl"
