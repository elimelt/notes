#!/usr/bin/env python3
"""Keep Quartz's desktop graph libraries off the mobile critical path."""

from __future__ import annotations

import sys
from pathlib import Path


LOAD_PREFIX = (
    'Promise.all([e("https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"),'
    'e("https://cdn.jsdelivr.net/npm/pixi.js@8/dist/pixi.js")])'
    '.then(function(){r()}).catch(function(o){'
)
PATCHED_PREFIX = (
    'function loadGraphLibraries(){return Promise.all(['
    'e("https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"),'
    'e("https://cdn.jsdelivr.net/npm/pixi.js@8/dist/pixi.min.js")])'
    '.then(function(){r()}).catch(function(o){'
)
LOAD_SUFFIX = 'a[n].style.fontSize="0.9rem"});function r(){'
PATCHED_SUFFIX = (
    'a[n].style.fontSize="0.9rem"})}'
    'var graphLibrariesStarted=false;'
    'function startGraphLibraries(){'
    'if(graphLibrariesStarted)return;graphLibrariesStarted=true;'
    'var o=function(){void loadGraphLibraries()};'
    'if("requestIdleCallback"in window){window.requestIdleCallback(o,{timeout:2000})}'
    'else{window.setTimeout(o,1000)}}'
    'function scheduleGraphLibraries(){'
    'if(document.readyState==="complete")startGraphLibraries();'
    'else window.addEventListener("load",startGraphLibraries,{once:true})}'
    'var graphMedia=window.matchMedia("(min-width: 801px)");'
    'if(graphMedia.matches)scheduleGraphLibraries();'
    'else{var onDesktop=function(o){if(o.matches){'
    'graphMedia.removeEventListener("change",onDesktop);scheduleGraphLibraries()}};'
    'graphMedia.addEventListener("change",onDesktop)}'
    ';function r(){'
)


def patch(path: Path) -> None:
    source = path.read_text()
    if PATCHED_PREFIX in source and PATCHED_SUFFIX in source:
        return
    if source.count(LOAD_PREFIX) != 1 or source.count(LOAD_SUFFIX) != 1:
        raise SystemExit(f"graph loading patch did not match {path}")
    patched = source.replace(LOAD_PREFIX, PATCHED_PREFIX).replace(
        LOAD_SUFFIX, PATCHED_SUFFIX
    )
    path.write_text(patched)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: patch_graph_loading.py <graph-bundle> [...]")
    for filename in sys.argv[1:]:
        patch(Path(filename))
