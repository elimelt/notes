from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import execute_notebooks


class ExecuteNotebookTests(unittest.TestCase):
    def test_strip_warning_streams_preserves_normal_stderr(self) -> None:
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "outputs": [
                        {
                            "output_type": "stream",
                            "name": "stderr",
                            "text": "UserWarning: noisy\n",
                        },
                        {
                            "output_type": "stream",
                            "name": "stderr",
                            "text": "useful diagnostic\n",
                        },
                        {
                            "output_type": "stream",
                            "name": "stdout",
                            "text": "result\n",
                        },
                    ],
                }
            ]
        }

        removed = execute_notebooks.strip_warning_streams(notebook)

        self.assertEqual(removed, 1)
        self.assertEqual(
            [output["text"] for output in notebook["cells"][0]["outputs"]],
            ["useful diagnostic\n", "result\n"],
        )

    def test_quiet_environment_restores_existing_values(self) -> None:
        original = execute_notebooks.os.environ.get("PYTHONWARNINGS")
        execute_notebooks.os.environ["PYTHONWARNINGS"] = "default"
        try:
            with execute_notebooks.quiet_environment():
                self.assertEqual(
                    execute_notebooks.os.environ["PYTHONWARNINGS"], "ignore"
                )
            self.assertEqual(
                execute_notebooks.os.environ["PYTHONWARNINGS"], "default"
            )
        finally:
            if original is None:
                execute_notebooks.os.environ.pop("PYTHONWARNINGS", None)
            else:
                execute_notebooks.os.environ["PYTHONWARNINGS"] = original


if __name__ == "__main__":
    unittest.main()
