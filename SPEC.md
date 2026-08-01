# Missing-Link Discovery Pipeline

Status: proposed

## Problem statement

Given a corpus of semi-structured documents and its existing explicit links,
build a reusable batch pipeline that proposes high-value missing links. The
system must favor semantically strong document pairs that are not already
linked, preserve enough evidence for a human to judge each proposal, and run
locally with accelerator fallback.

The pipeline must be composable. Content ingestion, preprocessing, embedding,
candidate generation, ranking, and presentation need stable boundaries so each
stage can be tested, cached, and replaced independently. Knowledge of a host
repository's file layout, markup, metadata, and link syntax belongs in an
adapter. The core pipeline must not depend on Markdown, Quartz, Git, a specific
filesystem, or a particular vector database.

Semantic similarity is necessary but insufficient. Two documents may be
similar because they duplicate each other, share boilerplate, belong to a broad
topic, or cite the same source. A useful proposal must answer a stronger
question: would a reader benefit from a direct navigational link between these
documents, and where is the evidence for placing it?

The initial system proposes links for review. It does not modify source
documents.

## Goals

- Discover strong, currently absent relationships between documents.
- Produce ranked candidates with inspectable source evidence.
- Support document-level and section-level semantic matching.
- Run locally, preferring Apple MPS when available and falling back to CPU.
- Use a quality-first embedding model while keeping the model replaceable.
- Recompute only artifacts affected by a content or configuration change.
- Learn from accepted and rejected proposals without requiring training in the
  first version.
- Support corpora ranging from hundreds to hundreds of thousands of documents.
- Keep all intermediate artifacts versioned, reproducible, and auditable.

## Non-goals

- Automatically inserting links in source documents.
- Treating model-generated relationships as established facts.
- Building a general knowledge graph or extracting arbitrary subject-predicate-
  object triples.
- Reorganizing a corpus, assigning categories, or generating content.
- Replacing lexical search or the host application's navigation.
- Requiring an LLM, hosted API, graph database, or GPU service.

## Design principles

1. **Adapters own source semantics.** The host integration defines document
   identity, parsing, aliases, existing links, and exclusions.
2. **Stages exchange data, not framework objects.** Every boundary uses a
   typed, serializable, versioned artifact.
3. **Retrieval and judgment are separate.** Candidate generation optimizes
   recall. Ranking estimates whether a candidate is worth linking.
4. **Evidence survives aggregation.** A document score always points back to
   the sections that produced it.
5. **Existing links are weak supervision.** They inform evaluation and
   calibration, but do not define all valid relationships.
6. **No silent fallback.** Device, precision, model revision, cache reuse, and
   runtime fallbacks are recorded in the run manifest.
7. **Human decisions are durable data.** Accepted, rejected, and deferred
   candidates become reusable evaluation and calibration records.

## System boundary

The logical flow is:

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

The user's shorter model remains the public mental model:

```text
raw content -> preprocessing -> embedding -> algorithm
```

The `algorithm` stage is internally split because candidate retrieval, scoring,
and reporting have different quality targets and invalidation rules.

## Terminology

- **Document:** A source item that may be a link endpoint.
- **Relationship:** An existing explicit connection between two document IDs.
- **Region:** A typed span such as a heading, paragraph, code block, equation,
  table, citation, or metadata field.
- **Semantic unit:** A deterministic piece of a document sent to an embedder.
- **Retrieval view:** A representation used for matching, such as a whole-note
  view, title and headings, or a section chunk.
- **Candidate pair:** Two documents returned by high-recall retrieval.
- **Proposal:** A ranked candidate with direction, evidence, and review state.
- **Run:** One execution against an immutable corpus manifest and configuration.

## Public interfaces

The public API should remain small. Names below are illustrative; the data
contracts are normative.

```python
corpus = source_adapter.load(source_config)
processed = preprocessor.process(corpus, preprocess_config)
embedding_index = embedder.embed(processed, embedding_config, cache)
candidates = candidate_generator.generate(
    processed,
    embedding_index,
    corpus.relationships,
    candidate_config,
)
proposals = ranker.rank(candidates, ranking_config, review_history)
reporter.write(proposals, report_config)
```

Each stage must also be callable independently from its serialized input
artifact.

### Source adapter

```python
class SourceAdapter(Protocol):
    def load(self, config: SourceConfig) -> Corpus: ...
```

The adapter is responsible for:

