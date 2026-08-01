---
title: Missing-Link Discovery Pipeline
aliases:
  - software/missing-link-discovery
category: Natural Language Processing
tags:
  - embeddings
  - information retrieval
  - ranking
  - pipeline design
  - knowledge base
date: 2026-07-31
status: evergreen
description: How this repo's missing-link discovery system works — stage architecture, the retrieval and ranking algorithm, and how to run it.
sources:
  - title: "SPEC.md: Missing-Link Discovery Pipeline"
    url: https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/SPEC.md
    type: docs
  - title: "First real run: proposals and evaluation (issue #54)"
    url: https://github.com/elimelt/notes/issues/54
    type: docs
  - title: "Baseline rerun and experiment export (issue #119)"
    url: https://github.com/elimelt/notes/issues/119
    type: docs
  - title: "Word Translation Without Parallel Data (CSLS), Conneau et al. 2018"
    url: https://arxiv.org/abs/1710.04087
    type: paper
  - title: Qwen3-Embedding-0.6B model card
    url: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
    type: docs
  - title: "TextRank: Bringing Order into Text"
    url: https://aclanthology.org/W04-3252/
    type: paper
  - title: "PositionRank: An Unsupervised Approach to Keyphrase Extraction"
    url: https://aclanthology.org/P17-1102/
    type: paper
  - title: "Simple Unsupervised Keyphrase Extraction using Sentence Embeddings"
    url: https://aclanthology.org/K18-1022/
    type: paper
  - title: "SPEC-INLINE-LINKING.md: learned inline-link discovery"
    url: https://github.com/elimelt/notes/blob/6ae85f5a2b35d18beb83eaf7882f0e89e724b315/linkdiscovery/SPEC-INLINE-LINKING.md
    type: docs
  - title: "Gerlach et al. 2021 — Multilingual Entity Linking System for Wikipedia with a Machine-in-the-Loop Approach (add-a-link)"
    url: https://arxiv.org/abs/2105.15110
    type: paper
---

## Purpose

