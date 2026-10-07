#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


def materialize(lock_path: Path, quartz_dir: Path) -> None:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for entry in lock.get("plugins", {}).values():
        if entry.get("commit") != "local":
            continue
        source = entry.get("source")
        if not isinstance(source, str):
            raise ValueError("local Quartz plugin is missing a string source path")
        resolved = (quartz_dir / source).resolve()
        if not resolved.is_dir():
            raise FileNotFoundError(f"local Quartz plugin path does not exist: {resolved}")
        entry["resolved"] = str(resolved)
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


def make_portable(lock_path: Path) -> None:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for entry in lock.get("plugins", {}).values():
        if entry.get("commit") == "local" and isinstance(entry.get("source"), str):
            entry["resolved"] = entry["source"]
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve local Quartz plugin paths for this checkout.")
    parser.add_argument("lock_path", type=Path)
    parser.add_argument("quartz_dir", type=Path)
    parser.add_argument("--portable", action="store_true")
    args = parser.parse_args()
    if args.portable:
        make_portable(args.lock_path)
    else:
        materialize(args.lock_path, args.quartz_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
