"""Preprocessing stage: canonicalization, parsing, chunking, views, identity.

This subpackage implements the SPEC "Preprocessing specification":
deterministic conversion of canonical source content into typed regions and
semantic units, for a fixed parser version and configuration. The public
entry point is :class:`DefaultPreprocessor`, which satisfies the
:class:`~linkdiscovery.interfaces.Preprocessor` Protocol; the building blocks
(token counters, the plain-text parser, the chunker, the view builders, and
unit-identity assignment) are exported individually so host integrations can
recompose them.
"""

from linkdiscovery.preprocess.canonicalize import CanonicalizationPolicy, canonicalize
from linkdiscovery.preprocess.chunking import chunk_sections
from linkdiscovery.preprocess.identity import UnitDraft, assign_unit_ids
from linkdiscovery.preprocess.parser import PlainTextParser
from linkdiscovery.preprocess.preprocessor import DEFAULT_PRODUCER_VERSION, DefaultPreprocessor
from linkdiscovery.preprocess.tokenize import HuggingFaceTokenCounter, SimpleTokenCounter
from linkdiscovery.preprocess.views import (
    DEFAULT_DOCUMENT_METADATA_KEYS,
    KNOWN_VIEWS,
    build_document_view,
    build_section_view,
    build_title_view,
    build_views,
)

__all__ = [
    "DEFAULT_DOCUMENT_METADATA_KEYS",
    "DEFAULT_PRODUCER_VERSION",
    "KNOWN_VIEWS",
    "CanonicalizationPolicy",
    "DefaultPreprocessor",
    "HuggingFaceTokenCounter",
    "PlainTextParser",
    "SimpleTokenCounter",
    "UnitDraft",
    "assign_unit_ids",
    "build_document_view",
    "build_section_view",
    "build_title_view",
    "build_views",
    "canonicalize",
    "chunk_sections",
]
