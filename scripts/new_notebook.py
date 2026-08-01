#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = ROOT / "content"
TEMPLATE_ROOT = ROOT / "notebook-templates"


def available_templates() -> dict[str, Path]:
    return {path.stem: path for path in sorted(TEMPLATE_ROOT.glob("*.ipynb"))}


def parse_args() -> argparse.Namespace:
    templates = available_templates()
    parser = argparse.ArgumentParser(
        description="Scaffold a Jupyter notebook from a tracked template."
    )
    parser.add_argument("path", nargs="?", help="Target .ipynb path under content/")
    parser.add_argument(
        "--template",
        choices=sorted(templates),
        default="experiment",
        help="Notebook template to use",
    )
    parser.add_argument("--list-templates", action="store_true")
    parser.add_argument("--title", help="Notebook title")
    parser.add_argument("--category", help="Broad note category")
    parser.add_argument("--tags", nargs="*", default=[], help="Specific tags")
    parser.add_argument(
        "--sources",
        nargs="*",
        default=[],
        help="Primary source URLs or dataset cards",
    )
    parser.add_argument(
        "--description",
        default="Replace with the question this notebook answers.",
        help="Scoped frontmatter description",
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="Publish a standalone page instead of an embedded-only companion",
    )
    return parser.parse_args()


def replace_placeholders(value: object, replacements: dict[str, str]) -> object:
    if isinstance(value, str):
        for placeholder, replacement in replacements.items():
            value = value.replace(placeholder, replacement)
        return value
    if isinstance(value, list):
        return [replace_placeholders(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: replace_placeholders(item, replacements)
            for key, item in value.items()
        }
    return value


def render_notebook(
    template: dict[str, object],
    *,
    title: str,
    category: str,
    tags: list[str],
    sources: list[str],
    description: str,
    standalone: bool,
) -> dict[str, object]:
    tag_lines = tags or ["replace-me"]
    source_lines = sources or ["replace-with-primary-source"]
    replacements = {
        "{{title}}": json.dumps(title),
        "{{category}}": json.dumps(category),
        "{{date}}": dt.date.today().isoformat(),
        "{{description}}": json.dumps(description),
        "{{tags}}": "\n".join(f"  - {json.dumps(tag)}" for tag in tag_lines),
        "{{sources}}": "\n".join(
            f"  - {json.dumps(source)}" for source in source_lines
        ),
        "{{notebook_page}}": "true" if standalone else "false",
    }
    rendered = replace_placeholders(template, replacements)
    if not isinstance(rendered, dict):
        raise TypeError("Notebook template must be a JSON object")
    return rendered


def validate_target(raw_path: str) -> Path:
    target = (ROOT / raw_path).resolve()
    if target.suffix != ".ipynb":
        raise SystemExit("Target path must end in .ipynb")
    if CONTENT_ROOT not in target.parents:
        raise SystemExit("Target notebook must be under content/")
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {target}")
    return target


def main() -> int:
    args = parse_args()
    templates = available_templates()
    if args.list_templates:
        for name in templates:
            print(name)
        return 0
    if not args.path or not args.title or not args.category:
        raise SystemExit("path, --title, and --category are required")

    target = validate_target(args.path)
    template = json.loads(templates[args.template].read_text(encoding="utf-8"))
    rendered = render_notebook(
        template,
        title=args.title,
        category=args.category,
        tags=args.tags,
        sources=args.sources,
        description=args.description,
        standalone=args.standalone,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(rendered, indent=2) + "\n", encoding="utf-8")
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
