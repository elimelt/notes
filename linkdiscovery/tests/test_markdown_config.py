"""configs/notes.yaml must load through the strict core config parser."""

from __future__ import annotations

from pathlib import Path

from linkdiscovery.config import load_config
from linkdiscovery.interfaces import RegionParser, SourceAdapter
from linkdiscovery.plugins import instantiate_plugin

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "notes.yaml"


def test_notes_config_loads_and_resolves() -> None:
    config = load_config(CONFIG_PATH)
    assert config.schema_version == 1

    assert config.source.adapter == "linkdiscovery_markdown.adapter:MarkdownSourceAdapter"
    assert config.source.options == {"root": "../content", "exclude": ["templates/**"]}

    assert config.preprocess.parser == "linkdiscovery_markdown.parser:MarkdownRegionParser"
    assert config.preprocess.views == ("document", "section", "title")
    assert config.preprocess.target_tokens == 384
    assert config.preprocess.max_tokens == 512
    assert config.preprocess.overlap_tokens == 48
    assert config.preprocess.exclude_regions == ("boilerplate", "metadata")

    assert config.embedding.provider == "sentence-transformers"
    assert config.embedding.model == "Qwen/Qwen3-Embedding-0.6B"
    # The SPEC requires an immutable model revision; "main" is a moving ref.
    assert config.embedding.revision == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    assert config.embedding.dimensions == 1024
    assert config.embedding.normalize is True
    assert config.embedding.device_preference == ("mps", "cpu")
    assert config.embedding.precision == "float32"
    assert config.embedding.batch_size == "auto"

    assert config.candidates.backend == "auto"
    assert config.candidates.neighbors_per_unit == 50
    assert config.candidates.existing_relationship_kinds == ("explicit-link",)
    assert config.candidates.max_pairs_per_document == 100

    assert config.ranking.profile == "weighted-v1"
    assert config.ranking.minimum_relatedness == 0.0
    assert config.ranking.results_per_document == 10
    assert config.ranking.diversity == 0.2

    assert config.report.formats == ("jsonl", "markdown")
    assert config.report.output_dir == "reports"
    assert config.report.include_evidence_text is True

    # the resolved configuration is fingerprintable (JSON-safe throughout)
    assert config.fingerprint().startswith("sha256:")


def test_plugin_specs_resolve_to_protocol_conformant_instances() -> None:
    config = load_config(CONFIG_PATH)
    adapter = instantiate_plugin(config.source.adapter, SourceAdapter)
    parser = instantiate_plugin(config.preprocess.parser, RegionParser)
    assert isinstance(adapter, SourceAdapter)
    assert isinstance(parser, RegionParser)
    assert parser.fingerprint.startswith("linkdiscovery-markdown-parser/")
