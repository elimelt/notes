"""Review artifacts for inline-link proposals: JSONL and Markdown.

Mirrors the style of :mod:`linkdiscovery.report.reporters` for the inline
subsystem's :class:`~linkdiscovery.inline.records.InlineProposalSet`:

- ``inline-proposals.jsonl`` — the machine artifact: one canonical-JSON
  proposal dict per line, accepted **and** abstained, so the rejection
  decisions stay auditable.
- ``inline-proposals.md`` — the human review document: accepted proposals
  grouped by source note, each showing the anchor in its surrounding corpus
  context, the target title, the three head scores plus the combined score,
  with ``suggest_better_anchor`` drafts flagged distinctly; abstained
  proposals are summarized (by rejection reason) at the bottom.

All writes are atomic via :func:`linkdiscovery.report._io.atomic_write_text`;
this module never mutates source documents.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from linkdiscovery.fingerprint import canonical_json
from linkdiscovery.report._io import atomic_write_text

if TYPE_CHECKING:
    from linkdiscovery.contracts.documents import Corpus
    from linkdiscovery.inline.records import InlineProposal, InlineProposalSet

__all__ = ["write_inline_report"]

_JSONL_NAME = "inline-proposals.jsonl"
_MARKDOWN_NAME = "inline-proposals.md"
_CONTEXT_RADIUS = 80
"""Characters of raw source content shown on each side of the anchor."""

_MD_SIGNIFICANT = re.compile(r"([\\`*_\[\]#|<>{}])")


def _escape_md(text: str) -> str:
    """Escape markdown-significant characters in corpus-derived text.

    Covers emphasis, code spans, links, headings, table pipes, raw HTML, and
    templating braces so anchors and excerpts cannot break the document
    structure (same coverage as the v1 reporter).
    """
    return _MD_SIGNIFICANT.sub(r"\\\1", text)


def _anchor_in_context(content: str, proposal: InlineProposal) -> str:
    """The anchor bolded inside a whitespace-collapsed window of source text."""
    span = proposal.span
    start = max(0, span.start - _CONTEXT_RADIUS)
    end = min(len(content), span.end + _CONTEXT_RADIUS)
    before = " ".join(content[start : span.start].split())
    anchor = " ".join(content[span.start : span.end].split())
    after = " ".join(content[span.end : end].split())
    if start > 0:
        before = f"...{before}"
    if end < len(content):
        after = f"{after}..."
    left = f"{_escape_md(before)} " if before else ""
    right = f" {_escape_md(after)}" if after else ""
    return f"{left}**{_escape_md(anchor)}**{right}"


def _rejection_reason(proposal: InlineProposal) -> str:
    """The ``rejected_<reason>`` feature flag, or a generic label."""
    for name, value in sorted(proposal.features.items()):
        if name.startswith("rejected_") and value:
            return name.removeprefix("rejected_")
    return "abstained"


def _proposal_lines(proposal: InlineProposal, content: str, titles: dict[str, str]) -> list[str]:
    """Render one accepted proposal as a markdown block."""
    target_title = titles.get(proposal.target_document_id, "")
    target = (
        f"{_escape_md(target_title)} (`{proposal.target_document_id}`)"
        if target_title
        else f"`{proposal.target_document_id}`"
    )
    lines = [f"- **{_escape_md(proposal.anchor_text)}** -> {target}"]
    if proposal.features.get("suggest_better_anchor", 0.0):
        lines.append(
            "  - FLAG: suggest a better anchor — the target looks correct but the "
            "anchor scored below the naturalness floor (spec §6 Q25); review the "
            "wording rather than auto-linking."
        )
    scores = (
        f"naturalness {proposal.naturalness:.3f} · "
        f"target {proposal.target_correctness:.3f} · "
        f"placement {proposal.placement_validity:.3f} · "
        f"combined {proposal.combined_score:.3f}"
    )
    if proposal.calibrated_probability is not None:
        scores += f" · calibrated {proposal.calibrated_probability:.3f}"
    lines.append(f"  - scores: {scores}")
    lines.append(f"  - span: [{proposal.span.start}, {proposal.span.end})")
    if content:
        lines.append(f"  - context: {_anchor_in_context(content, proposal)}")
    lines.append("")
    return lines


def _render_markdown(proposals: InlineProposalSet, corpus: Corpus) -> str:
    """The human review document, grouped by source note."""
    contents = {document.id: document.content for document in corpus.documents}
    titles = {document.id: document.title for document in corpus.documents if document.title}
    accepted = [proposal for proposal in proposals.proposals if not proposal.abstained]
    abstained = [proposal for proposal in proposals.proposals if proposal.abstained]

    groups: dict[str, list[InlineProposal]] = {}
    for proposal in accepted:
        groups.setdefault(proposal.source_document_id, []).append(proposal)

    header = proposals.header
    lines = [
        "# Inline link proposals",
        "",
        f"- Run: `{header.run_id}`",
        f"- Corpus: `{header.corpus_id}`",
        f"- Generated: {header.created_at}",
        f"- Accepted: {len(accepted)} across {len(groups)} source note(s)",
        f"- Abstained: {len(abstained)}",
        "",
    ]
    if not accepted:
        lines.append(
            "No proposals were accepted. This is a successful empty result, not a failed run."
        )
        lines.append("")
    for document_id in sorted(groups):
        source_title = titles.get(document_id, "")
        label = (
            f"{_escape_md(source_title)} (`{document_id}`)" if source_title else f"`{document_id}`"
        )
        lines.append(f"## {label}")
        lines.append("")
        ordered = sorted(groups[document_id], key=lambda p: (p.span.start, p.id))
        for proposal in ordered:
            lines.extend(_proposal_lines(proposal, contents.get(document_id, ""), titles))
    if abstained:
        reasons: dict[str, int] = {}
        for proposal in abstained:
            reason = _rejection_reason(proposal)
            reasons[reason] = reasons.get(reason, 0) + 1
        lines.append("## Abstained")
        lines.append("")
        lines.append(
            f"{len(abstained)} draft(s) were rejected at selection and kept for audit "
            "(full records in `inline-proposals.jsonl`):"
        )
        lines.append("")
        lines.extend(f"- {reason}: {count}" for reason, count in sorted(reasons.items()))
        lines.append("")
    return "\n".join(lines)


def write_inline_report(
    proposals: InlineProposalSet, corpus: Corpus, *, out_dir: Path
) -> list[Path]:
    """Write ``inline-proposals.jsonl`` and ``inline-proposals.md`` into ``out_dir``.

    The JSONL artifact carries every proposal (accepted and abstained) as one
    full contract dict per line; the markdown document groups accepted
    proposals by source note with anchor-in-context excerpts, target titles,
    and the three head scores, flags ``suggest_better_anchor`` drafts, and
    summarizes abstentions by rejection reason. Both writes are atomic.
    Returns the written paths, JSONL first.
    """
    out = Path(out_dir)
    jsonl_path = out / _JSONL_NAME
    markdown_path = out / _MARKDOWN_NAME
    jsonl = "".join(canonical_json(proposal.to_dict()) + "\n" for proposal in proposals.proposals)
    atomic_write_text(jsonl_path, jsonl)
    atomic_write_text(markdown_path, _render_markdown(proposals, corpus) + "\n")
    return [jsonl_path, markdown_path]
