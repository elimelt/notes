"""End-to-end tests for the inline-link workflow over the fixture corpus.

One shared :func:`~linkdiscovery.inline.workflow.load_inline_inputs` call
(module-scoped, hashing embedding provider) feeds every phase: audit
sampling, anchor artifacts, the recall-ceiling gate, the deterministic
baseline engine, head training on synthetic two-annotator labels, the
learned engine, and the report renderer.
"""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from linkdiscovery import PipelineConfig, config_from_dict
from linkdiscovery.artifacts.cache import ArtifactCache
from linkdiscovery.artifacts.store import ArtifactStore
from linkdiscovery.contracts import SourceDocument, Span
from linkdiscovery.errors import ConfigError, ContractError
from linkdiscovery.inline import workflow
from linkdiscovery.inline.anchors import AnchorConfig, AnchorDictionary
from linkdiscovery.inline.audit.annotate import save_audit_labels
from linkdiscovery.inline.audit.tiers import derive_tier
from linkdiscovery.inline.baseline import BaselineConfig
from linkdiscovery.inline.calibrate import TEMPERATURE_MAX, TEMPERATURE_MIN
from linkdiscovery.inline.encode import HashingTokenEncoder, span_representation
from linkdiscovery.inline.heads import TrainedHeads
from linkdiscovery.inline.records import (
    AuditItem,
    AuditLabel,
    AuditSample,
    Benchmark,
    BenchmarkCase,
    BenchmarkKind,
    InlineProposal,
    InlineProposalSet,
    InlineReviewDecision,
    LinkRegionKind,
)
from linkdiscovery.inline.report import write_inline_report
from linkdiscovery.inline.select import SelectionConfig
from linkdiscovery.inline.spans import SpanConfig
from linkdiscovery.inline.train import TrainConfig, review_span_key
from tests.conftest import make_header

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "markdown_corpus"

RECALL_GATE = 0.85
"""The §12 candidate-generation ceiling the fixture corpus must clear."""

TEST_THRESHOLD = 0.2
"""A low accept threshold so the tiny fixture corpus yields accepted proposals."""


