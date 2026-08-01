from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_graph_index


class PrepareGraphIndexTests(unittest.TestCase):
    def test_preserves_folder_indexes_and_adds_hierarchy_edges(self) -> None:
        index = {
            "index": {"links": [], "content": "Home"},
            "ml/index": {"links": [], "content": "Machine learning"},
            "ml/deep-learning/index": {"links": [], "content": ""},
            "ml/deep-learning/gcn": {
                "links": ["tags/gnn"],
                "tags": ["gnn"],
                "content": "GCN",
            },
            "tags": {"links": [], "content": ""},
            "tags/gnn": {"links": [], "content": ""},
            "tags/synthetic-parent": {"links": [], "content": ""},
        }

        removed, added, tag_edges = prepare_graph_index.prepare_index(index)

        self.assertEqual(removed, 2)
        self.assertEqual(added, 3)
        self.assertEqual(tag_edges, 1)
        self.assertNotIn("tags", index)
        self.assertNotIn("tags/synthetic-parent", index)
        self.assertIn("tags/gnn", index)
        self.assertIn("ml/index", index["index"]["links"])
        self.assertIn("ml/deep-learning/index", index["ml/index"]["links"])
        self.assertIn(
            "ml/deep-learning/gcn", index["ml/deep-learning/index"]["links"]
        )
        self.assertNotIn("tags/gnn", index["ml/deep-learning/gcn"]["links"])
        self.assertEqual(index["tags/gnn"]["links"], ["ml/deep-learning/gcn"])


if __name__ == "__main__":
    unittest.main()
