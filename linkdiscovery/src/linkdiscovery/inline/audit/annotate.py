"""Terminal annotation tool for the data audit (stdlib only).

Implements the "annotation tool" deliverable of SPEC-INLINE-LINKING §4 and
§11 phase 1: an interactive session over an :class:`AuditSample` that
records one :class:`AuditLabel` per item per annotator. Labels persist as a
JSONL file (one label object per line) rewritten atomically after every
answer, so an interrupted session never corrupts or loses accepted labels.

``input_fn`` and ``output_fn`` are injectable so sessions are unit-testable
without a TTY; the defaults are the builtins.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from linkdiscovery.contracts.base import utc_now_iso
from linkdiscovery.errors import ContractError
from linkdiscovery.fingerprint import canonical_json
from linkdiscovery.inline.audit.tiers import derive_tier
from linkdiscovery.inline.records import AuditItem, AuditLabel, AuditSample, Tier
from linkdiscovery.report._io import atomic_write_text

__all__ = ["load_audit_labels", "run_annotation_session", "save_audit_labels"]

_QUIT = "q"
_SKIP = "s"
_TIER_CHOICES = frozenset({"a", "b", "c", "d"})


def load_audit_labels(path: Path) -> tuple[AuditLabel, ...]:
    """Load labels from a JSONL file; a missing file is an empty label set.

    Each non-blank line must be one JSON-encoded :class:`AuditLabel` object.
    A malformed line raises :class:`~linkdiscovery.errors.ContractError`
    naming the file and line number, so a corrupted labels file fails loudly
    instead of silently dropping judgments.
    """
    if not path.exists():
        return ()
    labels: list[AuditLabel] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{path}: line {line_number} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ContractError(
                f"{path}: line {line_number} must be a JSON object, got {type(data).__name__}"
            )
        labels.append(AuditLabel.from_dict(data))
    return tuple(labels)


def save_audit_labels(labels: Sequence[AuditLabel], path: Path) -> None:
    """Write labels as JSONL via one atomic replace of the whole file.

    Uses :func:`~linkdiscovery.report._io.atomic_write_text`, so a crash
    mid-write leaves the previous file intact rather than a truncated one.
    Lines are canonical JSON for byte-stable output.
    """
    text = "".join(canonical_json(label.to_dict()) + "\n" for label in labels)
    atomic_write_text(path, text)


@dataclass(frozen=True, slots=True)
class _Answers:
    """The judgments collected for one item before the label is built."""

    target_correct: bool
    anchor_natural: bool
    placement_valid: bool
    tier: Tier
    note: str


def _ask(prompt: str, input_fn: Callable[[str], str]) -> str:
    """Read one trimmed, lowercased answer; end-of-input means quit."""
    try:
        return input_fn(prompt).strip().lower()
    except EOFError:
        return _QUIT


def _ask_bool(prompt: str, input_fn: Callable[[str], str], output_fn: Callable[[str], None]) -> str:
    """Prompt until the answer is y, n, s (skip item), or q (save and quit)."""
    while True:
        answer = _ask(f"{prompt} [y/n/s/q] ", input_fn)
        if answer in {"y", "n", _SKIP, _QUIT}:
            return answer
        output_fn("please answer y, n, s (skip item), or q (save and quit)")


def _ask_tier(
    item: AuditItem,
    answers: dict[str, bool],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> Tier | str:
    """Prompt for a tier; ``auto`` (or empty) derives it from the judgments."""
    derived = derive_tier(
        answers["target_correct"],
        answers["anchor_natural"],
        answers["placement_valid"],
        item.region_kind,
    )
    while True:
        answer = _ask(f"tier [a/b/c/d/auto={derived.value}] ", input_fn)
        if answer in {"", "auto"}:
            return derived
        if answer in _TIER_CHOICES:
            return Tier(answer)
        if answer in {_SKIP, _QUIT}:
            return answer
        output_fn("please answer a, b, c, d, auto (derive from judgments), s, or q")


def _show_item(
    item: AuditItem,
    position: int,
    total: int,
    output_fn: Callable[[str], None],
) -> None:
    """Print everything an annotator needs to judge one sampled link."""
    output_fn("")
    output_fn(f"--- item {position}/{total} [{item.id}] ---")
    output_fn(f"source:  {item.source_document_id}")
    output_fn(f"target:  {item.target_document_id}")
    output_fn(f"anchor:  {item.anchor_text!r} ({item.anchor_word_count} word(s))")
    output_fn(f"region:  {item.region_kind.value}  topic: {item.topic_family}")
    output_fn(f"context: {item.context}")


def _collect_answers(
    item: AuditItem,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> _Answers | str:
    """Run the prompts for one item; returns answers, or ``"s"``/``"q"``."""
    booleans: dict[str, bool] = {}
    prompts = (
        ("target_correct", "target correct?"),
        ("anchor_natural", "anchor natural?"),
        ("placement_valid", "placement valid?"),
    )
    for field_name, prompt in prompts:
        answer = _ask_bool(prompt, input_fn, output_fn)
        if answer in {_SKIP, _QUIT}:
            return answer
        booleans[field_name] = answer == "y"
    tier = _ask_tier(item, booleans, input_fn, output_fn)
    if not isinstance(tier, Tier):
        return tier
    try:
        note = input_fn("note (optional) ").strip()
    except EOFError:
        note = ""
    return _Answers(
        target_correct=booleans["target_correct"],
        anchor_natural=booleans["anchor_natural"],
        placement_valid=booleans["placement_valid"],
        tier=tier,
        note=note,
    )


def run_annotation_session(
    sample: AuditSample,
    *,
    annotator: str,
    labels_path: Path,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Annotate the sample's unlabeled items interactively; returns labels added.

    Existing labels at ``labels_path`` are loaded first (a missing file is
    fine) and items this annotator already labeled are skipped, so sessions
    resume where they left off. For each remaining item the tool shows the
    document IDs, anchor, region kind, and context window, then asks for
    target correctness, anchor naturalness, placement validity, a tier
    (``auto`` derives it via
    :func:`~linkdiscovery.inline.audit.tiers.derive_tier`), and an optional
    note. ``s`` skips the current item; ``q`` (or end of input) saves and
    quits. Every accepted label triggers an atomic rewrite of the whole
    JSONL file, so a crash never corrupts previously saved labels.
    """
    labels = list(load_audit_labels(labels_path))
    done = {label.item_id for label in labels if label.annotator == annotator}
    pending = [item for item in sample.items if item.id not in done]
    output_fn(f"annotator {annotator!r}: {len(pending)} of {len(sample.items)} item(s) pending")
    labeled = 0
    for position, item in enumerate(pending, start=1):
        _show_item(item, position, len(pending), output_fn)
        answers = _collect_answers(item, input_fn, output_fn)
        if isinstance(answers, str):
            if answers == _QUIT:
                break
            continue
        labels.append(
            AuditLabel(
                item_id=item.id,
                annotator=annotator,
                target_correct=answers.target_correct,
                anchor_natural=answers.anchor_natural,
                placement_valid=answers.placement_valid,
                tier=answers.tier,
                note=answers.note,
                labeled_at=utc_now_iso(),
            )
        )
        save_audit_labels(labels, labels_path)
        labeled += 1
    output_fn(f"labeled {labeled} item(s) this session; labels saved to {labels_path}")
    return labeled