def config_for_root(root: Path, exclude: list[str] | None = None) -> PipelineConfig:
    """A hashing-provider configuration over any markdown corpus root."""
    options: dict[str, Any] = {"root": str(root)}
    if exclude is not None:
        options["exclude"] = exclude
    data: dict[str, Any] = {
        "schema_version": 1,
        "source": {
            "adapter": "linkdiscovery_markdown.adapter:MarkdownSourceAdapter",
            "options": options,
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
    return config_from_dict(data)


def make_config() -> PipelineConfig:
    """The hashing-provider configuration over the fixture corpus."""
    return config_for_root(FIXTURE_ROOT, exclude=["templates/**"])


def synthetic_labels(sample: AuditSample) -> list[AuditLabel]:
    """Two plausible annotators over the whole sample; bob disputes some anchors."""
    labels: list[AuditLabel] = []
    for position, item in enumerate(sample.items):
        for annotator in ("alice", "bob"):
            natural = not (annotator == "bob" and position % 5 == 0)
            tier = derive_tier(True, natural, True, item.region_kind)
            labels.append(
                AuditLabel(
                    item_id=item.id,
                    annotator=annotator,
                    target_correct=True,
                    anchor_natural=natural,
                    placement_valid=True,
                    tier=tier,
                )
            )
    return labels


@pytest.fixture(scope="module")
def inputs(tmp_path_factory: pytest.TempPathFactory) -> workflow.InlineInputs:
    """Shared v1-stage inputs (adapter, preprocess, embed) over the fixture corpus."""
    root = tmp_path_factory.mktemp("inline-workflow") / "artifacts"
    return workflow.load_inline_inputs(make_config(), artifacts_root=root)


@pytest.fixture(scope="module")
def audit_dir(tmp_path_factory: pytest.TempPathFactory, inputs: workflow.InlineInputs) -> Path:
    """Audit artifacts written once for the whole module."""
    out = tmp_path_factory.mktemp("inline-workflow-audit")
    workflow.build_audit_artifacts(inputs, size=50, seed=7, out_dir=out)
    return out


@pytest.fixture(scope="module")
def sample(audit_dir: Path) -> AuditSample:
    return workflow.load_audit_sample(audit_dir / "audit-sample.json")


BASELINE_SELECTION = SelectionConfig(
    accept_threshold=TEST_THRESHOLD,
    existing_target_window_chars=0,
    single_word_naturalness_floor=0.2,
)
"""Shared-fixture selection config with the precision rules relaxed. The
fixture corpus's only above-threshold baseline draft ("consistency" in the
dynamo note) is BOTH a same-target near-duplicate (28 characters from an
existing link to the same target) AND a generic single lowercase word below
the raised floor — i.e. exactly what the new rules reject — and this fixture
needs at least one *accepted* proposal to exercise the happy path. The
precision rules themselves are integration-tested on a purpose-built corpus
in :class:`TestPrecisionRules`."""


@pytest.fixture(scope="module")
def baseline_set(inputs: workflow.InlineInputs) -> InlineProposalSet:
    return workflow.propose_inline_baseline(
        inputs,
        anchor_config=AnchorConfig(),
        span_config=SpanConfig(),
        baseline_config=BaselineConfig(),
        selection_config=BASELINE_SELECTION,
        run_id="wf-baseline",
    )


def existing_link_spans(inputs: workflow.InlineInputs) -> dict[str, list[tuple[int, int]]]:
    """(start, end) of every span-carrying explicit link, per source document."""
    spans: dict[str, list[tuple[int, int]]] = {}
    for relationship in inputs.relationships.relationships:
        if relationship.kind == "explicit-link" and relationship.source_span is not None:
            spans.setdefault(relationship.source_id, []).append(
                (relationship.source_span.start, relationship.source_span.end)
            )
    return spans


def note_budget(inputs: workflow.InlineInputs, document_id: str) -> int:
    """The SelectionConfig-default per-note budget from the document's word count."""
    config = SelectionConfig()
    document = next(d for d in inputs.corpus.documents if d.id == document_id)
    words = len(document.content.split())
    return min(config.max_links_per_note, max(1, words // config.words_per_link))


def assert_hard_constraints(
    proposals: InlineProposalSet, inputs: workflow.InlineInputs
) -> list[InlineProposal]:
    """Assert budget/overlap/self-link/existing-link constraints; return accepted."""
    accepted = [p for p in proposals.proposals if not p.abstained]
    link_spans = existing_link_spans(inputs)
    by_note: dict[str, list[InlineProposal]] = {}
    for proposal in accepted:
        assert proposal.source_document_id != proposal.target_document_id
        for start, end in link_spans.get(proposal.source_document_id, []):
            assert not (proposal.span.start < end and start < proposal.span.end), (
                "accepted proposal overlaps an existing link"
            )
        by_note.setdefault(proposal.source_document_id, []).append(proposal)
    for document_id, group in by_note.items():
        assert len(group) <= note_budget(inputs, document_id)
        ordered = sorted(group, key=lambda p: p.span.start)
        for left, right in pairwise(ordered):
            assert left.span.end <= right.span.start, "accepted spans overlap within a note"
    return accepted


class TestAuditArtifacts:
    def test_sample_round_trips(self, audit_dir: Path, sample: AuditSample) -> None:
        raw = json.loads((audit_dir / "audit-sample.json").read_text(encoding="utf-8"))
        assert AuditSample.from_dict(raw) == sample
        assert sample.items
        assert sum(sample.strata_counts.values()) == len(sample.items)

    def test_items_reference_real_links(
        self, sample: AuditSample, inputs: workflow.InlineInputs
    ) -> None:
        document_ids = {document.id for document in inputs.corpus.documents}
        for item in sample.items:
            assert item.source_document_id in document_ids
            assert item.target_document_id in document_ids
            assert item.source_span is not None

    def test_markdown_companion_lists_every_item(
        self, audit_dir: Path, sample: AuditSample
    ) -> None:
        text = (audit_dir / "audit-sample.md").read_text(encoding="utf-8")
        assert "# Inline-link audit sample" in text
        for item in sample.items:
            assert item.id in text
            assert item.source_document_id in text

    def test_deterministic_for_fixed_seed(
        self, inputs: workflow.InlineInputs, sample: AuditSample, tmp_path: Path
    ) -> None:
        again = workflow.build_audit_artifacts(inputs, size=50, seed=7, out_dir=tmp_path)
        assert [item.id for item in again.items] == [item.id for item in sample.items]


@pytest.fixture(scope="module")
def anchors_dir(tmp_path_factory: pytest.TempPathFactory, inputs: workflow.InlineInputs) -> Path:
    out = tmp_path_factory.mktemp("inline-workflow-anchors")
    workflow.build_anchor_artifacts(inputs, config=AnchorConfig(), out_dir=out)
    return out


@pytest.fixture(scope="module")
def heads_dir(
    tmp_path_factory: pytest.TempPathFactory,
    inputs: workflow.InlineInputs,
    audit_dir: Path,
    sample: AuditSample,
) -> Path:
    out = tmp_path_factory.mktemp("inline-workflow-train")
    labels_path = out / "labels.jsonl"
    save_audit_labels(synthetic_labels(sample), labels_path)
    heads_out = out / "heads"
    workflow.train_inline_heads(
        inputs,
        labels_path,
        audit_dir / "audit-sample.json",
        train_config=TrainConfig(epochs=2, batch_size=16),
        seed=0,
        out_dir=heads_out,
    )
    return heads_out


class TestAnchorArtifacts:
    def test_dictionary_written_with_occurrences(self, anchors_dir: Path) -> None:
        raw = json.loads((anchors_dir / "anchor-dictionary.json").read_text(encoding="utf-8"))
        dictionary = AnchorDictionary.from_dict(raw)
        assert dictionary.has_occurrences
        assert dictionary.mentions()

    def test_stats_are_sane(self, anchors_dir: Path) -> None:
        stats = json.loads((anchors_dir / "anchor-stats.json").read_text(encoding="utf-8"))
        assert stats["mention_count"] > 0
        assert 0 <= stats["eligible_mention_count"] <= stats["mention_count"]
        assert 0 <= stats["synthetic_mention_count"] <= stats["mention_count"]
        deciles = stats["keyphraseness_deciles"]
        assert set(deciles) == {f"p{d}" for d in range(0, 101, 10)}
        values = [deciles[f"p{d}"] for d in range(0, 101, 10)]
        assert values == sorted(values)
        assert all(0.0 <= value <= 1.0 for value in values)


def _markup_item(content: str, anchor_text: str, doc_id: str = "note") -> AuditItem:
    """An audit item whose source span covers the whole link markup in ``content``."""
    start = content.index("[")
    end = content.index(")") + 1 if "](" in content else content.index("]]") + 2
    return AuditItem(
        id="item-1",
        source_document_id=doc_id,
        target_document_id="target",
        anchor_text=anchor_text,
        source_span=Span(start=start, end=end),
        region_kind=LinkRegionKind.PROSE,
        context="",
        anchor_word_count=len(anchor_text.split()),
        topic_family="t",
        strata_key="k",
    )


def _doc(content: str, doc_id: str = "note") -> SourceDocument:
    return SourceDocument(id=doc_id, revision="r1", media_type="text/markdown", content=content)


class TestNarrowToAnchor:
    """Pinning tests: markup spans narrow to the RENDERED display text."""

    def test_wikilink_display_text_inside_target_path_is_not_mislocated(self) -> None:
        # The display text "cache" is also a substring of the target
        # ("[[caches|cache]]"); the narrowed span must be the rendered
        # anchor after the pipe, not the first occurrence inside the target.
        content = "We rely on [[caches|cache]] behavior in hot paths.\n"
        item = _markup_item(content, "cache")
        narrowed = workflow._narrow_to_anchor(item, {"note": _doc(content)})
        assert narrowed.source_span is not None
        expected_start = content.index("|") + 1
        assert narrowed.source_span.start == expected_start
        assert content[narrowed.source_span.start : narrowed.source_span.end] == "cache"

    def test_markdown_link_display_text_precedes_target(self) -> None:
        content = "See the [cache](notes/cache.md) writeup.\n"
        item = _markup_item(content, "cache")
        narrowed = workflow._narrow_to_anchor(item, {"note": _doc(content)})
        assert narrowed.source_span is not None
        assert narrowed.source_span.start == content.index("[cache]") + 1
        assert content[narrowed.source_span.start : narrowed.source_span.end] == "cache"

    def test_unfindable_anchor_keeps_the_markup_span(self) -> None:
        # Humanized anchors that never appear verbatim stay conservative.
        content = "Read [[graph-theory]] for background.\n"
        item = _markup_item(content, "Graph Theory")
        narrowed = workflow._narrow_to_anchor(item, {"note": _doc(content)})
        assert narrowed.source_span == item.source_span


class TestRecallCheck:
    def test_gate_passes_on_fixture(
        self, inputs: workflow.InlineInputs, sample: AuditSample
    ) -> None:
        metrics = workflow.check_span_recall(
            inputs, sample, anchor_config=AnchorConfig(), span_config=SpanConfig()
        )
        assert set(metrics) == {"exact_recall", "overlap_recall", "n_prose_items"}
        assert metrics["n_prose_items"] > 0
        assert 0.0 < metrics["exact_recall"] <= metrics["overlap_recall"] <= 1.0
        assert metrics["overlap_recall"] >= RECALL_GATE


class TestBaselinePropose:
    def test_returns_proposal_set_with_accepted(
        self, baseline_set: InlineProposalSet, inputs: workflow.InlineInputs
    ) -> None:
        accepted = assert_hard_constraints(baseline_set, inputs)
        assert accepted, "the fixture corpus should yield at least one accepted proposal"
        for proposal in accepted:
            effective = (
                proposal.calibrated_probability
                if proposal.calibrated_probability is not None
                else proposal.combined_score
            )
            assert effective >= TEST_THRESHOLD
            assert 0.0 <= proposal.naturalness <= 1.0
            assert 0.0 <= proposal.target_correctness <= 1.0
            assert 0.0 <= proposal.placement_validity <= 1.0

    def test_abstentions_kept_with_reasons(self, baseline_set: InlineProposalSet) -> None:
        for proposal in baseline_set.proposals:
            if proposal.abstained:
                assert proposal.features.get("selection_rejected") == 1.0
                assert any(name.startswith("rejected_") for name in proposal.features)

    def test_round_trips(self, baseline_set: InlineProposalSet) -> None:
        parsed = InlineProposalSet.from_dict(baseline_set.to_dict())
        assert parsed == baseline_set

    def test_deterministic(
        self, baseline_set: InlineProposalSet, inputs: workflow.InlineInputs
    ) -> None:
        again = workflow.propose_inline_baseline(
            inputs,
            anchor_config=AnchorConfig(),
            span_config=SpanConfig(),
            baseline_config=BaselineConfig(),
            selection_config=BASELINE_SELECTION,
            run_id="wf-baseline",
        )
        assert [p.id for p in again.proposals] == [p.id for p in baseline_set.proposals]
        assert [p.combined_score for p in again.proposals] == [
            p.combined_score for p in baseline_set.proposals
        ]


class TestFamiliesFromDocumentIds:
    def test_depth_one_takes_the_first_path_segment(self) -> None:
        families = workflow.families_from_document_ids(
            ["systems/dynamo", "plain", "math/attention/scaled"]
        )
        assert families == {
            "systems/dynamo": "systems",
            "math/attention/scaled": "math",
        }

    def test_depth_two_joins_the_first_two_segments(self) -> None:
        families = workflow.families_from_document_ids(["a/b/c/d", "a/b", "flat"], depth=2)
        assert families == {"a/b/c/d": "a/b", "a/b": "a/b"}

    def test_ids_without_slash_are_omitted(self) -> None:
        assert workflow.families_from_document_ids(["plain", "index"]) == {}

    def test_depth_below_one_raises(self) -> None:
        with pytest.raises(ConfigError, match="depth"):
            workflow.families_from_document_ids(["a/b"], depth=0)


PRECISION_CORPUS = {
    "os/source.md": (
        "---\ntitle: Source Note\n---\n\n# Source Note\n\n"
        "Read [[ml/target|Target Note]] for background on the idea. Later in\n"
        "the same paragraph the phrase Target Note shows up again in plain\n"
        "prose, well inside the suppression window, restating the concept.\n"
    ),
    "ml/target.md": (
        "---\ntitle: Target Note\naliases:\n  - shared memory\n---\n\n# Target Note\n\n"
        "The target concept explained at length, including how shared memory\n"
        "behaves under contention.\n"
    ),
    "os/other.md": (
        "---\ntitle: Other Note\n---\n\n# Other Note\n\n"
        "The kernel tracks shared memory regions carefully across process\n"
        "boundaries and reclaims them on exit.\n"
    ),
    "os/related.md": (
        "---\ntitle: Related Holder\n---\n\n# Related Holder\n\n"
        "This prose paragraph mentions Target Note as a plain phrase with no\n"
        "inline link anywhere near it in the running text.\n\n"
        "## Related notes\n\n"
        "- [[ml/target|Target Note]]\n"
    ),
}
"""A purpose-built corpus for the precision rules: ``os/source`` already
links ``ml/target`` in PROSE and repeats the anchor phrase nearby (Rule A
suppresses), ``os/other`` mentions a lowercase alias of the cross-family
``ml/target`` (Rule B), and ``os/related`` links ``ml/target`` only from a
Related-notes navigation entry near a prose mention (Rule A must NOT
suppress — guideline duplication rule: prose is the preferred home)."""


@pytest.fixture(scope="module")
def precision_inputs(tmp_path_factory: pytest.TempPathFactory) -> workflow.InlineInputs:
    root = tmp_path_factory.mktemp("precision-corpus")
    for name, content in PRECISION_CORPUS.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    artifacts = tmp_path_factory.mktemp("precision-artifacts")
    return workflow.load_inline_inputs(config_for_root(root), artifacts_root=artifacts)


def propose_precision(inputs: workflow.InlineInputs, family_depth: int) -> InlineProposalSet:
    return workflow.propose_inline_baseline(
        inputs,
        anchor_config=AnchorConfig(),
        span_config=SpanConfig(),
        baseline_config=BaselineConfig(),
        selection_config=SelectionConfig(accept_threshold=0.05),
        run_id="wf-precision",
        family_depth=family_depth,
    )


class TestPrecisionRules:
    """Workflow-level integration of the report §5-6 precision rules."""

    def test_existing_link_suppresses_nearby_same_target_proposal(
        self, precision_inputs: workflow.InlineInputs
    ) -> None:
        result = propose_precision(precision_inputs, family_depth=1)
        suppressed = [
            p
            for p in result.proposals
            if p.abstained and p.features.get("rejected_near_existing_same_target") == 1.0
        ]
        assert suppressed, "the repeated 'Target Note' phrase should be suppressed"
        for proposal in suppressed:
            assert proposal.source_document_id == "os/source"
            assert proposal.target_document_id == "ml/target"
            assert 0.0 <= proposal.features["existing_same_target_gap"] <= 600.0
        # The suppressed span never surfaces in the accepted list.
        for proposal in result.proposals:
            if not proposal.abstained and proposal.source_document_id == "os/source":
                assert proposal.target_document_id != "ml/target"

    def test_related_notes_link_does_not_suppress_prose_draft(
        self, precision_inputs: workflow.InlineInputs
    ) -> None:
        """Guideline duplication rule: a Related-notes entry is the duplicate,
        prose the preferred home — so a navigation-zone link must never
        suppress a nearby same-target prose proposal (the only two
        review-ACCEPTED items Rule A removed were blocked this way)."""
        result = propose_precision(precision_inputs, family_depth=1)
        from_related = [p for p in result.proposals if p.source_document_id == "os/related"]
        assert all(
            p.features.get("rejected_near_existing_same_target") != 1.0 for p in from_related
        )
        accepted = [
            p for p in from_related if not p.abstained and p.target_document_id == "ml/target"
        ]
        assert accepted, "the prose 'Target Note' mention should survive selection"

    def test_cross_family_prior_fires_for_lowercase_alias(
        self, precision_inputs: workflow.InlineInputs
    ) -> None:
        result = propose_precision(precision_inputs, family_depth=1)
        cross_family = [
            p
            for p in result.proposals
            if p.features.get("same_family") == 0.0
            and p.source_document_id == "os/other"
            and p.target_document_id == "ml/target"
        ]
        assert cross_family, "the 'shared memory' alias mention should carry same_family=0.0"

    def test_family_depth_zero_disables_the_prior(
        self, precision_inputs: workflow.InlineInputs
    ) -> None:
        result = propose_precision(precision_inputs, family_depth=0)
        assert all("same_family" not in p.features for p in result.proposals)


class TestTrainAndLearned:
    def test_heads_saved_and_loadable(self, heads_dir: Path) -> None:
        assert (heads_dir / "weights.pt").is_file()
        assert (heads_dir / "metadata.json").is_file()
        heads = TrainedHeads.load(heads_dir)
        assert heads.feature_names == workflow.INLINE_FEATURE_NAMES
        assert heads.hidden_size == 64
        assert set(heads.loss_history) == {"naturalness", "retrieval", "reranker"}

    def test_learned_propose_runs(self, heads_dir: Path, inputs: workflow.InlineInputs) -> None:
        heads = TrainedHeads.load(heads_dir)
        proposals = workflow.propose_inline_learned(
            inputs,
            heads,
            anchor_config=AnchorConfig(),
            span_config=SpanConfig(),
            selection_config=SelectionConfig(accept_threshold=TEST_THRESHOLD),
            calibration=1.5,
            run_id="wf-learned",
        )
        accepted = assert_hard_constraints(proposals, inputs)
        assert proposals.proposals, "the learned engine should draft from candidate spans"
        for proposal in accepted:
            assert proposal.calibrated_probability is not None
            assert 0.0 < proposal.calibrated_probability < 1.0
            assert proposal.model_version == heads.model_version

    def test_labeled_training_reps_use_display_text_spans(
        self,
        inputs: workflow.InlineInputs,
        audit_dir: Path,
        sample: AuditSample,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Seam pin: labeled positives are encoded over the anchor display
        text (the plain-text span shape inference scores), never over the
        whole ``[[target|anchor]]`` markup when the anchor is findable."""
        labels_path = tmp_path / "labels.jsonl"
        save_audit_labels(synthetic_labels(sample), labels_path)
        recorded: list[tuple[int, int]] = []
        original = workflow.span_representation

        def spy(states: Any, span: Any, *, hand_features: Any) -> Any:
            recorded.append((span.start, span.end))
            return original(states, span, hand_features=hand_features)

        monkeypatch.setattr(workflow, "span_representation", spy)
        workflow.train_inline_heads(
            inputs,
            labels_path,
            audit_dir / "audit-sample.json",
            train_config=TrainConfig(epochs=0),
            seed=0,
            out_dir=tmp_path / "heads",
        )
        recorded_spans = set(recorded)
        documents = {document.id: document for document in inputs.corpus.documents}
        narrowed_differs = 0
        for item in sample.items:
            assert item.source_span is not None
            narrowed = workflow._narrow_to_anchor(item, documents)
            assert narrowed.source_span is not None
            expected = (narrowed.source_span.start, narrowed.source_span.end)
            assert expected in recorded_spans, (
                f"labeled item {item.id} was not encoded over its display-text span"
            )
            if narrowed.source_span != item.source_span:
                narrowed_differs += 1
                markup = (item.source_span.start, item.source_span.end)
                assert markup not in recorded_spans, (
                    f"labeled item {item.id} was encoded over its full link markup"
                )
        assert narrowed_differs > 0, "fixture sample should contain narrowable wikilinks"

    def test_encoder_mismatch_is_rejected(
        self, heads_dir: Path, inputs: workflow.InlineInputs
    ) -> None:
        heads = TrainedHeads.load(heads_dir)
        with pytest.raises(ContractError, match="fingerprint"):
            workflow.propose_inline_learned(
                inputs,
                heads,
                anchor_config=AnchorConfig(),
                span_config=SpanConfig(),
                selection_config=SelectionConfig(),
                run_id="wf-learned",
                encoder_factory=lambda: HashingTokenEncoder(32),
            )


@pytest.fixture(scope="module")
def result(inputs: workflow.InlineInputs, audit_dir: Path, heads_dir: Path) -> dict[str, Any]:
    """One evaluate_inline_engines run shared by every assertion below."""
    heads = TrainedHeads.load(heads_dir)
    return workflow.evaluate_inline_engines(
        inputs,
        heads,
        heads_dir.parent / "labels.jsonl",
        audit_dir / "audit-sample.json",
        selection_config=SelectionConfig(accept_threshold=TEST_THRESHOLD),
        seed=0,
        sweep_thresholds=(0.1, 0.3, 0.5, 0.7),
    )


class TestEvaluateEngines:
    def test_split_section_is_coherent(self, result: dict[str, Any], sample: AuditSample) -> None:
        split = result["split"]
        assert sum(split["counts"].values()) == len(sample.items)
        assert abs(sum(split["achieved_fractions"].values()) - 1.0) < 1e-9
        assert split["group_count"] >= 1
        assert 0 <= split["test_positives"] <= split["counts"]["test"]

    def test_retrieval_metrics_align_across_engines(self, result: dict[str, Any]) -> None:
        retrieval = result["retrieval"]
        assert set(retrieval) == {"learned_retrieval", "learned_reranked", "baseline"}
        counts = {metrics["query_count"] for metrics in retrieval.values()}
        assert len(counts) == 1
        for metrics in retrieval.values():
            for key, value in metrics.items():
                if key != "query_count":
                    assert 0.0 <= value <= 1.0, f"{key}={value}"
            assert metrics["recall_at_1"] <= metrics["recall_at_10"]

    def test_naturalness_section_reports_both_classes(self, result: dict[str, Any]) -> None:
        naturalness = result["naturalness"]
        assert set(naturalness) == {
            "n_natural",
            "n_not_natural",
            "mean_natural",
            "mean_not_natural",
            "auc",
        }
        assert 0.0 <= naturalness["auc"] <= 1.0
        assert 0.0 <= naturalness["mean_natural"] <= 1.0

    def test_recovery_is_matched_budget(self, result: dict[str, Any]) -> None:
        recovery = result["recovery"]
        budgets = [row["budget"] for row in recovery["at_budget"]]
        assert budgets == sorted(budgets)
        for row in recovery["at_budget"]:
            assert 0.0 <= row["learned_fraction"] <= 1.0
            assert 0.0 <= row["baseline_fraction"] <= 1.0
            assert row["learned_recovered"] <= recovery["n_test_positives"]

    def test_corpus_section_and_sweep(self, result: dict[str, Any]) -> None:
        corpus = result["corpus"]
        assert corpus["accepted_overlap_span_target"] <= min(
            corpus["learned_accepted"], corpus["baseline_accepted"]
        )
        assert corpus["accepted_overlap_span_target"] <= corpus["accepted_overlap_source_target"]
        assert len(corpus["learned_top"]) <= 10
        for entry in corpus["learned_top"]:
            assert set(entry) == {
                "source",
                "anchor",
                "target",
                "combined",
                "naturalness",
                "target_correctness",
            }
        learned_counts = [row["learned_accepted"] for row in corpus["threshold_sweep"]]
        assert learned_counts == sorted(learned_counts, reverse=True)

    def test_result_is_json_safe(self, result: dict[str, Any]) -> None:
        json.dumps(result)

    def test_encoder_mismatch_is_rejected(
        self, inputs: workflow.InlineInputs, audit_dir: Path, heads_dir: Path
    ) -> None:
        heads = TrainedHeads.load(heads_dir)
        with pytest.raises(ContractError, match="fingerprint"):
            workflow.evaluate_inline_engines(
                inputs,
                heads,
                heads_dir.parent / "labels.jsonl",
                audit_dir / "audit-sample.json",
                encoder_factory=lambda: HashingTokenEncoder(32),
            )


class TestTokenStateCache:
    def test_training_reuses_cached_states_identically(
        self,
        inputs: workflow.InlineInputs,
        audit_dir: Path,
        sample: AuditSample,
        tmp_path: Path,
    ) -> None:
        labels_path = tmp_path / "labels.jsonl"
        save_audit_labels(synthetic_labels(sample), labels_path)
        store = ArtifactStore(tmp_path / "store")
        config = TrainConfig(epochs=0)

        def train(out: str, cache: ArtifactCache | None) -> TrainedHeads:
            return workflow.train_inline_heads(
                inputs,
                labels_path,
                audit_dir / "audit-sample.json",
                train_config=config,
                seed=0,
                out_dir=tmp_path / out,
                token_state_cache=cache,
            )

        cold = ArtifactCache(store)
        first = train("heads-cold", cold)
        assert cold.stats().misses > 0
        assert cold.stats().hits == 0

        warm = ArtifactCache(store)
        second = train("heads-warm", warm)
        assert warm.stats().hits > 0
        assert warm.stats().misses == 0

        uncached = train("heads-uncached", None)
        assert first.model_version == second.model_version == uncached.model_version


class TestReport:
    def test_report_files_parse(
        self,
        baseline_set: InlineProposalSet,
        inputs: workflow.InlineInputs,
        tmp_path: Path,
    ) -> None:
        paths = write_inline_report(baseline_set, inputs.corpus, out_dir=tmp_path)
        assert [path.name for path in paths] == [
            "inline-proposals.jsonl",
            "inline-proposals.md",
        ]
        parsed_ids = set()
        for line in paths[0].read_text(encoding="utf-8").splitlines():
            proposal = InlineProposal.from_dict(json.loads(line))
            parsed_ids.add(proposal.id)
        assert parsed_ids == {p.id for p in baseline_set.proposals}
        text = paths[1].read_text(encoding="utf-8")
        assert "# Inline link proposals" in text
        accepted = [p for p in baseline_set.proposals if not p.abstained]
        for proposal in accepted:
            assert proposal.target_document_id in text
        if any(p.abstained for p in baseline_set.proposals):
            assert "## Abstained" in text

    def test_empty_set_renders_successful_empty_result(
        self, baseline_set: InlineProposalSet, inputs: workflow.InlineInputs, tmp_path: Path
    ) -> None:
        empty = InlineProposalSet(header=baseline_set.header, proposals=())
        paths = write_inline_report(empty, inputs.corpus, out_dir=tmp_path)
        assert paths[0].read_text(encoding="utf-8") == ""
        assert "successful empty result" in paths[1].read_text(encoding="utf-8")


def review_decision(
    *,
    engine: str = "baseline",
    verdict: str = "accept",
    score: float = 0.7,
    start: int = 0,
    end: int | None = None,
    source: str = "doc-a",
    target: str = "doc-b",
    anchor_ok: bool = True,
    target_ok: bool = True,
    reason: str = "good",
) -> InlineReviewDecision:
    return InlineReviewDecision(
        engine=engine,
        source_document_id=source,
        span=Span(start=start, end=end if end is not None else start + 6),
        anchor_text="anchor",
        target_document_id=target,
        verdict=verdict,
        target_ok=target_ok,
        anchor_ok=anchor_ok,
        placement_ok=verdict == "accept",
        reason=reason,
        note="",
        combined_score=score,
    )


def synthetic_review_decisions(engine: str) -> list[InlineReviewDecision]:
    """20 score-separated decisions: accepts high, rejects low (both classes)."""
    decisions = [
        review_decision(engine=engine, verdict="accept", score=0.55 + index * 0.03, start=index)
        for index in range(12)
    ]
    decisions.extend(
        review_decision(
            engine=engine,
            verdict="reject",
            score=0.15 + index * 0.04,
            start=100 + index,
            target_ok=False,
            anchor_ok=False,
            reason="wrong_target",
        )
        for index in range(8)
    )
    return decisions


class TestLoadReviewDecisions:
    def test_round_trips_a_jsonl_file(self, tmp_path: Path) -> None:
        decisions = synthetic_review_decisions("baseline")[:3]
        path = tmp_path / "decisions.jsonl"
        path.write_text(
            "".join(json.dumps(decision.to_dict()) + "\n" for decision in decisions),
            encoding="utf-8",
        )
        assert workflow.load_review_decisions(path) == tuple(decisions)

    def test_missing_file_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(ContractError, match="cannot read review decisions"):
            workflow.load_review_decisions(tmp_path / "missing.jsonl")

    def test_malformed_line_names_the_line(self, tmp_path: Path) -> None:
        path = tmp_path / "decisions.jsonl"
        path.write_text(json.dumps(review_decision().to_dict()) + "\nnot json\n", encoding="utf-8")
        with pytest.raises(ContractError, match="line 2"):
            workflow.load_review_decisions(path)


class TestReviewCalibration:
    def test_fit_reports_temperature_and_calibration_quality(self) -> None:
        decisions = synthetic_review_decisions("baseline")
        result = workflow.fit_review_calibration(decisions, engine="baseline")
        assert set(result) == {
            "engine",
            "n",
            "positives",
            "temperature",
            "ece_before",
            "ece_after",
            "reliability",
            "conformal",
        }
        assert result["engine"] == "baseline"
        assert result["n"] == 20
        assert result["positives"] == 12
        assert TEMPERATURE_MIN <= result["temperature"] <= TEMPERATURE_MAX
        assert 0.0 <= result["ece_after"] <= result["ece_before"] <= 1.0
        assert len(result["reliability"]) == 10
        assert set(result["conformal"]) == {
            "threshold",
            "target_error",
            "n_calibration",
            "n_errors",
        }
        assert result["conformal"]["target_error"] == pytest.approx(0.2)
        assert result["conformal"]["n_calibration"] == 20
        json.dumps(result)  # the report must be JSON-safe

    def test_fit_filters_to_the_requested_engine(self) -> None:
        decisions = synthetic_review_decisions("baseline") + synthetic_review_decisions("learned")
        result = workflow.fit_review_calibration(decisions, engine="learned")
        assert result["engine"] == "learned"
        assert result["n"] == 20

    def test_unknown_engine_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="unknown engine"):
            workflow.fit_review_calibration([], engine="quantum")

    def test_no_decisions_for_engine_raises(self) -> None:
        decisions = synthetic_review_decisions("baseline")
        with pytest.raises(ContractError, match="no review decisions"):
            workflow.fit_review_calibration(decisions, engine="learned")

    def test_one_class_labels_raise(self) -> None:
        accepts_only = [
            decision
            for decision in synthetic_review_decisions("baseline")
            if decision.verdict == "accept"
        ]
        with pytest.raises(ContractError, match="one class"):
            workflow.fit_review_calibration(accepts_only, engine="baseline")

    def test_write_load_round_trip(self, tmp_path: Path) -> None:
        results = {
            engine: workflow.fit_review_calibration(
                synthetic_review_decisions(engine), engine=engine
            )
            for engine in ("baseline", "learned")
        }
        path = tmp_path / "calibration.json"
        workflow.write_review_calibration(path, results)
        loaded = workflow.load_review_calibration(path)
        assert set(loaded) == {"baseline", "learned"}
        for engine, result in results.items():
            assert loaded[engine]["temperature"] == pytest.approx(result["temperature"])
            assert loaded[engine]["n"] == result["n"]

    def test_write_rejects_unknown_engine_keys(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="unknown engine key"):
            workflow.write_review_calibration(
                tmp_path / "calibration.json", {"quantum": {"temperature": 1.0}}
            )

    def test_load_validates_shape_and_temperature(self, tmp_path: Path) -> None:
        path = tmp_path / "calibration.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(ContractError, match="must be a JSON object"):
            workflow.load_review_calibration(path)
        path.write_text(json.dumps({"quantum": {"temperature": 1.0}}), encoding="utf-8")
        with pytest.raises(ContractError, match="unknown engine"):
            workflow.load_review_calibration(path)
        path.write_text(json.dumps({"baseline": {"temperature": -2.0}}), encoding="utf-8")
        with pytest.raises(ContractError, match="finite positive 'temperature'"):
            workflow.load_review_calibration(path)
        with pytest.raises(ContractError, match="cannot read"):
            workflow.load_review_calibration(tmp_path / "missing.json")


class TestTemperatureApplication:
    """One shared temperature-application point across both engines."""

    def test_baseline_temperature_populates_calibrated_probability(
        self, inputs: workflow.InlineInputs, baseline_set: InlineProposalSet
    ) -> None:
        calibrated = workflow.propose_inline_baseline(
            inputs,
            anchor_config=AnchorConfig(),
            span_config=SpanConfig(),
            baseline_config=BaselineConfig(),
            selection_config=BASELINE_SELECTION,
            run_id="wf-baseline",
            temperature=1.0,
        )
        assert calibrated.proposals
        for proposal in calibrated.proposals:
            assert proposal.calibrated_probability is not None
            # T=1.0 is the identity through the logit round trip.
            assert proposal.calibrated_probability == pytest.approx(
                proposal.combined_score, abs=1e-9
            )
        # Without a temperature the baseline stays uncalibrated (the
        # pre-existing behavior, pinned by baseline_set).
        assert all(p.calibrated_probability is None for p in baseline_set.proposals)

    def test_learned_temperature_and_calibration_are_the_same_knob(
        self, heads_dir: Path, inputs: workflow.InlineInputs
    ) -> None:
        heads = TrainedHeads.load(heads_dir)

        def propose(
            *, calibration: float | None = None, temperature: float | None = None
        ) -> InlineProposalSet:
            return workflow.propose_inline_learned(
                inputs,
                heads,
                anchor_config=AnchorConfig(),
                span_config=SpanConfig(),
                selection_config=SelectionConfig(accept_threshold=TEST_THRESHOLD),
                calibration=calibration,
                temperature=temperature,
                run_id="wf-learned",
            )

        via_calibration = propose(calibration=1.5)
        via_temperature = propose(temperature=1.5)
        assert [p.id for p in via_calibration.proposals] == [
            p.id for p in via_temperature.proposals
        ]
        assert [p.calibrated_probability for p in via_calibration.proposals] == [
            p.calibrated_probability for p in via_temperature.proposals
        ]
        assert any(p.calibrated_probability is not None for p in via_temperature.proposals)

    def test_passing_both_knobs_is_rejected(
        self, heads_dir: Path, inputs: workflow.InlineInputs
    ) -> None:
        heads = TrainedHeads.load(heads_dir)
        with pytest.raises(ConfigError, match="not both"):
            workflow.propose_inline_learned(
                inputs,
                heads,
                anchor_config=AnchorConfig(),
                span_config=SpanConfig(),
                selection_config=SelectionConfig(),
                calibration=1.5,
                temperature=1.5,
                run_id="wf-learned",
            )


class TestTrainWithReviews:
    def test_review_spans_are_encoded_without_narrowing(
        self,
        inputs: workflow.InlineInputs,
        audit_dir: Path,
        sample: AuditSample,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Seam pin: review spans reach the encoder verbatim (they are
        plain-text anchor spans already), and broken_span decisions are
        never encoded."""
        labels_path = tmp_path / "labels.jsonl"
        save_audit_labels(synthetic_labels(sample), labels_path)
        documents = sorted(
            (d for d in inputs.corpus.documents if len(d.content) > 60), key=lambda d: d.id
        )
        source, target = documents[0], documents[1]
        kept = review_decision(
            engine="learned", source=source.id, target=target.id, start=5, end=17
        )
        broken = review_decision(
            engine="learned",
            source=source.id,
            target=target.id,
            start=25,
            end=37,
            verdict="reject",
            target_ok=False,
            anchor_ok=False,
            reason="broken_span",
        )
        recorded: list[tuple[int, int]] = []
        original = span_representation

        def spy(states: Any, span: Any, *, hand_features: Any) -> Any:
            recorded.append((span.start, span.end))
            return original(states, span, hand_features=hand_features)

        monkeypatch.setattr(workflow, "span_representation", spy)
        workflow.train_inline_heads(
            inputs,
            labels_path,
            audit_dir / "audit-sample.json",
            train_config=TrainConfig(epochs=0),
            seed=0,
            out_dir=tmp_path / "heads",
            reviews=[kept, broken],
        )
        assert (5, 17) in recorded
        assert (25, 37) not in recorded

    def test_review_rep_key_matches_the_trainer_contract(
        self, inputs: workflow.InlineInputs
    ) -> None:
        decision = review_decision()
        assert review_span_key(decision).startswith("review:")


def make_benchmark_case(
    case_id: str,
    kind: BenchmarkKind,
    *,
    source: str,
    anchor: str,
    target: str | None = None,
    expected: bool = True,
) -> BenchmarkCase:
    return BenchmarkCase(
        id=case_id,
        kind=kind,
        source_document_id=source,
        span=None,
        anchor_text=anchor,
        target_document_id=target,
        expected=expected,
    )


@pytest.fixture(scope="module")
def benchmark() -> Benchmark:
    """Two locatable fixture-corpus cases plus one over a missing document."""
    return Benchmark(
        header=make_header(),
        cases=(
            make_benchmark_case(
                "bm-natural",
                BenchmarkKind.NATURAL_SPAN,
                source="systems/dynamo",
                anchor="consistency",
            ),
            make_benchmark_case(
                "bm-no-link",
                BenchmarkKind.NO_LINK,
                source="systems/dynamo",
                anchor="availability",
            ),
            make_benchmark_case(
                "bm-ghost",
                BenchmarkKind.NO_LINK,
                source="ghost/missing",
                anchor="anything",
            ),
        ),
    )


class TestBenchmarkEngine:
    def test_baseline_engine_scores_locatable_cases(
        self, inputs: workflow.InlineInputs, benchmark: Benchmark
    ) -> None:
        result = workflow.benchmark_engine(
            inputs, benchmark, engine="baseline", selection_config=BASELINE_SELECTION
        )
        assert set(result) == {"outcomes", "scores"}
        assert set(result["outcomes"]) == {"bm-natural", "bm-no-link"}
        scores = result["scores"]
        expected_slices = {kind.value for kind in BenchmarkKind} | {"overall", "hard_case"}
        assert set(scores) == expected_slices
        assert scores["overall"]["evaluated"] == 2.0
        assert scores["overall"]["unevaluated"] == 1.0
        json.dumps(result)

    def test_learned_engine_runs_end_to_end(
        self, inputs: workflow.InlineInputs, heads_dir: Path, benchmark: Benchmark
    ) -> None:
        heads = TrainedHeads.load(heads_dir)
        result = workflow.benchmark_engine(
            inputs,
            benchmark,
            engine="learned",
            heads=heads,
            selection_config=SelectionConfig(accept_threshold=TEST_THRESHOLD),
            temperature=1.5,
        )
        assert set(result["outcomes"]) == {"bm-natural", "bm-no-link"}
        assert result["scores"]["overall"]["evaluated"] == 2.0

    def test_unknown_engine_raises(
        self, inputs: workflow.InlineInputs, benchmark: Benchmark
    ) -> None:
        with pytest.raises(ConfigError, match="unknown engine"):
            workflow.benchmark_engine(inputs, benchmark, engine="quantum")

    def test_learned_without_heads_raises(
        self, inputs: workflow.InlineInputs, benchmark: Benchmark
    ) -> None:
        with pytest.raises(ConfigError, match="heads are required"):
            workflow.benchmark_engine(inputs, benchmark, engine="learned")
