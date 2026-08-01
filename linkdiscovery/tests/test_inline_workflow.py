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
from linkdiscovery.contracts import SourceDocument, Span
from linkdiscovery.errors import ContractError
from linkdiscovery.inline import workflow
from linkdiscovery.inline.anchors import AnchorConfig, AnchorDictionary
from linkdiscovery.inline.audit.annotate import save_audit_labels
from linkdiscovery.inline.audit.tiers import derive_tier
from linkdiscovery.inline.baseline import BaselineConfig
from linkdiscovery.inline.encode import HashingTokenEncoder
from linkdiscovery.inline.heads import TrainedHeads
from linkdiscovery.inline.records import (
    AuditItem,
    AuditLabel,
    AuditSample,
    InlineProposal,
    InlineProposalSet,
    LinkRegionKind,
)
from linkdiscovery.inline.report import write_inline_report
from linkdiscovery.inline.select import SelectionConfig
from linkdiscovery.inline.spans import SpanConfig
from linkdiscovery.inline.train import TrainConfig

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "markdown_corpus"

RECALL_GATE = 0.85
"""The §12 candidate-generation ceiling the fixture corpus must clear."""

TEST_THRESHOLD = 0.2
"""A low accept threshold so the tiny fixture corpus yields accepted proposals."""


def make_config() -> PipelineConfig:
    """The hashing-provider configuration over the fixture corpus."""
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
    return config_from_dict(data)


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


@pytest.fixture(scope="module")
def baseline_set(inputs: workflow.InlineInputs) -> InlineProposalSet:
    return workflow.propose_inline_baseline(
        inputs,
        anchor_config=AnchorConfig(),
        span_config=SpanConfig(),
        baseline_config=BaselineConfig(),
        selection_config=SelectionConfig(accept_threshold=TEST_THRESHOLD),
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
            selection_config=SelectionConfig(accept_threshold=TEST_THRESHOLD),
            run_id="wf-baseline",
        )
        assert [p.id for p in again.proposals] == [p.id for p in baseline_set.proposals]
        assert [p.combined_score for p in again.proposals] == [
            p.combined_score for p in baseline_set.proposals
        ]


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
