"""Strict, declarative pipeline configuration mirroring the SPEC YAML shape.

One YAML document composes the whole pipeline. Parsing is strict by design
(SPEC: "Unknown configuration fields are errors by default"): every unknown
field raises :class:`~linkdiscovery.errors.ConfigError` naming the field and
its location, missing required fields raise with a clear message, and every
default is explicit in the dataclass definitions below.

Each stage config exposes ``resolved_dict()`` (defaults filled, JSON-safe,
suitable for the run manifest) and ``fingerprint()``; per-stage fingerprints
implement the SPEC's stage-specific cache invalidation — changing ranking
weights must not invalidate embeddings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from linkdiscovery.contracts.units import RegionKind
from linkdiscovery.errors import ConfigError
from linkdiscovery.fingerprint import fingerprint as _fingerprint

__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "DEFAULT_RANKING_WEIGHTS",
    "CandidateConfig",
    "EmbeddingConfig",
    "PipelineConfig",
    "PreprocessConfig",
    "RankingConfig",
    "ReportConfig",
    "SourceConfig",
    "config_from_dict",
    "load_config",
]

CONFIG_SCHEMA_VERSION = 1
"""The configuration schema version this build reads."""

DEFAULT_RANKING_WEIGHTS: dict[str, float] = {
    "w_document": 0.35,
    "w_local": 0.30,
    "w_breadth": 0.15,
    "w_lexical": 0.10,
    "w_bridge": 0.10,
    "w_hub": 0.10,
    "w_duplicate": 0.20,
    "w_redundancy": 0.10,
}
"""Default weights for every term of the SPEC ranking score formula."""

_DEFAULT_VIEWS = ("document", "section", "title")
_DEFAULT_INCLUDE_REGIONS = (
    "title",
    "heading",
    "prose",
    "list",
    "code",
    "equation",
    "table",
    "citation",
)
_DEFAULT_EXCLUDE_REGIONS = ("boilerplate",)

_DEVICES = frozenset({"mps", "cuda", "cpu"})
_PRECISIONS = frozenset({"float32", "float16", "bfloat16"})
_BACKENDS = frozenset({"auto", "exact", "hnsw"})

_MISSING = object()


def _expect_section(value: object, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{location}: expected a mapping, got {type(value).__name__}")
    for key in value:
        if not isinstance(key, str):
            raise ConfigError(f"{location}: keys must be strings, got {key!r}")
    return cast("dict[str, Any]", value)


def _check_unknown(data: Mapping[str, Any], allowed: frozenset[str], location: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        names = ", ".join(f"'{name}'" for name in unknown)
        expected = ", ".join(sorted(allowed))
        raise ConfigError(
            f"{location}: unknown field{'s' if len(unknown) > 1 else ''} {names}; "
            f"expected only: {expected}"
        )


def _lookup(data: Mapping[str, Any], name: str, location: str, default: object) -> object:
    if name in data:
        return data[name]
    if default is _MISSING:
        raise ConfigError(f"{location}: missing required field '{name}'")
    return default


def _get_str(
    data: Mapping[str, Any], name: str, location: str, default: str | object = _MISSING
) -> str:
    value = _lookup(data, name, location, default)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{location}: field '{name}' must be a non-empty string, got {value!r}")
    return value


def _get_nullable_str(data: Mapping[str, Any], name: str, location: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(
            f"{location}: field '{name}' must be a non-empty string or null, got {value!r}"
        )
    return value


def _get_bool(data: Mapping[str, Any], name: str, location: str, default: bool) -> bool:
    value = _lookup(data, name, location, default)
    if not isinstance(value, bool):
        raise ConfigError(
            f"{location}: field '{name}' must be a boolean, got {type(value).__name__}"
        )
    return value


def _get_int(
    data: Mapping[str, Any],
    name: str,
    location: str,
    default: int | object = _MISSING,
    minimum: int | None = None,
) -> int:
    value = _lookup(data, name, location, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(
            f"{location}: field '{name}' must be an integer, got {type(value).__name__}"
        )
    if minimum is not None and value < minimum:
        raise ConfigError(f"{location}: field '{name}' must be >= {minimum}, got {value}")
    return value


def _get_nullable_int(
    data: Mapping[str, Any], name: str, location: str, minimum: int | None = None
) -> int | None:
    if data.get(name) is None:
        return None
    return _get_int(data, name, location, minimum=minimum)


def _get_float(
    data: Mapping[str, Any],
    name: str,
    location: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = _lookup(data, name, location, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigError(
            f"{location}: field '{name}' must be a number, got {type(value).__name__}"
        )
    result = float(value)
    if (minimum is not None and result < minimum) or (maximum is not None and result > maximum):
        raise ConfigError(
            f"{location}: field '{name}' must be within "
            f"[{minimum if minimum is not None else '-inf'}, "
            f"{maximum if maximum is not None else 'inf'}], got {result}"
        )
    return result


def _get_str_tuple(
    data: Mapping[str, Any], name: str, location: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    value = _lookup(data, name, location, default)
    if isinstance(value, tuple):
        return value
    if not isinstance(value, list):
        raise ConfigError(
            f"{location}: field '{name}' must be a list of strings, got {type(value).__name__}"
        )
    for item in value:
        if not isinstance(item, str) or not item:
            raise ConfigError(
                f"{location}: field '{name}' must contain non-empty strings, got {item!r}"
            )
    return tuple(cast("list[str]", value))


def _get_regions(
    data: Mapping[str, Any], name: str, location: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    values = _get_str_tuple(data, name, location, default)
    valid = {kind.value for kind in RegionKind}
    for item in values:
        if item not in valid:
            allowed = ", ".join(kind.value for kind in RegionKind)
            raise ConfigError(
                f"{location}: field '{name}' contains unknown region kind {item!r}; "
                f"expected one of: {allowed}"
            )
    return values


def _get_options(data: Mapping[str, Any], name: str, location: str) -> dict[str, Any]:
    value = _lookup(data, name, location, {})
    return dict(_expect_section(value, f"{location}.{name}"))


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Source-adapter selection and its opaque options.

    ``adapter`` is a ``"package.module:Attr"`` plugin spec resolved via
    :func:`linkdiscovery.plugins.load_plugin`; ``options`` is passed through
    to the adapter untouched and must stay JSON-safe.
    """

    adapter: str
    options: dict[str, Any] = field(default_factory=dict)

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {"adapter": self.adapter, "options": dict(self.options)}

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section, for corpus-manifest invalidation."""
        return _fingerprint(self.resolved_dict())

    @classmethod
    def _parse(cls, data: Mapping[str, Any], location: str) -> SourceConfig:
        _check_unknown(data, frozenset({"adapter", "options"}), location)
        return cls(
            adapter=_get_str(data, "adapter", location),
            options=_get_options(data, "options", location),
        )


@dataclass(frozen=True, slots=True)
class PreprocessConfig:
    """Parsing, view construction, and tokenizer-aware chunking policy.

    Invariants (validated at parse time): ``target_tokens <= max_tokens``,
    ``overlap_tokens < target_tokens``, region lists contain only
    :class:`~linkdiscovery.contracts.units.RegionKind` values, and no region
    kind appears in both ``include_regions`` and ``exclude_regions``. The
    resolved section is part of the preprocessing fingerprint, so any change
    here invalidates processed units and everything downstream.
    """

    parser: str
    views: tuple[str, ...] = _DEFAULT_VIEWS
    target_tokens: int = 384
    max_tokens: int = 512
    overlap_tokens: int = 48
    include_regions: tuple[str, ...] = _DEFAULT_INCLUDE_REGIONS
    exclude_regions: tuple[str, ...] = _DEFAULT_EXCLUDE_REGIONS

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "parser": self.parser,
            "views": list(self.views),
            "target_tokens": self.target_tokens,
            "max_tokens": self.max_tokens,
            "overlap_tokens": self.overlap_tokens,
            "include_regions": list(self.include_regions),
            "exclude_regions": list(self.exclude_regions),
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section, a component of unit cache keys."""
        return _fingerprint(self.resolved_dict())

    @classmethod
    def _parse(cls, data: Mapping[str, Any], location: str) -> PreprocessConfig:
        allowed = frozenset(
            {
                "parser",
                "views",
                "target_tokens",
                "max_tokens",
                "overlap_tokens",
                "include_regions",
                "exclude_regions",
            }
        )
        _check_unknown(data, allowed, location)
        config = cls(
            parser=_get_str(data, "parser", location),
            views=_get_str_tuple(data, "views", location, _DEFAULT_VIEWS),
            target_tokens=_get_int(data, "target_tokens", location, 384, minimum=1),
            max_tokens=_get_int(data, "max_tokens", location, 512, minimum=1),
            overlap_tokens=_get_int(data, "overlap_tokens", location, 48, minimum=0),
            include_regions=_get_regions(
                data, "include_regions", location, _DEFAULT_INCLUDE_REGIONS
            ),
            exclude_regions=_get_regions(
                data, "exclude_regions", location, _DEFAULT_EXCLUDE_REGIONS
            ),
        )
        if config.max_tokens < config.target_tokens:
            raise ConfigError(
                f"{location}: 'max_tokens' ({config.max_tokens}) must be >= "
                f"'target_tokens' ({config.target_tokens})"
            )
        if config.overlap_tokens >= config.target_tokens:
            raise ConfigError(
                f"{location}: 'overlap_tokens' ({config.overlap_tokens}) must be < "
                f"'target_tokens' ({config.target_tokens})"
            )
        if not config.views:
            raise ConfigError(f"{location}: 'views' must not be empty")
        overlap = set(config.include_regions) & set(config.exclude_regions)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ConfigError(
                f"{location}: region kinds present in both 'include_regions' and "
                f"'exclude_regions': {names}"
            )
        return config


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Model, revision, and runtime policy for the embedding stage.

    ``model`` and ``revision`` pin the exact model (SPEC: downloads are
    pinned by immutable revision); ``batch_size`` is a positive integer or
    ``"auto"``; ``instruction`` is optional instruction text for
    instruction-aware models; ``max_input_tokens`` optionally caps model
    input. The resolved section feeds the model fingerprint — changing any
    field here invalidates embeddings and everything downstream.
    """

    model: str
    revision: str
    dimensions: int
    provider: str = "sentence-transformers"
    normalize: bool = True
    device_preference: tuple[str, ...] = ("mps", "cpu")
    precision: str = "float16"
    batch_size: int | str = "auto"
    instruction: str | None = None
    max_input_tokens: int | None = None

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "provider": self.provider,
            "model": self.model,
            "revision": self.revision,
            "dimensions": self.dimensions,
            "normalize": self.normalize,
            "device_preference": list(self.device_preference),
            "precision": self.precision,
            "batch_size": self.batch_size,
            "instruction": self.instruction,
            "max_input_tokens": self.max_input_tokens,
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section, a component of embedding cache keys."""
        return _fingerprint(self.resolved_dict())

    @classmethod
    def _parse(cls, data: Mapping[str, Any], location: str) -> EmbeddingConfig:
        allowed = frozenset(
            {
                "provider",
                "model",
                "revision",
                "dimensions",
                "normalize",
                "device_preference",
                "precision",
                "batch_size",
                "instruction",
                "max_input_tokens",
            }
        )
        _check_unknown(data, allowed, location)
        devices = _get_str_tuple(data, "device_preference", location, ("mps", "cpu"))
        if not devices:
            raise ConfigError(f"{location}: 'device_preference' must not be empty")
        for device in devices:
            if device not in _DEVICES:
                allowed_devices = ", ".join(sorted(_DEVICES))
                raise ConfigError(
                    f"{location}: unknown device {device!r} in 'device_preference'; "
                    f"expected one of: {allowed_devices}"
                )
        precision = _get_str(data, "precision", location, "float16")
        if precision not in _PRECISIONS:
            allowed_precisions = ", ".join(sorted(_PRECISIONS))
            raise ConfigError(
                f"{location}: unknown precision {precision!r}; "
                f"expected one of: {allowed_precisions}"
            )
        batch_size: int | str
        raw_batch = data.get("batch_size", "auto")
        if isinstance(raw_batch, str):
            if raw_batch != "auto":
                raise ConfigError(
                    f"{location}: field 'batch_size' must be a positive integer or 'auto', "
                    f"got {raw_batch!r}"
                )
            batch_size = "auto"
        else:
            batch_size = _get_int(data, "batch_size", location, minimum=1)
        return cls(
            provider=_get_str(data, "provider", location, "sentence-transformers"),
            model=_get_str(data, "model", location),
            revision=_get_str(data, "revision", location),
            dimensions=_get_int(data, "dimensions", location, minimum=1),
            normalize=_get_bool(data, "normalize", location, True),
            device_preference=devices,
            precision=precision,
            batch_size=batch_size,
            instruction=_get_nullable_str(data, "instruction", location),
            max_input_tokens=_get_nullable_int(data, "max_input_tokens", location, minimum=1),
        )


