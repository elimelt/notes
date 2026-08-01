"""Markdown source adapter: loads a directory of ``.md`` notes into a ``Corpus``.

Implements :class:`linkdiscovery.interfaces.SourceAdapter`. The adapter is
zero-arg constructible; every behavior is driven by ``SourceConfig.options``
(unknown option keys are :class:`~linkdiscovery.errors.ConfigError`):

``root`` (required, string)
    The corpus directory. A relative path is resolved against the current
    working directory, so runs must start from a known directory (the
    shipped ``configs/notes.yaml`` assumes the ``linkdiscovery/`` checkout).
``include`` (default ``["**/*.md"]``) / ``exclude`` (default ``[]``)
    Glob patterns matched against POSIX paths relative to ``root``.
    ``**`` crosses directory separators (``**/`` also matches zero
    directories); ``*`` and ``?`` never cross a ``/``.
``exclude_flags`` (default ``{"draft": true, "private": true}``)
    Frontmatter ``key: value`` pairs; any match marks the document
    ``excluded``.
``archived_flags`` (default ``{"archived": true, "status": "archived"}``)
    Same shape; any match marks the document ``archived``.
``generated_marker`` (default ``"<!-- generated -->"``)
    A document is ``generated`` when this marker occurs (case-insensitively)
    in the first 500 bytes of the raw file, or frontmatter has
    ``generated: true``.
``metadata_keys`` (default ``["description", "category", "tags", "date"]``)
    Frontmatter keys copied into ``SourceDocument.metadata``; values are
    coerced to ``str`` (scalars, including dates) or ``list[str]``.
``language`` (default ``"en"``) and ``run_id`` (default ``"adhoc"``)
    Document language tag and the corpus header's run identifier.

Document contract:

- ``id`` is the POSIX path relative to ``root`` without the ``.md``
  extension (``distributed-systems/dynamo-db``), matching wikilink target
  syntax; ``source_ref`` keeps the extension.
- ``revision`` is the fingerprint of the raw file bytes, so any content
  edit changes it.
- ``title`` is the frontmatter ``title``, else the first ``# H1`` outside
  code fences, else the filename stem.
- ``content`` is the full raw file text, frontmatter included (the region
  parser separates it).
- Documents are emitted sorted by ``id``; a duplicate id raises
  ``ContractError`` from :class:`~linkdiscovery.contracts.documents.Corpus`.

Relationships are extracted from each document body (never from
frontmatter; the ``sources`` key is intentionally ignored): wikilinks and
internal Markdown links, excluding anything inside fenced code blocks.
Wikilink targets resolve relative to ``root``; Markdown link targets
resolve relative to the linking document's directory first, then to
``root``; both try the target exactly and with ``.md``, case-sensitively.
Resolved links become ``kind="explicit-link"`` with the display text in
``metadata["anchor_text"]`` (and the stripped ``#anchor`` in
``metadata["anchor"]``); unresolved targets become
``kind="unresolved-link"`` with ``metadata["raw_target"]`` --- reported,
never silently dropped, never a crash (SPEC failure handling). Excluded
and archived documents still contribute relationships; the candidate
policy decides what to do with them.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from linkdiscovery.config import SourceConfig
from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.documents import (
    SCHEMA_VERSION,
    Corpus,
    DocumentFlags,
    Relationship,
    RelationshipSet,
    SourceDocument,
)
from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ConfigError, ContractError
from linkdiscovery.fingerprint import fingerprint, fingerprint_bytes
from linkdiscovery_markdown._syntax import (
    Frontmatter,
    clean_heading,
    fenced_code_spans,
    humanize_target,
    iter_links,
    mask_spans,
    split_frontmatter,
)

__all__ = ["MarkdownSourceAdapter"]

PRODUCER_VERSION = "linkdiscovery-markdown/0.1.0"
"""Producer version recorded in every corpus header this adapter writes."""

_GENERATED_PREFIX_BYTES = 500
_OPTIONS_LOCATION = "source.options"
_ALLOWED_OPTIONS = frozenset(
    {
        "root",
        "include",
        "exclude",
        "exclude_flags",
        "archived_flags",
        "generated_marker",
        "metadata_keys",
        "language",
        "run_id",
    }
)
_H1_RE = re.compile(r"^ {0,3}#[ \t]+(.+)$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class _Options:
    """Validated adapter options with every default resolved."""

    root: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    exclude_flags: dict[str, Any]
    archived_flags: dict[str, Any]
    generated_marker: str
    metadata_keys: tuple[str, ...]
    language: str
    run_id: str


class MarkdownSourceAdapter:
    """Loads a Markdown knowledge base into the generic corpus contracts.

    Zero-arg constructible so it can be instantiated from the plugin spec
    ``linkdiscovery_markdown.adapter:MarkdownSourceAdapter``. See the module
    docstring for the full option and contract reference.
    """

    def load(self, config: SourceConfig) -> Corpus:
        """Discover documents and relationships, returning a frozen corpus.

        Output is deterministic for a fixed directory state and options:
        documents are sorted by id and relationships follow document order,
        then in-document offset order.
        """
        options = _parse_options(config.options)
        root = Path(options.root)
        if not root.is_dir():
            raise ConfigError(
                f"{_OPTIONS_LOCATION}.root: {str(root)!r} is not a directory "
                f"(resolved to {root.resolve()})"
            )
        rel_paths = _discover(root, options)
        ids = frozenset(_path_to_id(rel_path) for rel_path in rel_paths)
        documents: list[SourceDocument] = []
        relationships: list[Relationship] = []
        for rel_path in sorted(rel_paths, key=_path_to_id):
            document, document_relationships = _load_document(root, rel_path, ids, options)
            documents.append(document)
            relationships.extend(document_relationships)
        corpus_id = fingerprint([[document.id, document.revision] for document in documents])
        header = ArtifactHeader(
            schema_version=SCHEMA_VERSION,
            run_id=options.run_id,
            corpus_id=corpus_id,
            created_at=utc_now_iso(),
            config_fingerprint=config.fingerprint(),
            producer_version=PRODUCER_VERSION,
        )
        return Corpus(
            header=header,
            documents=tuple(documents),
            relationships=RelationshipSet(relationships=tuple(relationships)),
        )


def _parse_options(options: Mapping[str, Any]) -> _Options:
    """Strictly validate ``SourceConfig.options``; unknown keys are errors."""
    unknown = sorted(set(options) - _ALLOWED_OPTIONS)
    if unknown:
        names = ", ".join(f"'{name}'" for name in unknown)
        expected = ", ".join(sorted(_ALLOWED_OPTIONS))
        raise ConfigError(
            f"{_OPTIONS_LOCATION}: unknown option{'s' if len(unknown) > 1 else ''} {names}; "
            f"expected only: {expected}"
        )
    if "root" not in options:
        raise ConfigError(f"{_OPTIONS_LOCATION}: missing required option 'root'")
    include = _opt_str_list(options, "include", ["**/*.md"])
    if not include:
        raise ConfigError(f"{_OPTIONS_LOCATION}: option 'include' must not be empty")
    return _Options(
        root=_opt_str(options, "root", ""),
        include=include,
        exclude=_opt_str_list(options, "exclude", []),
        exclude_flags=_opt_flag_map(options, "exclude_flags", {"draft": True, "private": True}),
        archived_flags=_opt_flag_map(
            options, "archived_flags", {"archived": True, "status": "archived"}
        ),
        generated_marker=_opt_str(options, "generated_marker", "<!-- generated -->"),
        metadata_keys=_opt_str_list(
            options, "metadata_keys", ["description", "category", "tags", "date"]
        ),
        language=_opt_str(options, "language", "en"),
        run_id=_opt_str(options, "run_id", "adhoc"),
    )


def _opt_str(options: Mapping[str, Any], name: str, default: str) -> str:
    value = options.get(name, default)
    if not isinstance(value, str) or not value:
        raise ConfigError(
            f"{_OPTIONS_LOCATION}: option '{name}' must be a non-empty string, got {value!r}"
        )
    return value


def _opt_str_list(options: Mapping[str, Any], name: str, default: list[str]) -> tuple[str, ...]:
    value = options.get(name, default)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ConfigError(
            f"{_OPTIONS_LOCATION}: option '{name}' must be a list of non-empty strings, "
            f"got {value!r}"
        )
    return tuple(value)


def _opt_flag_map(options: Mapping[str, Any], name: str, default: dict[str, Any]) -> dict[str, Any]:
    value = options.get(name, default)
    if not isinstance(value, dict):
        raise ConfigError(
            f"{_OPTIONS_LOCATION}: option '{name}' must be a mapping of frontmatter key to "
            f"expected value, got {type(value).__name__}"
        )
    for key, expected in value.items():
        if not isinstance(key, str) or not key:
            raise ConfigError(
                f"{_OPTIONS_LOCATION}: option '{name}' keys must be non-empty strings, got {key!r}"
            )
        if not isinstance(expected, bool | int | float | str):
            raise ConfigError(
                f"{_OPTIONS_LOCATION}: option '{name}[{key!r}]' must be a scalar "
                f"(string, number, or boolean), got {type(expected).__name__}"
            )
    return dict(value)


def _glob_regex(pattern: str) -> re.Pattern[str]:
    """Translate a glob pattern to a regex over POSIX relative paths.

    Implemented locally (rather than ``pathlib.match``/``fnmatch``) so
    ``**`` semantics are identical on every supported Python version:
    ``**/`` matches zero or more whole directories, ``**`` matches any
    run of characters including ``/``, ``*`` and ``?`` stay within one
    path segment.
    """
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if pattern[index : index + 3] == "**/":
                parts.append("(?:[^/]+/)*")
                index += 3
            elif pattern[index : index + 2] == "**":
                parts.append(".*")
                index += 2
            else:
                parts.append("[^/]*")
                index += 1
        elif char == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(char))
            index += 1
    return re.compile("".join(parts) + r"\Z")


def _discover(root: Path, options: _Options) -> list[str]:
    """Return sorted POSIX relative paths matching include and not exclude."""
    include = [_glob_regex(pattern) for pattern in options.include]
    exclude = [_glob_regex(pattern) for pattern in options.exclude]
    results: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root).as_posix()
        if not any(regex.match(rel_path) for regex in include):
            continue
        if any(regex.match(rel_path) for regex in exclude):
            continue
        results.append(rel_path)
    return results


def _path_to_id(rel_path: str) -> str:
    """POSIX relative path without ``.md``: the document id and wikilink target."""
    return rel_path[:-3] if rel_path.endswith(".md") else rel_path


def _load_document(
    root: Path, rel_path: str, ids: frozenset[str], options: _Options
) -> tuple[SourceDocument, list[Relationship]]:
    """Build one document plus its body relationships from the file at ``rel_path``."""
    raw = (root / rel_path).read_bytes()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"source file {rel_path!r} is not valid UTF-8: {exc}") from exc
    frontmatter = split_frontmatter(content)
    mapping = frontmatter.mapping if frontmatter is not None else {}
    masked = _mask_non_body(content, frontmatter)
    document_id = _path_to_id(rel_path)
    document = SourceDocument(
        id=document_id,
        revision=fingerprint_bytes(raw),
        media_type="text/markdown",
        content=content,
        title=_document_title(mapping, masked, rel_path),
        language=options.language,
        source_ref=rel_path,
        metadata=_document_metadata(mapping, options.metadata_keys),
        flags=DocumentFlags(
            excluded=_matches_flags(mapping, options.exclude_flags),
            generated=_is_generated(raw, mapping, options.generated_marker),
            archived=_matches_flags(mapping, options.archived_flags),
        ),
    )
    return document, _extract_relationships(document_id, rel_path, masked, ids)


def _mask_non_body(content: str, frontmatter: Frontmatter | None) -> str:
    """Mask frontmatter and fenced code so neither yields links or titles."""
    spans = fenced_code_spans(content)
    if frontmatter is not None:
        spans = [frontmatter.span, *spans]
    return mask_spans(content, spans)


def _document_title(mapping: dict[str, Any], masked: str, rel_path: str) -> str:
    """Frontmatter ``title``, else the first H1 outside code fences, else the stem."""
    raw_title = mapping.get("title")
    if raw_title is not None and str(raw_title).strip():
        return str(raw_title).strip()
    match = _H1_RE.search(masked)
    if match is not None:
        heading = clean_heading(match.group(1))
        if heading:
            return heading
    return Path(rel_path).stem


def _coerce_metadata_value(value: Any) -> str | list[str]:
    """Coerce a frontmatter value to ``str`` or ``list[str]`` for metadata."""
    if isinstance(value, list):
        return [str(item) for item in value]
    return str(value)


def _document_metadata(mapping: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Copy configured frontmatter keys (plus ``aliases``) into document metadata."""
    metadata: dict[str, Any] = {}
    for key in keys:
        if key in mapping and mapping[key] is not None:
            metadata[key] = _coerce_metadata_value(mapping[key])
    aliases = mapping.get("aliases")
    if aliases is not None:
        metadata["aliases"] = (
            [str(item) for item in aliases] if isinstance(aliases, list) else [str(aliases)]
        )
    return metadata


