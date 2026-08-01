"""Adapter tests against the fixture corpus in tests/fixtures/markdown_corpus.

The fixture corpus exercises frontmatter variants (tags as string and list,
aliases, draft/private/status flags), wikilinks with and without display
text and anchors, unresolved links, internal Markdown links, links inside
code fences, repeated-title H1s, unicode content, a templates/ directory
for glob exclusion, and a file with no frontmatter.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from linkdiscovery.config import SourceConfig
from linkdiscovery.contracts.documents import Corpus, Relationship, SourceDocument
from linkdiscovery.errors import ConfigError
from linkdiscovery_markdown.adapter import PRODUCER_VERSION, MarkdownSourceAdapter

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "markdown_corpus"
ADAPTER_SPEC = "linkdiscovery_markdown.adapter:MarkdownSourceAdapter"

EXPECTED_IDS = [
    "archive/old",
    "drafts/wip",
    "generated/auto",
    "index",
    "math/attention",
    "plain",
    "private-note",
    "systems/consistency",
    "systems/dynamo",
    "todo",
    "unicode-note",
]


def make_config(root: Path | str = FIXTURES, **overrides: object) -> SourceConfig:
    options: dict[str, object] = {"root": str(root), "exclude": ["templates/**"]}
    options.update(overrides)
    return SourceConfig(adapter=ADAPTER_SPEC, options=options)


def load(root: Path | str = FIXTURES, **overrides: object) -> Corpus:
    return MarkdownSourceAdapter().load(make_config(root, **overrides))


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return load()


def document(corpus: Corpus, doc_id: str) -> SourceDocument:
    matches = [doc for doc in corpus.documents if doc.id == doc_id]
    assert len(matches) == 1, f"expected exactly one document {doc_id!r}"
    return matches[0]


def relationships_from(corpus: Corpus, doc_id: str) -> list[Relationship]:
    return [rel for rel in corpus.relationships.relationships if rel.source_id == doc_id]


class TestDiscovery:
    def test_ids_are_relative_posix_paths_without_extension_sorted(self, corpus: Corpus) -> None:
        assert [doc.id for doc in corpus.documents] == EXPECTED_IDS

    def test_templates_glob_excluded(self, corpus: Corpus) -> None:
        assert all(not doc.id.startswith("templates/") for doc in corpus.documents)

    def test_source_ref_keeps_extension_and_media_type(self, corpus: Corpus) -> None:
        doc = document(corpus, "systems/dynamo")
        assert doc.source_ref == "systems/dynamo.md"
        assert doc.media_type == "text/markdown"
        assert doc.language == "en"

    def test_content_is_raw_file_text_including_frontmatter(self, corpus: Corpus) -> None:
        doc = document(corpus, "index")
        assert doc.content == (FIXTURES / "index.md").read_text(encoding="utf-8")
        assert doc.content.startswith("---\n")


class TestTitles:
    def test_frontmatter_title_wins(self, corpus: Corpus) -> None:
        assert document(corpus, "index").title == "Index of Notes"

    def test_h1_fallback(self, corpus: Corpus) -> None:
        assert document(corpus, "plain").title == "Plain Note"

    def test_stem_fallback(self, corpus: Corpus) -> None:
        assert document(corpus, "todo").title == "todo"


class TestFlags:
    def test_draft_and_private_are_excluded(self, corpus: Corpus) -> None:
        assert document(corpus, "drafts/wip").flags.excluded
        assert document(corpus, "private-note").flags.excluded
        assert not document(corpus, "index").flags.excluded

    def test_status_archived(self, corpus: Corpus) -> None:
        old = document(corpus, "archive/old")
        assert old.flags.archived
        assert not old.flags.excluded

    def test_generated_marker_in_prefix(self, corpus: Corpus) -> None:
        assert document(corpus, "generated/auto").flags.generated
        assert not document(corpus, "index").flags.generated

    def test_custom_flag_options(self) -> None:
        corpus = load(exclude_flags={"category": "Meta"}, archived_flags={"draft": True})
        assert document(corpus, "index").flags.excluded
        assert document(corpus, "drafts/wip").flags.archived
        assert not document(corpus, "drafts/wip").flags.excluded


class TestMetadata:
    def test_default_keys_with_tags_as_list(self, corpus: Corpus) -> None:
        metadata = document(corpus, "index").metadata
        assert metadata["description"] == "The landing page for the fixture corpus."
        assert metadata["category"] == "Meta"
        assert metadata["tags"] == ["meta", "navigation"]
        assert metadata["date"] == "2026-01-15"

    def test_tags_as_comma_string_stay_a_string(self, corpus: Corpus) -> None:
        metadata = document(corpus, "systems/consistency").metadata
        assert metadata["tags"] == "distributed-systems, consistency, replication"

    def test_aliases_copied_as_list(self, corpus: Corpus) -> None:
        metadata = document(corpus, "systems/consistency").metadata
        assert metadata["aliases"] == ["linearizability-notes", "consistency-cheatsheet"]
        assert "aliases" not in document(corpus, "index").metadata

    def test_frontmatter_sources_ignored(self, corpus: Corpus) -> None:
        assert "sources" not in document(corpus, "systems/dynamo").metadata

    def test_no_frontmatter_means_empty_metadata(self, corpus: Corpus) -> None:
        assert document(corpus, "plain").metadata == {}


class TestRelationships:
    def test_wikilinks_resolve_to_document_ids(self, corpus: Corpus) -> None:
        explicit = [
            rel for rel in relationships_from(corpus, "index") if rel.kind == "explicit-link"
        ]
        assert [rel.target_id for rel in explicit] == [
            "systems/consistency",
            "systems/dynamo",
            "systems/consistency",
            "systems/dynamo",
            "math/attention",
        ]
        assert all(rel.directed for rel in explicit)

    def test_spans_slice_the_link_markup(self, corpus: Corpus) -> None:
        for rel in corpus.relationships.relationships:
            doc = document(corpus, rel.source_id)
            assert rel.source_span is not None
            snippet = doc.content[rel.source_span.start : rel.source_span.end]
            assert snippet.startswith(("[[", "["))
            assert snippet.endswith(("]]", ")"))

    def test_anchor_stripped_from_target_and_kept_in_metadata(self, corpus: Corpus) -> None:
        (attention_link,) = [
            rel for rel in relationships_from(corpus, "index") if rel.target_id == "math/attention"
        ]
        assert attention_link.metadata == {
            "anchor_text": "attention math",
            "anchor": "scaled-dot-product",
        }

    def test_bare_wikilink_anchor_text_is_humanized(self, corpus: Corpus) -> None:
        (dynamo_link,) = [
            rel for rel in relationships_from(corpus, "private-note") if rel.kind == "explicit-link"
        ]
        assert dynamo_link.target_id == "systems/dynamo"
        assert dynamo_link.metadata == {"anchor_text": "dynamo"}

    def test_unresolved_links_reported_not_dropped(self, corpus: Corpus) -> None:
        unresolved = [
            rel for rel in corpus.relationships.relationships if rel.kind == "unresolved-link"
        ]
        assert {(rel.source_id, rel.target_id) for rel in unresolved} == {
            ("systems/dynamo", "systems/vector-clocks"),
            ("todo", "missing/target"),
        }
        for rel in unresolved:
            assert rel.metadata["raw_target"] == rel.target_id

    def test_links_inside_code_fences_are_not_relationships(self, corpus: Corpus) -> None:
        assert not [
            rel for rel in corpus.relationships.relationships if "quorum-code-only" in rel.target_id
        ]

    def test_internal_markdown_links_resolve_root_and_document_relative(
        self, corpus: Corpus
    ) -> None:
        plain_targets = [
            rel.target_id
            for rel in relationships_from(corpus, "plain")
            if rel.kind == "explicit-link"
        ]
        assert plain_targets == ["systems/consistency", "systems/dynamo"]
        consistency_md_links = [
            rel
            for rel in relationships_from(corpus, "systems/consistency")
            if rel.metadata.get("anchor_text") == "the Dynamo notes"
        ]
        assert [rel.target_id for rel in consistency_md_links] == ["systems/dynamo"]

    def test_external_urls_and_images_are_not_relationships(self, corpus: Corpus) -> None:
        targets = [rel.target_id for rel in relationships_from(corpus, "systems/dynamo")]
        assert not any("example.com" in target or "ring" in target for target in targets)

    def test_total_relationship_counts(self, corpus: Corpus) -> None:
        kinds = [rel.kind for rel in corpus.relationships.relationships]
        assert kinds.count("explicit-link") == 13
        assert kinds.count("unresolved-link") == 2

    def test_unicode_content_spans_are_correct(self, corpus: Corpus) -> None:
        (rel,) = relationships_from(corpus, "unicode-note")
        doc = document(corpus, "unicode-note")
        assert rel.source_span is not None
        assert (
            doc.content[rel.source_span.start : rel.source_span.end]
            == "[[systems/consistency|一致性]]"
        )
        assert rel.metadata["anchor_text"] == "一致性"


class TestHeaderAndDeterminism:
    def test_header_fields(self, corpus: Corpus) -> None:
        header = corpus.header
        assert header.run_id == "adhoc"
        assert header.producer_version == PRODUCER_VERSION
        assert header.corpus_id.startswith("sha256:")
        assert header.config_fingerprint == make_config().fingerprint()

    def test_run_id_option(self) -> None:
        assert load(run_id="run-42").header.run_id == "run-42"

    def test_deterministic_output(self, corpus: Corpus) -> None:
        again = load()
        assert again.documents == corpus.documents
        assert again.relationships == corpus.relationships
        assert again.header.corpus_id == corpus.header.corpus_id

    def test_revision_and_corpus_id_change_on_edit(self, tmp_path: Path) -> None:
        root = tmp_path / "corpus"
        shutil.copytree(FIXTURES, root)
        before = load(root)
        target = root / "systems" / "dynamo.md"
        target.write_text(
            target.read_text(encoding="utf-8") + "\nNew closing thought.\n",
            encoding="utf-8",
        )
        after = load(root)
        assert (
            document(after, "systems/dynamo").revision
            != document(before, "systems/dynamo").revision
        )
        assert document(after, "index").revision == document(before, "index").revision
        assert after.header.corpus_id != before.header.corpus_id


class TestOptionValidation:
    def test_unknown_option_key(self) -> None:
        with pytest.raises(ConfigError, match="unknown option 'wat'"):
            load(wat=True)

    def test_missing_root(self) -> None:
        config = SourceConfig(adapter=ADAPTER_SPEC, options={})
        with pytest.raises(ConfigError, match="missing required option 'root'"):
            MarkdownSourceAdapter().load(config)

    def test_root_must_be_a_directory(self) -> None:
        with pytest.raises(ConfigError, match="is not a directory"):
            load(FIXTURES / "index.md")

    def test_include_must_be_string_list(self) -> None:
        with pytest.raises(ConfigError, match="'include' must be a list"):
            load(include="**/*.md")

    def test_flag_map_values_must_be_scalars(self) -> None:
        with pytest.raises(ConfigError, match="must be a scalar"):
            load(exclude_flags={"draft": [True]})

    def test_language_option(self) -> None:
        corpus = load(language="de")
        assert all(doc.language == "de" for doc in corpus.documents)
