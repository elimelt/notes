"""Importable plugin targets for plugin-loading tests.

These objects exist so ``load_plugin`` can be exercised against real
``"module:Attr"`` specs, including Protocol conformance checks.
"""

from __future__ import annotations

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts import Region, RegionKind, SourceDocument, Span


class WordTokenCounter:
    """A trivial TokenCounter implementation (whitespace tokens)."""

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    @property
    def fingerprint(self) -> str:
        return "word-token-counter-v1"


class SingleRegionParser:
    """A trivial RegionParser implementation (one prose region per document)."""

    def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
        del config
        return [
            Region(
                kind=RegionKind.PROSE,
                span=Span(start=0, end=len(document.content)),
                text=document.content,
            )
        ]

    @property
    def fingerprint(self) -> str:
        return "single-region-parser-v1"


class NotAPlugin:
    """Implements none of the stage Protocols."""


class Unconstructable:
    """A class whose zero-argument construction fails."""

    def __init__(self, required: str) -> None:
        self.required = required


COUNTER_INSTANCE = WordTokenCounter()
NOT_A_PLUGIN_INSTANCE = NotAPlugin()