- Discovering source documents.
- Assigning stable document IDs.
- Supplying raw content and media type.
- Resolving aliases and redirects to canonical IDs.
- Extracting existing explicit relationships.
- Marking generated, archived, private, duplicate, or excluded content.
- Converting source locations into human-facing references.

The core never opens repository files or parses source-specific link syntax.

### Preprocessor

```python
class Preprocessor(Protocol):
    def process(self, corpus: Corpus, config: PreprocessConfig) -> ProcessedCorpus: ...
```

The preprocessor converts canonical source content into typed regions and
semantic units. Format-specific parsing may be supplied as an adapter plugin,
but chunking and normalization policies remain independently configurable.

### Embedder

```python
class Embedder(Protocol):
    def embed(
        self,
        corpus: ProcessedCorpus,
        config: EmbeddingConfig,
        cache: ArtifactCache,
    ) -> EmbeddingIndex: ...
```

The interface returns normalized vectors plus model and runtime provenance. It
must not expose PyTorch, MLX, NumPy, or sentence-transformers objects across the
boundary.

### Candidate generator

```python
class CandidateGenerator(Protocol):
    def generate(
        self,
        corpus: ProcessedCorpus,
        index: EmbeddingIndex,
        relationships: RelationshipSet,
        config: CandidateConfig,
    ) -> CandidateSet: ...
```

This stage retrieves a bounded, high-recall set. It does not make final link
decisions.

### Ranker

```python
class Ranker(Protocol):
    def rank(
        self,
        candidates: CandidateSet,
        config: RankingConfig,
        feedback: ReviewHistory | None = None,
    ) -> ProposalSet: ...
```

The ranker computes interpretable features, applies policy filters, calibrates
confidence, and selects supporting evidence.

### Reporter

```python
class Reporter(Protocol):
    def write(self, proposals: ProposalSet, config: ReportConfig) -> ReportManifest: ...
```

Reporters may produce JSONL, JSON, Markdown, HTML, or records for another
review system. They cannot mutate source documents.

## Data contracts

All artifacts carry `schema_version`, `run_id`, `corpus_id`, creation time,
configuration fingerprint, and producer version. IDs are opaque strings to the
core.

### SourceDocument

```json
{
  "id": "opaque-stable-id",
  "revision": "content-revision-or-hash",
  "media_type": "text/plain",
  "content": "raw source content",
  "title": "Canonical title",
  "language": "en",
  "source_ref": "adapter-defined-reference",
  "metadata": {},
  "flags": {
    "excluded": false,
    "generated": false,
    "archived": false
  }
}
```

`id` must remain stable when an adapter can recognize a move or rename.
`revision` must change whenever content or embedding-relevant metadata changes.

### Relationship

```json
{
  "source_id": "document-a",
  "target_id": "document-b",
  "kind": "explicit-link",
  "directed": true,
  "source_span": {
    "start": 120,
    "end": 148
  },
  "metadata": {}
}
```

Relationship kinds are adapter-defined. The candidate policy declares which
kinds count as an existing link, alias, exclusion, or weaker graph signal.

### SemanticUnit

```json
{
  "id": "document-a:section-3:chunk-1",
  "document_id": "document-a",
  "view": "section",
  "section_path": ["Scheduling", "Fairness"],
  "region_kinds": ["heading", "prose", "equation"],
  "source_spans": [{"start": 420, "end": 1080}],
  "text": "text presented to the embedding model",
  "token_count": 173,
  "content_hash": "sha256:..."
}
```

The unit ID is stable for unchanged semantic content. Source spans may change
after unrelated edits and must not be the sole identity input.

### EmbeddingRecord

```json
{
  "unit_id": "document-a:section-3:chunk-1",
  "model_fingerprint": "model-and-inference-fingerprint",
  "dimensions": 4096,
  "normalized": true,
  "dtype": "float16",
  "vector_ref": "artifact-relative-reference"
}
```

Vectors may live in a columnar file, memory-mapped matrix, or vector index.
The record format must not require one storage backend.

### LinkProposal

```json
{
  "id": "stable-pair-and-ranking-version-id",
  "source_document_id": "document-a",
  "target_document_id": "document-b",
  "direction": "source-to-target",
  "rank": 1,
  "score": 0.91,
  "confidence": "high",
  "features": {
    "document_similarity": 0.84,
    "best_chunk_similarity": 0.93,
    "support_breadth": 0.71,
    "lexical_similarity": 0.24,
    "hubness_penalty": 0.05,
    "graph_redundancy_penalty": 0.0
  },
  "evidence": [
    {
      "source_unit_id": "document-a:section-3:chunk-1",
      "target_unit_id": "document-b:section-1:chunk-0",
      "similarity": 0.93,
      "source_spans": [{"start": 420, "end": 1080}],
      "target_spans": [{"start": 80, "end": 510}]
    }
  ],
  "existing_relationship": false,
  "ranking_version": "ranker-fingerprint",
  "review": {
    "status": "unreviewed",
    "reason": null
  }
}
```

