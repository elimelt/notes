#!/usr/bin/env python3
"""Add the local-only style panel component to a temporary Quartz config."""

from pathlib import Path
import sys


PLUGIN = """plugins:
  - source: ../quartz-site/dev/style-debug-panel
    enabled: true
    layout:
      position: footer
      priority: 1000
"""


def main() -> None:
    path = Path(sys.argv[1])
    config = path.read_text()
    if "source: ../quartz-site/dev/style-debug-panel" not in config:
        config = config.replace("plugins:\n", PLUGIN, 1)
        path.write_text(config)


if __name__ == "__main__":
    main()
