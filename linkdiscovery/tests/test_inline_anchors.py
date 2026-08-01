"""Anchor dictionary: normalization, counts, keyphraseness, eligibility, persistence."""

from __future__ import annotations

import json
from typing import Any

import pytest

from linkdiscovery.contracts import Corpus, Relationship, RelationshipSet, SourceDocument, Span
from linkdiscovery.errors import ContractError
from linkdiscovery.inline.anchors import (
    AnchorConfig,
    AnchorDictionary,
    build_anchor_dictionary,
    mention_pattern,
    normalize_mention,
)
from tests.conftest import make_header


def make_document(
    doc_id: str,
    content: str,
    *,
    title: str = "",
    metadata: dict[str, Any] | None = None,
) -> SourceDocument:
    """A minimal source document with optional title and metadata."""
    return SourceDocument(
        id=doc_id,
        revision="rev-1",
        media_type="text/markdown",
        content=content,
        title=title,
        metadata=metadata or {},
    )


def make_link(
    source_id: str,
    target_id: str,
    *,
    span: Span | None = None,
    anchor: str | None = None,
    kind: str = "explicit-link",
) -> Relationship:
    """An explicit-link relationship with optional span and metadata anchor."""
    metadata: dict[str, Any] = {"anchor_text": anchor} if anchor is not None else {}
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        source_span=span,
        metadata=metadata,
    )


def make_corpus(documents: list[SourceDocument], relationships: list[Relationship]) -> Corpus:
    """A corpus wrapping the given documents and relationships."""
    return Corpus(
        header=make_header(),
        documents=tuple(documents),
        relationships=RelationshipSet(relationships=tuple(relationships)),
    )


class TestNormalizeMention:
    def test_collapses_whitespace_and_lowercases(self) -> None:
        assert normalize_mention("  Paxos\n Made \t Simple ") == "paxos made simple"

    def test_lowercase_false_preserves_case(self) -> None:
        assert normalize_mention("Paxos Made Simple", lowercase=False) == "Paxos Made Simple"

    def test_applies_nfc(self) -> None:
        decomposed = "Café"  # 'e' + combining acute
        assert normalize_mention(decomposed) == "café"

    def test_strips_surrounding_punctuation_only(self) -> None:
        assert normalize_mention("(**head-of-line**),") == "head-of-line"
        assert normalize_mention('"c. elegans"') == "c. elegans"

    def test_keeps_surrounding_symbols(self) -> None:
        assert normalize_mention("C++") == "c++"

    def test_idempotent(self) -> None:
        once = normalize_mention(" (Paxos  Made) ")
        assert normalize_mention(once) == once


class TestMentionPattern:
    def test_matches_with_word_boundaries(self) -> None:
        pattern = mention_pattern("paxos")
        assert [m.group() for m in pattern.finditer("Paxos, paxos; but not Paxosy")] == [
            "Paxos",
            "paxos",
        ]

    def test_multiword_matches_across_whitespace(self) -> None:
        pattern = mention_pattern("alpha beta")
        assert pattern.search("stuff alpha\n   beta stuff") is not None

    def test_case_sensitive_when_lowercase_false(self) -> None:
        pattern = mention_pattern("Paxos", lowercase=False)
        assert pattern.search("paxos") is None
        assert pattern.search("Paxos") is not None


class TestAnchorConfig:
    def test_defaults(self) -> None:
        config = AnchorConfig()
        assert config.keyphraseness_floor == 0.065
        assert config.max_span_words == 5
        assert config.min_anchor_chars == 3
        assert config.lowercase is True

    def test_resolved_dict_and_fingerprint(self) -> None:
        config = AnchorConfig()
        resolved = config.resolved_dict()
        assert resolved == {
            "keyphraseness_floor": 0.065,
            "max_span_words": 5,
            "min_anchor_chars": 3,
            "lowercase": True,
        }
        assert config.fingerprint() == AnchorConfig().fingerprint()
        assert config.fingerprint() != AnchorConfig(keyphraseness_floor=0.1).fingerprint()

    def test_from_dict_roundtrip_and_errors(self) -> None:
        config = AnchorConfig(keyphraseness_floor=0.1, lowercase=False)
        assert AnchorConfig.from_dict(config.resolved_dict()) == config
        with pytest.raises(ContractError):
            AnchorConfig.from_dict({"keyphraseness_floor": "high"})