@dataclass(frozen=True, slots=True)
class CandidateConfig:
    """Retrieval backend and recall budgets for candidate generation.

    ``backend`` is ``auto`` (choose exact or approximate by corpus size),
    ``exact``, or ``hnsw``. ``existing_relationship_kinds`` names the
    relationship kinds that count as an existing direct link for exclusion.
    ``max_total_pairs`` of ``None`` means no global bound.
    """

    backend: str = "auto"
    neighbors_per_unit: int = 50
    existing_relationship_kinds: tuple[str, ...] = ("explicit-link",)
    max_pairs_per_document: int = 100
    max_total_pairs: int | None = None

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "backend": self.backend,
            "neighbors_per_unit": self.neighbors_per_unit,
            "existing_relationship_kinds": list(self.existing_relationship_kinds),
            "max_pairs_per_document": self.max_pairs_per_document,
            "max_total_pairs": self.max_total_pairs,
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section, for candidate-set invalidation."""
        return _fingerprint(self.resolved_dict())

    @classmethod
    def _parse(cls, data: Mapping[str, Any], location: str) -> CandidateConfig:
        allowed = frozenset(
            {
                "backend",
                "neighbors_per_unit",
                "existing_relationship_kinds",
                "max_pairs_per_document",
                "max_total_pairs",
            }
        )
        _check_unknown(data, allowed, location)
        backend = _get_str(data, "backend", location, "auto")
        if backend not in _BACKENDS:
            allowed_backends = ", ".join(sorted(_BACKENDS))
            raise ConfigError(
                f"{location}: unknown backend {backend!r}; expected one of: {allowed_backends}"
            )
        defaults = cls()
        return cls(
            backend=backend,
            neighbors_per_unit=_get_int(data, "neighbors_per_unit", location, 50, minimum=1),
            existing_relationship_kinds=_get_str_tuple(
                data,
                "existing_relationship_kinds",
                location,
                defaults.existing_relationship_kinds,
            ),
            max_pairs_per_document=_get_int(
                data, "max_pairs_per_document", location, 100, minimum=1
            ),
            max_total_pairs=_get_nullable_int(data, "max_total_pairs", location, minimum=1),
        )


@dataclass(frozen=True, slots=True)
class RankingConfig:
    """Versioned ranking policy: profile, weights, thresholds, diversity.

    ``weights`` covers every term of the SPEC score formula
    (:data:`DEFAULT_RANKING_WEIGHTS`); user-provided weights merge over the
    defaults and unknown weight names are errors. ``diversity`` is the
    maximal-marginal-relevance trade-off in ``[0, 1]``. Changing this section
    invalidates proposals but not embeddings or raw candidates. (The ``r`` in
    "mean of the top r distinct section-pair similarities" is a candidate
    aggregation constant — :data:`linkdiscovery.candidates.generator.
    TOP_R_SECTIONS` — not a ranking knob.)
    """

    profile: str = "weighted-v1"
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_RANKING_WEIGHTS))
    minimum_relatedness: float = 0.0
    results_per_document: int = 10
    diversity: float = 0.2

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "profile": self.profile,
            "weights": dict(self.weights),
            "minimum_relatedness": self.minimum_relatedness,
            "results_per_document": self.results_per_document,
            "diversity": self.diversity,
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section; part of ``ranking_version``."""
        return _fingerprint(self.resolved_dict())

    @classmethod
    def _parse(cls, data: Mapping[str, Any], location: str) -> RankingConfig:
        allowed = frozenset(
            {
                "profile",
                "weights",
                "minimum_relatedness",
                "results_per_document",
                "diversity",
            }
        )
        _check_unknown(data, allowed, location)
        weights = dict(DEFAULT_RANKING_WEIGHTS)
        raw_weights = data.get("weights", {})
        weight_section = _expect_section(raw_weights, f"{location}.weights")
        for name, value in weight_section.items():
            if name not in DEFAULT_RANKING_WEIGHTS:
                allowed_weights = ", ".join(sorted(DEFAULT_RANKING_WEIGHTS))
                raise ConfigError(
                    f"{location}.weights: unknown weight {name!r}; "
                    f"expected one of: {allowed_weights}"
                )
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ConfigError(
                    f"{location}.weights: weight '{name}' must be a number, "
                    f"got {type(value).__name__}"
                )
            weights[name] = float(value)
        return cls(
            profile=_get_str(data, "profile", location, "weighted-v1"),
            weights=weights,
            minimum_relatedness=_get_float(data, "minimum_relatedness", location, 0.0),
            results_per_document=_get_int(data, "results_per_document", location, 10, minimum=1),
            diversity=_get_float(data, "diversity", location, 0.2, minimum=0.0, maximum=1.0),
        )


