# Inline-Link Engine Tuning Round 1 — Measurements

Date: 2026-08-01 · Follow-up to `inline-engine-performance-report-2026-08-01.md`,
executing its P0/P1 directions with a measurement after each step.
Artifacts: review decisions and fitted calibration in `../reviews/`, frozen
benchmark in `../benchmarks/`, new proposal lists and raw eval JSON in this
directory.

## 0. Executive summary

Three interventions, each measured:

1. **Honest precision measurement** (160-item case-by-case review): the
   shipped baseline list was **37.4%** precise (34/91), the learned list
   **4.3%** (3/69). The prior report's "near-uniformly acceptable through
   rank 60" qualitative estimate was wrong — score correlates with quality
   (75% precision in ranks 1–20) but decays much earlier than rank 60.
2. **Four mechanical selection rules** (proximity suppression, cross-family
   penalty, single-word floor, per-note same-target cap): baseline precision
   on the reviewed subset **37.4% → 66.7%** while keeping **88.2%** of
   review-accepted links (42 noise removed, 4 good lost). The production
   list is now **45 links** (was 91), all with review verdicts.
3. **Review-driven retraining + calibration + frozen benchmark**: the review
   harvest exposed and fixed a latent reranker training bug (shift-invariant
   listwise loss with an unanchored negative BCE — absolute probabilities
   collapsed to 0 the first time Tier-D data existed). Post-fix, the learned
   target stack is healthy; the naturalness head remains the binding
   constraint. The frozen benchmark then exposed a bottleneck *upstream of
   both engines*: span candidate generation cannot propose
   never-before-linked lowercase phrases at all — the new top tuning
   priority.

## 1. The review: honest precision of the shipped lists

All 160 accepted proposals (91 baseline @0.65, 69 learned @0.40) were judged
case-by-case in their note context under the refined audit guideline
(`.inline/audit/guidelines.md`), each with per-head verdicts (target_ok /
anchor_ok / placement_ok) so every rejection routes to the head that erred.
Disclosure: judgments by independent Claude reviewer agents under the written
guideline, one item adjudicated by the coordinator; decisions preserved at
`reviews/inline-review-decisions-2026-08-01.jsonl`.

| engine | accepted | precision |
|---|---|---|
| baseline @0.65 | 34/91 | **37.4%** |
| learned @0.40 | 3/69 | **4.3%** |

Baseline precision by rank bucket: 1–20 → **75%**, 21–40 → 35%, 41–60 →
20%, 61–91 → 27%. Reject taxonomy (both engines): wrong_target 38,
duplicate_nearby 30, bad_placement 28, unnatural_anchor 17, generic 8,
broken_span 1.

**Load-bearing discovery**: the MMR same-target redundancy penalty only
*reorders* — acceptance thresholds the raw score — so single notes accepted
the same target repeatedly (6× "file systems" from one chapter, 5×
"resistance" from one cheatsheet). Roughly a third of all baseline noise was
this one mechanical defect.

## 2. The rules: measured against the 160 verdicts

Four rules (all config-gated, defaults in parentheses), implemented outside
any learned score:

- **A — existing-target proximity suppression** (600 chars): reject a draft
  whose target is already linked nearby in the source. Refined after
  measurement: existing links inside Related-notes zones are exempt — the
  guideline's duplication rule says prose is the preferred home, and the
  only two review-accepted links Rule A initially removed were both blocked
  solely by navigation entries.
- **B — cross-family penalty** (0.35 on target correctness, document-id
  path family, depth 1): lowercase phrases are family-polysemous ("memory
  management"), TitleCase/acronym anchors are exempt ("Paxos", "TCP" name
  global concepts).
- **C — single-word naturalness floor** (0.5): lowercase 1-word anchors
  face a higher bar ("resistance"-class tail).
- **D — per-note same-target cap** (1): fixes the reorder-not-reject MMR
  defect directly.

Result on the reviewed subset (proposals re-run, same artifacts):

| | before rules | after rules |
|---|---|---|
| accepted | 91 | 45 |
| review-accepted kept | 34 | 30 |
| precision | 37.4% | **66.7%** |
| good-link retention | — | **88.2%** |

