# Learned vs baseline inline-link engines — evaluation summary (2026-08-01)

End-to-end evaluation of the SPEC-INLINE-LINKING Architecture-A learned
engine (frozen Qwen3-Embedding-0.6B token states via windowed encoding,
three trained heads) against the deterministic keyphraseness+dictionary
baseline, on the 300-item two-annotator audit (κ 0.88–1.00, GO verdict,
124 A / 29 B / 147 C / 0 D).

## Verdict (SPEC decision thresholds)

**Plateau — the deterministic baseline remains the production review-tool
engine.** The Qwen encoder swap fixed retrieval exactly as SPEC §9
predicted, but end-to-end the learned engine cannot demonstrate
precision@1 ≥ 0.75 at a usable operating point: its accepted set overlaps
the vetted baseline set on only 1 (span, target) pair, and its top-10
contains plainly unnatural anchors ("Handle", "Designing", "chapter 5").
The binding constraint is the **naturalness head** (pairwise AUC 0.664,
trained on 124 Tier-A positives + PU pseudo-negatives, evaluated on only
9 test negatives) — a label-limited problem, not an encoder problem.
Recommended next lever per SPEC §11: the Wikipedia-keyphraseness
pretraining ablation and/or more negative anchor labels — not LoRA.

## Training losses (epochs 30, seed 0)

| head        | hashing encoder | Qwen windowed encoder |
|-------------|-----------------|------------------------|
| naturalness | 0.465 → 0.044   | 0.337 → 0.039          |
| retrieval   | 5.615 → 5.189 (≈ uniform ln 276 = 5.62) | 10.86 → 0.0001 |
| reranker    | 1.940 → 0.732   | 1.005 → 0.0003         |

## Held-out evaluation (document+anchor+target-grouped split, 60/20/20, 28 test A/B positives)

| engine | recall@1 | recall@10 | MRR |
|---|---|---|---|
| Qwen retrieval head       | **0.964** | 0.964 | 0.964 |
| Qwen retrieval + reranker | 0.964 | 0.964 | 0.964 |
| dictionary baseline       | 0.964 | 0.964 | 0.964 |
| hashing retrieval (before)| 0.000 | 0.000 | 0.023 |

Naturalness separation (51 natural / 9 not-natural test anchors): Qwen
mean 0.931 vs 0.879, AUC 0.664 (hashing: AUC 0.379 — below chance).

Matched-budget recovery of the 28 held-out positives (links hidden, both
engines over identical candidates): baseline wins at review budgets
(budget 100: 3 vs 2), learned wins on the full list (12 = 42.9% vs
6 = 21.4%) — it finds twice as many true links but ranks them too low.

## Full-corpus operating points

- Baseline @0.65: **91 accepted / 67 notes** (the production list,
  `inline-link-proposals-2026-08-01.md`).
- Learned @0.40: 69 accepted / 43 notes, 32 anchor-improvement flags
  (`inline-link-proposals-learned-2026-08-01.md`) — supplementary review
  stream only; almost disjoint from the baseline set (1 shared span).

## Runtime

Token encoding on MPS; one-time corpus encode ≈ 10 min, then fully cached
(545 hits / 0 misses on re-run). Qwen train ≈ 12 min wall; heads train on
CPU in seconds. Raw metrics: `inline-eval-qwen-2026-08-01.json`,
`inline-eval-hashing-2026-08-01.json`.