@dataclass(frozen=True, slots=True)
class ReportConfig:
    """Report formats and output policy.

    ``output_dir`` is handed to the reporter as a string; the pipeline
    orchestrator resolves a relative value against the artifacts root before
    the reporter sees it (stage implementations do no path logic of their
    own). ``include_evidence_text`` set to ``False`` omits evidence text
    while retaining source references, per the SPEC privacy section.
    Changing this section invalidates only rendered reports.
    """

    formats: tuple[str, ...] = ("jsonl", "markdown")
    output_dir: str = "reports"
    include_evidence_text: bool = True

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "formats": list(self.formats),
            "output_dir": self.output_dir,
            "include_evidence_text": self.include_evidence_text,
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section, for report invalidation."""
        return _fingerprint(self.resolved_dict())

    @classmethod
    def _parse(cls, data: Mapping[str, Any], location: str) -> ReportConfig:
        allowed = frozenset({"formats", "output_dir", "include_evidence_text"})
        _check_unknown(data, allowed, location)
        defaults = cls()
        formats = _get_str_tuple(data, "formats", location, defaults.formats)
        if not formats:
            raise ConfigError(f"{location}: 'formats' must not be empty")
        return cls(
            formats=formats,
            output_dir=_get_str(data, "output_dir", location, defaults.output_dir),
            include_evidence_text=_get_bool(data, "include_evidence_text", location, True),
        )


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """The complete declarative pipeline configuration.

    Composed of one section per stage; sections with required fields
    (``source``, ``preprocess``, ``embedding``) must be present, the rest
    default. ``resolved_dict()`` is written to the run manifest so a run
    records exactly what it ran with.
    """

    source: SourceConfig
    preprocess: PreprocessConfig
    embedding: EmbeddingConfig
    candidates: CandidateConfig = field(default_factory=CandidateConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    schema_version: int = CONFIG_SCHEMA_VERSION

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe configuration."""
        return {
            "schema_version": self.schema_version,
            "source": self.source.resolved_dict(),
            "preprocess": self.preprocess.resolved_dict(),
            "embedding": self.embedding.resolved_dict(),
            "candidates": self.candidates.resolved_dict(),
            "ranking": self.ranking.resolved_dict(),
            "report": self.report.resolved_dict(),
        }

    def fingerprint(self) -> str:
        """Fingerprint of the whole resolved configuration (run identity)."""
        return _fingerprint(self.resolved_dict())