42 of 46 removals were review-rejected items; the 4 lost good links are
known rule trade-offs (2 cross-family penalties on good cross-domain links,
1 same-target-cap instance choice, 1 single-word floor). Zero unreviewed
newcomers entered. The new production list:
`inline-link-proposals-rules-2026-08-01.md`.

Residual noise (15 kept-but-rejected) is dominated by same-family wrong
targets the family prior cannot see (e.g. "Memory management" in
`ml/serving-systems/gpu-basics` → the serving memory note judged
wrong-in-context) and placement judgment calls.

## 3. Retraining on review labels — and the bug it exposed

Review decisions route per-head into training (`inline train --reviews`):
anchor_ok is direct naturalness ground truth (the head previously had ~124
positives vs ~9 negatives; the review adds 47 real anchor negatives),
accept→Tier A, reject-with-correct-target→Tier B, wrong-target→Tier D
reranker negatives.

**The first retrain collapsed**: every draft's target_correctness went to
0.00 while training loss read 0.0007. Root cause (confirmed by control runs
and a synthetic reproduction): the reranker's listwise cross-entropy is
shift-invariant — it pins only relative order — and its absolute-scale BCE
step ran on Tier-D negatives alone, with no positive anchor. The audit had
zero Tier-D rows, so the term had never fired; the review's 65 wrong-target
pairs gave the optimizer a free direction — shift every logit down. Fixed by
anchoring the BCE with true pairs at 1.0; a regression test asserts positives
clear an absolute floor (the old code trains to mean positive probability
0.0000, the fixed code 1.0000).

