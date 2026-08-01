---
title: Missing-Link Discovery Pipeline
category: Software Engineering
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
  - title: "Word Translation Without Parallel Data (CSLS), Conneau et al. 2018"
    url: https://arxiv.org/abs/1710.04087
    type: paper
  - title: Qwen3-Embedding-0.6B model card
    url: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
    type: docs
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
merged in [#59](https://github.com/elimelt/notes/pull/59).

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

# Full run with Qwen3-Embedding-0.6B on MPS (falls back to CPU):
uv run linkdiscovery run --config configs/notes.yaml --artifacts .artifacts

# Weak-supervision quality check: hide 15% of existing links, measure recovery:
uv run linkdiscovery evaluate --config configs/notes.yaml --artifacts .artifacts \
  --holdout-fraction 0.15 --seed 7

# Stratified review queue (top-ranked / near-threshold / random / sparse regions):
uv run linkdiscovery review-queue --proposals .artifacts/reports/proposals.jsonl \
  --size 25 --seed 7
```

The whole pipeline is one declarative config
([configs/notes.yaml](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/linkdiscovery/configs/notes.yaml));
unknown fields are hard errors, the model is pinned to an immutable revision,
and the resolved config lands in the run manifest. Reports are written to
`.artifacts/reports/`: `proposals.jsonl` is the machine artifact (every
feature and evidence span), `proposals.md` is the human review document with
per-proposal checklists. Review decisions persist as durable data and feed
back into confidence calibration on the next run.

On this corpus (242 notes, 2,931 units), a cold run embeds in a few minutes on
MPS; warm re-runs are all cache hits. The first run proposed 2,292 candidate
links, and recovered held-out existing links at recall@25 ≈ 0.20 with untuned
default weights — the baseline the qualification loop is meant to beat.

## Edge cases or limits

- Existing links are biased supervision: recovery metrics measure agreement
  with past linking habits, not the value of genuinely novel links. Human
  precision-at-k from review decisions is the primary quality metric.
- Proposal IDs currently embed direction, so a direction flip between runs
  orphans that pair's earlier review decision (it is ignored, not misapplied).
- Notebook-generated notes should receive links in their sources; edits to the
  generated Markdown are lost on regeneration.

## Sources

- [SPEC.md — the full design contract](https://github.com/elimelt/notes/blob/feb11ef355944ddfcac5848cb32c17b66623a57b/SPEC.md)
- [Issue #54 — first-run proposals and evaluation](https://github.com/elimelt/notes/issues/54)
- [PR #63 — pipeline implementation](https://github.com/elimelt/notes/pull/63) and [PR #59 — applied links](https://github.com/elimelt/notes/pull/59)
- [Conneau et al. 2018 — CSLS hubness correction](https://arxiv.org/abs/1710.04087)
- [Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

## Related notes

- [[ml/recommender-systems/retrieval-and-ranking|Retrieval and ranking]]
- [[ml/nlp/reading/information-retrieval|Information retrieval]]
- [[ml/recommender-systems/two-tower-retrieval|Two-tower retrieval]]
