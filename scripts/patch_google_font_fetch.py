#!/usr/bin/env python3
"""Make Quartz's build-time Google Fonts fetch request subsetted WOFF2."""

from __future__ import annotations

import argparse
from pathlib import Path


MARKER = "// Notes site: request unicode-subsetted WOFF2 font CSS."

OLD = """        const theme = ctx.cfg.configuration.theme
        const response = await fetch(googleFontHref(theme))
        googleFontsStyleSheet = await response.text()

        if (theme.typography.title) {
          const title = ctx.cfg.configuration.pageTitle
          const response = await fetch(googleFontSubsetHref(theme, title))
          googleFontsStyleSheet += `\\n${await response.text()}`
        }
"""

NEW = f"""        const theme = ctx.cfg.configuration.theme
        {MARKER}
        const fontRequest = {{
          headers: {{
            "User-Agent":
              "Mozilla/5.0 AppleWebKit/537.36 Chrome/109.0.0.0 Safari/537.36",
          }},
        }}
        const response = await fetch(googleFontHref(theme), fontRequest)
        googleFontsStyleSheet = await response.text()

        if (theme.typography.title) {{
          const title = ctx.cfg.configuration.pageTitle
          const response = await fetch(googleFontSubsetHref(theme, title), fontRequest)
          googleFontsStyleSheet += `\\n${{await response.text()}}`
        }}

"""

OLD_PROCESSED = """        googleFontsStyleSheet = processedStylesheet
"""

NEW_PROCESSED = """        // Keep emitted font URLs portable across local preview and production.
        googleFontsStyleSheet = processedStylesheet.replaceAll(
          `https://${cfg.baseUrl}/static/fonts/`,
          "/static/fonts/",
        )
"""


def patch(path: Path) -> None:
    source = path.read_text()
    if MARKER in source:
        if (
            "fetch(googleFontSubsetHref(theme, title), fontRequest)" not in source
            or NEW_PROCESSED not in source
        ):
            raise SystemExit(f"Google Fonts fetch patch is incomplete in {path}")
        return
    if source.count(OLD) != 1 or source.count(OLD_PROCESSED) != 1:
        raise SystemExit(f"Quartz Google Fonts source changed; refusing to patch {path}")
    path.write_text(source.replace(OLD, NEW).replace(OLD_PROCESSED, NEW_PROCESSED))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    patch(args.path)


if __name__ == "__main__":
    main()