Post-fix retrained engine (raw @0.40): **244 accepted** across 151 notes,
top of list all target-correct natural anchors ("SystemVerilog", "flow
control", "UDP" → their exact notes, scores ≈0.99). Sanity fit against the
review verdicts (**training data, not generalization**): review-accepted
items score 0.866 mean vs 0.646 for rejected; accept-vs-reject AUC 0.691.

One diagnostic line captures the remaining constraint — on "NumPy" in the
linear-algebra glossary the retrained stack scores retrieval 1.000 and
rerank 1.000 for exactly the right note (`python-cheatsheet`) and
naturalness 0.007 kills it. **The target stack is fixed; anchor taste is
still the binder**, now erring conservative rather than accepting garbage.

## 4. Calibration: the scores confess

Temperature fit per engine on the 160 review outcomes
(`reviews/review-calibration-2026-08-01.json`):

| engine | n | T | ECE before | ECE after |
|---|---|---|---|---|
| baseline | 91 | 20.0 | 0.351 | **0.139** |
| learned (pre-retrain) | 69 | 20.0 | 0.470 | 0.458 |

T = 20 (the fit bound) for both: raw combined scores carry rank information
but almost no absolute-probability information. The honest consequence:
running the pre-retrain learned engine with calibration at threshold 0.40
accepts **zero** proposals — at 4.3% measured precision nothing should clear
a 40% acceptance bar, and now the pipeline says so itself. The retrained
engine needs calibration fit on *fresh* review outcomes (fitting on the 160
would calibrate on its own training data); until then it ships uncalibrated
and is a review stream, not an applier.

## 5. The frozen benchmark: both engines hit the same wall

`benchmarks/expert-benchmark-v1.json`: 53 hand-authored cases, all seven
SPEC §7 judgment kinds, 24 hard-flagged, built exclusively from unlinked
spans (zero overlap with audit labels or review decisions — it stays valid
as training data grows).

| kind | baseline | learned (retrained) |
|---|---|---|
| natural_span | 0.364 | 0.364 |
| acceptable_span | 0.400 | 0.400 |
| correct_target | 0.250 | 0.250 |
| incorrect_target | **1.000** | **1.000** |
| no_link | **1.000** | **1.000** |
| valid_placement | 0.429 | 0.429 |
| reverse_direction | 0.333 | 0.333 |
| hard_case | 0.583 | 0.583 |
| **overall** | **0.547** | **0.547** |

The identical columns are the finding. Every failure is a *miss* (zero
false links — both engines are perfect on the never-link kinds), and the
misses trace to a stage upstream of both engines: **span candidate
generation only proposes dictionary mentions (already-linked vocabulary),
title n-grams, and TitleCase/acronym/hyphenated tokens.** A
never-before-linked lowercase concept phrase — "congestion collapse",
"max-min fairness", "sampled softmax" — never becomes a candidate span, so
no engine can score it, however good its heads. The candidate stage was
built high-recall against *audited existing links* (where it measured well)
— the benchmark is the first instrument that measures recall on the
discovery distribution, which is the distribution that matters for finding
missing links.

Known benchmark artifact: locate-by-first-verbatim-occurrence lands a few
cases (e.g. "NumPy") on text inside existing link markup where spans are
excluded; a v2 convention should skip occurrences overlapping existing
links. The artifact stays frozen; the flaw is documented, consistent across
engines, and does not affect the bottleneck conclusion.

## 6. Held-out eval of the retrained heads

`inline-eval-qwen-retrained-2026-08-01.json`, same grouped split as the
original eval. **Caveat**: the split isolates audit items only — review
labels were not part of its union-find, so test-split numbers for retrained
heads can leak through shared (anchor, target) groups; treat the benchmark
(§5) and the next fresh review round as the trustworthy generalization
instruments.

Retrieval on the 28 test positives is unchanged and saturated — recall@1
0.964 for the retrieval head, retrieval+reranker, and baseline alike (the
encoder swap solved this last round; the reranker fix did not disturb it).

**Naturalness — the metric the review labels targeted — moved decisively:**

| | previous heads | retrained heads |
|---|---|---|
| pairwise AUC | 0.664 | **0.767** |
| mean score, natural anchors (n=51) | 0.931 | 0.897 |
| mean score, not-natural anchors (n=9) | 0.879 | 0.644 |
| separation gap | 0.052 | **0.253** |

The head stopped scoring everything ~0.9: it now pushes bad anchors down
five times harder while conceding little on good ones.

Matched-budget recovery of the 28 hidden positives (both engines now run
with the selection rules, so both are more conservative than last round):
baseline recovers 5 (17.9%, was 6) on a 547-draft ranked list; learned
recovers 8 (28.6%, was 12) on 1,287 — the learned engine still wins on the
deep list (8 vs 5 by budget 400), the baseline still wins at small review
budgets (3 vs 2 at 100). Some hidden positives are now legitimately
suppressed by the rules (e.g. cross-family pairs), which trades historical
recovery for the measured precision gain of §2 — the trade the review said
to make.

## 7. Updated tuning directions

1. **P0 (new, from §5): a discovery-recall candidate source.** Add a
   general noun-phrase span source (corpus-frequency n-grams over prose, or
   a light POS chunker) gated by the existing masking/region rules. Every
   downstream improvement is capped by this stage; it is the only component
   both engines share and the benchmark shows it is the binding constraint
   on discovery.
2. **P0: fresh review round on the 45-link rules list + the retrained
   learned top-50.** Those decisions are (a) the first honest measurement
   of the post-rules operating point, (b) clean calibration data for the
   retrained engine, and (c) the next batch of naturalness negatives — the
   loop §7 of the previous report described, now fully wired
   (`inline calibrate`, `inline train --reviews`).
3. **P1: naturalness head shape features.** The "NumPy at 0.007" class
   (title-shaped single tokens with healthy target scores) suggests the
   head under-uses surface shape; the span stage already computes
   is_titlecase/is_acronym features — verify they reach the rep and
   consider a per-shape calibration or floor interaction at selection.
4. **P1: benchmark v2 location convention** (skip occurrences inside
   existing link markup), keeping v1 frozen for comparability.
5. **P2 unchanged**: LoRA stays gated behind the new negatives; reranker
   bake-off; section-level targets.

## 8. Operating guidance (changed from the previous report)

- **Production review list**: the rules list @0.65 —
  `inline-link-proposals-rules-2026-08-01.md`, 45 links, measured 66.7%
  precise with the top-20 band at ~75%+. Apply with a light skim; every
  item already carries a review verdict.
- **Learned engine**: `inline-link-proposals-learned-retrained-2026-08-01.md`
  (244 @0.40 raw) is a discovery stream — strong targets, conservative but
  imperfect anchors; skim the top ~50. Do not auto-apply; it has no valid
  calibration until the next review round.
- **Calibrated pipelines** (`--calibration`) currently and correctly refuse
  to accept learned proposals at review-grade thresholds; this is the
  system being honest, not broken.
