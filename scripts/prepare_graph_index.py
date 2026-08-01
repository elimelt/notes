#!/usr/bin/env python3
"""Connect folder and tag pages in Quartz graph data."""

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


def prepare_index(index: dict[str, dict[str, object]]) -> tuple[int, int, int]:
    tag_members: dict[str, list[str]] = {}
    for slug, details in index.items():
        if is_tag_page(slug):
            continue
        tags = details.get("tags", [])
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if isinstance(tag, str) and tag:
                tag_members.setdefault(tag, []).append(slug)

    wanted_tag_pages = {f"tags/{tag}" for tag in tag_members}
    generated_tag_pages = {slug for slug in index if is_tag_page(slug)}
    discarded_tag_pages = generated_tag_pages - wanted_tag_pages
    for slug in discarded_tag_pages:
        del index[slug]

    # Tag pages are emitted by Quartz with empty links. Point each one at the
    # notes that declare the tag so local and global graphs share the same data.
    tag_edges = 0
    for tag, members in sorted(tag_members.items()):
        tag_slug = f"tags/{tag}"
        if tag_slug not in index:
            continue
        links = sorted(set(members))
        index[tag_slug]["links"] = links
        tag_edges += len(links)

    available = {slug for slug in index if not is_tag_page(slug)}
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

    for slug, details in index.items():
        if is_tag_page(slug):
            continue
        links = details.get("links", [])
        if isinstance(links, list):
            details["links"] = [link for link in links if not is_tag_page(str(link))]

    return len(discarded_tag_pages), added_edges, tag_edges


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    args = parser.parse_args()

    with args.index.open(encoding="utf-8") as handle:
        index = json.load(handle)

    removed_tags, added_edges, tag_edges = prepare_index(index)
    args.index.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    print(
        f"Prepared graph index: removed {removed_tags} synthetic tag pages; "
        f"added {added_edges} hierarchy edges and {tag_edges} tag edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
