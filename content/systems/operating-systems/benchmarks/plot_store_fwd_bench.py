"""Render the recorded store/load loop timings. Requires matplotlib 3.10+.

Run beside the note: python3 plot_store_fwd_bench.py
The input and output paths resolve relative to this file.
"""

import csv
import io
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
text = (HERE / "store_fwd_bench-results.txt").read_text()
metadata = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
raw = text.split("raw_samples_ns_per_op\n", 1)[1].split("\nsummary_ns_per_op", 1)[0]
rows = list(csv.DictReader(io.StringIO(raw.strip())))
patterns = ["exact", "independent", "partial_overlap"]
labels = ["Exact match\nstore +0 / load +0", "Independent\nstore +0 / load +64", "Partial overlap\nstore +1 / load +0"]
colors = ["#21618c", "#487c75", "#a75131"]

fig, ax = plt.subplots(figsize=(9, 4.8))
fig.subplots_adjust(left=0.11, right=0.97, top=0.76, bottom=0.30)
for i, (pattern, color) in enumerate(zip(patterns, colors)):
    values = sorted(float(row[pattern]) for row in rows)
    n = len(values)
    mid = median(values)
    # Match the benchmark's reported order-statistic quartiles exactly.
    q1, q3 = values[n // 4], values[(3 * n) // 4]
    jitter = [(j % 7 - 3) * 0.025 for j in range(n)]
    ax.scatter([i + dx for dx in jitter], values, s=19, color=color, alpha=0.40, zorder=3)
    ax.plot([i, i], [q1, q3], color=color, linewidth=7, solid_capstyle="butt", zorder=4)
    ax.plot([i - 0.14, i + 0.14], [mid, mid], color="#17212b", linewidth=2, zorder=5)
    ax.annotate(f"{mid:.3f} ns", (i, max(values)), xytext=(0, 12),
                textcoords="offset points", ha="center", fontsize=11, fontweight="bold")

ax.set_xticks(range(3), labels, fontsize=10)
ax.tick_params(axis="both", length=0, pad=8)
ax.set_ylabel("Elapsed ns per loop iteration", fontsize=11)
upper = max(float(row[p]) for row in rows for p in patterns)
ax.set_ylim(0, upper * 1.25)
ax.set_xlim(-0.5, 2.5)
ax.grid(axis="y", color="#e1e5e8", zorder=0)
for spine in ax.spines.values():
    spine.set_visible(False)
fig.text(0.11, 0.94, "Partially overlapping store/load pairs slow this loop", fontsize=15, weight="bold")
fig.text(0.11, 0.865, "Intel Core i9-13900HK · " + metadata["compiler"] + " · " + metadata["measured_at_utc"][:10], fontsize=10, color="#46525c")
fig.text(0.11, 0.15, f"Dots: {len(rows)} samples per case · thick line: middle 50% · black tick: median", fontsize=10)
fig.text(0.11, 0.09, f"{int(metadata['iterations_per_sample']):,} iterations/sample; CPU {metadata['affinity_cpu']}; balanced order; warmup before timing.", fontsize=9, color="#46525c")
fig.text(0.11, 0.035, "Each iteration includes one store, one load, checksum and loop work. Throughput, not isolated load latency.", fontsize=9, color="#46525c")
fig.savefig(HERE / "store_fwd_bench.png", dpi=180, facecolor="white")
plt.close(fig)
