"""Strict configuration loading tests."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from linkdiscovery.config import (
    DEFAULT_RANKING_WEIGHTS,
    PipelineConfig,
    config_from_dict,
    load_config,
)
from linkdiscovery.errors import ConfigError

SPEC_YAML = textwrap.dedent(
    """
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
    """
)

MINIMAL: dict[str, Any] = {
    "schema_version": 1,
    "source": {"adapter": "package.module:Adapter"},
    "preprocess": {"parser": "package.module:Parser"},
    "embedding": {
        "model": "Qwen/Qwen3-Embedding-8B",
        "revision": "rev-abc",
        "dimensions": 4096,
    },
}


def minimal() -> dict[str, Any]:
    """A deep-enough copy of the minimal valid configuration."""
    return {
        "schema_version": 1,
        "source": dict(MINIMAL["source"]),
        "preprocess": dict(MINIMAL["preprocess"]),
        "embedding": dict(MINIMAL["embedding"]),
    }


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "pipeline.yaml"
    path.write_text(content, encoding="utf-8")
    return path


class TestLoadConfig:
    def test_spec_example_loads(self, tmp_path: Path) -> None:
        config = load_config(write_config(tmp_path, SPEC_YAML))
        assert config.source.adapter == "package.module:Adapter"
        assert config.preprocess.views == ("document", "section", "title")
        assert config.preprocess.target_tokens == 384
        assert config.embedding.model == "Qwen/Qwen3-Embedding-8B"
        assert config.embedding.batch_size == "auto"
        assert config.candidates.neighbors_per_unit == 50
        assert config.ranking.profile == "weighted-v1"
        assert config.report.formats == ("jsonl", "markdown")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="cannot read configuration file"):
            load_config(tmp_path / "absent.yaml")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="invalid YAML"):
            load_config(write_config(tmp_path, "source: [unclosed"))

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="configuration file is empty"):
            load_config(write_config(tmp_path, ""))

    def test_non_mapping_top_level_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="top level must be a mapping"):
            load_config(write_config(tmp_path, "- just\n- a\n- list\n"))

    def test_error_location_names_the_file(self, tmp_path: Path) -> None:
        path = write_config(tmp_path, SPEC_YAML.replace("neighbors_per_unit", "neighbours"))
        with pytest.raises(ConfigError, match=r"pipeline\.yaml\.candidates.*'neighbours'"):
            load_config(path)


class TestStrictness:
    def test_unknown_top_level_field_named(self) -> None:
        data = minimal()
        data["rankings"] = {}
        with pytest.raises(ConfigError, match=r"<config>: unknown field 'rankings'"):
            config_from_dict(data)

    def test_unknown_section_field_named_with_location(self) -> None:
        data = minimal()
        data["embedding"]["quantize"] = True
        with pytest.raises(ConfigError, match=r"<config>\.embedding: unknown field 'quantize'"):
            config_from_dict(data)

    def test_missing_required_section(self) -> None:
        data = minimal()
        del data["embedding"]
        with pytest.raises(ConfigError, match="missing required section 'embedding'"):
            config_from_dict(data)

    def test_missing_required_field(self) -> None:
        data = minimal()
        del data["embedding"]["revision"]
        with pytest.raises(ConfigError, match="missing required field 'revision'"):
            config_from_dict(data)

    def test_missing_schema_version(self) -> None:
        data = minimal()
        del data["schema_version"]
        with pytest.raises(ConfigError, match="missing required field 'schema_version'"):
            config_from_dict(data)

    def test_unknown_schema_version(self) -> None:
        data = minimal()
        data["schema_version"] = 2
        with pytest.raises(ConfigError, match="unknown schema_version 2"):
            config_from_dict(data)

    def test_wrong_type_reports_field_and_location(self) -> None:
        data = minimal()
        data["preprocess"]["target_tokens"] = "many"
        with pytest.raises(
            ConfigError, match=r"<config>\.preprocess: field 'target_tokens' must be an integer"
        ):
            config_from_dict(data)


class TestDomainValidation:
    def test_overlap_must_be_less_than_target(self) -> None:
        data = minimal()
        data["preprocess"]["target_tokens"] = 100
        data["preprocess"]["overlap_tokens"] = 100
        with pytest.raises(ConfigError, match="'overlap_tokens' \\(100\\) must be <"):
            config_from_dict(data)

    def test_max_tokens_must_cover_target(self) -> None:
        data = minimal()
        data["preprocess"]["target_tokens"] = 600
        with pytest.raises(ConfigError, match="'max_tokens' \\(512\\) must be >="):
            config_from_dict(data)

    def test_unknown_region_kind_rejected(self) -> None:
        data = minimal()
        data["preprocess"]["include_regions"] = ["prose", "sidebar"]
        with pytest.raises(ConfigError, match="unknown region kind 'sidebar'"):
            config_from_dict(data)

    def test_region_in_both_lists_rejected(self) -> None:
        data = minimal()
        data["preprocess"]["include_regions"] = ["prose", "boilerplate"]
        with pytest.raises(ConfigError, match="both 'include_regions' and 'exclude_regions'"):
            config_from_dict(data)

    def test_unknown_device_rejected(self) -> None:
        data = minimal()
        data["embedding"]["device_preference"] = ["tpu"]
        with pytest.raises(ConfigError, match="unknown device 'tpu'"):
            config_from_dict(data)

    def test_unknown_precision_rejected(self) -> None:
        data = minimal()
        data["embedding"]["precision"] = "int4"
        with pytest.raises(ConfigError, match="unknown precision 'int4'"):
            config_from_dict(data)

    def test_batch_size_accepts_auto_and_int(self) -> None:
        data = minimal()
        data["embedding"]["batch_size"] = 32
        assert config_from_dict(data).embedding.batch_size == 32
        data["embedding"]["batch_size"] = "auto"
        assert config_from_dict(data).embedding.batch_size == "auto"

    def test_batch_size_rejects_other_strings_and_zero(self) -> None:
        data = minimal()
        data["embedding"]["batch_size"] = "big"
        with pytest.raises(ConfigError, match="'batch_size' must be a positive integer"):
            config_from_dict(data)
        data["embedding"]["batch_size"] = 0
        with pytest.raises(ConfigError, match="'batch_size' must be >= 1"):
            config_from_dict(data)

    def test_unknown_backend_rejected(self) -> None:
        data = minimal()
        data["candidates"] = {"backend": "faiss"}
        with pytest.raises(ConfigError, match="unknown backend 'faiss'"):
            config_from_dict(data)

    def test_diversity_out_of_range_rejected(self) -> None:
        data = minimal()
        data["ranking"] = {"diversity": 1.5}
        with pytest.raises(ConfigError, match="'diversity' must be within"):
            config_from_dict(data)

    def test_unknown_weight_rejected(self) -> None:
        data = minimal()
        data["ranking"] = {"weights": {"w_document": 0.5, "w_magic": 1.0}}
        with pytest.raises(ConfigError, match=r"\.ranking\.weights: unknown weight 'w_magic'"):
            config_from_dict(data)

    def test_weights_merge_over_defaults(self) -> None:
        data = minimal()
        data["ranking"] = {"weights": {"w_hub": 0.9}}
        weights = config_from_dict(data).ranking.weights
        assert weights["w_hub"] == 0.9
        assert weights["w_document"] == DEFAULT_RANKING_WEIGHTS["w_document"]
        assert set(weights) == set(DEFAULT_RANKING_WEIGHTS)


class TestDefaultsAndResolution:
    def test_defaults_are_filled(self) -> None:
        config = config_from_dict(minimal())
        assert config.preprocess.target_tokens == 384
        assert config.preprocess.exclude_regions == ("boilerplate",)
        assert config.embedding.provider == "sentence-transformers"
        assert config.embedding.device_preference == ("mps", "cpu")
        assert config.embedding.instruction is None
        assert config.embedding.max_input_tokens is None
        assert config.candidates.backend == "auto"
        assert config.candidates.max_total_pairs is None
        assert config.ranking.weights == DEFAULT_RANKING_WEIGHTS
        assert config.report.output_dir == "reports"

    def test_resolved_dict_covers_every_section(self) -> None:
        resolved = config_from_dict(minimal()).resolved_dict()
        assert set(resolved) == {
            "schema_version",
            "source",
            "preprocess",
            "embedding",
            "candidates",
            "ranking",
            "report",
        }
        assert resolved["ranking"]["weights"] == DEFAULT_RANKING_WEIGHTS
        assert resolved["embedding"]["batch_size"] == "auto"

    def test_resolved_dict_reconstructs_identically(self) -> None:
        config = config_from_dict(minimal())
        assert config_from_dict(config.resolved_dict()) == config


class TestFingerprints:
    def test_fingerprint_stable_for_equivalent_configs(self, tmp_path: Path) -> None:
        from_yaml = load_config(write_config(tmp_path, SPEC_YAML))
        from_minimal_equivalent = config_from_dict(from_yaml.resolved_dict())
        assert from_yaml.fingerprint() == from_minimal_equivalent.fingerprint()

    def test_fingerprint_changes_when_a_field_changes(self) -> None:
        base = config_from_dict(minimal())
        data = minimal()
        data["embedding"]["dimensions"] = 1024
        changed = config_from_dict(data)
        assert base.fingerprint() != changed.fingerprint()

    def test_stage_fingerprints_are_independent(self) -> None:
        base = config_from_dict(minimal())
        data = minimal()
        data["ranking"] = {"diversity": 0.5}
        changed = config_from_dict(data)
        # A ranking change must not invalidate embeddings or preprocessing.
        assert base.embedding.fingerprint() == changed.embedding.fingerprint()
        assert base.preprocess.fingerprint() == changed.preprocess.fingerprint()
        assert base.ranking.fingerprint() != changed.ranking.fingerprint()
        assert base.fingerprint() != changed.fingerprint()

    def test_defaults_explicit_vs_implicit_fingerprint_identical(self) -> None:
        implicit = config_from_dict(minimal())
        data = minimal()
        data["candidates"] = {"backend": "auto", "neighbors_per_unit": 50}
        explicit = config_from_dict(data)
        assert implicit.fingerprint() == explicit.fingerprint()

    def test_config_type_is_frozen(self) -> None:
        config = config_from_dict(minimal())
        assert isinstance(config, PipelineConfig)
        with pytest.raises(AttributeError):
            config.schema_version = 2  # type: ignore[misc]
