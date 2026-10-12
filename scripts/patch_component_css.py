#!/usr/bin/env python3
"""Bundle Quartz component styles into the core stylesheet.

The Quartz checkout is disposable and refreshed independently of this site, so
this patch deliberately fails when the upstream source no longer matches the
version it was written for.
"""

from __future__ import annotations

import argparse
from pathlib import Path


MARKER = "// Notes site: component CSS is bundled into the core stylesheet."

OLD_JOIN = """        ...globalCss,
        baseStyles,
      )"""

NEW_JOIN = f"""        ...globalCss,
        baseStyles,
        {MARKER}
        ...componentResources.componentCssStrings,
      )"""

OLD_EMISSION = """      const cssStringToFilename = new Map<string, string>()
      for (const cssString of componentResources.componentCssStrings) {
        if (cssStringToFilename.has(cssString)) continue

        const wrapped = `@layer quartz-base {\\n${cssString}\\n}`
        const minified = transform({
          filename: "component.css",
          code: Buffer.from(wrapped),
          minify: true,
          targets: lightningTargets,
          include: Features.MediaQueries,
        }).code.toString()

        const hash = hashContent(minified)
        const slug = `component-${hash}`
        const filename = `${slug}.css`
        cssStringToFilename.set(cssString, filename)

        yield write({
          ctx,
          slug: slug as FullSlug,
          ext: ".css",
          content: minified,
        })
      }

      ctx.componentCssMap = cssStringToFilename
"""

NEW_EMISSION = """      // Component styles are already part of index.css, so renderPage must not
      // add the old per-component stylesheet links.
      ctx.componentCssMap = new Map()
"""


def patch(path: Path) -> None:
    source = path.read_text()
    if MARKER in source:
        if NEW_EMISSION not in source:
            raise SystemExit(f"component CSS patch is incomplete in {path}")
        return

    if source.count(OLD_JOIN) != 1 or source.count(OLD_EMISSION) != 1:
        raise SystemExit(
            f"Quartz component resource source changed; refusing to patch {path}"
        )

    patched = source.replace(OLD_JOIN, NEW_JOIN).replace(OLD_EMISSION, NEW_EMISSION)
    path.write_text(patched)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    patch(args.path)


if __name__ == "__main__":
    main()
