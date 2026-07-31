#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "content" / "templates"

TEMPLATES = {
    "concept": TEMPLATE_DIR / "concept-note.md",
    "paper": TEMPLATE_DIR / "paper-note.md",
    "benchmark": TEMPLATE_DIR / "benchmark-note.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a note from a template.")
    parser.add_argument("path", help="Path relative to repo root, usually under content/")
    parser.add_argument(
        "--template",
        choices=sorted(TEMPLATES),
        default="concept",
        help="Template to use",
    )
    parser.add_argument("--title", required=True, help="Frontmatter title")
    parser.add_argument("--category", required=True, help="Frontmatter category")
    parser.add_argument(
        "--tags",
        nargs="*",
        default=[],
        help="Zero or more tags. Example: --tags systems caching benchmarks",
    )
    parser.add_argument(
        "--description",
        default="Replace with a scoped description.",
        help="Frontmatter description",
    )
    parser.add_argument(
        "--status",
        default="draft",
        help="Frontmatter status",
    )
    return parser.parse_args()


def render(template_text: str, *, title: str, category: str, tags: list[str], description: str, status: str) -> str:
    date = dt.date.today().isoformat()
    tag_block = "\n".join(f"  - {tag}" for tag in tags) if tags else "  - replace-me"
    rendered = template_text
    rendered = rendered.replace("Replace with title", title)
    rendered = rendered.replace("Replace with paper title", title)
    rendered = rendered.replace("Replace with benchmark title", title)
    rendered = rendered.replace("Replace with category", category)
    rendered = rendered.replace("date: 2026-07-31", f"date: {date}")
    rendered = rendered.replace("status: draft", f"status: {status}")
    rendered = rendered.replace(
        "description: State what this note explains and where it stops.",
        f"description: {description}",
    )
    rendered = rendered.replace(
        "description: State what this paper tried to solve and what this note extracts from it.",
        f"description: {description}",
    )
    rendered = rendered.replace(
        "description: State what was measured, under what setup, and why it matters.",
        f"description: {description}",
    )
    rendered = rendered.replace("tags:\n  - replace-me", f"tags:\n{tag_block}")
    rendered = rendered.replace("category: Systems Research", f"category: {category}")
    rendered = rendered.replace("category: Performance Engineering", f"category: {category}")
    return rendered


def main() -> int:
    args = parse_args()
    target = (ROOT / args.path).resolve()
    if ROOT not in target.parents and target != ROOT:
      raise SystemExit("Target path must stay inside the repository.")

    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {target}")

    template_path = TEMPLATES[args.template]
    template_text = template_path.read_text(encoding="utf-8")
    rendered = render(
        template_text,
        title=args.title,
        category=args.category,
        tags=args.tags,
        description=args.description,
        status=args.status,
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
