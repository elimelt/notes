from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import new_notebook


class NewNotebookTests(unittest.TestCase):
    def test_templates_are_discovered_and_render_valid_notebooks(self) -> None:
        templates = new_notebook.available_templates()
        self.assertEqual(set(templates), {"benchmark", "derivation", "experiment"})

        for path in templates.values():
            template = json.loads(path.read_text(encoding="utf-8"))
            rendered = new_notebook.render_notebook(
                template,
                title="Queueing Experiment",
                category="Scheduling",
                tags=["queueing", "simulation"],
                sources=["https://example.com/source"],
                description="Measure waiting time under a small workload.",
                standalone=False,
            )
            self.assertEqual(rendered["nbformat"], 4)
            first_cell = "".join(rendered["cells"][0]["source"])
            self.assertIn('title: "Queueing Experiment"', first_cell)
            self.assertIn('  - "queueing"\n  - "simulation"', first_cell)
            self.assertIn('  - "https://example.com/source"', first_cell)
            self.assertIn("notebook_page: false", first_cell)
            self.assertNotIn("{{", json.dumps(rendered))

    def test_standalone_mode_sets_notebook_page_true(self) -> None:
        template = json.loads(
            new_notebook.available_templates()["experiment"].read_text(encoding="utf-8")
        )
        rendered = new_notebook.render_notebook(
            template,
            title="Standalone",
            category="Experiments",
            tags=[],
            sources=[],
            description="A standalone experiment.",
            standalone=True,
        )
        first_cell = "".join(rendered["cells"][0]["source"])
        self.assertIn("notebook_page: true", first_cell)


if __name__ == "__main__":
    unittest.main()
