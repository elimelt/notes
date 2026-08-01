"""Terminal annotation sessions driven by scripted input functions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from linkdiscovery.errors import ContractError
from linkdiscovery.inline import (
    AuditItem,
    AuditLabel,
    AuditSample,
    LinkRegionKind,
    Tier,
    load_audit_labels,
    run_annotation_session,
    save_audit_labels,
)
from tests.conftest import make_header


def make_item(item_id: str, region_kind: LinkRegionKind = LinkRegionKind.PROSE) -> AuditItem:
    """A minimal audit item to annotate."""
    return AuditItem(
        id=item_id,
        source_document_id="systems/a",
        target_document_id="systems/b",
        anchor_text="fair queueing",
        source_span=None,
        region_kind=region_kind,
        context="...rely on fair queueing to bound latency...",
        anchor_word_count=2,
        topic_family="systems",
        strata_key=f"{region_kind.value}|2-3|systems|note",
    )


def make_sample(*items: AuditItem) -> AuditSample:
    """An audit sample over the given items."""
    return AuditSample(header=make_header(), items=items)


def scripted(*answers: str) -> Callable[[str], str]:
    """An input function yielding canned answers, then raising EOFError."""
    iterator: Iterator[str] = iter(answers)

    def input_fn(_prompt: str) -> str:
        try:
            return next(iterator)
        except StopIteration:
            raise EOFError from None

    return input_fn


class TestLabelPersistence:
    def test_missing_file_loads_as_empty(self, tmp_path: Path) -> None:
        assert load_audit_labels(tmp_path / "absent.jsonl") == ()

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        labels = (
            AuditLabel(
                item_id="i1",
                annotator="alice",
                target_correct=True,
                anchor_natural=False,
                placement_valid=True,
                tier=Tier.B,
                note="anchor too generic",
                labeled_at="2026-07-31T12:00:00+00:00",
            ),
        )
        path = tmp_path / "labels.jsonl"
        save_audit_labels(labels, path)
        assert load_audit_labels(path) == labels
        assert len(path.read_text(encoding="utf-8").splitlines()) == 1

    def test_blank_lines_are_tolerated(self, tmp_path: Path) -> None:
        path = tmp_path / "labels.jsonl"
        save_audit_labels(
            (
                AuditLabel(
                    item_id="i1",
                    annotator="alice",
                    target_correct=True,
                    anchor_natural=True,
                    placement_valid=True,
                    tier=Tier.A,
                ),
            ),
            path,
        )
        path.write_text(path.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
        assert len(load_audit_labels(path)) == 1

    def test_malformed_line_raises_with_location(self, tmp_path: Path) -> None:
        path = tmp_path / "labels.jsonl"
        path.write_text('{"item_id": "i1"\n', encoding="utf-8")
        with pytest.raises(ContractError, match="line 1 is not valid JSON"):
            load_audit_labels(path)

    def test_non_object_line_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "labels.jsonl"
        path.write_text("[1, 2]\n", encoding="utf-8")
        with pytest.raises(ContractError, match="line 1 must be a JSON object"):
            load_audit_labels(path)


class TestAnnotationSession:
    def test_full_session_labels_all_items(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"), make_item("i2"))
        path = tmp_path / "labels.jsonl"
        outputs: list[str] = []
        count = run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted(
                "y",
                "y",
                "y",
                "auto",
                "clean",  # i1 -> derived Tier A
                "y",
                "n",
                "y",
                "auto",
                "",  # i2 -> derived Tier B
            ),
            output_fn=outputs.append,
        )
        assert count == 2
        labels = load_audit_labels(path)
        assert [label.item_id for label in labels] == ["i1", "i2"]
        assert labels[0].tier == Tier.A
        assert labels[0].note == "clean"
        assert labels[0].labeled_at != ""
        assert labels[1].tier == Tier.B
        assert labels[1].anchor_natural is False
        assert any("2 of 2 item(s) pending" in line for line in outputs)

    def test_auto_tier_respects_region_kind(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1", LinkRegionKind.RELATED_NOTES))
        path = tmp_path / "labels.jsonl"
        run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("y", "y", "y", "", ""),  # empty tier answer means auto
            output_fn=lambda _line: None,
        )
        assert load_audit_labels(path)[0].tier == Tier.C

    def test_explicit_tier_overrides_auto(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"))
        path = tmp_path / "labels.jsonl"
        run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("y", "y", "y", "d", "manual override"),
            output_fn=lambda _line: None,
        )
        assert load_audit_labels(path)[0].tier == Tier.D

    def test_session_resumes_skipping_already_labeled_items(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"), make_item("i2"))
        path = tmp_path / "labels.jsonl"
        run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("y", "y", "y", "auto", "", "q"),
            output_fn=lambda _line: None,
        )
        assert [label.item_id for label in load_audit_labels(path)] == ["i1"]
        count = run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("y", "y", "y", "auto", ""),
            output_fn=lambda _line: None,
        )
        assert count == 1
        assert [label.item_id for label in load_audit_labels(path)] == ["i1", "i2"]

    def test_other_annotators_labels_do_not_block_items(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"))
        path = tmp_path / "labels.jsonl"
        run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("y", "y", "y", "auto", ""),
            output_fn=lambda _line: None,
        )
        count = run_annotation_session(
            sample,
            annotator="bob",
            labels_path=path,
            input_fn=scripted("y", "n", "y", "auto", ""),
            output_fn=lambda _line: None,
        )
        assert count == 1
        annotators = [label.annotator for label in load_audit_labels(path)]
        assert annotators == ["alice", "bob"]

    def test_quit_saves_progress_and_stops(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"), make_item("i2"), make_item("i3"))
        path = tmp_path / "labels.jsonl"
        count = run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("y", "y", "y", "auto", "", "q"),
            output_fn=lambda _line: None,
        )
        assert count == 1
        assert [label.item_id for label in load_audit_labels(path)] == ["i1"]

    def test_skip_moves_to_next_item_without_labeling(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"), make_item("i2"))
        path = tmp_path / "labels.jsonl"
        count = run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("s", "y", "y", "y", "auto", ""),
            output_fn=lambda _line: None,
        )
        assert count == 1
        assert [label.item_id for label in load_audit_labels(path)] == ["i2"]

    def test_end_of_input_quits_gracefully(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"))
        count = run_annotation_session(
            sample,
            annotator="alice",
            labels_path=tmp_path / "labels.jsonl",
            input_fn=scripted(),  # raises EOFError immediately
            output_fn=lambda _line: None,
        )
        assert count == 0
        assert not (tmp_path / "labels.jsonl").exists()

    def test_invalid_answers_reprompt(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"))
        path = tmp_path / "labels.jsonl"
        outputs: list[str] = []
        count = run_annotation_session(
            sample,
            annotator="alice",
            labels_path=path,
            input_fn=scripted("maybe", "y", "y", "y", "x", "auto", "done"),
            output_fn=outputs.append,
        )
        assert count == 1
        assert any("please answer y, n, s" in line for line in outputs)
        assert any("please answer a, b, c, d, auto" in line for line in outputs)

    def test_item_details_are_shown(self, tmp_path: Path) -> None:
        sample = make_sample(make_item("i1"))
        outputs: list[str] = []
        run_annotation_session(
            sample,
            annotator="alice",
            labels_path=tmp_path / "labels.jsonl",
            input_fn=scripted("q"),
            output_fn=outputs.append,
        )
        text = "\n".join(outputs)
        assert "systems/a" in text
        assert "systems/b" in text
        assert "fair queueing" in text
        assert "prose" in text
        assert "bound latency" in text
