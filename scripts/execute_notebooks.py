#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WARNING_PATTERN = re.compile(r"warning", re.IGNORECASE)
WARNING_SETUP = """\
import logging
import os
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("DATASETS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("datasets").setLevel(logging.ERROR)
"""
QUIET_ENV = {
    "PYTHONWARNINGS": "ignore",
    "HF_HUB_DISABLE_PROGRESS_BARS": "1",
    "HF_HUB_VERBOSITY": "error",
    "DATASETS_VERBOSITY": "error",
    "TOKENIZERS_PARALLELISM": "false",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute Jupyter notebooks in place.")
    parser.add_argument("paths", nargs="+", help="Notebook paths to execute")
    parser.add_argument(
        "--kernel",
        help="Override the notebook's declared Jupyter kernel",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Per-cell timeout in seconds",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Remove stored warning streams without executing notebooks",
    )
    return parser.parse_args()


@contextmanager
def quiet_environment():
    previous = {key: os.environ.get(key) for key in QUIET_ENV}
    os.environ.update(QUIET_ENV)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def strip_warning_streams(notebook: dict[str, object]) -> int:
    removed = 0
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        return removed
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        if "outputs" not in cell:
            continue
        outputs = cell.get("outputs", [])
        if not isinstance(outputs, list):
            continue
        kept = []
        for output in outputs:
            if not isinstance(output, dict):
                kept.append(output)
                continue
            text = output.get("text", "")
            joined = "".join(text) if isinstance(text, list) else str(text)
            is_warning = (
                output.get("output_type") == "stream"
                and WARNING_PATTERN.search(joined)
            )
            if is_warning:
                removed += 1
            else:
                kept.append(output)
        cell["outputs"] = kept
    return removed


def execute_notebook(path: Path, timeout: int, kernel_name: str | None) -> None:
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError as error:
        raise SystemExit(
            "Notebook execution requires nbformat and nbclient. "
            "Install the optional notebook dependencies described in README.md."
        ) from error

    notebook = nbformat.read(path, as_version=4)
    first_code_cell = next(
        (cell for cell in notebook.cells if cell.get("cell_type") == "code"), None
    )
    original_source = first_code_cell.source if first_code_cell is not None else None
    if first_code_cell is not None:
        first_code_cell.source = f"{WARNING_SETUP}\n{original_source}"
    client_options = {
        "timeout": timeout,
        "extra_arguments": ["--Application.log_level=ERROR"],
        "resources": {"metadata": {"path": str(path.parent)}},
    }
    if kernel_name:
        client_options["kernel_name"] = kernel_name
    client = NotebookClient(notebook, **client_options)
    try:
        with quiet_environment():
            client.execute()
    finally:
        if first_code_cell is not None:
            first_code_cell.source = original_source
    strip_warning_streams(notebook)
    nbformat.write(notebook, path)


def main() -> int:
    args = parse_args()
    for raw in args.paths:
        path = (ROOT / raw).resolve()
        if path.suffix != ".ipynb":
            raise SystemExit(f"Not a notebook: {raw}")
        if args.clean_only:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            removed = strip_warning_streams(notebook)
            if removed:
                path.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
            print(f"Removed {removed} warning stream(s) from {path.relative_to(ROOT)}")
        else:
            execute_notebook(path, timeout=args.timeout, kernel_name=args.kernel)
            print(f"Executed {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
