"""End-to-end tests for ``DefaultPreprocessor``.

Covers the stage contract: determinism, exclusion, empty documents, error
handling, fingerprint composition and sensitivity, and unit-identity
stability under unrelated edits.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.documents import SourceDocument
from linkdiscovery.contracts.units import ProcessedCorpus, Region, SemanticUnit
from linkdiscovery.errors import PreprocessError
from linkdiscovery.fingerprint import canonical_json, combine_fingerprints, fingerprint
from linkdiscovery.preprocess import (
    DEFAULT_PRODUCER_VERSION,
    CanonicalizationPolicy,
    DefaultPreprocessor,
    PlainTextParser,
    SimpleTokenCounter,
)
from tests.test_preprocess_helpers import (
    TinyMarkupParser,
    make_config,
    make_corpus,
    make_document,
)

SECTIONED_CONTENT = """\
# Alpha

Alpha body text here.

# Beta

Beta body text here.
"""


def make_preprocessor(**kwargs: object) -> DefaultPreprocessor:
    return DefaultPreprocessor(TinyMarkupParser(), SimpleTokenCounter(), **kwargs)  # type: ignore[arg-type]


def section_units(corpus: ProcessedCorpus, document_id: str) -> list[SemanticUnit]:
    (document,) = [d for d in corpus.documents if d.document_id == document_id]
    return [unit for unit in document.units if unit.view == "section"]


class TestProcess:
    def test_produces_regions_and_units_for_all_views(self) -> None:
        corpus = make_corpus(make_document(content=SECTIONED_CONTENT, title="Sectioned"))
        processed = make_preprocessor().process(corpus, make_config())
        (document,) = processed.documents
        assert document.document_id == "doc-a"
        assert document.revision == "rev-doc-a"
        assert len(document.regions) > 0
        views = {unit.view for unit in document.units}
        assert views == {"document", "section", "title"}

    def test_section_units_carry_paths_and_context(self) -> None:
        corpus = make_corpus(make_document(content=SECTIONED_CONTENT, title="Sectioned"))
        processed = make_preprocessor().process(corpus, make_config())
        units = section_units(processed, "doc-a")
        assert [unit.section_path for unit in units] == [("Alpha",), ("Beta",)]
        assert units[0].text == "Sectioned > Alpha\n\nAlpha body text here."

    def test_unit_ids_unique_within_document(self) -> None:
        content = "# A\n\nsame text\n\n# A\n\nsame text\n"
        corpus = make_corpus(make_document(content=content, title="T"))
        processed = make_preprocessor().process(corpus, make_config())
        units = section_units(processed, "doc-a")
        assert len(units) == 2
        assert units[0].id != units[1].id
        assert units[1].id == f"{units[0].id}~1"

    def test_header_fields(self) -> None:
        corpus = make_corpus(make_document())
        config = make_config()
        preprocessor = make_preprocessor(run_id="run-42", producer_version="me/9.9.9")
        processed = preprocessor.process(corpus, config)
        assert processed.header.schema_version == 1
        assert processed.header.run_id == "run-42"
        assert processed.header.corpus_id == corpus.header.corpus_id
        assert processed.header.config_fingerprint == config.fingerprint()
        assert processed.header.producer_version == "me/9.9.9"

    def test_default_run_id_and_producer_version(self) -> None:
        processed = make_preprocessor().process(make_corpus(make_document()), make_config())
        assert processed.header.run_id == "adhoc"
        assert processed.header.producer_version == DEFAULT_PRODUCER_VERSION
        assert DEFAULT_PRODUCER_VERSION == "linkdiscovery/0.1.0"

    def test_round_trip_serialization(self) -> None:
        corpus = make_corpus(make_document(content=SECTIONED_CONTENT))
        processed = make_preprocessor().process(corpus, make_config())
        assert ProcessedCorpus.from_dict(processed.to_dict()).to_dict() == processed.to_dict()


class TestExclusionAndEmpties:
    def test_excluded_documents_skipped_entirely(self) -> None:
        corpus = make_corpus(
            make_document("doc-keep"),
            make_document("doc-skip", excluded=True),
        )
        preprocessor = make_preprocessor()
        processed = preprocessor.process(corpus, make_config())
        assert [d.document_id for d in processed.documents] == ["doc-keep"]
        assert preprocessor.skipped_excluded_count == 1

    def test_empty_body_produces_document_with_no_units(self) -> None:
        corpus = make_corpus(make_document(content="", title="Only A Title"))
        processed = make_preprocessor().process(corpus, make_config())
        (document,) = processed.documents
        assert document.units == ()

    def test_whitespace_body_produces_document_with_no_units(self) -> None:
        corpus = make_corpus(make_document(content="  \n\t \n", title="T"))
        processed = make_preprocessor().process(corpus, make_config())
        (document,) = processed.documents
        assert document.units == ()


class TestErrors:
    class _RaisingParser:
        def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
            raise ValueError("internal parser bug")

        @property
        def fingerprint(self) -> str:
            return "raising-parser:v1"

    class _NotAListParser:
        def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
            return "not a list"  # type: ignore[return-value]

        @property
        def fingerprint(self) -> str:
            return "not-a-list-parser:v1"

    class _JunkItemsParser:
        def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
            return ["junk"]  # type: ignore[list-item]

        @property
        def fingerprint(self) -> str:
            return "junk-items-parser:v1"

    def test_parser_exception_wrapped_naming_document(self) -> None:
        preprocessor = DefaultPreprocessor(self._RaisingParser(), SimpleTokenCounter())
        with pytest.raises(PreprocessError, match=r"'doc-a'.*internal parser bug"):
            preprocessor.process(make_corpus(make_document()), make_config())

    def test_non_list_parser_output_rejected(self) -> None:
        preprocessor = DefaultPreprocessor(self._NotAListParser(), SimpleTokenCounter())
        with pytest.raises(PreprocessError, match=r"'doc-a'.*malformed"):
            preprocessor.process(make_corpus(make_document()), make_config())

    def test_non_region_items_rejected(self) -> None:
        preprocessor = DefaultPreprocessor(self._JunkItemsParser(), SimpleTokenCounter())
        with pytest.raises(PreprocessError, match=r"'doc-a'.*malformed"):
            preprocessor.process(make_corpus(make_document()), make_config())

    def test_unknown_view_rejected_before_processing(self) -> None:
        preprocessor = make_preprocessor()
        with pytest.raises(PreprocessError, match="bogus"):
            preprocessor.process(make_corpus(), make_config(views=("document", "bogus")))


class TestCanonicalization:
    def test_region_text_canonicalized_spans_stay_raw(self) -> None:
        content = "café line  \r\nsecond line\r\n"
        corpus = make_corpus(make_document(content=content, title=""))
        preprocessor = DefaultPreprocessor(PlainTextParser(), SimpleTokenCounter())
        processed = preprocessor.process(corpus, make_config())
        (document,) = processed.documents
        (region,) = document.regions
        assert region.text == "café line\nsecond line"
        # The span still indexes the raw content, not the canonicalized text.
        assert content[region.span.start : region.span.end] == "café line  \r\nsecond line"

    def test_policy_can_be_disabled(self) -> None:
        content = "line one  \nline two"
        corpus = make_corpus(make_document(content=content, title=""))
        policy = CanonicalizationPolicy(strip_trailing_whitespace=False)
        preprocessor = DefaultPreprocessor(
            PlainTextParser(), SimpleTokenCounter(), canonicalization=policy
        )
        processed = preprocessor.process(corpus, make_config())
        (region,) = processed.documents[0].regions
        assert region.text == "line one  \nline two"


class TestDeterminism:
    def test_repeated_runs_serialize_identically(self) -> None:
        corpus = make_corpus(
            make_document("doc-a", SECTIONED_CONTENT, title="A"),
            make_document("doc-b", "Some plain body.\n\nMore body.", title="B"),
        )
        preprocessor = make_preprocessor()
        config = make_config()
        first = preprocessor.process(corpus, config)
        second = preprocessor.process(corpus, config)

        def serialize(processed: ProcessedCorpus) -> str:
            return canonical_json([d.to_dict() for d in processed.documents])

        assert serialize(first) == serialize(second)
        assert first.preprocessing_fingerprint == second.preprocessing_fingerprint


class TestFingerprint:
    def test_composition_is_documented_combination(self) -> None:
        preprocessor = make_preprocessor()
        config = make_config()
        expected = combine_fingerprints(
            config.fingerprint(),
            fingerprint(TinyMarkupParser().fingerprint),
            fingerprint(SimpleTokenCounter().fingerprint),
            CanonicalizationPolicy().fingerprint(),
        )
        assert preprocessor.process(make_corpus(), config).preprocessing_fingerprint == expected

    def test_sensitive_to_target_tokens(self) -> None:
        preprocessor = make_preprocessor()
        config = make_config()
        changed = replace(config, target_tokens=config.target_tokens // 2)
        assert (
            preprocessor.process(make_corpus(), config).preprocessing_fingerprint
            != preprocessor.process(make_corpus(), changed).preprocessing_fingerprint
        )

    def test_sensitive_to_parser_tokenizer_and_policy(self) -> None:
        config = make_config()
        corpus = make_corpus()
        base = DefaultPreprocessor(TinyMarkupParser(), SimpleTokenCounter())
        other_parser = DefaultPreprocessor(PlainTextParser(), SimpleTokenCounter())
        other_policy = DefaultPreprocessor(
            TinyMarkupParser(),
            SimpleTokenCounter(),
            canonicalization=CanonicalizationPolicy(unicode_nfc=False),
        )
        fingerprints = {
            p.process(corpus, config).preprocessing_fingerprint
            for p in (base, other_parser, other_policy)
        }
        assert len(fingerprints) == 3


class TestUnitIdStability:
    """SPEC: "The unit ID is stable for unchanged semantic content"."""

    def _units_by_path(self, corpus: ProcessedCorpus) -> dict[tuple[str, ...], SemanticUnit]:
        units = section_units(corpus, "doc-a")
        assert len({unit.section_path for unit in units}) == len(units)
        return {unit.section_path: unit for unit in units}

    def test_editing_one_section_changes_only_that_sections_units(self) -> None:
        edited_content = SECTIONED_CONTENT.replace("Beta body text here.", "Beta body was EDITED.")
        preprocessor = make_preprocessor()
        config = make_config()
        before = self._units_by_path(
            preprocessor.process(
                make_corpus(make_document(content=SECTIONED_CONTENT, title="T")), config
            )
        )
        after = self._units_by_path(
            preprocessor.process(
                make_corpus(make_document(content=edited_content, title="T")), config
            )
        )
        # The untouched sibling keeps its id, hash, and text exactly.
        assert after[("Alpha",)].id == before[("Alpha",)].id
        assert after[("Alpha",)].content_hash == before[("Alpha",)].content_hash
        assert after[("Alpha",)].text == before[("Alpha",)].text
        # The edited section gets a new identity.
        assert after[("Beta",)].id != before[("Beta",)].id
        assert after[("Beta",)].content_hash != before[("Beta",)].content_hash

    def test_unrelated_edit_shifts_spans_but_not_identity(self) -> None:
        grown_content = SECTIONED_CONTENT.replace(
            "Alpha body text here.", "Alpha body text here, now considerably longer than before."
        )
        preprocessor = make_preprocessor()
        config = make_config()
        before = self._units_by_path(
            preprocessor.process(
                make_corpus(make_document(content=SECTIONED_CONTENT, title="T")), config
            )
        )
        after = self._units_by_path(
            preprocessor.process(
                make_corpus(make_document(content=grown_content, title="T")), config
            )
        )
        assert after[("Beta",)].source_spans != before[("Beta",)].source_spans
        assert after[("Beta",)].id == before[("Beta",)].id
        assert after[("Beta",)].content_hash == before[("Beta",)].content_hash
