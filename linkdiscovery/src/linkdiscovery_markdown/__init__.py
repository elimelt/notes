"""Markdown host adapter and parser for the linkdiscovery pipeline.

This package owns every host-specific concept for a directory-of-Markdown
corpus (Obsidian/Quartz style): YAML frontmatter, wikilinks, standard
Markdown links, path-based document identity, and exclusion/archival flag
conventions. It translates them into the generic ``linkdiscovery``
contracts; the core pipeline gains zero Markdown, Quartz, or filesystem
knowledge from it.

Public API:

- :class:`~linkdiscovery_markdown.adapter.MarkdownSourceAdapter` implements
  ``linkdiscovery.interfaces.SourceAdapter``.
- :class:`~linkdiscovery_markdown.parser.MarkdownRegionParser` implements
  ``linkdiscovery.interfaces.RegionParser``.

Both are zero-arg constructible so they can be loaded from configuration
plugin specs (``linkdiscovery_markdown.adapter:MarkdownSourceAdapter`` and
``linkdiscovery_markdown.parser:MarkdownRegionParser``).
"""

from linkdiscovery_markdown.adapter import MarkdownSourceAdapter
from linkdiscovery_markdown.parser import MarkdownRegionParser

__all__ = ["MarkdownRegionParser", "MarkdownSourceAdapter"]

__version__ = "0.1.0"
