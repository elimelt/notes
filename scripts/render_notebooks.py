#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = ROOT / "content"
GENERATED_MARKER = "<!-- Generated from "
FRONTMATTER_KEYS = ("frontmatter", "quartz")
MIME_IMAGE_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/svg+xml": "svg",
}
TEXT_MIME_PRIORITY = (
    "text/markdown",
    "text/html",
    "text/plain",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Jupyter notebooks in content/ to Markdown for Quartz."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Notebook files or directories to scan. Defaults to content/.",
    )
    return parser.parse_args()


def iter_notebooks(paths: list[str]) -> list[Path]:
    notebooks: list[Path] = []
    for raw in paths:
        path = (ROOT / raw).resolve()
        if path.is_file() and path.suffix == ".ipynb":
            notebooks.append(path)
            continue
        if path.is_dir():
            notebooks.extend(sorted(path.rglob("*.ipynb")))
    return sorted(set(notebooks))


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
    timestamp = path.stat().st_mtime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


def humanize_segment(segment: str) -> str:
    pieces = re.split(r"[-_\s]+", segment.strip())
    words: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if piece.isalpha() and len(piece) <= 4:
            words.append(piece.upper())
            continue
        words.append(piece[:1].upper() + piece[1:])
    return " ".join(words)


def default_frontmatter(notebook_path: Path) -> dict[str, object]:
    rel = notebook_path.relative_to(CONTENT_ROOT)
    parent = rel.parent.name or rel.stem
    return {
        "title": humanize_segment(notebook_path.stem),
        "category": humanize_segment(parent),
        "tags": ["notebook", "python", "jupyter"],
        "date": git_date(notebook_path),
        "description": f"Rendered notebook for {humanize_segment(notebook_path.stem)}.",
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
            raw = "\n".join(lines[1:idx])
            remainder = "\n".join(lines[idx + 1 :]).lstrip("\n")
            return parse_simple_frontmatter(raw), remainder
    return {}, cell_source


def notebook_frontmatter(nb: dict[str, object], notebook_path: Path) -> tuple[dict[str, object], int, str | None]:
    metadata = nb.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    custom: dict[str, object] = {}
    direct = metadata.get("frontmatter")
    if isinstance(direct, dict):
        custom.update(direct)

    quartz = metadata.get("quartz")
    if isinstance(quartz, dict):
        frontmatter = quartz.get("frontmatter")
        if isinstance(frontmatter, dict):
            custom.update(frontmatter)

    first_cell_remainder: str | None = None
    cells = nb.get("cells", [])
    start_index = 0
    if cells:
        first_cell = cells[0]
        if isinstance(first_cell, dict) and first_cell.get("cell_type") == "markdown":
            parsed, remainder = extract_cell_frontmatter(join_source(first_cell.get("source", [])))
            if parsed:
                custom.update(parsed)
                first_cell_remainder = remainder
                start_index = 1

    merged = default_frontmatter(notebook_path)
    merged.update(custom)
    return merged, start_index, first_cell_remainder


def yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    text = str(value)
    if text == "" or any(ch in text for ch in ":#[]{}&*!|>'\"%@`"):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def dump_frontmatter(data: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_scalar(item)}")
            continue
        lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def join_source(source: object) -> str:
    if isinstance(source, str):
        return source
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return ""


def ensure_generated_target(target: Path) -> None:
    if not target.exists():
        return
    existing = target.read_text(encoding="utf-8")
    if GENERATED_MARKER not in existing:
        raise RuntimeError(f"Refusing to overwrite non-generated file: {target.relative_to(ROOT)}")


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def write_binary_if_changed(path: Path, content: bytes) -> None:
    if path.exists() and path.read_bytes() == content:
        return
    path.write_bytes(content)


def markdown_attachment_rewriter(asset_dir_name: str, asset_dir: Path, cell_index: int):
    counter = {"value": 0}

    def replace(match: re.Match[str], attachments: dict[str, object]) -> str:
        name = match.group(1)
        payload = attachments.get(name)
        if not isinstance(payload, dict):
            return match.group(0)
        for mime_type, data in payload.items():
            extension = MIME_IMAGE_EXTENSIONS.get(mime_type)
            if extension is None:
                continue
            encoded = join_source(data)
            target_name = f"attachment-{cell_index}-{counter['value']}.{extension}"
            counter["value"] += 1
            asset_path = asset_dir / target_name
            write_binary_if_changed(asset_path, base64.b64decode(encoded))
            return f"{asset_dir_name}/{target_name}"
        return match.group(0)

    return replace


def render_markdown_cell(
    cell: dict[str, object],
    asset_dir_name: str,
    asset_dir: Path,
    cell_index: int,
) -> str:
    text = join_source(cell.get("source", []))
    attachments = cell.get("attachments", {})
    if isinstance(attachments, dict) and attachments:
        rewriter = markdown_attachment_rewriter(asset_dir_name, asset_dir, cell_index)

        def _replace(match: re.Match[str]) -> str:
            return rewriter(match, attachments)

        text = re.sub(r"attachment:([^)\"'\s]+)", _replace, text)
    return text.strip()


def output_text_block(text: str) -> str:
    return f"```text\n{text.rstrip()}\n```"


def render_output(
    output: dict[str, object],
    asset_dir_name: str,
    asset_dir: Path,
    cell_index: int,
    output_index: int,
) -> str:
    output_type = output.get("output_type")

    if output_type == "stream":
        return output_text_block(join_source(output.get("text", [])))

    if output_type == "error":
        traceback = output.get("traceback", [])
        if isinstance(traceback, list) and traceback:
            text = "\n".join(str(line) for line in traceback)
        else:
            text = f"{output.get('ename', 'Error')}: {output.get('evalue', '')}"
        return output_text_block(text)

    data = output.get("data", {})
    if not isinstance(data, dict):
        return ""

    for mime_type in ("text/markdown", "text/plain", "text/html"):
        if mime_type in data:
            if mime_type == "text/plain":
                return output_text_block(join_source(data[mime_type]))
            return join_source(data[mime_type]).strip()

    for mime_type, extension in MIME_IMAGE_EXTENSIONS.items():
        if mime_type not in data:
            continue
        target_name = f"output-{cell_index}-{output_index}.{extension}"
        asset_path = asset_dir / target_name
        payload = join_source(data[mime_type])
        if mime_type == "image/svg+xml":
            write_if_changed(asset_path, payload)
        else:
            write_binary_if_changed(asset_path, base64.b64decode(payload))
        return f"![Notebook output]({asset_dir_name}/{target_name})"

    for mime_type in TEXT_MIME_PRIORITY:
        if mime_type in data:
            return output_text_block(join_source(data[mime_type]))

    return output_text_block(json.dumps(data, indent=2))


def render_code_cell(
    cell: dict[str, object],
    language: str,
    asset_dir_name: str,
    asset_dir: Path,
    cell_index: int,
) -> str:
    parts: list[str] = []
    source = join_source(cell.get("source", [])).rstrip()
    if source:
        parts.append(f"```{language}\n{source}\n```")

    outputs = cell.get("outputs", [])
    if isinstance(outputs, list):
        for output_index, output in enumerate(outputs):
            if not isinstance(output, dict):
                continue
            rendered = render_output(output, asset_dir_name, asset_dir, cell_index, output_index)
            if rendered:
                parts.append(rendered)

    return "\n\n".join(parts)


def render_notebook(notebook_path: Path) -> None:
    target = notebook_path.with_suffix(".md")
    ensure_generated_target(target)

    asset_dir = notebook_path.with_name(f"{notebook_path.stem}_files")
    if asset_dir.exists():
        shutil.rmtree(asset_dir)

    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    language = (
        nb.get("metadata", {})
        .get("language_info", {})
        .get("name", "python")
    )
    frontmatter, start_index, first_cell_remainder = notebook_frontmatter(nb, notebook_path)

    parts = [
        dump_frontmatter(frontmatter),
        f"{GENERATED_MARKER}{notebook_path.relative_to(ROOT).as_posix()} -->",
    ]

    cells = nb.get("cells", [])
    if first_cell_remainder:
        parts.append(first_cell_remainder.strip())

    asset_dir_used = False
    asset_dir_name = asset_dir.name
    asset_dir.mkdir(parents=True, exist_ok=True)

    for cell_index, cell in enumerate(cells[start_index:], start=start_index):
        if not isinstance(cell, dict):
            continue
        cell_type = cell.get("cell_type")
        if cell_type == "markdown":
            rendered = render_markdown_cell(cell, asset_dir_name, asset_dir, cell_index)
        elif cell_type == "code":
            rendered = render_code_cell(cell, str(language), asset_dir_name, asset_dir, cell_index)
        else:
            rendered = join_source(cell.get("source", [])).strip()
        if rendered:
            parts.append(rendered)
        if asset_dir.exists() and any(asset_dir.iterdir()):
            asset_dir_used = True

    if not asset_dir_used and asset_dir.exists():
        asset_dir.rmdir()

    rendered_markdown = "\n\n".join(part for part in parts if part).rstrip() + "\n"
    write_if_changed(target, rendered_markdown)


def main() -> int:
    args = parse_args()
    notebooks = iter_notebooks(args.paths or ["content"])
    if not notebooks:
        print("No notebooks found.")
        return 0

    for notebook_path in notebooks:
        render_notebook(notebook_path)
        print(f"Rendered {notebook_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
