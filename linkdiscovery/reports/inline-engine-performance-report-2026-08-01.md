# Inline-Link Engine Performance Report

Date: 2026-08-01 · System: `linkdiscovery/inline` (SPEC-INLINE-LINKING.md) ·
Corpus: 300 notes / ~3.2k semantic units · Related artifacts in this
directory: production list (`inline-link-proposals-2026-08-01.*`), learned
stream (`...-learned-...`), raw metrics (`inline-eval-{qwen,hashing}-*.json`).

## 1. Executive summary

**The deterministic baseline engine performs well and is the production
review-tool engine.** Its 91-link high-confidence list is near-uniformly
acceptable through roughly rank 60, with quality decaying in step with the
score — exactly the behavior a review-ranked list needs. On held-out audited
links it places the true target at rank 1 for **96.4%** of test positives.

**The learned engine is not ready and the reason is precisely localized.**
Swapping the test-grade hashing token encoder for windowed Qwen token states
fixed target retrieval outright (held-out recall@1 **0.0 → 0.964**),
confirming the spec's §9 prediction. The binding constraint is now the
**anchor-naturalness head** (pairwise AUC 0.664), which trained on 124
positive anchors and almost no negatives. By the spec's decision thresholds
this is a *plateau*, not a kill: retrieval works, full-list recovery is 2×
the baseline's, but at review budgets the baseline wins and the learned
top-10 contains anchors no author would link ("Handle", "chapter 5").

## 2. Evaluation basis

- **Audit** (SPEC §4): 300 stratified existing links, two independent
  annotators, three judgments each, one guideline-refinement round after
  κ(anchor_natural) = 0.41 exposed underspecification on title-shaped
  anchors. Final agreement: κ(target) = 1.00, κ(anchor) = 0.98,
  κ(placement) = 0.88, κ(tier) = 0.98. Consensus: 124 A / 29 B / 147 C /
  0 D → GO (153 clean positives). Disclosure: annotators were independent
  Claude agents operating under a written guideline, not humans.
- **Splits** (SPEC §8): document ∧ anchor-string ∧ target grouped
  (union-find, 71 groups), 60/20/20 achieved exactly; 28 held-out Tier-A/B
  positives in test.
- **Corpus finding worth keeping**: zero wrong-target links in 300 audited.
  All link noise in this corpus is anchor *phrasing* (≥5-word title dumps,
  comma enumerations) and duplicated Related-notes placements — never the
  destination. Target-correctness weak supervision from existing links is
  safe here.

## 3. Quantitative results

Training losses (epochs 30, seed 0):

| head | hashing encoder | windowed Qwen |
|---|---|---|
| naturalness | 0.465 → 0.044 | 0.337 → 0.039 |
| retrieval | 5.615 → 5.189 (uniform = ln 276 ≈ 5.62) | 10.86 → 0.0001 |
| reranker | 1.940 → 0.732 | 1.005 → 0.0003 |

Held-out retrieval (28 test positives):

| engine | recall@1 | recall@10 | MRR |
|---|---|---|---|
| Qwen retrieval head | **0.964** | 0.964 | 0.964 |
| Qwen retrieval + reranker | 0.964 | 0.964 | 0.964 |
| dictionary baseline | 0.964 | 0.964 | 0.964 |
| hashing retrieval (before) | 0.000 | 0.000 | 0.023 |

Naturalness separation on test anchors (51 natural / 9 not): Qwen mean
0.931 vs 0.879, AUC 0.664. (Hashing: AUC 0.379 — below chance.)

Matched-budget recovery of the 28 hidden positives (identical candidates):

| budget | learned | baseline |
|---|---|---|
| 25 | 0 | 1 |
| 100 | 2 | 3 |
| 400 | 10 | 6 |
| full list | **12 (42.9%)** | 6 (21.4%) |

The learned engine finds twice as many true links overall but ranks them too
low to matter at review budgets. Overlap of accepted sets at production
thresholds: 1 (span, target) pair — the engines see almost disjoint things.

## 4. Qualitative sample across the ranking depth (baseline, 91 accepted @0.65)

| rank | score | note · anchor → target | verdict |
|---|---|---|---|
| 1 | 0.866 | framing · "The physical layer" → physical-layer note ("...delivers a stream of bits. The link layer has to know where each frame starts...") | correct, natural |
| 4 | 0.855 | HTTP · "load balancing" → load-balancing ("...an intermediary between clients and servers also helps with load balancing, security...") | correct, natural |
| 7 | 0.848 | OS file-systems lecture · "files and directories" → OSPP ch. 13 | correct, natural |
| 21 | 0.800 | network-components · "the global internet" → global-internet | correct, natural |
| 31 | 0.758 | unix-timesharing · "file systems" → file-systems lecture | **duplicate**: the same target is wikilinked two words earlier in the sentence |
| 46 | 0.689 | distributed-training · "Sharding" → distributed-systems/sharding | defensible; ZeRO sharding vs DB sharding is a judgment call |
| 61 | 0.670 | OS components lecture · "memory management" → **ml/serving-systems**/memory-management | **wrong domain**: OS memory management ≠ LLM-serving memory management |
| 89 | 0.654 | circuits cheatsheet · "resistance" → signal-conditioning lecture 3 | generic anchor, marginal value |

