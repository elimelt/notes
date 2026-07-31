#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
TITLE_RE = re.compile(r"(?m)^title\s*:")
ARCHIVE_RE = re.compile(r"(?mi)^archive\s*:\s*(?:true|\"true\"|'true')\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply publication-only content rules.")
    parser.add_argument("content_dir", type=Path)
    return parser.parse_args()


def prepare(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return True
    frontmatter = match.group(1)
    if ARCHIVE_RE.search(frontmatter):
        path.unlink()
        path.with_suffix(".ipynb").unlink(missing_ok=True)
        return False
    if TITLE_RE.search(frontmatter):
        body_start = match.end()
        body = text[body_start:]
        lines = body.splitlines(keepends=True)
        fence: str | None = None
        for index, line in enumerate(lines):
            stripped = line.lstrip()
            marker = stripped[:3]
            if marker in {"```", "~~~"}:
                fence = None if fence == marker else marker if fence is None else fence
                continue
            if fence is None and line.startswith("# "):
                del lines[index]
                break
        body = "".join(lines).lstrip("\n")
        updated = text[:body_start] + body
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    kept = 0
    archived = 0
    for path in sorted(args.content_dir.rglob("*.md")):
        if prepare(path):
            kept += 1
        else:
            archived += 1
    print(f"Prepared {kept} pages; excluded {archived} archived pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
