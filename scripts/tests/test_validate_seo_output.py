from pathlib import Path
import tempfile
import unittest

from scripts.validate_seo_output import expected_canonical, validate


class ValidateSeoOutputTests(unittest.TestCase):
    def test_expected_canonical_normalizes_index_pages(self) -> None:
        root = Path("/tmp/public")
        self.assertEqual(expected_canonical(root, root / "index.html"), "https://notes.elimelt.com/")
        self.assertEqual(
            expected_canonical(root, root / "tags" / "cpu.html"),
            "https://notes.elimelt.com/tags/cpu",
        )
        self.assertEqual(
            expected_canonical(root, root / "algorithms" / "index.html"),
            "https://notes.elimelt.com/algorithms/",
        )

    def test_validate_accepts_consistent_quartz_and_graph_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "robots.txt").write_text(
                "User-agent: *\nAllow: /\n\nSitemap: https://notes.elimelt.com/sitemap.xml\n"
            )
            (root / "sitemap.xml").write_text(
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<url><loc>https://notes.elimelt.com/</loc></url>"
                "</urlset>"
            )
            (root / "index.html").write_text(
                '<meta name="generator" content="Quartz">'
                '<link rel="canonical" href="https://notes.elimelt.com/">'
                '<meta property="og:url" content="https://notes.elimelt.com/">'
                '<meta property="twitter:url" content="https://notes.elimelt.com/">'
                '<meta property="og:image:type" content="image/png">'
            )
            graph = root / "graph"
            graph.mkdir()
            (graph / "index.html").write_text(
                '<link rel="canonical" href="https://notes.elimelt.com/graph/">'
                '<meta property="og:url" content="https://notes.elimelt.com/graph/">'
            )
            self.assertEqual(validate(root), [])

    def test_validate_rejects_duplicate_or_index_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "robots.txt").write_text(
                "Sitemap: https://notes.elimelt.com/sitemap.xml\n"
            )
            (root / "sitemap.xml").write_text(
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<url><loc>https://notes.elimelt.com/</loc></url>"
                "</urlset>"
            )
            (root / "index.html").write_text(
                '<meta name="generator" content="Quartz">'
                '<link rel="canonical" href="https://notes.elimelt.com/index">'
                '<link rel="canonical" href="https://notes.elimelt.com/">'
                '<meta property="og:url" content="https://notes.elimelt.com/index">'
            )
            errors = validate(root)
            self.assertTrue(any("canonical" in error for error in errors))
            self.assertTrue(any("og:url" in error for error in errors))

    def test_validate_preserves_alias_redirect_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "robots.txt").write_text(
                "Sitemap: https://notes.elimelt.com/sitemap.xml\n"
            )
            (root / "sitemap.xml").write_text(
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<url><loc>https://notes.elimelt.com/</loc></url>"
                "</urlset>"
            )
            alias = root / "old-name.html"
            alias.write_text(
                '<meta http-equiv="refresh" content="0; url=new-name">'
                '<link rel="canonical" href="new-name">'
            )
            graph = root / "graph"
            graph.mkdir()
            (graph / "index.html").write_text(
                '<link rel="canonical" href="https://notes.elimelt.com/graph/">'
                '<meta property="og:url" content="https://notes.elimelt.com/graph/">'
            )
            errors = validate(root)
            self.assertFalse(any("alias redirect" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
