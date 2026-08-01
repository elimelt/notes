"""Stage interface Protocols: the public shapes from the SPEC.

Every stage is a Protocol so implementations can live anywhere (including
host-integration packages loaded via
:func:`linkdiscovery.plugins.load_plugin`) without inheriting from core
classes. All Protocols are ``runtime_checkable``, so plugin loading can
verify instances; note that runtime checks verify method presence, not
signatures — the data contracts remain the normative boundary.

Stages exchange contract types only. Each stage must also be callable
independently from its serialized input artifact, which is why every
parameter and return type here has ``to_dict``/``from_dict``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from linkdiscovery.artifacts.cache import ArtifactCache
from linkdiscovery.config import (
    CandidateConfig,
    EmbeddingConfig,
    PreprocessConfig,
    RankingConfig,
    ReportConfig,
    SourceConfig,
)
from linkdiscovery.contracts.candidates import CandidateSet
from linkdiscovery.contracts.documents import Corpus, RelationshipSet, SourceDocument
from linkdiscovery.contracts.embeddings import EmbeddingIndex
from linkdiscovery.contracts.manifests import ReportManifest
from linkdiscovery.contracts.proposals import ProposalSet
from linkdiscovery.contracts.reviews import ReviewHistory
from linkdiscovery.contracts.units import ProcessedCorpus, Region

__all__ = [
    "CandidateGenerator",
    "Embedder",
    "Preprocessor",
    "Ranker",
    "RegionParser",
    "Reporter",
    "SourceAdapter",
    "TokenCounter",
]


@runtime_checkable
class SourceAdapter(Protocol):
    """Loads a host corpus into the canonical contracts.

    The adapter owns source semantics: document identity, aliases, existing
    relationships, exclusions, and human-facing references. The core never
    opens repository files or parses source-specific link syntax.
    """

    def load(self, config: SourceConfig) -> Corpus:
        """Discover documents and relationships, returning a frozen corpus."""
        ...


@runtime_checkable
class Preprocessor(Protocol):
    """Converts canonical source content into typed regions and semantic units.

    Must be deterministic for a fixed parser version and configuration; the
    output's ``preprocessing_fingerprint`` captures both.
    """

    def process(self, corpus: Corpus, config: PreprocessConfig) -> ProcessedCorpus:
        """Produce regions, retrieval views, and chunked semantic units."""
        ...


@runtime_checkable
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


@runtime_checkable
class CandidateGenerator(Protocol):
    """Retrieves a bounded, high-recall candidate set; makes no link decisions.

    Must remove self-pairs, resolve aliases, exclude flagged documents and
    existing direct links, collapse reciprocal matches, and apply
    deterministic tie-breaking.
    """

    def generate(
        self,
        corpus: ProcessedCorpus,
        index: EmbeddingIndex,
        relationships: RelationshipSet,
        config: CandidateConfig,
    ) -> CandidateSet:
        """Retrieve nearest-neighbor unit matches and aggregate document pairs."""
        ...


@runtime_checkable
class Ranker(Protocol):
    """Scores candidates with interpretable features and calibrated confidence.

    Every proposal must carry raw feature values and evidence; ``feedback``
    supplies durable review decisions for calibration and is optional.
    """

    def rank(
        self,
        candidates: CandidateSet,
        config: RankingConfig,
        feedback: ReviewHistory | None = None,
    ) -> ProposalSet:
        """Filter, score, calibrate, and order candidates into proposals."""
        ...


@runtime_checkable
class Reporter(Protocol):
    """Renders proposals for review; never mutates source documents."""

    def write(self, proposals: ProposalSet, config: ReportConfig) -> ReportManifest:
        """Write the configured formats and return references to the outputs."""
        ...


@runtime_checkable
class TokenCounter(Protocol):
    """Counts tokens with the selected model's tokenizer.

    Chunk sizes are measured with the model tokenizer — word-count
    approximations are not valid for reproducible model input — so chunkers
    take a ``TokenCounter`` rather than guessing.
    """

    def count_tokens(self, text: str) -> int:
        """Return the number of model tokens in ``text``."""
        ...

    @property
    def fingerprint(self) -> str:
        """Identity of the tokenizer (name and revision); part of preprocessing keys."""
        ...


@runtime_checkable
class RegionParser(Protocol):
    """Parses one document's raw content into typed regions.

    Format-specific parsing is an adapter plugin; chunking and normalization
    stay in the core preprocessor. Parsers map unknown region kinds to
    ``RegionKind.OTHER`` and must be deterministic for a fixed fingerprint.
    """

    def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
        """Emit typed regions covering the document's embedding-relevant content."""
        ...

    @property
    def fingerprint(self) -> str:
        """Identity of the parser (name and version); part of the preprocessing fingerprint."""
        ...
