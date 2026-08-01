"""Integration test against the real notes corpus.

Skipped cleanly when the corpus directory is absent so the package works
standalone; on the notes machine it verifies the adapter and parser handle
every real document without exceptions and with plausible link volumes.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from linkdiscovery.config import PreprocessConfig, SourceConfig
from linkdiscovery_markdown.adapter import MarkdownSourceAdapter
from linkdiscovery_markdown.parser import MarkdownRegionParser

REAL_ROOT = Path("/Users/elimelt/repos/notes/content")

pytestmark = pytest.mark.skipif(
    not REAL_ROOT.is_dir(), reason="real notes corpus not available on this machine"
)


def test_real_corpus_loads_and_parses() -> None:
    config = SourceConfig(
        adapter="linkdiscovery_markdown.adapter:MarkdownSourceAdapter",
        options={"root": str(REAL_ROOT), "exclude": ["templates/**"]},
    )
    corpus = MarkdownSourceAdapter().load(config)

    assert len(corpus.documents) >= 190
    assert all(doc.content for doc in corpus.documents)
    assert [doc.id for doc in corpus.documents] == sorted(doc.id for doc in corpus.documents)

    kinds = Counter(rel.kind for rel in corpus.relationships.relationships)
    assert kinds["explicit-link"] > 200

    # unresolved links are reported, not dropped and not fatal
    assert set(kinds) <= {"explicit-link", "unresolved-link"}

    # every relationship span slices real link markup out of its source
    documents = {doc.id: doc for doc in corpus.documents}
    for rel in corpus.relationships.relationships:
        assert rel.source_span is not None
        snippet = documents[rel.source_id].content[rel.source_span.start : rel.source_span.end]
        assert snippet.startswith(("[[", "["))

    # every document parses into in-bounds, ordered regions without error
    parser = MarkdownRegionParser()
    preprocess = PreprocessConfig(parser="linkdiscovery_markdown.parser:MarkdownRegionParser")
    total_regions = 0
    for doc in corpus.documents:
        regions = parser.parse(doc, preprocess)
        total_regions += len(regions)
        for region in regions:
            assert 0 <= region.span.start <= region.span.end <= len(doc.content)
    assert total_regions > len(corpus.documents)