Raw feature values are required. A scalar score without evidence and component
features is not a valid proposal.

## Preprocessing specification

Preprocessing must be deterministic for a fixed parser version and
configuration.

### Canonicalization

- Decode content using the adapter-provided encoding.
- Normalize Unicode and line endings according to explicit configuration.
- Separate source metadata from body content.
- Detect repeated titles and other adapter-identified boilerplate.
- Preserve code, equations, identifiers, citations, and link anchor text.
- Represent non-prose regions by type rather than deleting them globally.
- Retain a mapping from normalized text to source spans where practical.

Markup removal must not concatenate tokens that were separated in the source.
Existing link targets should not be embedded as path-like text by default;
human-readable anchor text remains useful semantic evidence.

### Regions

Parsers should emit typed regions. The minimum portable region kinds are:

- title
- heading
- prose
- list
- code
- equation
- table
- quote
- citation
- metadata
- boilerplate

Unknown kinds are preserved as `other`. A preprocessing profile controls the
weight or inclusion of each region kind for each retrieval view.

### Chunking

Chunk boundaries should follow semantic structure before token count. The
default strategy is:

1. Keep a section path with every chunk.
2. Group adjacent regions under the same lowest-level heading.
3. Split oversized groups at paragraph or region boundaries.
4. Use token overlap only when a split crosses continuous prose.
5. Carry the title and relevant heading path as chunk context.

Chunk sizes are measured with the selected model's tokenizer. Word-count
approximations are not valid for reproducible model input.

The pipeline must retain both local evidence chunks and a document retrieval
view. A long document must not gain an unfair score merely because it produces
more chunks.

### Retrieval views

The initial design supports three views:

- `document`: a bounded representation of the title, descriptive metadata,
  headings, and content.
- `section`: semantically coherent chunks with heading context.
- `title`: title, aliases, and optional descriptive metadata.

Additional views can be registered without changing the core contracts. A
view's construction policy is part of the preprocessing fingerprint.

## Embedding specification

### Model policy

