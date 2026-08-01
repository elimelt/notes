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

    tag_pages = sorted(slug for slug in index if slug == "tags" or slug.startswith("tags/"))
    if tag_pages:
        preview = ", ".join(tag_pages[:5])
        raise SystemExit(
            f"Graph index contains {len(tag_pages)} generated tag pages: {preview}"
        )

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

    print(f"Validated graph index: {len(index)} content and folder pages, no tag nodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
