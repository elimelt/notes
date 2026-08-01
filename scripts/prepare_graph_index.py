#!/usr/bin/env python3
"""Keep folder indexes in Quartz graph data and connect the content hierarchy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def is_tag_page(slug: str) -> bool:
    return slug == "tags" or slug.startswith("tags/")


def logical_path(slug: str) -> str:
    if slug == "index":
        return ""
    if slug.endswith("/index"):
        return slug[: -len("/index")]
    return slug


def nearest_parent_index(slug: str, available: set[str]) -> str | None:
    path = logical_path(slug)
    if not path:
        return None

    parent_parts = path.split("/")[:-1]
    while True:
        candidate = "/".join([*parent_parts, "index"]) if parent_parts else "index"
        if candidate in available and candidate != slug:
            return candidate
        if not parent_parts:
            return None
        parent_parts.pop()


def prepare_index(index: dict[str, dict[str, object]]) -> tuple[int, int]:
    tag_pages = {slug for slug in index if is_tag_page(slug)}
    for slug in tag_pages:
        del index[slug]

    available = set(index)
    added_edges = 0
    for slug in sorted(available):
        parent = nearest_parent_index(slug, available)
        if parent is None:
            continue
        details = index[parent]
        links = details.setdefault("links", [])
        if not isinstance(links, list):
            links = []
            details["links"] = links
        if slug not in links:
            links.append(slug)
            added_edges += 1

    for details in index.values():
        links = details.get("links", [])
        if isinstance(links, list):
            details["links"] = [link for link in links if not is_tag_page(str(link))]

    return len(tag_pages), added_edges


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    args = parser.parse_args()

    with args.index.open(encoding="utf-8") as handle:
        index = json.load(handle)

    removed_tags, added_edges = prepare_index(index)
    args.index.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    print(
        f"Prepared graph index: removed {removed_tags} generated tag pages; "
        f"added {added_edges} hierarchy edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