The model is selected by a reproducible benchmark on the target corpus, not by
leaderboard position alone. The quality-first reference candidate is
[`Qwen/Qwen3-Embedding-8B`](https://huggingface.co/Qwen/Qwen3-Embedding-8B).
Its model card describes a 32K context window, instruction-aware embeddings,
Matryoshka dimensions up to 4096, and smaller 4B and 0.6B variants. The 8B
model is the preferred starting point on machines with enough unified memory.

The initial qualification benchmark should compare at least:

- Qwen3-Embedding-8B as the quality candidate.
- Qwen3-Embedding-4B as the lower-memory fallback profile.
- One compact baseline to quantify the value of the larger models.
- Optionally [`BAAI/bge-m3`](https://huggingface.co/BAAI/bge-m3) when hybrid
  dense and lexical retrieval or multilingual behavior is valuable.

The chosen default must outperform the compact baseline on human-reviewed
precision and held-out-link recovery. If 8B and 4B are statistically tied on
the corpus, throughput and incremental indexing cost may break the tie.

Model identifier, immutable revision, tokenizer revision, pooling method,
instruction text, output dimension, normalization, precision, and maximum
input length form the model fingerprint. Changing any of them invalidates the
affected embeddings.

### Runtime policy

Device preference is ordered and configurable:

```yaml
device_preference:
  - mps
  - cpu
```

The runtime must test MPS execution with representative inputs before a batch.
Framework-level MPS availability does not establish that every model operation
works. PyTorch's [MPS backend documentation](https://docs.pytorch.org/docs/stable/notes/mps.html)
is the baseline runtime reference.

On an out-of-memory failure, the runtime first reduces batch size and retries
from the last complete batch. It may then use CPU if configured. It must not
silently switch model, output dimension, precision, or truncation policy.

The run manifest records:

- selected device and fallback events
- model and tokenizer revisions
- precision and output dimensions
- requested and effective batch size
- token throughput and wall time
- peak memory when available
- truncation counts
- warnings and failed units

Artifacts are written atomically. A partial run cannot appear complete.

### Embedding cache

The cache key for one semantic unit is derived from:

```text
hash(
  semantic_unit_content_hash,
  preprocessing_fingerprint,
  model_fingerprint,
  embedding_runtime_options_that_affect_output
)
```

Paths, modification times, and device choice alone are not correctness keys.
Changing candidate-ranking weights must not invalidate embeddings.

## Candidate algorithm

### Phase 1: high-recall retrieval

For each retrieval view, find the nearest semantic units under cosine
similarity or an equivalent normalized dot product. Exact search is acceptable
for small corpora. An approximate nearest-neighbor backend is required once an
all-pairs scan exceeds configured time or memory budgets.

Retrieve more neighbors than will be shown. Candidate generation optimizes
recall and leaves precision to the ranker.

The generator must:

- Remove self-pairs.
- Resolve aliases before pair construction.
- Exclude archived, private, generated, and adapter-excluded documents.
- Exclude pairs with an existing relationship designated as a direct link.
- Collapse reciprocal unit matches into a canonical document pair.
- Preserve the strongest supporting unit pairs and retrieval views.
- Apply deterministic tie-breaking.
- Bound candidates per document and globally.

An indirect graph path is a ranking signal, not a hard exclusion. A direct link
may still be useful when two documents are currently connected through a hub.

### Phase 2: document-pair aggregation

Chunk vectors must not be reduced to an unexamined document mean. For a pair of
documents, retain at least:

- similarity between document views
- maximum section-pair similarity
- mean of the top `r` distinct section-pair similarities
- number and diversity of supporting sections
- title-view similarity
- document lengths and chunk counts

The aggregator must correct for length bias. More chunks create more chances
for an accidental high maximum. Initial correction should compare a match to
the source and target documents' local neighbor distributions, with an
explicit, testable alternative such as percentile normalization or hubness
correction.

### Phase 3: filtering and features

Hard filters remove invalid candidates:

- existing direct links
- self-links and alias-equivalent pairs
- excluded documents or pairs
- empty or failed documents
- exact duplicates when the desired action is deduplication rather than linking

Soft features inform ranking:

- semantic similarity by retrieval view
- best and top-section similarities
- breadth of supporting evidence
- lexical and keyphrase overlap
- shared citations or entities, when available
- graph distance and common-neighbor count
- category or collection relationship supplied as generic metadata
- near-duplicate probability
- document quality and information content
- hubness or genericness
- novelty relative to each document's existing neighborhood
- agreement across embedding models or profiles, when enabled

Features must be optional and discoverable. The core ranker cannot require a
category field, citation parser, or graph database.

### Phase 4: ranking

The first ranker should be an interpretable weighted model with normalized
features. A representative shape is:

```text
score =
    w_document * document_similarity
  + w_local * best_section_similarity
  + w_breadth * support_breadth
  + w_lexical * lexical_similarity
  + w_bridge * cross_neighborhood_value
  - w_hub * hubness
  - w_duplicate * near_duplicate_probability
  - w_redundancy * graph_redundancy
```

This formula defines structure, not initial weights. Feature normalization,
weights, and thresholds are versioned configuration. Existing links are
excluded before ranking, so novelty does not become an arbitrary bonus that can
overpower weak semantic evidence.

The ranker should expose three separate estimates:

- **Relatedness:** how strongly the content is semantically connected.
- **Usefulness:** how likely a direct navigation link is to help a reader.
- **Missingness:** how confident the system is that the relationship is absent
  after alias and link normalization.

The final confidence band derives from these estimates and calibration data.

### Direction and placement

Retrieval begins with an unordered document pair. Reporting may propose one or
both directed links.

Direction uses:

- the source span with the clearest placement evidence
- whether one document defines a concept used by the other
- existing link direction conventions supplied by the adapter
- document roles and metadata, when available

The system should emit the best source span and target document. Exact markup
generation remains a downstream adapter concern.

### Diversity

Per-document results should use a configurable diversity policy such as maximal
marginal relevance. This prevents several nearly identical targets from
occupying the review queue. Diversity cannot suppress the raw candidate record;
it changes presentation rank only.

## Explainability

Every proposal must include machine-readable evidence. At minimum:

- the best matching source and target semantic units
- source spans or adapter references for both units
- raw similarity values
- all ranking feature values and penalties
- existing graph distance when used
- the filter and ranking configuration fingerprints

Natural-language explanations are optional and derived. They cannot replace
the underlying evidence. If an LLM later generates explanations, its output is
clearly marked as generated and receives its own provenance.

## Evaluation and calibration

### Weak supervision from existing links

Existing links provide useful but biased positive examples. The evaluation
harness should hide a stratified sample, run discovery as if those links were
absent, and report:

- recall at `k`
- mean reciprocal rank
- nDCG when graded judgments exist
- recovery by document length, category, and graph degree

These metrics measure whether the system rediscovers current linking behavior.
They do not measure the quality of genuinely new links.

### Human review set

A durable review dataset is required before tuning ranking weights. It should
contain:

- top-ranked proposals
- candidates near decision thresholds
- random retrieved candidates
- candidates from sparse or underrepresented corpus regions
- candidates where retrieval views or models disagree

Review decisions are `accept`, `reject`, or `defer`, with optional reason codes.
Recommended reason codes include `already_related`, `useful_bridge`,
`too_generic`, `duplicate`, `weak_evidence`, `wrong_direction`, and
`bad_placement`.

Primary quality metrics are reviewer precision at `k`, acceptance rate, corpus
coverage, recommendation concentration, and stability across runs. The model
qualification benchmark must report quality alongside runtime and memory.

### Calibration

Version 1 may map normalized scores to confidence bands using reviewed
examples. A later version may fit a logistic model or pairwise ranker over the
same interpretable features. Training data, splits, feature versions, and
metrics must be recorded.

Rejected candidates are not universal negatives. A rejection may be specific
to direction, placement, timing, or the current corpus structure.

## Configuration

One declarative configuration composes the pipeline. This example is generic:

```yaml
schema_version: 1

source:
  adapter: package.module:Adapter
  options: {}

preprocess:
  parser: package.module:Parser
  views: [document, section, title]
  target_tokens: 384
  max_tokens: 512
  overlap_tokens: 48
  include_regions: [title, heading, prose, list, code, equation, table, citation]
  exclude_regions: [boilerplate]

embedding:
  provider: sentence-transformers
  model: Qwen/Qwen3-Embedding-8B
  revision: immutable-model-revision
  dimensions: 4096
  normalize: true
  device_preference: [mps, cpu]
  precision: float16
  batch_size: auto

candidates:
  backend: auto
  neighbors_per_unit: 50
  existing_relationship_kinds: [explicit-link]
  max_pairs_per_document: 100

ranking:
  profile: weighted-v1
  minimum_relatedness: 0.0
  results_per_document: 10
  diversity: 0.2

report:
  formats: [jsonl, markdown]
  include_evidence_text: true
```

Unknown configuration fields are errors by default. The resolved configuration
and defaults are written to the run manifest.

## Artifact layout

Storage is backend-defined, but the logical artifact groups are stable:

```text
artifacts/
  corpus-manifest/
  processed-corpus/
  embeddings/
  indexes/
  candidates/
  proposals/
  reviews/
  runs/
```

Artifacts use content-addressed keys where possible. A stage writes to a
temporary location, validates completeness, then atomically publishes a
manifest. Cache invalidation is stage-specific:

- A source content change invalidates that document's processed units and
  downstream records.
- A parser or chunking change invalidates processed units and downstream
  records.
- A model change invalidates embeddings, indexes, candidates, and proposals.
- A ranking change invalidates proposals, but not embeddings or raw candidates.
- A reporting change invalidates only rendered reports.

## Batch and incremental operation

The same interfaces support both modes.

Full batch mode freezes a corpus manifest, processes all eligible documents,
builds an index, generates candidates, and writes a complete proposal set.

Incremental mode compares corpus manifests, reprocesses changed documents,
reuses matching unit embeddings, updates or rebuilds indexes according to the
backend's consistency guarantees, and reranks affected neighborhoods. A deleted
document removes its vectors and proposals in the newly published artifact
version.

Candidate retrieval must avoid all-pairs comparison once configured corpus or
unit thresholds are exceeded. Reranking always operates on a bounded candidate
set.

## Reproducibility and observability

Each run manifest records:

- corpus and relationship fingerprints
- resolved configuration
- dependency and producer versions
- model and tokenizer revisions
- random seeds
- device, precision, batch sizes, and fallbacks
- cache hits and misses by stage
- document, region, unit, and vector counts
- exclusions and failure counts by reason
- index parameters
- timing and throughput by stage
- output artifact references

Approximate indexes must use deterministic construction where supported. When
they cannot, the manifest records parameters and the evaluation suite measures
top-k stability.

## Failure handling

The system must detect and report:

- duplicate or unstable document IDs
- unresolved relationship targets
- malformed, empty, or unsupported source content
- a corpus changing after its manifest is frozen
- model or tokenizer revision drift
- unavailable MPS, unsupported MPS operations, and out-of-memory failures
- embedding dimension or normalization mismatches
- stale or incompatible cache artifacts
- truncated inputs and failed semantic units
- duplicate reciprocal candidates
- incomplete or corrupt artifacts
- scores compared across incompatible ranking versions

A successful empty result is distinguishable from a failed or partial run.
Strict mode fails the run on any skipped document or unit. Permissive mode emits
a complete artifact with explicit omissions.

## Security and privacy

- Local providers must not send source content over the network after model
  acquisition.
- Remote model downloads are pinned by immutable revision and may be mirrored.
- Adapters may mark sensitive documents as excluded before preprocessing.
- Reports may omit evidence text while retaining source references.
- Artifact directories may contain source-derived text and must be treated with
  the same sensitivity as the corpus.

## Host integration

A host-specific package should contain only adapters and configuration:

```text
host-integration/
  source_adapter
  parser
  relationship_resolver
  report_renderer
  config
```

For a Markdown knowledge base, that adapter may understand frontmatter,
wikilinks, standard Markdown links, aliases, generated pages, and archive
flags. These concepts are translated into the generic contracts before the core
pipeline runs. Another adapter could load records from a database or API
without changing preprocessing, embedding, or ranking.

The first integration should remain manually invoked or scheduled as a batch
job. It must not become part of a website's production build, since model
downloads and embedding computation would make that build slow and
nondeterministic.

## Acceptance criteria

A conforming first implementation must:

1. Load a fixture corpus through an adapter without core knowledge of its
   storage or markup.
2. Produce deterministic semantic units with source evidence and versioned
   preprocessing artifacts.
3. Run the selected embedding model on MPS when qualification succeeds, record
   the effective runtime, and complete on CPU when MPS is unavailable.
4. Reuse embeddings for unchanged units and invalidate them when any
   output-affecting input changes.
5. Generate candidates from document and section views.
6. Emit no self-pairs, alias-equivalent pairs, excluded pairs, or existing
   direct links.
7. Correct for document length and embedding-space hubness in a measurable way.
8. Rank proposals with inspectable features and supporting source spans.
9. Serialize proposals and review decisions in versioned, machine-readable
   formats.
10. Recover held-out links more accurately than the compact embedding baseline
    and report human precision at `k` on a seed review set.
11. Produce equivalent candidate rankings within documented tolerance on MPS
    and CPU.
12. Leave source documents unchanged.

## Implementation phases

### Phase 0: qualification harness

- Create a small format-independent fixture corpus.
- Define held-out-link and human-review datasets.
- Benchmark embedding candidates on MPS and CPU.
- Select the initial model, dimensions, chunk sizes, and runtime profile.

### Phase 1: contracts and adapters

- Define schemas and validation.
- Implement source, parser, and reporter plugin loading.
- Build one host adapter without leaking host concepts into core types.

### Phase 2: preprocessing and artifacts

- Add typed regions, tokenizer-aware chunking, retrieval views, manifests, and
  content-addressed caching.

### Phase 3: embedding and indexing

- Add device qualification, adaptive batching, atomic artifacts, exact search,
  and an approximate backend selected by corpus size.

### Phase 4: candidate ranking

- Add existing-link filtering, document-pair aggregation, length and hubness
  correction, interpretable features, direction, and diversity.

### Phase 5: review and calibration

- Add JSONL and human-readable reports, durable review decisions, evaluation
  dashboards, and confidence calibration.

Automatic source mutation, learned reranking, LLM explanations, and graph-wide
optimization remain later opt-in extensions.

## Open decisions

- Which embedding candidate wins the corpus-specific qualification benchmark?
- Which region types should be embedded together for code-heavy and math-heavy
  documents?
- Should the initial document view embed full documents within model context,
  or use a deterministic bounded representation for every document?
- Which hubness correction gives the best precision without suppressing useful
  foundational documents?
- How should review reason codes map to later training examples?
- At what corpus size should the default backend switch from exact to
  approximate search?
- Should direction ranking ship in version 1, or should the first report expose
  unordered pairs with evidence on both sides?

These are qualification and product decisions. They do not change the stage
boundaries or artifact contracts defined above.
