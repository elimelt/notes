#!/usr/bin/env python3
"""Reject generated taxonomy pages in the graph's content index."""

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

    print(f"Validated graph index: {len(index)} authored pages, no generated tag nodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
