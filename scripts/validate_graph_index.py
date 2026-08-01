#!/usr/bin/env python3
"""Validate the graph's prepared content hierarchy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    args = parser.parse_args()

    with args.index.open(encoding="utf-8") as handle:
        index = json.load(handle)

    declared_tags: dict[str, set[str]] = {}
    for slug, details in index.items():
        if slug.startswith("tags/"):
            continue
        tags = details.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str) and tag:
                    declared_tags.setdefault(tag, set()).add(slug)

    tag_pages = {slug for slug in index if slug.startswith("tags/")}
    expected_tag_pages = {f"tags/{tag}" for tag in declared_tags}
    unexpected_tags = sorted(tag_pages ^ expected_tag_pages)
    if unexpected_tags or "tags" in index:
        preview = ", ".join(unexpected_tags[:5])
        raise SystemExit(
            f"Graph index tag pages do not match declared tags: {preview}"
        )

    invalid_tag_pages = []
    for tag, expected_notes in declared_tags.items():
        links = index[f"tags/{tag}"].get("links", [])
        actual_notes = set(links) if isinstance(links, list) else set()
        if actual_notes != expected_notes:
            invalid_tag_pages.append(tag)
    if invalid_tag_pages:
        preview = ", ".join(sorted(invalid_tag_pages)[:5])
        raise SystemExit(f"Graph index contains invalid tag edges: {preview}")

    empty_indexes = sorted(
        slug
        for slug, details in index.items()
        if (slug == "index" or slug.endswith("/index"))
        and not details.get("content")
        and not details.get("links")
    )
    if empty_indexes:
        preview = ", ".join(empty_indexes[:5])
        raise SystemExit(
            f"Graph index contains {len(empty_indexes)} unconnected folder pages: {preview}"
        )

    print(
        f"Validated graph index: {len(index)} pages, "
        f"{len(tag_pages)} tags connected to their notes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
