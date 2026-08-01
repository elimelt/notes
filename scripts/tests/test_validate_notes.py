from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_notes


class ValidateNotesTests(unittest.TestCase):
    def test_canonical_slug_normalizes_index_pages(self) -> None:
        path = validate_notes.CONTENT_ROOT / "systems" / "index.md"

        self.assertEqual(validate_notes.canonical_slug(path), "systems")

    def test_self_alias_forms_normalize_to_the_canonical_slug(self) -> None:
        canonical = "hardware/computer-architecture/caches-virtual-memory"

        for alias in (
            canonical,
            f"/{canonical}/",
            f"{canonical}.html",
            f"{canonical}/index",
        ):
            with self.subTest(alias=alias):
                self.assertEqual(validate_notes.normalize_page_slug(alias), canonical)


if __name__ == "__main__":
    unittest.main()
