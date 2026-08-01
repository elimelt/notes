#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import copy
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = ROOT / "content"
GENERATED_MARKER = "<!-- Generated from "


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Quartz wrappers and cache entries for Jupyter notebooks."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Notebook files or directories to scan. Defaults to content/.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Seed quartz-jupyter-embed's cache at this path.",
    )
    parser.add_argument(
        "--source-base-url",
        default="https://github.com/elimelt/notes/blob/main",
        help="Public repository URL used by generated notebook links.",
    )
    return parser.parse_args()


def iter_notebooks(paths: list[str]) -> list[Path]:
    roots = paths or [str(CONTENT_ROOT)]
    notebooks: list[Path] = []
    for raw in roots:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        path = path.resolve()
        if path.is_file() and path.suffix == ".ipynb":
            notebooks.append(path)
        elif path.is_dir():
            notebooks.extend(sorted(path.rglob("*.ipynb")))
    return sorted(set(notebooks))


def join_source(source: object) -> str:
    if isinstance(source, str):
        return source
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return ""


def git_date(path: Path) -> str:
    rel = path.relative_to(ROOT)
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", str(rel)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def humanize_segment(segment: str) -> str:
    pieces = re.split(r"[-_\s]+", segment.strip())
    return " ".join(
        piece.upper() if piece.isalpha() and len(piece) <= 4 else piece.capitalize()
        for piece in pieces
        if piece
    )


def default_frontmatter(notebook_path: Path) -> dict[str, object]:
    rel = notebook_path.relative_to(CONTENT_ROOT)
    return {
        "title": humanize_segment(notebook_path.stem),
        "category": humanize_segment(rel.parent.name or rel.stem),
        "tags": ["notebook", "python", "jupyter"],
        "date": git_date(notebook_path),
        "description": f"Executable notebook for {humanize_segment(notebook_path.stem)}.",
        "sources": [rel.as_posix()],
    }


def parse_simple_frontmatter(raw: str) -> dict[str, object]:
    lines = raw.splitlines()
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


def extract_cell_frontmatter(cell_source: str) -> tuple[dict[str, object], str]:
    lines = cell_source.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, cell_source
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return parse_simple_frontmatter("\n".join(lines[1:idx])), "\n".join(lines[idx + 1 :]).lstrip()
    return {}, cell_source


def notebook_frontmatter(
    notebook: dict[str, object], notebook_path: Path
) -> tuple[dict[str, object], str | None]:
    metadata = notebook.get("metadata", {})
    custom: dict[str, object] = {}
    if isinstance(metadata, dict):
        direct = metadata.get("frontmatter")
        if isinstance(direct, dict):
            custom.update(direct)
        quartz = metadata.get("quartz")
        if isinstance(quartz, dict) and isinstance(quartz.get("frontmatter"), dict):
            custom.update(quartz["frontmatter"])

    remainder: str | None = None
    cells = notebook.get("cells", [])
    if isinstance(cells, list) and cells and isinstance(cells[0], dict):
        first = cells[0]
        if first.get("cell_type") == "markdown":
            parsed, parsed_remainder = extract_cell_frontmatter(join_source(first.get("source", [])))
            if parsed:
                custom.update(parsed)
                remainder = parsed_remainder

    merged = default_frontmatter(notebook_path)
    merged.update(custom)
    return merged, remainder


def yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    text = str(value)
    if text == "" or any(ch in text for ch in ":#[]{}&*!|>'\"%@`"):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def dump_frontmatter(data: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {yaml_scalar(item)}" for item in value)
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def ensure_generated_target(target: Path) -> None:
    if target.exists() and GENERATED_MARKER not in target.read_text(encoding="utf-8"):
        raise RuntimeError(f"Refusing to overwrite non-generated file: {target.relative_to(ROOT)}")


def write_if_changed(path: Path, content: str) -> None:
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def source_url(base_url: str, notebook_path: Path) -> str:
    rel = notebook_path.relative_to(ROOT).as_posix()
    return f"{base_url.rstrip('/')}/{quote(rel, safe='/')}"


def asset_url(notebook_path: Path) -> str:
    rel = notebook_path.relative_to(CONTENT_ROOT).as_posix()
    return f"/{quote(rel, safe='/')}"


def frontmatter_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return default


def notebook_without_frontmatter(
    notebook: dict[str, object], first_cell_remainder: str | None
) -> dict[str, object]:
    rendered = copy.deepcopy(notebook)
    cells = rendered.get("cells", [])
    if not isinstance(cells, list):
        return rendered
    if first_cell_remainder and cells:
        first = cells[0]
        if isinstance(first, dict):
            first["source"] = [line + "\n" for line in first_cell_remainder.splitlines()]
    elif first_cell_remainder == "" and cells:
        rendered["cells"] = cells[1:]
    for cell in rendered.get("cells", []):
        if isinstance(cell, dict) and cell.get("cell_type") == "markdown":
            source = cell.get("source", [])
            if isinstance(source, list):
                cell["source"] = [str(part).replace("\\\\", "\\") for part in source]
            elif isinstance(source, str):
                cell["source"] = source.replace("\\\\", "\\")
    return rendered


def cache_path(cache_dir: Path, url: str) -> Path:
    key = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    return cache_dir / f"{key}.json"


def render_notebook(path: Path, args: argparse.Namespace) -> None:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    frontmatter, remainder = notebook_frontmatter(notebook, path)
    url = source_url(args.source_base_url, path)
    target = path.with_suffix(".md")
    publish_page = frontmatter_bool(frontmatter.pop("notebook_page", True), True)
    if publish_page:
        ensure_generated_target(target)
        wrapper = (
            f"{dump_frontmatter(frontmatter)}\n\n"
            f"{GENERATED_MARKER}{path.relative_to(ROOT).as_posix()}; do not edit. -->\n\n"
            f"[Open notebook source]({url})\n"
        )
        write_if_changed(target, wrapper)
    elif target.exists() and GENERATED_MARKER in target.read_text(encoding="utf-8"):
        target.unlink()

    archived = frontmatter.get("archive") is True or str(frontmatter.get("archive", "")).lower() == "true"
    if args.cache_dir and not archived:
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        cached = notebook_without_frontmatter(notebook, remainder)
        payload = json.dumps(cached, separators=(",", ":"))
        for cache_url in (url, asset_url(path)):
            write_if_changed(cache_path(args.cache_dir, cache_url), payload)


def main() -> int:
    args = parse_args()
    if args.cache_dir and args.cache_dir.exists():
        for cached_notebook in args.cache_dir.glob("*.json"):
            cached_notebook.unlink()
    notebooks = iter_notebooks(args.paths)
    for notebook in notebooks:
        render_notebook(notebook, args)
    print(f"Prepared {len(notebooks)} notebook(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
