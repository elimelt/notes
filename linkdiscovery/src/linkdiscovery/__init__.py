"""linkdiscovery: the Missing-Link Discovery Pipeline foundation.

This package provides the stable core every stage builds on: typed,
serializable, versioned data contracts; stage interface Protocols; strict
declarative configuration; deterministic fingerprinting; plugin loading; and
content-addressed artifact storage with atomic publishing. Stage
implementations (preprocessing, embedding, candidate generation, ranking,
reporting, adapters, CLI) are added as subpackages and plug in through the
Protocols in :mod:`linkdiscovery.interfaces`.
"""

from linkdiscovery.artifacts import GROUPS, ArtifactCache, ArtifactStore, CacheStats
from linkdiscovery.candidates import DefaultCandidateGenerator
from linkdiscovery.config import (
    CONFIG_SCHEMA_VERSION,
    DEFAULT_RANKING_WEIGHTS,
    CandidateConfig,
    EmbeddingConfig,
    PipelineConfig,
    PreprocessConfig,
    RankingConfig,
    ReportConfig,
    SourceConfig,
    config_from_dict,
    load_config,
)
from linkdiscovery.contracts import (
    ArtifactHeader,
    ArtifactRef,
    CandidatePair,
    CandidateSet,
    Confidence,
    Corpus,
    DecisionKind,
    DocumentFlags,
    EmbeddingIndex,
    EmbeddingRecord,
    Evidence,
    LinkProposal,
    ProcessedCorpus,
    ProcessedDocument,
    ProposalSet,
    ReasonCode,
    Region,
    RegionKind,
    Relationship,
    RelationshipSet,
    ReportManifest,
    ReviewDecision,
    ReviewHistory,
    ReviewState,
    RunManifest,
    RuntimeReport,
    SemanticUnit,
    SourceDocument,
    Span,
    StageStats,
    UnitMatch,
    utc_now_iso,
)
from linkdiscovery.embed import DefaultEmbedder
from linkdiscovery.errors import (
    ArtifactError,
    CacheError,
    CandidateError,
    ConfigError,
    ContractError,
    EmbeddingRuntimeError,
    LinkDiscoveryError,
    PluginError,
    PreprocessError,
    RankingError,
    ReportError,
)
from linkdiscovery.fingerprint import (
    canonical_json,
    combine_fingerprints,
    fingerprint,
    fingerprint_bytes,
)
from linkdiscovery.interfaces import (
    CandidateGenerator,
    Embedder,
    Preprocessor,
    Ranker,
    RegionParser,
    Reporter,
    SourceAdapter,
    TokenCounter,
)
from linkdiscovery.pipeline import Pipeline, RunResult
from linkdiscovery.plugins import instantiate_plugin, load_plugin
from linkdiscovery.preprocess import (
    DefaultPreprocessor,
    HuggingFaceTokenCounter,
    SimpleTokenCounter,
)
from linkdiscovery.ranking import WeightedRanker
from linkdiscovery.report import DefaultReporter

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Stage implementations are wired above: DefaultPreprocessor (+ token
# counters), DefaultEmbedder, DefaultCandidateGenerator, WeightedRanker,
# DefaultReporter, and the Pipeline orchestrator with its RunResult. The
# foundation API (contracts, config, errors, fingerprinting, plugins,
# artifacts) is stable and must not be reshuffled.
# ---------------------------------------------------------------------------

__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "DEFAULT_RANKING_WEIGHTS",
    "GROUPS",
    "ArtifactCache",
    "ArtifactError",
    "ArtifactHeader",
    "ArtifactRef",
    "ArtifactStore",
    "CacheError",
    "CacheStats",
    "CandidateConfig",
    "CandidateError",
    "CandidateGenerator",
    "CandidatePair",
    "CandidateSet",
    "Confidence",
    "ConfigError",
    "ContractError",
    "Corpus",
    "DecisionKind",
    "DefaultCandidateGenerator",
    "DefaultEmbedder",
    "DefaultPreprocessor",
    "DefaultReporter",
    "DocumentFlags",
    "Embedder",
    "EmbeddingConfig",
    "EmbeddingIndex",
    "EmbeddingRecord",
    "EmbeddingRuntimeError",
    "Evidence",
    "HuggingFaceTokenCounter",
    "LinkDiscoveryError",
    "LinkProposal",
    "Pipeline",
    "PipelineConfig",
    "PluginError",
    "PreprocessConfig",
    "PreprocessError",
    "Preprocessor",
    "ProcessedCorpus",
    "ProcessedDocument",
    "ProposalSet",
    "Ranker",
    "RankingConfig",
    "RankingError",
    "ReasonCode",
    "Region",
    "RegionKind",
    "RegionParser",
    "Relationship",
    "RelationshipSet",
    "ReportConfig",
    "ReportError",
    "ReportManifest",
    "Reporter",
    "ReviewDecision",
    "ReviewHistory",
    "ReviewState",
    "RunManifest",
    "RunResult",
    "RuntimeReport",
    "SemanticUnit",
    "SimpleTokenCounter",
    "SourceAdapter",
    "SourceConfig",
    "SourceDocument",
    "Span",
    "StageStats",
    "TokenCounter",
    "UnitMatch",
    "WeightedRanker",
    "__version__",
    "canonical_json",
    "combine_fingerprints",
    "config_from_dict",
    "fingerprint",
    "fingerprint_bytes",
    "instantiate_plugin",
    "load_config",
    "load_plugin",
    "utc_now_iso",
]