Learned engine top-10 for contrast: genuinely novel finds ("pipelining and
hazards" → the pipelining note) interleaved with non-anchors ("Handle",
"Designing", "Potential", "chapter 5") — target choice strong, anchor taste
weak.

## 5. Failure modes observed

1. **Naturalness label scarcity** (learned engine's binder): 9 test
   negatives cannot teach a head what *not* to link.
2. **Cross-domain homonym anchors** (baseline rank 61): "memory management",
   "scheduling", "sharding" name different concepts in different topic
   families; embedding similarity alone doesn't disambiguate intent.
3. **Same-target duplication near existing links** (baseline rank 31): span
   overlap with existing links is excluded, but a proposal targeting a note
   already linked in the same sentence/paragraph is not.
4. **Generic single-noun anchors at the tail** ("resistance", "hardware"):
   keyphraseness admits them because they genuinely are linked elsewhere in
   the corpus.

## 6. Directions for further tuning

Ordered by expected value per unit effort.

### P0 — data for the naturalness head (the binding constraint)
- **Harvest negatives from review decisions.** Every rejected proposal from
  the PR #138 review (and the earlier #59 application pass) is a
  high-quality hard negative. Wire `apply_reviews` output into
  `build_training_data` as Tier-D-equivalent anchor negatives.
- **Wikipedia keyphraseness pretraining ablation** (SPEC §11 phase 7):
  pretrain the naturalness head on Wikipedia anchor statistics ("what
  strings are linkable in prose" transfers; entities do not), then
  fine-tune in-domain. Keep only if it beats in-domain-only on the frozen
  benchmark.
- **Mine cheap synthetic negatives** from the refined guideline's hard
  rules: ≥5-word title dumps, comma enumerations, ordinals, stopwordy
  fragments are *rule-defined* negatives — generate thousands from the
  corpus at zero labeling cost, PU-weighted below real rejections.

### P0 — selection rules (fix observed failure modes mechanically)
- **Same-target proximity suppression**: reject/downweight a proposal whose
  target is already linked within N characters (or the same paragraph) —
  fixes rank-31-style duplicates. Extend the existing MMR same-target
  penalty, which currently only sees other *proposals*, not existing links.
- **Topic-family consistency prior for generic anchors**: when an anchor's
  dictionary entry is dominated by one topic family, penalize cross-family
  targets (fixes "memory management" → serving-systems from an OS note).
  A one-feature addition to the baseline formula; a feature column for the
  learned reranker.
- **Raise the naturalness floor** for 1-word non-title anchors (kills
  "resistance"-class tail proposals at negligible recall cost).

### P1 — calibration and measurement
- **Fit calibration on real review outcomes**: once ≥100 accept/reject
  decisions exist from PR #138's list, fit temperature scaling (or the
  conformal abstainer for a guaranteed error rate among accepted) so the
  accept threshold maps to a predictable acceptance rate. The machinery is
  built (`fit_temperature`, `ConformalAbstainer`) and currently unfitted.
- **Author the frozen expert benchmark** (SPEC §7, seven judgment kinds,
  hard-case oversampling). Without it, every future tuning claim is
  unfalsifiable. `Benchmark`/`score_benchmark` exist; the artifact needs
  ~50 hand-authored cases.
- **Reranker bake-off** (SPEC §11 phase 4): lexical vs pooled-vector vs
  MaxSim vs cross-encoder over identical candidate sets; MaxSim is cheap at
  this scale and may fix boundary localization for free.

### P2 — model capacity (only after P0 data lands)
- **LoRA rank 4–8 on the encoder** (SPEC Architecture B), gated on the
  naturalness head plateauing *with* the new negatives — pointless before.
- **Section-level target vectors** for placement ("where in the target does
  this concept live"), enabling span→section links.
- **Instruction-aware encoding**: Qwen3 is instruction-tuned; a task
  instruction on the span-context side ("find the note this phrase should
  link to") is worth 1–5% per the model card and is a config-only change.

### Operating guidance (today, unchanged)
- Baseline @0.65 (91 links) for application review; treat ranks ≥ ~60 with
  extra skepticism.
- Learned @0.40 (69 links) as a supplementary stream for novel finds only.
- Budget: 1/175 words, cap 10 — no reviewer-fatigue signal yet to justify
  changing it.

## 7. The real metric going forward

Per SPEC §7 Q32, historical-link recovery was never the target — most
existing links are navigationally unused. The honest signal is **acceptance
rate of proposals under review**, which the review artifacts already
capture. Each review cycle simultaneously (a) measures the engines and
(b) produces the training negatives that P0 needs: the system is designed
to improve by being used.
