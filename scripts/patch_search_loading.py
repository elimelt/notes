#!/usr/bin/env python3
"""Defer Quartz's full-text index until somebody opens Search.

The Quartz checkout is disposable and refreshed independently of this site, so
this patch deliberately fails when the upstream bundle no longer matches the
version it was written for.
"""

from __future__ import annotations

import argparse
from pathlib import Path


MARKER = "/* Notes site: lazily build the search index. */"

OLD_LOADER = "var Rt=!1;async function Ti(){Rt||(Z=await bi(),await ki(),Rt=!0)}"
NEW_LOADER = (
    "var Rt=!1,searchIndexPromise=null;"
    f"{MARKER}"
    "async function Ti(){"
    "if(Rt)return;"
    "if(searchIndexPromise)return searchIndexPromise;"
    "return searchIndexPromise=(async()=>{"
    "Z=await bi(),await ki(),Rt=!0"
    "})().catch(t=>{searchIndexPromise=null;throw t})"
    "}"
    "function startSearchIndex(){void Ti().catch(()=>{})}"
)

OLD_OPEN = (
    'W=_=>{Me=_,u&&(u.style.zIndex="9999"),n.classList.add("active"),'
    'r.setAttribute("aria-expanded","true"),i.focus()}'
)
NEW_OPEN = (
    'W=_=>{Me=_,u&&(u.style.zIndex="9999"),n.classList.add("active"),'
    'r.setAttribute("aria-expanded","true"),i.focus(),startSearchIndex()}'
)

OLD_QUERY = "nt=async _=>{let A=_.target.value;"
NEW_QUERY = "nt=async _=>{try{await Ti()}catch{return}let A=_.target.value;"

OLD_NAV = "async function Mn(){Ai(),await Ti(),await wi(),Li()}"
NEW_NAV = "async function Mn(){Ai(),await wi(),Li()}"


def patch(path: Path) -> None:
    source = path.read_text()
    replacements = (
        (OLD_LOADER, NEW_LOADER),
        (OLD_OPEN, NEW_OPEN),
        (OLD_QUERY, NEW_QUERY),
        (OLD_NAV, NEW_NAV),
    )

    if MARKER in source:
        missing = [new for _, new in replacements if new not in source]
        if missing:
            raise SystemExit(f"search loading patch is incomplete in {path}")
        return

    if any(source.count(old) != 1 for old, _ in replacements):
        raise SystemExit(f"Quartz search source changed; refusing to patch {path}")

    for old, new in replacements:
        source = source.replace(old, new)
    path.write_text(source)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="+")
    args = parser.parse_args()
    for path in args.paths:
        patch(path)


if __name__ == "__main__":
    main()