def config_from_dict(data: dict[str, Any], location: str = "<config>") -> PipelineConfig:
    """Build a :class:`PipelineConfig` from already-parsed YAML/JSON data.

    Validation is strict: unknown fields anywhere raise ``ConfigError`` naming
    the field and location; ``schema_version`` must equal
    :data:`CONFIG_SCHEMA_VERSION`; ``source``, ``preprocess``, and
    ``embedding`` are required sections.
    """
    mapping = _expect_section(data, location)
    allowed = frozenset(
        {
            "schema_version",
            "source",
            "preprocess",
            "embedding",
            "candidates",
            "ranking",
            "report",
        }
    )
    _check_unknown(mapping, allowed, location)
    schema_version = _get_int(mapping, "schema_version", location)
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ConfigError(
            f"{location}: unknown schema_version {schema_version}; "
            f"this build of linkdiscovery reads version {CONFIG_SCHEMA_VERSION}"
        )

    def required_section(name: str) -> dict[str, Any]:
        if name not in mapping:
            raise ConfigError(f"{location}: missing required section '{name}'")
        return _expect_section(mapping[name], f"{location}.{name}")

    def optional_section(name: str) -> dict[str, Any] | None:
        if name not in mapping:
            return None
        return _expect_section(mapping[name], f"{location}.{name}")

    candidates_data = optional_section("candidates")
    ranking_data = optional_section("ranking")
    report_data = optional_section("report")
    return PipelineConfig(
        schema_version=schema_version,
        source=SourceConfig._parse(required_section("source"), f"{location}.source"),
        preprocess=PreprocessConfig._parse(
            required_section("preprocess"), f"{location}.preprocess"
        ),
        embedding=EmbeddingConfig._parse(required_section("embedding"), f"{location}.embedding"),
        candidates=(
            CandidateConfig._parse(candidates_data, f"{location}.candidates")
            if candidates_data is not None
            else CandidateConfig()
        ),
        ranking=(
            RankingConfig._parse(ranking_data, f"{location}.ranking")
            if ranking_data is not None
            else RankingConfig()
        ),
        report=(
            ReportConfig._parse(report_data, f"{location}.report")
            if report_data is not None
            else ReportConfig()
        ),
    )


def load_config(path: str | Path) -> PipelineConfig:
    """Load and strictly validate a pipeline configuration from a YAML file.

    Raises ``ConfigError`` when the file is unreadable, is not valid YAML, is
    not a mapping, or fails any validation in :func:`config_from_dict`. The
    file path appears in every error message as the location.
    """
    config_path = Path(path)
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read configuration file {config_path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{config_path}: invalid YAML: {exc}") from exc
    if data is None:
        raise ConfigError(f"{config_path}: configuration file is empty")
    if not isinstance(data, dict):
        raise ConfigError(f"{config_path}: top level must be a mapping, got {type(data).__name__}")
    return config_from_dict(data, location=str(config_path))
