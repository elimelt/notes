#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute Jupyter notebooks in place.")
    parser.add_argument("paths", nargs="+", help="Notebook paths to execute")
    parser.add_argument(
        "--kernel",
        default="notes-py312",
        help="Jupyter kernel name to use",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Per-cell timeout in seconds",
    )
    return parser.parse_args()


def execute_notebook(path: Path, timeout: int, kernel_name: str) -> None:
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name=kernel_name,
        resources={"metadata": {"path": str(path.parent)}},
    )
    client.execute()
    nbformat.write(notebook, path)


def main() -> int:
    args = parse_args()
    for raw in args.paths:
        path = (ROOT / raw).resolve()
        if path.suffix != ".ipynb":
            raise SystemExit(f"Not a notebook: {raw}")
        execute_notebook(path, timeout=args.timeout, kernel_name=args.kernel)
        print(f"Executed {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
