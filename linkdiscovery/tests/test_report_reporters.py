"""Tests for the default reporter: formats, excerpts, atomicity, manifests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linkdiscovery.config import ReportConfig
from linkdiscovery.contracts import (
    Confidence,
    Corpus,
    Evidence,
    LinkProposal,
    ProcessedCorpus,
    ProcessedDocument,
    ProposalSet,
    RegionKind,
    SemanticUnit,
    SourceDocument,
    Span,
)
from linkdiscovery.errors import ReportError
from linkdiscovery.interfaces import Reporter
from linkdiscovery.report import DefaultReporter
from tests.conftest import make_header


def test_default_reporter_satisfies_reporter_protocol() -> None:
    assert isinstance(DefaultReporter(), Reporter)


DOC_TITLES = {
    "doc-a": "Scheduling & Fairness [draft]",
    "doc-b": "Lottery *Scheduling*",
    "doc-c": "Queueing Theory",
}
UNIT_A = "doc-a#section#aaa111"
UNIT_B = "doc-b#section#bbb222"
LONG_TEXT = "word " * 100  # collapses to 499 chars, longer than the 240-char excerpt


def make_corpus() -> Corpus:
    documents = tuple(
        SourceDocument(
            id=doc_id,
            revision="rev-1",
            media_type="text/markdown",
            content="body",
            title=title,
            source_ref=f"notes/{doc_id}.md",
        )
        for doc_id, title in DOC_TITLES.items()
    )
    return Corpus(header=make_header(), documents=documents)


def make_unit(unit_id: str, doc_id: str, text: str, section: tuple[str, ...]) -> SemanticUnit:
    return SemanticUnit(
        id=unit_id,
        document_id=doc_id,
        view="section",
        section_path=section,
        region_kinds=(RegionKind.PROSE,),
        source_spans=(Span(start=0, end=len(text)),),
        text=text,
        token_count=42,
        content_hash="sha256:unit",
    )


def make_processed() -> ProcessedCorpus:
    return ProcessedCorpus(
        header=make_header(),
        preprocessing_fingerprint="sha256:preproc",
        documents=(
            ProcessedDocument(
                document_id="doc-a",
                revision="rev-1",
                units=(make_unit(UNIT_A, "doc-a", LONG_TEXT, ("Scheduling", "Fairness")),),
            ),
            ProcessedDocument(
                document_id="doc-b",
                revision="rev-1",
                units=(make_unit(UNIT_B, "doc-b", "lottery   tickets\nwin", ()),),
            ),
        ),
    )


def make_proposal(
    pid: str,
    source: str,
    target: str,
    rank: int,
    *,
    score: float = 0.9,
    direction: str = "source-to-target",
    features: dict[str, float] | None = None,
    evidence: tuple[Evidence, ...] = (),
) -> LinkProposal:
    return LinkProposal(
        id=pid,
        source_document_id=source,
        target_document_id=target,
        direction=direction,
        rank=rank,
        score=score,
        confidence=Confidence.MEDIUM,
        features=features if features is not None else {"document_similarity": 0.5},
        evidence=evidence,
        ranking_version="sha256:ranker",
    )


def make_proposal_set() -> ProposalSet:
    evidence = Evidence(
        source_unit_id=UNIT_A,
        target_unit_id=UNIT_B,
        similarity=0.93,
        source_spans=(Span(start=420, end=1080),),
        target_spans=(Span(start=80, end=510),),
    )
    features = {
        "document_similarity": 0.84,
        "best_chunk_similarity": 0.93,
        "support_breadth": 0.71,
        "lexical_similarity": 0.24,
        "hubness_penalty": 0.05,
        "graph_redundancy_penalty": 0.0,
        "document_similarity_norm": 0.91,
        "relatedness": 0.88,
    }
    return ProposalSet(
        header=make_header(),
        proposals=(
            make_proposal("pa-b", "doc-a", "doc-b", 1, features=features, evidence=(evidence,)),
            make_proposal("pa-c", "doc-a", "doc-c", 2, direction="undirected"),
            make_proposal("pc-a", "doc-c", "doc-a", 3, direction="target-to-source"),
        ),
    )


def all_formats_config(tmp_path: Path, *, include_evidence_text: bool = True) -> ReportConfig:
    return ReportConfig(
        formats=("jsonl", "json", "markdown"),
        output_dir=str(tmp_path / "reports"),
        include_evidence_text=include_evidence_text,
    )


def full_reporter() -> DefaultReporter:
    return DefaultReporter(make_corpus(), make_processed())


class TestManifest:
    def test_all_formats_written_and_referenced(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        manifest = full_reporter().write(make_proposal_set(), config)

        assert manifest.formats == ("jsonl", "json", "markdown")
        assert [ref.path for ref in manifest.outputs] == [
            "proposals.jsonl",
            "proposals.json",
            "proposals.md",
        ]
        for ref in manifest.outputs:
            data = (Path(config.output_dir) / ref.path).read_bytes()
            assert ref.size == len(data)
            assert ref.fingerprint.startswith("sha256:")

    def test_header_identity_and_fingerprint(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        proposals = make_proposal_set()
        manifest = full_reporter().write(proposals, config)

        assert manifest.header.run_id == proposals.header.run_id
        assert manifest.header.corpus_id == proposals.header.corpus_id
        assert manifest.header.config_fingerprint == config.fingerprint()
        assert manifest.header.producer_version == "linkdiscovery/0.1.0"

    def test_run_id_fallback_for_adhoc_sets(self, tmp_path: Path) -> None:
        proposals = ProposalSet(header=make_header(run_id=""))
        reporter = DefaultReporter(run_id="adhoc-7")
        manifest = reporter.write(proposals, all_formats_config(tmp_path))
        assert manifest.header.run_id == "adhoc-7"

    def test_duplicate_formats_rendered_once(self, tmp_path: Path) -> None:
        config = ReportConfig(formats=("jsonl", "jsonl"), output_dir=str(tmp_path))
        manifest = full_reporter().write(make_proposal_set(), config)
        assert manifest.formats == ("jsonl",)
        assert len(manifest.outputs) == 1

    def test_unknown_format_raises_listing_known(self, tmp_path: Path) -> None:
        config = ReportConfig(formats=("jsonl", "html"), output_dir=str(tmp_path))
        pattern = r"'html'.*known formats.*'jsonl'.*'json'.*'markdown'"
        with pytest.raises(ReportError, match=pattern):
            full_reporter().write(make_proposal_set(), config)
        assert not (tmp_path / "proposals.jsonl").exists()


class TestJsonl:
    def read_lines(self, config: ReportConfig) -> list[dict[str, object]]:
        text = (Path(config.output_dir) / "proposals.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines()]

    def test_round_trips_through_from_dict(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        proposals = make_proposal_set()
        full_reporter().write(proposals, config)

        lines = self.read_lines(config)
        parsed = tuple(LinkProposal.from_dict(line) for line in lines)  # type: ignore[arg-type]
        assert parsed == proposals.proposals

    def test_excerpts_present_when_enabled(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        full_reporter().write(make_proposal_set(), config)

        evidence = self.read_lines(config)[0]["evidence"]
        assert isinstance(evidence, list)
        entry = evidence[0]
        assert len(entry["source_excerpt"]) == 240
        assert entry["source_excerpt"] == (" ".join(LONG_TEXT.split()))[:240]
        assert entry["target_excerpt"] == "lottery tickets win"

    def test_excerpts_absent_when_disabled(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path, include_evidence_text=False)
        full_reporter().write(make_proposal_set(), config)

        entry = self.read_lines(config)[0]["evidence"][0]  # type: ignore[index]
        assert "source_excerpt" not in entry
        assert "target_excerpt" not in entry
        assert entry["source_unit_id"] == UNIT_A
        assert entry["source_spans"] == [{"start": 420, "end": 1080}]

    def test_degrades_without_processed_corpus(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        DefaultReporter(make_corpus()).write(make_proposal_set(), config)

        entry = self.read_lines(config)[0]["evidence"][0]  # type: ignore[index]
        assert "source_excerpt" not in entry

    def test_json_matches_proposal_set_to_dict(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        proposals = make_proposal_set()
        full_reporter().write(proposals, config)

        data = json.loads((Path(config.output_dir) / "proposals.json").read_text("utf-8"))
        assert data == proposals.to_dict()
        assert ProposalSet.from_dict(data) == proposals


class TestMarkdown:
    def render(self, tmp_path: Path, *, include_evidence_text: bool = True) -> str:
        config = all_formats_config(tmp_path, include_evidence_text=include_evidence_text)
        full_reporter().write(make_proposal_set(), config)
        return (Path(config.output_dir) / "proposals.md").read_text(encoding="utf-8")

    def test_titles_escaped_and_ids_shown(self, tmp_path: Path) -> None:
        text = self.render(tmp_path)
        assert r"Scheduling & Fairness \[draft\] (`doc-a`)" in text
        assert r"Lottery \*Scheduling\* (`doc-b`)" in text

    def test_direction_arrows(self, tmp_path: Path) -> None:
        text = self.render(tmp_path)
        assert "→" in text  # source-to-target
        assert "↔" in text  # undirected
        assert "←" in text  # target-to-source

    def test_feature_table_shows_raw_keys_only(self, tmp_path: Path) -> None:
        text = self.render(tmp_path)
        assert "| `document_similarity` | 0.8400 |" in text
        assert "| `hubness_penalty` | 0.0500 |" in text
        assert "| `relatedness` | 0.8800 |" in text
        assert "document_similarity_norm" not in text

    def test_evidence_section_context_spans_and_excerpt(self, tmp_path: Path) -> None:
        text = self.render(tmp_path)
        assert f"`{UNIT_A}`" in text
        assert "section: Scheduling > Fairness" in text
        assert "spans: source [420, 1080); target [80, 510)" in text
        assert "source excerpt: word word" in text
        assert "target excerpt: lottery tickets win" in text

    def test_excerpts_omitted_when_disabled(self, tmp_path: Path) -> None:
        text = self.render(tmp_path, include_evidence_text=False)
        assert "excerpt" not in text
        assert "Evidence text: omitted" in text
        assert f"`{UNIT_A}`" in text  # references retained (SPEC privacy)

    def test_summary_and_review_checklist(self, tmp_path: Path) -> None:
        text = self.render(tmp_path)
        assert "- Run: `run-0001`" in text
        assert "- Corpus: `corpus-alpha`" in text
        assert "- Ranking version: `sha256:ranker`" in text
        assert "- Proposals: 3 across 2 source document(s)" in text
        assert text.count("- [ ] accept / reject / defer — reason:") == 3

    def test_grouped_by_source_document_by_best_rank(self, tmp_path: Path) -> None:
        text = self.render(tmp_path)
        doc_a_group = text.index("## Scheduling")
        doc_c_group = text.index("## Queueing")
        assert doc_a_group < doc_c_group  # doc-a holds rank 1, doc-c only rank 3


class TestEdgeCases:
    def test_empty_proposal_set_produces_valid_outputs(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        empty = ProposalSet(header=make_header())
        manifest = DefaultReporter().write(empty, config)

        assert len(manifest.outputs) == 3
        out = Path(config.output_dir)
        assert (out / "proposals.jsonl").read_text("utf-8") == ""
        markdown = (out / "proposals.md").read_text("utf-8")
        assert "Proposals: 0" in markdown
        assert "successful empty result" in markdown
        json_data = json.loads((out / "proposals.json").read_text("utf-8"))
        assert ProposalSet.from_dict(json_data) == empty

    def test_bare_reporter_degrades_to_ids(self, tmp_path: Path) -> None:
        config = all_formats_config(tmp_path)
        DefaultReporter().write(make_proposal_set(), config)
        text = (Path(config.output_dir) / "proposals.md").read_text("utf-8")
        assert "## `doc-a`" in text  # no corpus: bare id instead of title
        assert "excerpt" not in text  # no processed corpus: no excerpts

    def test_failed_write_leaves_no_partial_file(self, tmp_path: Path) -> None:
        out = tmp_path / "reports"
        (out / "proposals.jsonl").mkdir(parents=True)  # rename onto a directory fails
        config = ReportConfig(formats=("jsonl",), output_dir=str(out))

        with pytest.raises(ReportError, match="atomic write"):
            full_reporter().write(make_proposal_set(), config)

        assert (out / "proposals.jsonl").is_dir()  # destination untouched
        leftovers = [p for p in out.iterdir() if p.name != "proposals.jsonl"]
        assert leftovers == []  # no temp files left behind

    def test_output_directory_is_created(self, tmp_path: Path) -> None:
        config = ReportConfig(formats=("markdown",), output_dir=str(tmp_path / "deep" / "nested"))
        full_reporter().write(make_proposal_set(), config)
        assert (tmp_path / "deep" / "nested" / "proposals.md").is_file()