def _matches_flags(mapping: dict[str, Any], flags: dict[str, Any]) -> bool:
    """True when any configured frontmatter key equals its expected value."""
    return any(key in mapping and mapping[key] == expected for key, expected in flags.items())


def _is_generated(raw: bytes, mapping: dict[str, Any], marker: str) -> bool:
    """Generated: marker in the first 500 raw bytes, or frontmatter ``generated: true``."""
    if mapping.get("generated") is True:
        return True
    return marker.encode("utf-8").lower() in raw[:_GENERATED_PREFIX_BYTES].lower()


def _resolve_target(
    path: str, source_id: str, source_dir: str, ids: frozenset[str], doc_relative: bool
) -> str | None:
    """Resolve a link target path to a known document id, or ``None``.

    A pure-anchor target (empty path) is a self link. Targets are tried
    with the ``.md`` extension stripped ("exact, then with ``.md``" over
    ids that themselves strip ``.md``), case-sensitively. Markdown links
    additionally try the linking document's directory before the root.
    """
    if not path:
        return source_id
    normalized = path.lstrip("/")
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    candidates: list[str] = []
    if doc_relative and source_dir:
        candidates.append(posixpath.normpath(posixpath.join(source_dir, normalized)))
    candidates.append(posixpath.normpath(normalized))
    for candidate in candidates:
        if candidate in ids:
            return candidate
    return None


def _extract_relationships(
    document_id: str, rel_path: str, masked: str, ids: frozenset[str]
) -> list[Relationship]:
    """Extract explicit-link / unresolved-link relationships from one body."""
    source_dir = posixpath.dirname(rel_path)
    relationships: list[Relationship] = []
    for link in iter_links(masked):
        span = Span(start=link.start, end=link.end)
        resolved = _resolve_target(
            link.path, document_id, source_dir, ids, doc_relative=link.kind == "markdown"
        )
        if resolved is None:
            relationships.append(
                Relationship(
                    source_id=document_id,
                    target_id=link.path,
                    kind="unresolved-link",
                    directed=True,
                    source_span=span,
                    metadata={"raw_target": link.target},
                )
            )
            continue
        anchor_text = link.text or (humanize_target(link.target) if link.kind == "wikilink" else "")
        metadata: dict[str, Any] = {"anchor_text": anchor_text}
        if link.anchor:
            metadata["anchor"] = link.anchor
        relationships.append(
            Relationship(
                source_id=document_id,
                target_id=resolved,
                kind="explicit-link",
                directed=True,
                source_span=span,
                metadata=metadata,
            )
        )
    return relationships
