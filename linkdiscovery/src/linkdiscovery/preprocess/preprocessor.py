"""The default :class:`~linkdiscovery.interfaces.Preprocessor` implementation.

:class:`DefaultPreprocessor` composes the pieces of this subpackage — region
parsing, canonicalization, retrieval-view construction, chunking, and unit
identity — into the stage contract:

    corpus (Corpus) -> ProcessedCorpus

Per document: parse regions with the injected
:class:`~linkdiscovery.interfaces.RegionParser`, canonicalize each region's
text under the configured policy (applied to region text, not raw content, so
source spans stay valid against the adapter's raw ``document.content``),
build the configured retrieval views, and assign stable content-derived unit
IDs. Deterministic for a fixed parser, token counter, policy, and
configuration.

``preprocessing_fingerprint`` composition (order-sensitive, see
:func:`~linkdiscovery.fingerprint.combine_fingerprints`):

1. ``config.fingerprint()`` — the resolved preprocess configuration;
2. ``fingerprint(parser.fingerprint)`` — the parser identity string, wrapped
   via :func:`~linkdiscovery.fingerprint.fingerprint` so raw identity strings
   become well-formed fingerprints;
3. ``fingerprint(token_counter.fingerprint)`` — the tokenizer identity,
   wrapped the same way;
4. the canonicalization policy fingerprint.

Changing any component invalidates processed units and everything downstream.
"""

from __future__ import annotations

from dataclasses import replace

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.documents import Corpus, SourceDocument
from linkdiscovery.contracts.units import (
    SCHEMA_VERSION,
    ProcessedCorpus,
    ProcessedDocument,
    Region,
)
from linkdiscovery.errors import PreprocessError
from linkdiscovery.fingerprint import combine_fingerprints, fingerprint
from linkdiscovery.interfaces import RegionParser, TokenCounter
from linkdiscovery.preprocess.canonicalize import CanonicalizationPolicy, canonicalize
from linkdiscovery.preprocess.identity import assign_unit_ids
from linkdiscovery.preprocess.views import KNOWN_VIEWS, build_views

__all__ = ["DEFAULT_PRODUCER_VERSION", "DefaultPreprocessor"]

DEFAULT_PRODUCER_VERSION = "linkdiscovery/0.1.0"
"""Producer version recorded in artifact headers by default."""


class DefaultPreprocessor:
    """Deterministic preprocessor over an injected parser and token counter.

    Contract highlights:

    - Documents flagged ``excluded`` are skipped entirely and produce no
      output; the count of skipped documents from the most recent
      :meth:`process` call is exposed as :attr:`skipped_excluded_count` for
      run-manifest reporting.
    - Documents whose canonicalized body is empty or whitespace-only produce
      a :class:`ProcessedDocument` with regions but no units (a successful
      empty result, never a crash).
    - Malformed parser output — anything but a list of ``Region`` — raises
      :class:`~linkdiscovery.errors.PreprocessError` naming the document, as
      does any exception escaping the parser.
    """

    def __init__(
        self,
        parser: RegionParser,
        token_counter: TokenCounter,
        *,
        run_id: str = "adhoc",
        producer_version: str = DEFAULT_PRODUCER_VERSION,
        canonicalization: CanonicalizationPolicy | None = None,
    ) -> None:
        self._parser = parser
        self._token_counter = token_counter
        self._run_id = run_id
        self._producer_version = producer_version
        self._policy = (
            canonicalization if canonicalization is not None else CanonicalizationPolicy()
        )
        self.skipped_excluded_count = 0

    def preprocessing_fingerprint(self, config: PreprocessConfig) -> str:
        """The composed preprocessing fingerprint (see module docstring)."""
        return combine_fingerprints(
            config.fingerprint(),
            fingerprint(self._parser.fingerprint),
            fingerprint(self._token_counter.fingerprint),
            self._policy.fingerprint(),
        )

    def process(self, corpus: Corpus, config: PreprocessConfig) -> ProcessedCorpus:
        """Convert a frozen corpus into typed regions and semantic units."""
        self._check_views(config)
        skipped = 0
        documents: list[ProcessedDocument] = []
        for document in corpus.documents:
            if document.flags.excluded:
                skipped += 1
                continue
            documents.append(self._process_document(document, config))
        self.skipped_excluded_count = skipped
        header = ArtifactHeader(
            schema_version=SCHEMA_VERSION,
            run_id=self._run_id,
            corpus_id=corpus.header.corpus_id,
            created_at=utc_now_iso(),
            config_fingerprint=config.fingerprint(),
            producer_version=self._producer_version,
        )
        return ProcessedCorpus(
            header=header,
            preprocessing_fingerprint=self.preprocessing_fingerprint(config),
            documents=tuple(documents),
        )

    @staticmethod
    def _check_views(config: PreprocessConfig) -> None:
        """Reject configurations naming views this preprocessor cannot build."""
        unknown = [view for view in config.views if view not in KNOWN_VIEWS]
        if unknown:
            names = ", ".join(repr(view) for view in unknown)
            known = ", ".join(sorted(KNOWN_VIEWS))
            raise PreprocessError(
                f"preprocess.views names unknown retrieval view{'s' if len(unknown) > 1 else ''} "
                f"{names}; this preprocessor builds: {known}"
            )

    def _process_document(
        self, document: SourceDocument, config: PreprocessConfig
    ) -> ProcessedDocument:
        """Parse, canonicalize, and build views for one document."""
        regions = self._parse_regions(document, config)
        if not canonicalize(document.content, self._policy).strip():
            return ProcessedDocument(
                document_id=document.id,
                revision=document.revision,
                regions=tuple(regions),
                units=(),
            )
        drafts = build_views(document, regions, config, self._token_counter)
        return ProcessedDocument(
            document_id=document.id,
            revision=document.revision,
            regions=tuple(regions),
            units=assign_unit_ids(document.id, drafts),
        )

    def _parse_regions(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
        """Run the parser and canonicalize region text; validate the output shape."""
        try:
            raw = self._parser.parse(document, config)
        except PreprocessError as exc:
            raise PreprocessError(f"document {document.id!r}: {exc}") from exc
        except Exception as exc:
            raise PreprocessError(
                f"document {document.id!r}: parser {self._parser.fingerprint!r} raised "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(raw, list) or not all(isinstance(region, Region) for region in raw):
            raise PreprocessError(
                f"document {document.id!r}: parser {self._parser.fingerprint!r} returned "
                "malformed output; expected a list of Region"
            )
        return [replace(region, text=canonicalize(region.text, self._policy)) for region in raw]
