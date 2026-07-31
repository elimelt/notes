#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import validate_notes as vn


ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = ROOT / "content"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit note categories and tags for sparsity and normalization drift."
    )
    parser.add_argument(
        "--category-threshold",
        type=int,
        default=5,
        help="Report categories with fewer than this many entries.",
    )
    parser.add_argument(
        "--tag-threshold",
        type=int,
        default=2,
        help="Report tags with fewer than this many entries.",
    )
    parser.add_argument(
        "--include-index",
        action="store_true",
        help="Include hub pages such as */index.md in counts.",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include notes with archive: true in counts.",
    )
    parser.add_argument(
        "--suggest-tag-propagation",
        action="store_true",
        help="For sparse tags, suggest notes whose text likely covers the concept but lacks the tag.",
    )
    parser.add_argument(
        "--max-propagation-suggestions",
        type=int,
        default=50,
        help="Maximum number of sparse tags to print propagation suggestions for.",
    )
    return parser.parse_args()


def is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


def iter_note_files() -> Iterable[Path]:
    for path in sorted(CONTENT_ROOT.rglob("*.md")):
        text_path = path.as_posix()
        if "content/templates" in text_path:
            continue
        yield path


def load_frontmatter(path: Path) -> dict[str, object] | None:
    frontmatter_lines, _ = vn.split_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter_lines is None:
        return None
    return vn.parse_frontmatter(frontmatter_lines)


def normalized_tag(tag: str) -> str:
    return " ".join(tag.lower().replace("-", " ").split())


def build_tag_pattern(tag: str) -> re.Pattern[str] | None:
    tokens = [re.escape(token) for token in normalized_tag(tag).split()]
    if not tokens:
        return None
    if len(tokens) == 1:
        return re.compile(rf"(?<![a-z0-9]){tokens[0]}(?![a-z0-9])", re.IGNORECASE)
    joined = r"[-\s]+".join(tokens)
    return re.compile(rf"(?<![a-z0-9]){joined}(?![a-z0-9])", re.IGNORECASE)


def main() -> int:
    args = parse_args()

    category_counts: Counter[str] = Counter()
    category_files: defaultdict[str, list[Path]] = defaultdict(list)
    tag_counts: Counter[str] = Counter()
    tag_files: defaultdict[str, list[Path]] = defaultdict(list)
    variant_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    variant_files: defaultdict[str, defaultdict[str, list[Path]]] = defaultdict(
        lambda: defaultdict(list)
    )
    scanned = 0
    note_texts: dict[Path, str] = {}
    note_norm_tags: dict[Path, set[str]] = {}

    for path in iter_note_files():
        data = load_frontmatter(path)
        if data is None:
            continue
        if not args.include_archived and is_truthy(data.get("archive")):
            continue
        if not args.include_index and path.name == "index.md":
            continue

        scanned += 1
        text = path.read_text(encoding="utf-8")
        note_texts[path] = text
        category = data.get("category")
        if isinstance(category, str) and category:
            category_counts[category] += 1
            category_files[category].append(path)

        tags = data.get("tags")
        if not isinstance(tags, list):
            continue
        note_norm_tags[path] = set()
        for raw_tag in tags:
            if not isinstance(raw_tag, str) or not raw_tag.strip():
                continue
            tag_counts[raw_tag] += 1
            tag_files[raw_tag].append(path)
            norm = normalized_tag(raw_tag)
            note_norm_tags[path].add(norm)
            variant_counts[norm][raw_tag] += 1
            variant_files[norm][raw_tag].append(path)

    print(f"Scanned {scanned} active notes.")
    print()
    print("Category counts")
    for category, count in category_counts.most_common():
        print(f"  {count:>3}  {category}")

    sparse_categories = [
        (category, count)
        for category, count in category_counts.items()
        if count < args.category_threshold
    ]
    print()
    print(f"Categories below threshold (< {args.category_threshold})")
    if not sparse_categories:
        print("  none")
    else:
        for category, count in sorted(sparse_categories, key=lambda item: (item[1], item[0])):
            files = ", ".join(path.relative_to(ROOT).as_posix() for path in category_files[category])
            print(f"  {count:>3}  {category}: {files}")

    print()
    print("Top tags")
    for tag, count in tag_counts.most_common(20):
        print(f"  {count:>3}  {tag}")

    sparse_tags = [
        (tag, count)
        for tag, count in tag_counts.items()
        if count < args.tag_threshold
    ]
    print()
    print(f"Tags below threshold (< {args.tag_threshold})")
    if not sparse_tags:
        print("  none")
    else:
        for tag, count in sorted(sparse_tags, key=lambda item: (item[1], item[0]))[:50]:
            files = ", ".join(path.relative_to(ROOT).as_posix() for path in tag_files[tag])
            print(f"  {count:>3}  {tag}: {files}")
        if len(sparse_tags) > 50:
            print(f"  ... {len(sparse_tags) - 50} more")

    collisions = []
    for norm, variants in variant_counts.items():
        if len(variants) <= 1:
            continue
        collisions.append((norm, sum(variants.values()), variants))

    print()
    print("Tag normalization collisions")
    if not collisions:
        print("  none")
    else:
        for norm, total, variants in sorted(collisions, key=lambda item: (-item[1], item[0])):
            details = []
            for variant, count in variants.most_common():
                files = ", ".join(
                    path.relative_to(ROOT).as_posix()
                    for path in variant_files[norm][variant]
                )
                details.append(f"{variant} ({count}): {files}")
            print(f"  {norm} [{total}]")
            for detail in details:
                print(f"    - {detail}")

    if args.suggest_tag_propagation:
        suggestions: list[tuple[str, list[Path]]] = []
        for tag, count in sorted(sparse_tags, key=lambda item: (item[1], item[0])):
            pattern = build_tag_pattern(tag)
            if pattern is None:
                continue
            norm = normalized_tag(tag)
            candidates: list[Path] = []
            for path, text in note_texts.items():
                if norm in note_norm_tags.get(path, set()):
                    continue
                if pattern.search(text):
                    candidates.append(path)
            if candidates:
                suggestions.append((tag, candidates))

        print()
        print("Sparse tag propagation suggestions")
        if not suggestions:
            print("  none")
        else:
            for tag, candidates in suggestions[: args.max_propagation_suggestions]:
                candidate_list = ", ".join(
                    path.relative_to(ROOT).as_posix() for path in candidates[:8]
                )
                if len(candidates) > 8:
                    candidate_list += f", ... {len(candidates) - 8} more"
                print(f"  {tag}: {candidate_list}")
            if len(suggestions) > args.max_propagation_suggestions:
                print(
                    "  "
                    f"... {len(suggestions) - args.max_propagation_suggestions} more sparse tags "
                    "with propagation candidates"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
