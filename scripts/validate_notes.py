#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FIELDS = ("title", "category", "tags", "date")
CONTENT_ROOT = ROOT / "content"
SPECIAL_CASES = {CONTENT_ROOT / "index.md"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate note frontmatter and rendering basics.")
    parser.add_argument("paths", nargs="*", help="Paths to scan")
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Validate tracked and untracked Markdown files changed from HEAD",
    )
    return parser.parse_args()


def iter_markdown_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = (ROOT / raw).resolve()
        if path.is_file() and path.suffix == ".md":
            if CONTENT_ROOT not in path.parents and path != CONTENT_ROOT:
                continue
            files.append(path)
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*.md")):
                if "content/templates" in candidate.as_posix():
                    continue
                if CONTENT_ROOT not in candidate.parents and candidate != CONTENT_ROOT:
                    continue
                files.append(candidate)
    return sorted(set(files))


def git_changed_markdown_files() -> list[Path]:
    commands = [
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    files: list[Path] = []
    for command in commands:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            if not line.endswith(".md"):
                continue
            path = (ROOT / line).resolve()
            if (
                path.exists()
                and "content/templates" not in path.as_posix()
                and (CONTENT_ROOT in path.parents or path == CONTENT_ROOT / "index.md")
            ):
                files.append(path)
    return sorted(set(files))


def split_frontmatter(text: str) -> tuple[list[str] | None, list[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return lines[1:idx], lines[idx + 1 :]
    return None, lines


def parse_frontmatter(lines: list[str]) -> dict[str, object]:
    data: dict[str, object] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*$", line):
            key = line.split(":", 1)[0].strip()
            values: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  - ") or not lines[i].strip()):
                if lines[i].startswith("  - "):
                    values.append(lines[i][4:].strip())
                i += 1
            data[key] = values
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
        i += 1
    return data


def validate_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    frontmatter_lines, body_lines = split_frontmatter(text)
    rel = path.relative_to(ROOT)

    if frontmatter_lines is None:
        return [f"{rel}: missing YAML frontmatter"]

    frontmatter = parse_frontmatter(frontmatter_lines)
    special_case = path in SPECIAL_CASES

    required_fields = ("title",) if special_case else REQUIRED_FIELDS
    for field in required_fields:
        if field not in frontmatter or frontmatter[field] in ("", []):
            errors.append(f"{rel}: missing required frontmatter field `{field}`")

    if not special_case:
        tags = frontmatter.get("tags")
        if not isinstance(tags, list):
            errors.append(f"{rel}: `tags` must be a YAML list")

        date = frontmatter.get("date", "")
        if isinstance(date, str) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            errors.append(f"{rel}: `date` must use YYYY-MM-DD")

    fence_count = sum(1 for line in body_lines if line.strip().startswith("```"))
    if fence_count % 2 != 0:
        errors.append(f"{rel}: unbalanced fenced code blocks")

    if not special_case:
        for idx, line in enumerate(body_lines, start=1):
            if line.startswith("# "):
                errors.append(f"{rel}:{idx}: do not use in-body H1 headings")
                break

    if not special_case and "sources" not in frontmatter:
        errors.append(f"{rel}: missing recommended frontmatter field `sources`")

    return errors


def main() -> int:
    args = parse_args()
    if args.changed:
        files = git_changed_markdown_files()
    else:
        files = iter_markdown_files(args.paths or ["content"])

    if not files:
        print("No Markdown files to validate.")
        return 0

    errors: list[str] = []
    for path in files:
        errors.extend(validate_file(path))

    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"Validated {len(files)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
