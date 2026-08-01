# linkdiscovery

Given a corpus of semi-structured documents and its existing explicit links,
`linkdiscovery` proposes high-value **missing** links: document pairs that are
semantically strong, not already connected, and worth a direct navigational
link. Every proposal carries raw feature values and span-level evidence so a
human can judge it; the pipeline never modifies source documents. It runs
locally (Apple MPS preferred, CPU fallback), caches aggressively so only
changed inputs are recomputed, and records everything needed to reproduce a
run. See `../SPEC.md` for the normative specification.

## Stage flow

```text
raw content
  -> source adapter
  -> canonical documents and existing relationships
  -> preprocessing and semantic units
  -> embeddings and retrieval views
  -> high-recall candidate generation
  -> pair aggregation and feature extraction
  -> filtering, ranking, and calibration
  -> review artifacts
```

Each boundary exchanges a typed, serializable, versioned artifact; each stage
is callable independently from its serialized input. The `Pipeline`
orchestrator wires the default implementations together; the `linkdiscovery`
CLI wraps the orchestrator.

## Quickstart

```sh
cd linkdiscovery
uv sync                      # create the environment (Python 3.12)

# Smoke run with the no-download hashing baseline against the notes corpus
# at ../content (paths in the config are relative to this directory):
uv run linkdiscovery run \
    --config configs/notes-baseline.yaml \
    --artifacts .artifacts

# Read the review report:
open .artifacts/reports/proposals.md      # human review document
head .artifacts/reports/proposals.jsonl   # machine artifact, one proposal/line

# Quantify: hide 20% of existing links and measure recovery.
uv run linkdiscovery evaluate \
    --config configs/notes-baseline.yaml \
    --artifacts .artifacts --holdout-fraction 0.2 --seed 7

# Build a stratified human review queue from a run's proposals:
uv run linkdiscovery review-queue \
    --proposals .artifacts/reports/proposals.jsonl \
    --size 25 --seed 7 --out review-queue.jsonl
```

`configs/notes.yaml` is the quality configuration (a real
sentence-transformers embedding model; requires
`uv sync --extra embeddings` and downloads the model on first use).
`configs/notes-baseline.yaml` is identical except for the embedding section:
the deterministic hashing provider, which is also the SPEC's compact baseline
that a real model must beat on held-out recovery. Add `-v` to any command for
INFO logging on stderr (`-vv` for DEBUG); errors print as `error: <message>`
and exit with code 2.

Python API equivalent:

```python
from pathlib import Path
from linkdiscovery import Pipeline, load_config

config = load_config("configs/notes-baseline.yaml")
result = Pipeline().run(config, artifacts_root=Path(".artifacts"))
print(len(result.proposals.proposals), "proposals")
print(result.report_dir)  # rendered reports
```

## Configuration reference

One YAML document composes the pipeline. Unknown fields anywhere are errors;
the fully resolved configuration is written to the run manifest. The
**invalidates** column tells you what gets recomputed when a field changes —
each section has its own fingerprint, so changing ranking weights never
re-embeds anything.