This repo contains [`linkdiscovery/`](https://github.com/elimelt/notes/tree/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery),
a batch pipeline that finds pairs of notes that are strongly related but not
yet linked, and proposes them for review with evidence attached. It answers a
stronger question than "are these similar": would a reader benefit from a
direct navigational link, and where in the source note should it be placed?
The system never edits notes itself — it emits ranked proposals
(`proposals.jsonl` / `proposals.md`), and link insertion is a separate,
human-approved step. Its first real run produced
[issue #54](https://github.com/elimelt/notes/issues/54); the accepted links
merged in [#59](https://github.com/elimelt/notes/pull/59). The later CPU
baseline rerun and its experiment bundle are tracked in
[issue #119](https://github.com/elimelt/notes/issues/119).

## Architecture

The pipeline is six stages with typed, serializable artifacts at every
boundary:

```text
raw content
  -> source adapter        (Corpus: documents + existing relationships)
  -> preprocessor          (ProcessedCorpus: typed regions, semantic units)
  -> embedder              (EmbeddingIndex: vectors + runtime provenance)
  -> candidate generator   (CandidateSet: high-recall pairs + raw features)
  -> ranker                (ProposalSet: scored, directed, evidence-backed)
  -> reporter              (JSONL / Markdown review artifacts)
```

Two design rules carry most of the weight:

**1. Adapters own source semantics.** The core package knows nothing about
Markdown, wikilinks, frontmatter, or this repo's layout — all of that lives in
a separate `linkdiscovery_markdown` package that translates host concepts into
generic contracts. Each stage is a `Protocol`, so any piece can be replaced
without touching the others:

```python
class Embedder(Protocol):
    """Embeds semantic units, returning vectors plus model and runtime provenance.

    Must not expose PyTorch, MLX, NumPy, or sentence-transformers objects
    across the boundary, must reuse cached vectors through ``cache``, and
    must record device selection and fallbacks in the returned runtime
    report (no silent fallback).
    """

    def embed(
        self, corpus: ProcessedCorpus, config: EmbeddingConfig, cache: ArtifactCache
    ) -> EmbeddingIndex:
        """Embed every eligible unit, reusing cache entries where keys match."""
        ...
```

[interfaces.py#L76-L90](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/src/linkdiscovery/interfaces.py#L76-L90)

**2. Everything is content-addressed.** Artifacts are written atomically to a
store keyed by fingerprints, and each stage's cache key is composed from
exactly the inputs that affect its output. The embedding cache key is the
canonical example — changing a ranking weight cannot invalidate embeddings,
but changing the chunker, the model revision, or the instruction text must:

```python
options_fp = _runtime_options_fingerprint(config)
keys = {
    unit.id: combine_fingerprints(
        unit.content_hash,
        corpus.preprocessing_fingerprint,
        provider.model_fingerprint,
        options_fp,
    )
    for unit in units
}
```

[embedder.py#L174-L183](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/src/linkdiscovery/embed/embedder.py#L174-L183)

Device and batch size are deliberately *excluded* from the key — they must not
change embedding values, so keying on them would throw away reusable vectors
([embedder.py#L89-L103](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/src/linkdiscovery/embed/embedder.py#L89-L103)).
This is why a second run over an unchanged corpus reports 2,931/2,931 cache
hits and re-ranks in seconds.

The embedding runtime qualifies devices in preference order (`[mps, cpu]`) by
actually encoding representative inputs — framework availability alone doesn't
count — and on OOM halves the batch size and resumes from the last complete
batch. Every fallback is recorded in the run manifest; the model, precision,
and output dimension are never silently changed.

### Experiment export

The pipeline's internal embedding table is unit-oriented because retrieval
needs document, section, and title views. For reranking experiments, the
completed run can be joined with its processed-corpus artifact into one
self-contained NumPy bundle:

```bash
cd linkdiscovery
uv run linkdiscovery export-embeddings \
  --artifacts .artifacts \
  --run-id run-20260801T043353Z-0e713a7a \
  --out .artifacts/experiments/run-20260801T043353Z-0e713a7a-embeddings.npz
```

The bundle is safe to load with `allow_pickle=False` and exposes aligned
arrays:

| Array | Shape in the baseline rerun | Meaning |
| --- | ---: | --- |
| `matrix` | `(258, 512)` | normalized document-view rows |
| `document_ids` | `(258,)` | row index for `matrix` |
| `unit_matrix` | `(3184, 512)` | every semantic-unit embedding |
| `unit_ids` | `(3184,)` | row index for `unit_matrix` |
| `unit_document_ids` / `unit_views` | `(3184,)` | document and retrieval view for each unit |
| `unit_texts` | `(3184,)` | text used for token/vocabulary matching |
| `unit_source_spans_json` | `(3184,)` | source offsets for inline placement |

`matrix` is the document-level experiment surface: its row `i` is the
document whose ID is `document_ids[i]`. `unit_matrix` is the full matrix used
by retrieval, so section-level reranking and vocabulary matching do not need
to reconstruct the pipeline. A minimal document reranker starts with:

```python
import numpy as np

with np.load(".artifacts/experiments/run-...-embeddings.npz", allow_pickle=False) as bundle:
    document_ids = bundle["document_ids"].astype(str)
    matrix = bundle["matrix"]
    row_by_document = {document_id: row for row, document_id in enumerate(document_ids)}
    query_row = row_by_document["ml/nlp/word-embeddings"]
    cosine_scores = matrix @ matrix[query_row]
```

For suggested inline links, filter `unit_views` to `section`, compare the
corresponding `unit_texts` or vectors, and use the decoded source spans to
present a review location. The exporter includes evidence metadata; it does
not edit Markdown or manufacture a link without review.

### Offline anchor analysis

The first offline experiment used the baseline rerun's 2,353 ranked proposals
and compared four anchor selectors. The reproducible analysis script is
[`scripts/inline_link_analysis.py`](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/scripts/inline_link_analysis.py);
its outputs are kept under `.artifacts/experiments/`.

| Selector | What it tries | Coverage | Observation |
| --- | --- | ---: | --- |
| Descending exact n-gram | First usable shared 4-, 3-, 2-, then 1-gram | 2,331 / 2,353 | 177 four-grams, 228 three-grams, 1,114 two-grams, and 812 one-grams; the long-first rule often falls back to generic words. |
| Weighted exact phrase | Shared phrase scored by IDF, length, position, and generic-word penalty | 2,331 / 2,353 | Better than length alone in principle, but still selects code fragments or words such as `len`, `void`, and `0` without stronger span typing. |
| Natural exact phrase | Exact overlap with code-like tokens, boilerplate, and weak one-word spans rejected | 2,081 / 2,353 | Safer because it declines more often, but the remaining one-word overlaps are not sufficient evidence of a natural link. |
| Asymmetric keyphrase | Independently extract a salient phrase on each side | 2,353 / 2,353 | More coverage and more natural bidirectionality, but a naive IDF/position scorer over-selects identifiers and implementation details. |

The main conclusion is that “bidirectional” should describe the relationship,
not require the same anchor text in both notes. A strict shared n-gram can make
links read unnaturally, and it cannot help when the ranked pair is semantically
related but uses different vocabulary. Conversely, an unconstrained
keyphrase scorer invents plausible-looking but irrelevant anchors. The safe
policy is therefore: generate independent source and target mention candidates,
rerank them with the pair evidence, and allow a no-link result.

The production design should look more like mention detection plus entity
disambiguation than blind phrase matching: identify noun-phrase, named-entity,
and section-heading candidates; remove headings, `Related notes`, tables, and
code spans; then score each candidate using local grammatical context, IDF,
target-title/description similarity, section-to-document similarity, source
position, and overlap with existing links. This follows the general direction
of TextRank's graph-based salience model and PositionRank's position-biased
PageRank for keyphrases, while the sentence-embedding approach in EmbedRank is
useful for ranking candidate phrases against the target note. See
[TextRank](https://aclanthology.org/W04-3252/),
[PositionRank](https://aclanthology.org/P17-1102/), and
[EmbedRank](https://aclanthology.org/K18-1022/).

### Token-alignment preflight

The next preflight used the cached, pinned Qwen3-Embedding-0.6B model on MPS,
so it exercised contextual token representations rather than the hashing
baseline used by the deterministic rerun. It encoded 64 unique evidence units
from the top 50 ranked proposals.

Unrestricted Smith-Waterman over the token similarity matrix over-aligned long
stretches of headings, prose, and code-like material, so its raw score is not
a suitable anchor selector. Markdown-aware prose candidates capped at 1–10
words plus bounded, bidirectional MaxSim produced spans for 48/50 pairs, with
a median span size of two words and median symmetric MaxSim of 0.4232.

As a separate candidate-recall audit, the same span generator recovered 1,142
of 1,451 existing explicit-link anchors (78.7%). This is only a preflight
recall measurement: existing links include boilerplate and `Related notes`
locations that should not necessarily be eligible for new inline links. The
bounded experiment validates the mechanics, not automatic link quality;
salience, prose-region filtering, target-document relevance, and human
precision measurement are still required before adding it to the main
pipeline. Detailed output is kept in
`.artifacts/experiments/token-alignment-preflight.md` and its JSON companion.

## Algorithm

**Views.** Each note is decomposed into three retrieval views: a bounded
`document` view (title, description, headings, leading content), `section`
chunks (grouped under their lowest heading, split at region boundaries,
carrying their heading path as context), and a `title` view. Chunk sizes are
measured with the actual model tokenizer, not word counts.

**High-recall retrieval.** For every unit in every view, cosine top-k
neighbors are retrieved (k = 50 per unit). Exact search runs as blocked
matrix products so memory stays bounded; an HNSW backend takes over past 50k
units:

```python
def exact_top_k(
    table: VectorTable,
    k: int,
    *,
    query: VectorTable | None = None,
    block_size: int = 1024,
) -> list[list[tuple[int, float]]]:
    """Blocked exact cosine top-k over normalized vectors. ..."""
```

[retrieval.py#L88-L104](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/src/linkdiscovery/candidates/retrieval.py#L88-L104)

Unit matches collapse into canonical unordered document pairs; self-pairs,
alias-equivalent pairs, excluded documents, and already-linked pairs are
removed here, so novelty never has to compete with existing links downstream.

**Hubness correction.** Raw cosine similarity favors "hub" notes that sit
near everything (surveys, index-like pages) and long notes that get more
chances at a lucky maximum. Every pair similarity is therefore corrected by
both endpoints' local neighborhood density — CSLS local scaling
(Conneau et al. 2018): `csls = 2·sim − density(a) − density(b)`, where a
document's density is its mean similarity to its 10 nearest neighbors. The
same correction applies at section level:

```python
flat = np.sort(sims, axis=None)[::-1]
best = float(flat[0])
top_r = float(flat[: min(TOP_R_SECTIONS, flat.shape[0])].mean())
tied = np.argwhere(sims >= flat[0])
best_source, best_target = min((source_ids[i], target_ids[j]) for i, j in tied)
csls_best = (
    2.0 * best - self._density.get(best_source, 0.0) - self._density.get(best_target, 0.0)
)
```

[generator.py#L347-L354](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/src/linkdiscovery/candidates/generator.py#L347-L354)

**Ranking.** The ranker is an interpretable weighted model over normalized
features — no learned weights in v1, so every score decomposes into
inspectable terms. Bridges between disconnected graph neighborhoods are
rewarded; hubs, near-duplicates, and pairs already connected through a short
graph path are penalized:

```python
score = clamp01(
    weights["w_document"] * normalized["csls_similarity_norm"]
    + weights["w_local"] * normalized["best_chunk_similarity_norm"]
    + weights["w_breadth"] * normalized["support_breadth_norm"]
    + weights["w_lexical"] * normalized["lexical_similarity_norm"]
    + weights["w_bridge"] * bridge
    - weights["w_hub"] * hub
    - weights["w_duplicate"] * near_duplicate
    - weights["w_redundancy"] * redundancy
)
```

[ranker.py#L383-L392](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/src/linkdiscovery/ranking/ranker.py#L383-L392)

Each proposal also exposes three separate estimates — *relatedness* (semantic
strength), *usefulness* (would a link help a reader), and *missingness*
(confidence the relationship is truly absent) — plus a confidence band that
recalibrates against accumulated accept/reject decisions. Link direction comes
from placement evidence: the note whose *section* best matches the other
note's document view hosts the link; symmetric evidence yields an undirected
proposal. Per-note results are reordered by maximal marginal relevance so
near-identical targets don't crowd the review queue.

## Usage

```bash
cd linkdiscovery
uv sync --extra embeddings   # or plain `uv sync` for the no-download baseline

: "Full run with Qwen3-Embedding-0.6B on MPS (falls back to CPU)"
uv run linkdiscovery run --config configs/notes.yaml --artifacts .artifacts

: "Weak-supervision quality check: hide 15% of existing links"
uv run linkdiscovery evaluate --config configs/notes.yaml --artifacts .artifacts \
  --holdout-fraction 0.15 --seed 7

: "Stratified review queue: top-ranked, near-threshold, random, and sparse regions"
uv run linkdiscovery review-queue --proposals .artifacts/reports/proposals.jsonl \
  --size 25 --seed 7

: "Export document and unit matrices for reranking and inline-link experiments"
uv run linkdiscovery export-embeddings --artifacts .artifacts \
  --run-id run-20260801T043353Z-0e713a7a \
  --out .artifacts/experiments/run-20260801T043353Z-0e713a7a-embeddings.npz
```

The whole pipeline is one declarative config
([configs/notes.yaml](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/configs/notes.yaml));
unknown fields are hard errors, the model is pinned to an immutable revision,
and the resolved config lands in the run manifest. Reports are written to
`.artifacts/reports/`: `proposals.jsonl` is the machine artifact (every
feature and evidence span), `proposals.md` is the human review document with
per-proposal checklists. Review decisions persist as durable data and feed
back into confidence calibration on the next run.

`candidates.existing_relationship_policy` controls the opt-in existing-link
behavior for token/lexical suggestion experiments. `exclude` is the default
and preserves missing-link discovery semantics. `penalize` or `reward` keeps
existing direct-link pairs in the candidate set and emits an
`existing_link_adjustment` of `-1` or `+1`; `ranking.weights.w_existing_link`
controls its score contribution. The policy is recorded in the resolved run
configuration and changing it invalidates candidate artifacts.

On the current corpus snapshot, the deterministic CPU baseline rerun processed
258 notes and 3,184 units, generated 8,714 candidate pairs, and produced
2,353 proposals. The run is reproducible from
[issue #119](https://github.com/elimelt/notes/issues/119); the earlier neural
MPS run proposed 2,292 candidate links and recovered held-out existing links
at recall@25 ≈ 0.20 with untuned default weights. These are qualification
measurements, not evidence that more proposals means better links.

## Learned inline links (v2)

The pair-level pipeline above answers "which notes should be connected."
Version 2 —
[`SPEC-INLINE-LINKING.md`](https://github.com/elimelt/notes/blob/6ae85f5a2b35d18beb83eaf7882f0e89e724b315/linkdiscovery/SPEC-INLINE-LINKING.md),
implemented in
[`linkdiscovery/inline/`](https://github.com/elimelt/notes/tree/6ae85f5a2b35d18beb83eaf7882f0e89e724b315/linkdiscovery/src/linkdiscovery/inline)
— answers the harder question: *which exact phrase in a note should become a
link, pointing where?* It is framed as staged, closed-world mention detection
plus entity linking with an explicit no-link option (the BLINK / Wikimedia
add-a-link pattern), not relation extraction and not a joint model.

**Audit gates everything.** Existing links are weak supervision, not gold, so
the first shipped piece is an annotation workflow: a 150-link stratified
sample, a terminal labeling tool, Cohen's κ / Krippendorff's α agreement, and
a go/no-go gate (κ ≥ 0.6 and ≥ 150 clean positives). Each judged link routes
to a supervision tier — the key rule being that Related-notes/heading/table
links are correct *edges* but terrible *anchor* examples:

```python
def derive_tier(
    target_correct: bool,
    anchor_natural: bool,
    placement_valid: bool,
    region_kind: LinkRegionKind,
) -> Tier:
    """Map one audit judgment onto a supervision tier per SPEC-INLINE-LINKING §4.

    1. Wrong target -> Tier D ("exclude or use as negatives") ...
    2. Graph-only region -> at best Tier C ("graph supervision only") ...
    3. Prose-like region with a natural anchor and valid placement -> Tier A ...
    4. Prose-like region, correct target, but an unnatural anchor or
       invalid placement -> Tier B ...
    """
```

[audit/tiers.py#L50-L71](https://github.com/elimelt/notes/blob/6ae85f5a2b35d18beb83eaf7882f0e89e724b315/linkdiscovery/src/linkdiscovery/inline/audit/tiers.py#L50-L71)

**Architecture A: frozen encoder, three small heads.** The encoder is never
fine-tuned; only tiny heads train (minutes on MPS): a naturalness MLP over
Lee/SpanBERT-style span representations (`[start | end | mean-interior |
width | hand features]`), target retrieval as a full-catalog softmax (at ~258
targets the entire catalog fits in every step — no in-batch-negative
approximation), and a reranker head. Unlinked spans are treated with
positive-unlabeled discipline — an unlinked "MapReduce" is usually a
true-but-unauthored link, not a negative — via class-prior weighting and
cross-encoder-confirmed negatives (the RocketQA hazard). Candidate anchors
come from a self-corpus anchor dictionary with Milne–Witten keyphraseness
(link-probability floor 6.5%), and hard rules live outside the learned
scores entirely: candidate spans can never overlap existing links, code,
math, or frontmatter.

**Three scores stay separate until selection.** A collapsed score cannot
express "right target, wrong anchor," so naturalness, target correctness,
and placement validity are combined only at global selection — by a
geometric mean, so any near-zero head vetoes:

```python
def combine_scores(
    naturalness: float,
    target_correctness: float,
    placement_validity: float,
    weights: Mapping[str, float],
) -> float:
    """Weighted geometric mean of the three head scores (spec §6 Q24).

    ... The geometric mean is chosen over an arithmetic one because it
    vetoes: any near-zero head drives the combined score toward zero, so a
    wrong target cannot be rescued by a beautiful anchor.
    """
```

[select.py#L150-L167](https://github.com/elimelt/notes/blob/6ae85f5a2b35d18beb83eaf7882f0e89e724b315/linkdiscovery/src/linkdiscovery/inline/select.py#L150-L167)

Selection then applies temperature-scaled (or split-conformal, with a
finite-sample `P(accepted ∧ wrong) ≤ ε` guarantee) acceptance thresholds, a
per-note budget (~1 link per 175 words, capped — Wikipedia server-log studies
show links compete for attention and most added links are never clicked), and
MMR diversity.

**Status.** Phases 1–3 are built and offline-only:

```bash
uv run linkdiscovery inline audit-sample --config configs/notes.yaml \
  --artifacts .artifacts --size 150 --seed 7 --out .inline/audit
uv run linkdiscovery inline annotate --sample .inline/audit/audit-sample.json \
  --annotator you --labels .inline/audit/labels-you.jsonl
uv run linkdiscovery inline recall-check --config configs/notes.yaml \
  --artifacts .artifacts --sample .inline/audit/audit-sample.json
uv run linkdiscovery inline propose --config configs/notes.yaml \
  --artifacts .artifacts --engine baseline --out .inline/proposals
```

On this corpus the span generator covers 93% of audited prose anchors (spec
gate: ≥ 85%). Nothing in this subsystem edits notes: like v1, it emits
proposals for review.

**Results.** The full loop has now run end to end. The audit (300
stratified links, two independent annotators, one guideline-refinement
round after κ on anchor-naturalness dropped to 0.41 on title-shaped
anchors — the exact underspecification the spec predicted) finished at
κ(target) = 1.00, κ(anchor natural) = 0.98, κ(placement) = 0.88, with
consensus tiers 124 A / 29 B / 147 C / 0 D → GO. The single best corpus
finding: **zero wrong-target links in 300 audited** — all link noise here
is anchor phrasing (long title-dump anchors) and duplicated Related-notes
placements, never the destination.

Training on those labels produced a clean natural experiment in encoder
choice. With the test-grade hashing token encoder, the retrieval head
never beat uniform (held-out recall@1 = 0.0); swapping in windowed Qwen
token states fixed it outright (recall@1 = 0.964, tying the anchor
dictionary), confirming the spec's §9 prediction that token-level
representations were the bottleneck. The binding constraint then moved to
the **naturalness head** (AUC 0.664 against only 9 held-out negative
anchors) — a label-limited problem, so by the spec's own decision
thresholds the verdict is *plateau*: the audited deterministic baseline
(keyphraseness + anchor dictionary + embedding features) remains the
production engine, with the learned engine as a supplementary stream. The
baseline's high-confidence list — **91 anchored links across 67 notes**
at threshold 0.65 — is published for review in
[PR #138](https://github.com/elimelt/notes/pull/138), alongside the full
evaluation tables. Next lever per the spec: Wikipedia-keyphraseness
pretraining for the naturalness head and more negative anchor labels,
not LoRA.

## Edge cases or limits

- Existing links are biased supervision: recovery metrics measure agreement
  with past linking habits, not the value of genuinely novel links. Human
  precision-at-k from review decisions is the primary quality metric.
- Proposal IDs currently embed direction, so a direction flip between runs
  orphans that pair's earlier review decision (it is ignored, not misapplied).
- Notebook-generated notes should receive links in their sources; edits to the
  generated Markdown are lost on regeneration.
- `exclude` remains the safe default for existing direct links. `reward` is
  useful for learning from positive linking behavior, while `penalize` is
  useful when the token-based phase should prefer genuinely novel suggestions;
  either opt-in mode can surface already-linked pairs and therefore is not a
  replacement for the missing-link review queue.

## Sources

- [SPEC.md — the full design contract](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/SPEC.md)
- [Issue #54 — first-run proposals and evaluation](https://github.com/elimelt/notes/issues/54)
- [Issue #119 — baseline rerun and experiment export](https://github.com/elimelt/notes/issues/119)
- [PR #63 — pipeline implementation](https://github.com/elimelt/notes/pull/63) and [PR #59 — applied links](https://github.com/elimelt/notes/pull/59)
- [SPEC-INLINE-LINKING.md — learned inline-link design contract](https://github.com/elimelt/notes/blob/6ae85f5a2b35d18beb83eaf7882f0e89e724b315/linkdiscovery/SPEC-INLINE-LINKING.md) and [PR #135 — inline subsystem implementation](https://github.com/elimelt/notes/pull/135)
- [Gerlach et al. 2021 — Wikimedia add-a-link](https://arxiv.org/abs/2105.15110), [Milne & Witten 2008 — Learning to Link with Wikipedia](https://doi.org/10.1145/1458082.1458150), [Paranjape et al. 2016 — Improving Website Hyperlink Structure Using Server Logs](https://doi.org/10.1145/2835776.2835832)
- [Conneau et al. 2018 — CSLS hubness correction](https://arxiv.org/abs/1710.04087)
- [Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Mihalcea & Tarau 2004 — TextRank](https://aclanthology.org/W04-3252/)
- [Florescu & Caragea 2017 — PositionRank](https://aclanthology.org/P17-1102/)
- [Bennett et al. 2018 — EmbedRank](https://aclanthology.org/K18-1022/)

## Related notes

- [[ml/recommender-systems/retrieval-and-ranking|Retrieval and ranking]]
- [[ml/nlp/reading/information-retrieval|Information retrieval]]
- [[ml/recommender-systems/two-tower-retrieval|Two-tower retrieval]]
