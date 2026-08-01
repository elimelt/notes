from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_notebooks


class RenderNotebookTests(unittest.TestCase):
    def test_embedded_only_notebook_preserves_same_stem_note_and_seeds_urls(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            content = root / "content"
            cache = root / "cache"
            content.mkdir()
            note = content / "topic.md"
            note.write_text("# Existing note\n", encoding="utf-8")
            notebook_path = content / "topic.ipynb"
            notebook_path.write_text(
                json.dumps(
                    {
                        "cells": [
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "---\n",
                                    "notebook_page: false\n",
                                    "---\n",
                                    "\n",
                                    "Embedded explanation.\n",
                                ],
                            }
                        ],
                        "metadata": {},
                        "nbformat": 4,
                        "nbformat_minor": 5,
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                cache_dir=cache,
                source_base_url="https://github.com/example/notes/blob/main",
            )

            with (
                patch.object(render_notebooks, "ROOT", root),
                patch.object(render_notebooks, "CONTENT_ROOT", content),
            ):
                render_notebooks.render_notebook(notebook_path, args)
                github_url = "https://github.com/example/notes/blob/main/content/topic.ipynb"
                cache_paths = [
                    render_notebooks.cache_path(cache, github_url),
                    render_notebooks.cache_path(cache, "/topic.ipynb"),
                ]

            self.assertEqual(note.read_text(encoding="utf-8"), "# Existing note\n")
            self.assertTrue(all(path.exists() for path in cache_paths))
            cached = json.loads(cache_paths[1].read_text(encoding="utf-8"))
            self.assertEqual("".join(cached["cells"][0]["source"]), "Embedded explanation.\n")


if __name__ == "__main__":
    unittest.main()
