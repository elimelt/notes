"""Default reporter: JSONL, JSON, and Markdown review artifacts.

:class:`DefaultReporter` implements the :class:`~linkdiscovery.interfaces.
Reporter` Protocol. It renders one file per configured format into
``ReportConfig.output_dir``:

- ``proposals.jsonl`` — the machine artifact: one canonical-JSON proposal
  dict per line, carrying the complete feature set and evidence. When
  evidence text is enabled and a processed corpus is available, each
  evidence entry gains ``source_excerpt``/``target_excerpt`` keys; contract
  deserialization ignores unknown keys, so every line round-trips through
  :meth:`~linkdiscovery.contracts.proposals.LinkProposal.from_dict`.
- ``proposals.json`` — the full ``ProposalSet.to_dict()`` artifact.
- ``proposals.md`` — the human review document, grouped by source document.

All writes are atomic (see :mod:`linkdiscovery.report._io`); reporters never
mutate source documents. Setting ``include_evidence_text`` to ``False`` omits
evidence text while retaining unit ids, spans, and similarities, per the SPEC
privacy section.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.manifests import SCHEMA_VERSION, ArtifactRef, ReportManifest
from linkdiscovery.errors import ReportError
from linkdiscovery.fingerprint import canonical_json, fingerprint_bytes
from linkdiscovery.report._io import atomic_write_text

if TYPE_CHECKING:
    from linkdiscovery.config import ReportConfig
    from linkdiscovery.contracts.documents import Corpus
    from linkdiscovery.contracts.proposals import Evidence, LinkProposal, ProposalSet
    from linkdiscovery.contracts.units import ProcessedCorpus, SemanticUnit, Span

__all__ = ["KNOWN_FORMATS", "DefaultReporter"]

KNOWN_FORMATS = ("jsonl", "json", "markdown")
"""Formats :class:`DefaultReporter` can render, in canonical order."""

_FILE_NAMES = {"jsonl": "proposals.jsonl", "json": "proposals.json", "markdown": "proposals.md"}
_ARROWS = {"source-to-target": "→", "target-to-source": "←", "undirected": "↔"}
_EXCERPT_CHARS = 240
_MD_SIGNIFICANT = re.compile(r"([\\`*_\[\]#|<>{}])")


def _escape_md(text: str) -> str:
    """Escape markdown-significant characters in reviewer-facing text.

    Covers emphasis, code spans, links, headings, table pipes, raw HTML, and
    templating braces so adapter-supplied titles and corpus excerpts cannot
    break the review document's structure.
    """
    return _MD_SIGNIFICANT.sub(r"\\\1", text)


def _format_spans(spans: tuple[Span, ...]) -> str:
    """Render spans as compact half-open ranges, e.g. ``[420, 1080)``."""
    return ", ".join(f"[{span.start}, {span.end})" for span in spans)


class DefaultReporter:
    """Renders a :class:`~linkdiscovery.contracts.proposals.ProposalSet` for review.

    ``corpus`` (optional) supplies document titles and source references for
    the markdown report; ``processed`` (optional) supplies semantic-unit
    texts for evidence excerpts. Both degrade gracefully: without them the
    report falls back to bare ids and omits excerpts. ``run_id`` is only a
    fallback identity for ad-hoc proposal sets whose header carries an empty
    ``run_id``; ``producer_version`` is recorded in the report manifest.
    """

    def __init__(
        self,
        corpus: Corpus | None = None,
        processed: ProcessedCorpus | None = None,
        *,
        run_id: str = "adhoc",
        producer_version: str = "linkdiscovery/0.1.0",
    ) -> None:
        self._run_id = run_id
        self._producer_version = producer_version
        self._titles: dict[str, str] = {}
        self._source_refs: dict[str, str] = {}
        if corpus is not None:
            for document in corpus.documents:
                if document.title:
                    self._titles[document.id] = document.title
                if document.source_ref:
                    self._source_refs[document.id] = document.source_ref
        self._units: dict[str, SemanticUnit] = {}
        if processed is not None:
            for processed_document in processed.documents:
                for unit in processed_document.units:
                    self._units[unit.id] = unit
        self._has_unit_text = processed is not None

    def write(self, proposals: ProposalSet, config: ReportConfig) -> ReportManifest:
        """Write one file per configured format and return the report manifest.

        Unknown formats raise :class:`~linkdiscovery.errors.ReportError`
        naming the known ones; duplicate formats are rendered once. An empty
        proposal set produces valid outputs stating zero proposals — a
        successful empty result is distinguishable from a failed run. The
        manifest header takes ``run_id``/``corpus_id`` from
        ``proposals.header``, the fingerprint of ``config``, and the current
        UTC time; ``outputs`` reference each written file by its path
        relative to ``config.output_dir``.
        """
        unknown = sorted({name for name in config.formats if name not in KNOWN_FORMATS})
        if unknown:
            names = ", ".join(repr(name) for name in unknown)
            known = ", ".join(repr(name) for name in KNOWN_FORMATS)
            raise ReportError(f"unknown report format(s) {names}; known formats: {known}")

        output_dir = Path(config.output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ReportError(f"cannot create report output directory {output_dir}: {exc}") from exc

        include_text = config.include_evidence_text and self._has_unit_text
        renderers = {
            "jsonl": lambda: self._render_jsonl(proposals, include_text),
            "json": lambda: self._render_json(proposals),
            "markdown": lambda: self._render_markdown(proposals, include_text),
        }
        formats = tuple(dict.fromkeys(config.formats))
        outputs: list[ArtifactRef] = []
        for name in formats:
            content = renderers[name]()
            file_name = _FILE_NAMES[name]
            atomic_write_text(output_dir / file_name, content)
            payload = content.encode("utf-8")
            outputs.append(
                ArtifactRef(
                    group="reports",
                    key=file_name,
                    path=file_name,
                    fingerprint=fingerprint_bytes(payload),
                    size=len(payload),
                )
            )
        header = ArtifactHeader(
            schema_version=SCHEMA_VERSION,
            run_id=proposals.header.run_id or self._run_id,
            corpus_id=proposals.header.corpus_id,
            created_at=utc_now_iso(),
            config_fingerprint=config.fingerprint(),
            producer_version=self._producer_version,
        )
        return ReportManifest(header=header, formats=formats, outputs=tuple(outputs))

    # ------------------------------------------------------------------ text

    def _excerpt(self, unit_id: str) -> str | None:
        """First 240 characters of the unit's whitespace-collapsed text.

        Returns ``None`` when the unit is unknown (evidence unit ids are
        opaque; missing units degrade to id-only evidence).
        """
        unit = self._units.get(unit_id)
        if unit is None:
            return None
        collapsed = " ".join(unit.text.split())
        return collapsed[:_EXCERPT_CHARS]

    def _section_context(self, unit_id: str) -> str:
        """The unit's heading path (`` > ``-joined, markdown-escaped) or ``""``."""
        unit = self._units.get(unit_id)
        if unit is None or not unit.section_path:
            return ""
        return " > ".join(_escape_md(part) for part in unit.section_path)

    def _label(self, document_id: str) -> str:
        """``Title (`id`)`` when the corpus supplies a title, else `` `id` ``."""
        title = self._titles.get(document_id, "")
        if title:
            return f"{_escape_md(title)} (`{document_id}`)"
        return f"`{document_id}`"

    # --------------------------------------------------------------- formats

    def _render_jsonl(self, proposals: ProposalSet, include_text: bool) -> str:
        """One canonical-JSON proposal dict per line; the machine artifact."""
        lines: list[str] = []
        for proposal in proposals.proposals:
            data = proposal.to_dict()
            if include_text:
                for evidence_dict, evidence in zip(
                    data["evidence"], proposal.evidence, strict=True
                ):
                    source_excerpt = self._excerpt(evidence.source_unit_id)
                    target_excerpt = self._excerpt(evidence.target_unit_id)
                    if source_excerpt is not None:
                        evidence_dict["source_excerpt"] = source_excerpt
                    if target_excerpt is not None:
                        evidence_dict["target_excerpt"] = target_excerpt
            lines.append(canonical_json(data))
        if not lines:
            return ""
        return "\n".join(lines) + "\n"

    def _render_json(self, proposals: ProposalSet) -> str:
        """The full ``ProposalSet.to_dict()`` in canonical JSON."""
        return canonical_json(proposals.to_dict()) + "\n"

    def _render_markdown(self, proposals: ProposalSet, include_text: bool) -> str:
        """The human review document: summary, grouped proposals, checklists."""
        header = proposals.header
        groups = self._group_by_source(proposals)
        ranking_versions = sorted(
            {proposal.ranking_version for proposal in proposals.proposals} - {""}
        )
        lines = [
            "# Link proposals",
            "",
            f"- Run: `{header.run_id or self._run_id}`",
            f"- Corpus: `{header.corpus_id}`",
            f"- Generated: {utc_now_iso()}",
            "- Ranking version: "
            + (", ".join(f"`{version}`" for version in ranking_versions) or "n/a"),
            f"- Proposals: {len(proposals.proposals)} across {len(groups)} source document(s)",
            f"- Evidence text: {'included' if include_text else 'omitted'}",
            "",
        ]
        if not proposals.proposals:
            lines.append(
                "No proposals were generated. This is a successful empty result, "
                "not a failed or partial run."
            )
            lines.append("")
            return "\n".join(lines)
        for document_id, group in groups:
            lines.append(f"## {self._label(document_id)}")
            lines.append("")
            for proposal in group:
                lines.extend(self._proposal_markdown(proposal, include_text))
        return "\n".join(lines)

    @staticmethod
    def _group_by_source(
        proposals: ProposalSet,
    ) -> list[tuple[str, list[LinkProposal]]]:
        """Group proposals by source document, ordered by each group's best rank."""
        groups: dict[str, list[LinkProposal]] = {}
        for proposal in sorted(proposals.proposals, key=lambda p: (p.rank, p.id)):
            groups.setdefault(proposal.source_document_id, []).append(proposal)
        return sorted(groups.items(), key=lambda item: (item[1][0].rank, item[1][0].id, item[0]))

    def _proposal_markdown(self, proposal: LinkProposal, include_text: bool) -> list[str]:
        """Render one proposal: heading, features, evidence, review checklist."""
        arrow = _ARROWS[proposal.direction]
        source = self._label(proposal.source_document_id)
        target = self._label(proposal.target_document_id)
        lines = [
            f"### {proposal.rank}. {source} {arrow} {target}",
            "",
            f"Score {proposal.score:.4f} · confidence **{proposal.confidence.value}**",
            "",
        ]
        # Raw SPEC-style keys only in markdown: normalized `*_norm` variants
        # stay in the jsonl artifact but are presentation noise here.
        feature_keys = sorted(key for key in proposal.features if not key.endswith("_norm"))
        if feature_keys:
            lines.append("| Feature | Value |")
            lines.append("| --- | ---: |")
            lines.extend(f"| `{key}` | {proposal.features[key]:.4f} |" for key in feature_keys)
            lines.append("")
        if proposal.evidence:
            lines.append("Evidence:")
            lines.append("")
            for evidence in proposal.evidence:
                lines.extend(self._evidence_markdown(evidence, include_text))
            lines.append("")
        lines.append("- [ ] accept / reject / defer — reason:")
        lines.append("")
        return lines

    def _evidence_markdown(self, evidence: Evidence, include_text: bool) -> list[str]:
        """Render one evidence bullet with section context, spans, and excerpts."""
        head = (
            f"- similarity {evidence.similarity:.4f} — "
            f"`{evidence.source_unit_id}` ↔ `{evidence.target_unit_id}`"
        )
        context = self._section_context(evidence.source_unit_id)
        if context:
            head += f" — section: {context}"
        lines = [head]
        source_spans = _format_spans(evidence.source_spans)
        target_spans = _format_spans(evidence.target_spans)
        if source_spans or target_spans:
            lines.append(
                f"  - spans: source {source_spans or 'n/a'}; target {target_spans or 'n/a'}"
            )
        if include_text:
            source_excerpt = self._excerpt(evidence.source_unit_id)
            target_excerpt = self._excerpt(evidence.target_unit_id)
            if source_excerpt:
                lines.append(f"  - source excerpt: {_escape_md(source_excerpt)}")
            if target_excerpt:
                lines.append(f"  - target excerpt: {_escape_md(target_excerpt)}")
        return lines