| Field | Default | Notes / invalidates |
| --- | --- | --- |
| `schema_version` | required (`1`) | must match the build's config schema |
| `source.adapter` | required | `"package.module:Attr"` plugin spec; must satisfy `SourceAdapter` |
| `source.options` | `{}` | opaque, adapter-defined; changing the corpus content invalidates everything downstream of the changed documents |
| `preprocess.parser` | required | plugin spec; must satisfy `RegionParser`. Any change here invalidates processed units and everything downstream |
| `preprocess.views` | `[document, section, title]` | retrieval views to build |
| `preprocess.target_tokens` | `384` | chunk size target, measured with the model tokenizer |
| `preprocess.max_tokens` | `512` | hard chunk bound (`>= target_tokens`) |
| `preprocess.overlap_tokens` | `48` | overlap when a split crosses continuous prose (`< target_tokens`) |
| `preprocess.include_regions` | title, heading, prose, list, code, equation, table, citation | region kinds embedded |
| `preprocess.exclude_regions` | `[boilerplate]` | region kinds dropped (disjoint from include) |
| `embedding.provider` | `sentence-transformers` | `sentence-transformers` or `hashing`. Any change in this section invalidates embeddings, candidates, and proposals — but never processed units |
| `embedding.model` | required | model id (`Qwen/Qwen3-Embedding-0.6B`, …) or a label for the hashing profile |
| `embedding.revision` | required | immutable model revision; pin before production runs |
| `embedding.dimensions` | required | output dimensions (hash buckets for the baseline) |
| `embedding.normalize` | `true` | L2-normalize vectors |
| `embedding.device_preference` | `[mps, cpu]` | ordered; each device is qualified with a real encoding probe. Device choice does **not** invalidate caches |
| `embedding.precision` | `float16` | `float32`, `float16`, or `bfloat16` |
| `embedding.batch_size` | `auto` | positive integer or `auto`; halved automatically on OOM. Not a cache key |
| `embedding.instruction` | `null` | instruction prefix for instruction-aware models |
| `embedding.max_input_tokens` | `null` | input cap; exceeding it counts as a truncation |
| `candidates.backend` | `auto` | `auto`, `exact`, or `hnsw`; `auto` switches by corpus size. Changing this section invalidates candidates and proposals only |
| `candidates.neighbors_per_unit` | `50` | high-recall retrieval breadth |
| `candidates.existing_relationship_kinds` | `[explicit-link]` | relationship kinds treated as an existing direct link |
| `candidates.existing_relationship_policy` | `exclude` | `exclude` preserves missing-link semantics; `penalize` or `reward` retains existing pairs with a signed token/lexical feature |
| `candidates.max_pairs_per_document` | `100` | per-document recall bound |
| `candidates.max_total_pairs` | `null` | global bound (`null` = unbounded) |
| `ranking.profile` | `weighted-v1` | ranker policy name. Changing this section invalidates proposals only |
| `ranking.weights` | SPEC formula defaults | weights for every score term; unknown names are errors |
| `ranking.minimum_relatedness` | `0.0` | floor on the relatedness estimate |
| `ranking.results_per_document` | `10` | presentation cap per source document |
| `ranking.diversity` | `0.2` | maximal-marginal-relevance trade-off in `[0, 1]` |

The optional `candidates.existing_relationship_policy` is intended for the
token/lexical suggestion phase. `exclude` is the default and keeps existing
direct links out of missing-link proposals. `penalize` and `reward` retain
those pairs and expose `existing_link_adjustment` as `-1` or `+1`; the
`ranking.weights.w_existing_link` value controls how much that signal moves a
score. Changing this candidate policy invalidates candidates and proposals,
while changing only its ranking weight invalidates proposals.
| `report.formats` | `[jsonl, markdown]` | also `json`. Changing this section invalidates rendered reports only |
| `report.output_dir` | `reports` | relative paths resolve against the artifacts root |
| `report.include_evidence_text` | `true` | `false` omits excerpt text but keeps ids, spans, similarities |

## Architecture

### Core vs adapter

The core (`src/linkdiscovery`) knows nothing about Markdown, Quartz, Git,
file layouts, or link syntax. Document and unit IDs are opaque strings.
Host knowledge lives in adapter packages behind two plugin points:

- `source.adapter` → a `SourceAdapter` (document identity, aliases, existing
  relationships, exclusion flags, human-facing references);
- `preprocess.parser` → a `RegionParser` (typed regions from raw content).

`src/linkdiscovery_markdown` is the first host integration: a directory of
Markdown notes with frontmatter, wikilinks, and standard links. Plugins are
addressed as `"package.module:Attr"`, resolved and Protocol-checked at run
start.

Stage implementations behind the SPEC Protocols:

| Stage | Implementation |
| --- | --- |
| Preprocess | `DefaultPreprocessor` (+ `SimpleTokenCounter` / `HuggingFaceTokenCounter`) |
| Embed | `DefaultEmbedder` over the `hashing` / `sentence-transformers` providers |
| Candidates | `DefaultCandidateGenerator` (exact or HNSW retrieval, CSLS hubness correction) |
| Rank | `WeightedRanker` (interpretable weighted formula, MMR diversity, calibration) |
| Report | `DefaultReporter` (JSONL, JSON, Markdown) |
| Orchestration | `Pipeline.run` / `Pipeline.evaluate_holdout` |

### Artifact groups

A run persists every stage output in a content-addressed store under
`--artifacts`:

```text
artifacts/
  corpus-manifest/    frozen snapshot: ids, revisions, flags, relationships (no content)
  processed-corpus/   regions + semantic units, keyed by corpus x preprocessing fingerprint
  embeddings/         index JSON + vector tables (.npz), keyed by ...x model fingerprint
  candidates/         high-recall pair set, keyed by ...x candidate config
  proposals/          ranked proposal set, keyed by ...x ranking config
  reports/            rendered proposals.jsonl / proposals.md
  reviews/            durable review histories (written by tooling, read via --reviews)
  runs/               run manifests (run-<id>) and evaluation results (eval-<id>)
  cache/              per-unit embedding vectors, fingerprint-keyed
```

All writes are atomic (temp file + rename). The run manifest is written
**last**, so a manifest's existence proves the run completed; it records the
resolved configuration, corpus and relationship fingerprints, per-stage wall
time and counters, cache hits/misses, device and fallback events, dependency
versions, seeds (empty — the batch flow is deterministic), and a reference to
every artifact written.

### Cache keys and the fingerprint chain

The per-unit embedding cache key is

```text
hash(unit_content_hash, preprocessing_fingerprint, model_fingerprint,
     output_affecting_runtime_options)
```

Paths, modification times, device, and batch size are deliberately not keys:
they change how vectors are computed, not what they are. The fingerprint
chain composes upward — configuration section → stage fingerprint → artifact
key — which is what makes invalidation exact: edit one document and only its
units re-embed; change `preprocess.target_tokens` and everything re-chunks
and re-embeds; change `ranking.weights` and only proposals and reports are
recomputed.

## Inline-link discovery (experimental)

Where the main pipeline proposes *document pairs*, the inline subsystem
proposes **anchored inline links**: a specific span of prose in one note
pointing at another note, with an explicit no-link rejection option. It is a
staged mention-detection + closed-world entity-linking pipeline (span
proposal → naturalness → target retrieval → rerank → calibrated rejection →
sparse global selection) specified in `SPEC-INLINE-LINKING.md`; read that
document for the design rationale, quality bars, and literature grounding.

The build is phased (SPEC §11), and the phases are strictly ordered — each
later stage is gated on the one before it:

1. **Audit** — sample ~150 existing links stratified by region/anchor
   length/topic/source type, label them with two annotators, and compute
   Cohen's κ / Krippendorff's α plus the A/B/C/D supervision-tier
   distribution. *Go/no-go gate:* every per-field κ ≥ 0.6 **and** ≥ 150
   clean Tier A+B positives → proceed to modeling; κ < 0.4 on naturalness →
   re-scope the annotation guidelines instead of training on incoherent
   labels.
2. **Recall check** — verify the deterministic high-recall span generator
   actually covers the audited prose anchors. *Kill criterion:* overlap
   recall < ~85% means no downstream model can recover — fix generation
   first.
3. **Train** — Architecture A: a frozen token encoder plus three small
   trained heads (naturalness, full-catalog-softmax retrieval, reranker),
   with PU-weighted pseudo-negatives and denoised hard negatives.
4. **Propose** — either engine writes a review report; nothing ever edits
   source documents. *Kill criterion:* if the learned engine cannot reach
   precision@1 ≈ 0.70 at ≥ 20% recall on the frozen benchmark, ship the
   deterministic baseline engine instead (it is always available and needs
   zero training data).