def make_mined_corpus() -> Corpus:
    """A hand-built corpus whose anchor statistics are checked by hand."""
    src_content = "See Paxos here and Paxos there. We discuss consensus often. ab go."
    src = make_document("notes/src", src_content)
    paxos = make_document("topics/paxos", "the protocol", title="Paxos")
    raft = make_document(
        "topics/raft",
        "the other protocol",
        title="Raft Consensus",
        metadata={"aliases": ["Raft", "log replication"]},
    )
    consensus_start = src_content.find("consensus")
    relationships = [
        make_link("notes/src", "topics/paxos", anchor="Paxos"),
        make_link("notes/src", "topics/paxos", anchor="Paxos"),
        make_link("notes/src", "topics/raft", anchor="Paxos"),  # ambiguous mention
        make_link(
            "notes/src",
            "topics/raft",
            span=Span(start=consensus_start, end=consensus_start + len("consensus")),
        ),
        make_link("notes/src", "missing", anchor="Paxos"),  # unresolved target
        make_link("notes/src", "topics/raft", anchor="Paxos", kind="related-note"),  # wrong kind
        make_link("notes/src", "topics/raft", anchor="ab"),  # below min_anchor_chars
        make_link("notes/src", "topics/raft", anchor="one two three four five six"),  # too long
        make_link("notes/src", "topics/raft"),  # no anchor text at all
    ]
    return make_corpus([src, paxos, raft], relationships)


class TestBuildAnchorDictionary:
    def test_linked_counts_and_synthetic_anchors(self) -> None:
        dictionary = build_anchor_dictionary(make_mined_corpus(), config=AnchorConfig())
        # 2 + 1 real links plus the synthetic title of topics/paxos.
        assert dictionary.lookup("Paxos") == {"topics/paxos": 3, "topics/raft": 1}
        assert dictionary.linked_count("paxos") == 3
        # Span-slice fallback anchor.
        assert dictionary.lookup("consensus") == {"topics/raft": 1}
        # Title and alias synthetic anchors map to their document.
        assert dictionary.is_title("paxos")
        assert dictionary.is_title("Raft Consensus")
        assert dictionary.is_alias("raft")
        assert dictionary.is_alias("log replication")
        assert dictionary.lookup("raft consensus") == {"topics/raft": 1}

    def test_filters_and_unknown_mentions(self) -> None:
        dictionary = build_anchor_dictionary(make_mined_corpus(), config=AnchorConfig())
        mentions = dictionary.mentions()
        assert "ab" not in mentions  # min_anchor_chars
        assert "one two three four five six" not in mentions  # max_span_words
        assert dictionary.lookup("unknown") == {}
        assert dictionary.commonness("unknown", "topics/raft") == 0.0

    def test_commonness_is_count_over_total(self) -> None:
        dictionary = build_anchor_dictionary(make_mined_corpus(), config=AnchorConfig())
        assert dictionary.commonness("paxos", "topics/paxos") == pytest.approx(3 / 4)
        assert dictionary.commonness("paxos", "topics/raft") == pytest.approx(1 / 4)
        assert dictionary.commonness("paxos", "elsewhere") == 0.0

    def test_synthetic_anchors_do_not_inflate_keyphraseness(self) -> None:
        dictionary = build_anchor_dictionary(make_mined_corpus(), config=AnchorConfig())
        # linked_count is 3 even though the title adds a 4th lookup count.
        assert dictionary.keyphraseness("paxos", 10) == pytest.approx(0.3)
        # A pure-title mention has no linked anchors at all.
        assert dictionary.keyphraseness("raft consensus", 10) == 0.0

    def test_deterministic_across_builds(self) -> None:
        first = build_anchor_dictionary(make_mined_corpus(), config=AnchorConfig())
        second = build_anchor_dictionary(make_mined_corpus(), config=AnchorConfig())
        assert first.to_dict() == second.to_dict()


class TestKeyphraseness:
    def test_hand_checked_ratio(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 2}})
        assert dictionary.keyphraseness("paxos", 8) == pytest.approx(0.25)

    def test_zero_occurrences_and_unknown_are_zero(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 2}})
        assert dictionary.keyphraseness("paxos", 0) == 0.0
        assert dictionary.keyphraseness("unknown", 10) == 0.0

    def test_capped_at_one(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 5}})
        assert dictionary.keyphraseness("paxos", 2) == 1.0


