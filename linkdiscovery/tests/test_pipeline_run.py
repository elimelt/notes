"""End-to-end tests for the pipeline orchestrator over the fixture corpus.

One full run over ``tests/fixtures/markdown_corpus`` with the hashing
provider is shared by the assertion tests (module-scoped fixture);
determinism, invalidation, review, and failure scenarios run their own
pipelines into fresh stores.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from linkdiscovery import (
    ConfigError,
    LinkProposal,
    Pipeline,
    PipelineConfig,
    PluginError,
    ReportError,
    RunManifest,
    RunResult,
    config_from_dict,
    load_config,
)
from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.reviews import DecisionKind, ReviewDecision, ReviewHistory
from linkdiscovery.interfaces import RegionParser, SourceAdapter
from linkdiscovery.plugins import instantiate_plugin
from linkdiscovery.report import save_review_history
from linkdiscovery_markdown.adapter import MarkdownSourceAdapter

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "markdown_corpus"
CONFIGS_DIR = Path(__file__).parent.parent / "configs"

SPEC_FEATURE_KEYS = frozenset(
    {
        "document_similarity",
        "best_chunk_similarity",
        "support_breadth",
        "lexical_similarity",
        "hubness_penalty",
        "graph_redundancy_penalty",
    }
)

STAGE_ORDER = ("source", "preprocess", "embed", "candidates", "rank", "report")

GROUPS_WRITTEN = (
    "corpus-manifest",
    "processed-corpus",
    "embeddings",
    "candidates",
    "proposals",
    "runs",
)


def make_config(**overrides: dict[str, Any]) -> PipelineConfig:
    """A hashing-provider configuration over the fixture corpus.

    ``overrides`` merge per section over the defaults, so a test can change
    one field (for example ``preprocess={"target_tokens": 96}``) without
    restating the rest.
    """
    data: dict[str, Any] = {
        "schema_version": 1,
        "source": {
            "adapter": "linkdiscovery_markdown.adapter:MarkdownSourceAdapter",
            "options": {"root": str(FIXTURE_ROOT), "exclude": ["templates/**"]},
        },
        "preprocess": {
            "parser": "linkdiscovery_markdown.parser:MarkdownRegionParser",
            "target_tokens": 128,
            "max_tokens": 192,
            "overlap_tokens": 16,
        },
        "embedding": {
            "provider": "hashing",
            "model": "hashing-baseline",
            "revision": "v1",
            "dimensions": 256,
            "precision": "float32",
            "device_preference": ["cpu"],
        },
    }
    for section, fields in overrides.items():
        data.setdefault(section, {}).update(fields)
    return config_from_dict(data)


def load_fixture_corpus() -> Any:
    """The fixture corpus straight from the adapter, for cross-checking."""
    config = make_config()
    return MarkdownSourceAdapter().load(config.source)


@pytest.fixture(scope="module")
def e2e(tmp_path_factory: pytest.TempPathFactory) -> RunResult:
    """One full pipeline run shared by the end-to-end assertion tests."""
    root = tmp_path_factory.mktemp("e2e") / "artifacts"
    return Pipeline().run(make_config(), artifacts_root=root, run_id="e2e")


def _unordered(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


class TestEndToEnd:
    def test_proposals_nonempty(self, e2e: RunResult) -> None:
        assert e2e.proposals.proposals

    def test_no_invalid_pairs(self, e2e: RunResult) -> None:
        """Acceptance criterion 6: no self, alias, excluded, or existing pairs."""
        corpus = load_fixture_corpus()
        ineligible = {
            doc.id
            for doc in corpus.documents
            if doc.flags.excluded or doc.flags.generated or doc.flags.archived
        }
        assert ineligible  # the fixture exercises every flag
        relationships = corpus.relationships.relationships
        existing = {
            _unordered(rel.source_id, rel.target_id)
            for rel in relationships
            if rel.kind == "explicit-link"
        }
        alias_pairs = {
            _unordered(rel.source_id, rel.target_id) for rel in relationships if rel.kind == "alias"
        }
        assert existing  # the fixture has explicit links to exclude
        for proposal in e2e.proposals.proposals:
            pair = _unordered(proposal.source_document_id, proposal.target_document_id)
            assert proposal.source_document_id != proposal.target_document_id
            assert proposal.source_document_id not in ineligible
            assert proposal.target_document_id not in ineligible
            assert pair not in existing
            assert pair not in alias_pairs

    def test_features_and_evidence(self, e2e: RunResult) -> None:
        """Every proposal carries the six SPEC features and span-backed evidence."""
        for proposal in e2e.proposals.proposals:
            assert set(proposal.features) >= SPEC_FEATURE_KEYS
            assert proposal.evidence
            assert any(
                evidence.source_spans and evidence.target_spans for evidence in proposal.evidence
            )
            assert proposal.ranking_version

    def test_all_artifact_groups_populated(self, e2e: RunResult) -> None:
        for group in GROUPS_WRITTEN:
            directory = e2e.artifacts_root / group
            assert directory.is_dir(), group
            assert any(directory.iterdir()), group

    def test_manifest_contents(self, e2e: RunResult) -> None:
        manifest = e2e.manifest
        assert manifest.resolved_config == make_config().resolved_dict()
        assert tuple(stage.stage for stage in manifest.stages) == STAGE_ORDER
        embed = next(stage for stage in manifest.stages if stage.stage == "embed")
        assert embed.cache_hits + embed.cache_misses == embed.input_count
        assert embed.output_count == embed.input_count > 0
        assert {ref.group for ref in manifest.artifacts} >= set(GROUPS_WRITTEN) - {"runs"}
        assert manifest.seeds == {}
        for key in (
            "corpus_fingerprint",
            "relationship_fingerprint",
            "model_fingerprint",
            "preprocessing_fingerprint",
            "device",
            "python",
            "numpy",
            "linkdiscovery",
            "platform",
        ):
            assert manifest.environment[key], key

    def test_stage_warnings_surface(self, e2e: RunResult) -> None:
        """Unresolved links and exclusions appear as stage warnings."""
        warnings = [w for stage in e2e.manifest.stages for w in stage.warnings]
        assert any("unresolved" in warning for warning in warnings)
        assert any("excluded" in warning for warning in warnings)

    def test_manifest_written_last_and_round_trips(self, e2e: RunResult) -> None:
        manifest_path = e2e.artifacts_root / "runs" / "run-e2e"
        assert manifest_path.is_file()
        parsed = RunManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        assert parsed == e2e.manifest
        manifest_mtime = manifest_path.stat().st_mtime_ns
        for ref in e2e.manifest.artifacts:
            if ref.group == "reports":
                path = e2e.report_dir / ref.path
            else:
                path = e2e.artifacts_root / ref.path
            assert path.is_file(), ref.path
            assert path.stat().st_mtime_ns <= manifest_mtime, ref.path

    def test_corpus_manifest_has_no_content(self, e2e: RunResult) -> None:
        ref = next(r for r in e2e.manifest.artifacts if r.group == "corpus-manifest")
        payload = json.loads((e2e.artifacts_root / ref.path).read_text(encoding="utf-8"))
        assert payload["documents"]
        for document in payload["documents"]:
            assert set(document) == {"id", "revision", "title", "source_ref", "flags"}
        assert payload["relationships"]["relationships"]

    def test_reports_exist_and_parse(self, e2e: RunResult) -> None:
        jsonl_path = e2e.report_dir / "proposals.jsonl"
        markdown_path = e2e.report_dir / "proposals.md"
        assert jsonl_path.is_file() and markdown_path.is_file()
        parsed_ids = set()
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            proposal = LinkProposal.from_dict(json.loads(line))
            parsed_ids.add(proposal.id)
        assert parsed_ids == {p.id for p in e2e.proposals.proposals}
        assert "# Link proposals" in markdown_path.read_text(encoding="utf-8")

    def test_source_documents_unchanged(self, e2e: RunResult) -> None:
        """Acceptance criterion 12: the run never touches the corpus files."""
        corpus = load_fixture_corpus()
        rerun = load_fixture_corpus()
        assert [doc.revision for doc in corpus.documents] == [
            doc.revision for doc in rerun.documents
        ]


class TestDeterminismAndIncremental:
    def test_second_run_is_identical_and_fully_cached(self, tmp_path: Path) -> None:
        root = tmp_path / "artifacts"
        config = make_config()
        first = Pipeline().run(config, artifacts_root=root, run_id="det")
        second = Pipeline().run(config, artifacts_root=root, run_id="det")

        assert [(p.id, p.score) for p in first.proposals.proposals] == [
            (p.id, p.score) for p in second.proposals.proposals
        ]
        embed_first = next(s for s in first.manifest.stages if s.stage == "embed")
        embed_second = next(s for s in second.manifest.stages if s.stage == "embed")
        assert embed_first.cache_hits == 0
        assert embed_first.cache_misses > 0
        assert embed_second.cache_misses == 0
        assert embed_second.cache_hits == embed_first.cache_misses

    def test_preprocess_change_invalidates_embedding_cache(self, tmp_path: Path) -> None:
        """The fingerprint chain: a chunking change re-embeds everything."""
        root = tmp_path / "artifacts"
        Pipeline().run(make_config(), artifacts_root=root, run_id="base")
        changed = make_config(preprocess={"target_tokens": 96, "max_tokens": 160})
        result = Pipeline().run(changed, artifacts_root=root, run_id="changed")
        embed = next(s for s in result.manifest.stages if s.stage == "embed")
        assert embed.cache_hits == 0
        assert embed.cache_misses > 0

    def test_default_run_id_shape(self, tmp_path: Path) -> None:
        result = Pipeline().run(make_config(), artifacts_root=tmp_path / "artifacts")
        stamp, _, digest = result.run_id.removeprefix("run-").rpartition("-")
        assert len(stamp) == 16 and stamp.endswith("Z")
        assert len(digest) == 8 and all(c in "0123456789abcdef" for c in digest)
        assert (result.artifacts_root / "runs" / result.run_id).is_file()


class TestReviews:
    def test_review_decisions_are_applied(self, tmp_path: Path) -> None:
        root = tmp_path / "artifacts"
        config = make_config()
        first = Pipeline().run(config, artifacts_root=root, run_id="rev")
        accepted_id = first.proposals.proposals[0].id
        history = ReviewHistory(
            header=ArtifactHeader(
                schema_version=1,
                run_id="rev",
                corpus_id=first.manifest.header.corpus_id,
                created_at=utc_now_iso(),
                config_fingerprint="",
                producer_version="tests",
            ),
            decisions=(
                ReviewDecision(
                    proposal_id=accepted_id,
                    decision=DecisionKind.ACCEPT,
                    decided_at=utc_now_iso(),
                ),
            ),
        )
        reviews_path = tmp_path / "reviews.json"
        save_review_history(history, reviews_path)

        second = Pipeline().run(
            config, artifacts_root=root, reviews_path=reviews_path, run_id="rev"
        )
        by_id = {p.id: p for p in second.proposals.proposals}
        assert by_id[accepted_id].review.status == "accepted"
        others = [p for p in second.proposals.proposals if p.id != accepted_id]
        assert all(p.review.status == "unreviewed" for p in others)
        rank = next(s for s in second.manifest.stages if s.stage == "rank")
        assert rank.counters["reviewed"] == 1
        assert rank.counters["review_decisions"] == 1


class TestFailureHandling:
    def test_stage_failure_writes_no_manifest(self, tmp_path: Path) -> None:
        root = tmp_path / "artifacts"
        config = make_config(report={"formats": ["jsonl", "html"]})
        with pytest.raises(ReportError, match="html"):
            Pipeline().run(config, artifacts_root=root, run_id="boom")
        runs_dir = root / "runs"
        assert not runs_dir.exists() or not any(runs_dir.iterdir())

    def test_wrong_plugin_type_is_rejected(self, tmp_path: Path) -> None:
        config = make_config(
            source={"adapter": "linkdiscovery_markdown.parser:MarkdownRegionParser"}
        )
        with pytest.raises(PluginError, match="SourceAdapter"):
            Pipeline().run(config, artifacts_root=tmp_path / "artifacts")

    def test_missing_plugin_module_is_rejected(self, tmp_path: Path) -> None:
        config = make_config(source={"adapter": "no.such.module:Adapter"})
        with pytest.raises(PluginError, match=r"no\.such\.module"):
            Pipeline().run(config, artifacts_root=tmp_path / "artifacts")

    def test_unknown_provider_has_no_token_counter(self, tmp_path: Path) -> None:
        config = make_config(embedding={"provider": "mystery"})
        with pytest.raises(ConfigError, match="token counter"):
            Pipeline().run(config, artifacts_root=tmp_path / "artifacts")


class TestShippedConfigs:
    @pytest.mark.parametrize("name", ["notes.yaml", "notes-baseline.yaml"])
    def test_config_loads_and_plugins_resolve(self, name: str) -> None:
        config = load_config(CONFIGS_DIR / name)
        adapter = instantiate_plugin(config.source.adapter, SourceAdapter)
        parser = instantiate_plugin(config.preprocess.parser, RegionParser)
        assert isinstance(adapter, SourceAdapter)
        assert isinstance(parser, RegionParser)

    def test_baseline_is_the_hashing_profile(self) -> None:
        config = load_config(CONFIGS_DIR / "notes-baseline.yaml")
        assert config.embedding.provider == "hashing"
        assert config.embedding.model == "hashing-baseline"
        assert config.embedding.revision == "v1"
        assert config.embedding.dimensions == 512
        assert config.embedding.precision == "float32"