Exact CLI walkthrough for this repo's notes corpus (run from
`linkdiscovery/`; `configs/notes.yaml` targets `../content`):

```sh
# Phase 1: draw and annotate the stratified audit sample.
uv run linkdiscovery inline audit-sample \
    --config configs/notes.yaml --artifacts .artifacts \
    --size 150 --seed 7 --out .inline/audit
uv run linkdiscovery inline annotate \
    --sample .inline/audit/audit-sample.json \
    --annotator you --labels .inline/audit/labels-you.jsonl
# (second annotator labels an overlapping subset into labels-other.jsonl)
uv run linkdiscovery inline audit-report \
    --sample .inline/audit/audit-sample.json \
    --labels .inline/audit/labels-you.jsonl \
    --labels2 .inline/audit/labels-other.jsonl   # prints kappa/alpha + GO/NO-GO

# Anchor dictionary + keyphraseness statistics (SPEC §5 weak supervision).
uv run linkdiscovery inline anchors \
    --config configs/notes.yaml --artifacts .artifacts --out .inline/anchors

# Phase 2: the recall-ceiling gate.
uv run linkdiscovery inline recall-check \
    --config configs/notes.yaml --artifacts .artifacts \
    --sample .inline/audit/audit-sample.json

# Deterministic baseline engine (works with zero training data).
uv run linkdiscovery inline propose \
    --config configs/notes.yaml --artifacts .artifacts \
    --engine baseline --out .inline/proposals

# Phase 3: train the three heads on the audited labels, then propose.
uv run linkdiscovery inline train \
    --config configs/notes.yaml --artifacts .artifacts \
    --sample .inline/audit/audit-sample.json \
    --labels .inline/audit/labels-you.jsonl \
    --out .inline/heads --epochs 30 --seed 0
uv run linkdiscovery inline propose \
    --config configs/notes.yaml --artifacts .artifacts \
    --engine learned --heads .inline/heads --out .inline/proposals-learned
```

`inline propose` accepts `--threshold`, `--budget-words`, and
`--max-per-note` to override the selection defaults (accept threshold 0.5,
~1 link per 175 words, hard cap 10 per note). Review output lands as
`inline-proposals.md` (accepted links grouped by note, anchor shown in
context, three head scores; anchor-improvement suggestions flagged) plus
`inline-proposals.jsonl` (every draft including audited abstentions).

Honesty note on encoders: the default token encoder is the dependency-free
hashing baseline, which makes every command runnable without downloads — its
representations are for wiring and testing, not quality. The production path
injects the frozen Qwen token encoder
(`linkdiscovery.inline.encode.QwenTokenEncoder`) through the workflow API's
`encoder_factory`; the learned path re-derives target vectors in that
encoder's hidden space (the v1 bi-encoder vectors are used only by the
baseline engine's cosine feature).

## Development

```sh
uv sync                        # environment (dev tools included)
uv run pytest -q               # tests (fixture corpus end-to-end included)
uv run mypy src                # strict type checking
uv run ruff check .            # lint
uv run ruff format --check .   # formatting
```

Optional extras: `linkdiscovery[embeddings]` (sentence-transformers, torch)
for real models, `linkdiscovery[ann]` (hnswlib) for approximate retrieval on
large corpora. Tests requiring them skip cleanly when absent.

## Moving out of this repo

The project is self-contained and designed to be lifted out wholesale:

- everything lives under `linkdiscovery/` with its own `pyproject.toml`,
  lockfile, and test suite; nothing imports from the surrounding notes repo;
- the core package has zero host knowledge — corpora enter only through the
  `SourceAdapter`/`RegionParser` plugin specs in configuration;
- `linkdiscovery_markdown` is separable: it depends on the core's public
  contracts only, so it can move to its own distribution (or stay behind)
  without touching core code;
- the `configs/*.yaml` files are the only place the notes corpus path
  (`../content`) appears — point `source.options.root` anywhere.

Per the SPEC, keep runs manually invoked or batch-scheduled; do not fold the
pipeline into a website's production build.