class TestOccurrenceCounts:
    def test_case_insensitive_word_boundary_counting(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 1}})
        corpus = make_corpus([make_document("a", "Paxos paxos PAXOS Paxosy paxos-like")], [])
        counts = dictionary.occurrence_counts(corpus)
        # "Paxosy" fails the boundary; "paxos-like" still has a non-word boundary.
        assert counts == {"paxos": 4}

    def test_counts_sum_across_documents(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 1}})
        corpus = make_corpus(
            [make_document("a", "Paxos here"), make_document("b", "and Paxos there")], []
        )
        assert dictionary.occurrence_counts(corpus) == {"paxos": 2}

    def test_multiword_matches_raw_whitespace(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), titles={"alpha beta": {"t": 1}})
        corpus = make_corpus([make_document("a", "alpha\n   beta and alpha beta")], [])
        assert dictionary.occurrence_counts(corpus) == {"alpha beta": 2}

    def test_occurrences_are_non_overlapping(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"ab ab": {"t": 1}})
        corpus = make_corpus([make_document("a", "ab ab ab")], [])
        assert dictionary.occurrence_counts(corpus) == {"ab ab": 1}

    def test_case_sensitive_when_config_says_so(self) -> None:
        config = AnchorConfig(lowercase=False)
        dictionary = AnchorDictionary(config, linked={"Paxos": {"t": 1}})
        corpus = make_corpus([make_document("a", "Paxos paxos")], [])
        assert dictionary.occurrence_counts(corpus) == {"Paxos": 1}

    def test_is_pure_and_does_not_attach(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 1}})
        dictionary.occurrence_counts(make_corpus([make_document("a", "Paxos")], []))
        assert not dictionary.has_occurrences


class TestEligibility:
    def make_dictionary(self) -> AnchorDictionary:
        return AnchorDictionary(
            AnchorConfig(),
            linked={"paxos": {"t": 2}, "rare term": {"t": 1}},
            titles={"raft consensus": {"topics/raft": 1}},
            aliases={"log replication": {"topics/raft": 1}},
        )

    def test_synthetic_always_eligible_even_before_attach(self) -> None:
        dictionary = self.make_dictionary()
        assert dictionary.eligible("Raft Consensus")
        assert dictionary.eligible("log replication")

    def test_unknown_mention_is_ineligible_without_raising(self) -> None:
        assert not self.make_dictionary().eligible("unknown thing")

    def test_linked_mention_requires_attached_occurrences(self) -> None:
        dictionary = self.make_dictionary()
        with pytest.raises(ContractError, match="attach_occurrences"):
            dictionary.eligible("paxos")
        with pytest.raises(ContractError, match="attach_occurrences"):
            dictionary.occurrence_count("paxos")

    def test_floor_behavior(self) -> None:
        dictionary = self.make_dictionary()
        # keyphraseness 2/8 = 0.25 >= 0.065; 1/100 = 0.01 < 0.065.
        dictionary.attach_occurrences({"paxos": 8, "rare term": 100})
        assert dictionary.eligible("paxos")
        assert not dictionary.eligible("rare term")
        assert dictionary.occurrence_count("paxos") == 8
        assert dictionary.occurrence_count("never seen") == 0

    def test_exactly_at_floor_is_eligible(self) -> None:
        dictionary = AnchorDictionary(
            AnchorConfig(keyphraseness_floor=0.25), linked={"paxos": {"t": 1}}
        )
        dictionary.attach_occurrences({"paxos": 4})
        assert dictionary.eligible("paxos")

    def test_attach_rejects_negative_counts(self) -> None:
        with pytest.raises(ContractError, match="non-negative"):
            self.make_dictionary().attach_occurrences({"paxos": -1})


class TestConstructionValidation:
    def test_rejects_unnormalized_mention_keys(self) -> None:
        with pytest.raises(ContractError, match="not normalized"):
            AnchorDictionary(AnchorConfig(), linked={"Paxos": {"t": 1}})

    def test_rejects_non_positive_counts(self) -> None:
        with pytest.raises(ContractError, match="positive integer"):
            AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 0}})

    def test_case_preserving_config_accepts_cased_keys(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(lowercase=False), linked={"Paxos": {"t": 1}})
        assert dictionary.lookup("Paxos") == {"t": 1}
        assert dictionary.lookup("paxos") == {}


class TestSerialization:
    def test_roundtrip_preserves_everything(self) -> None:
        dictionary = build_anchor_dictionary(make_mined_corpus(), config=AnchorConfig())
        dictionary.attach_occurrences({"paxos": 8})
        data = dictionary.to_dict()
        json.dumps(data)  # JSON-safe
        restored = AnchorDictionary.from_dict(data)
        assert restored.to_dict() == data
        assert restored.lookup("paxos") == dictionary.lookup("paxos")
        assert restored.eligible("paxos")
        assert restored.is_alias("raft")

    def test_roundtrip_without_occurrences(self) -> None:
        dictionary = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 1}})
        restored = AnchorDictionary.from_dict(dictionary.to_dict())
        assert not restored.has_occurrences

    def test_from_dict_rejects_bad_shapes(self) -> None:
        good = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 1}}).to_dict()
        with pytest.raises(ContractError):
            AnchorDictionary.from_dict({**good, "config": None})
        with pytest.raises(ContractError):
            AnchorDictionary.from_dict({**good, "linked": {"paxos": {"t": "many"}}})
        with pytest.raises(ContractError):
            AnchorDictionary.from_dict({**good, "occurrences": {"paxos": 1.5}})
