#!/usr/bin/env python3

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET


SITE_ORIGIN = "https://notes.elimelt.com"


class HeadMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonicals: list[str] = []
        self.meta: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("rel") == "canonical" and values.get("href"):
            self.canonicals.append(values["href"] or "")
        if tag == "meta":
            key = values.get("property") or values.get("name")
            content = values.get("content")
            if key and content is not None:
                self.meta.setdefault(key, []).append(content)


def expected_canonical(output_root: Path, html_path: Path) -> str:
    relative = html_path.relative_to(output_root).as_posix()
    if relative == "index.html":
        path = "/"
    elif relative.endswith("/index.html"):
        path = "/" + relative.removesuffix("index.html")
    else:
        path = "/" + relative.removesuffix(".html")
    return SITE_ORIGIN + quote(path, safe="/;,:@&=+$-_.!~*'()")


def parse_metadata(path: Path) -> HeadMetadataParser:
    parser = HeadMetadataParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def validate_with_stats(output_root: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    stats = {"quartz_pages": 0, "graph_pages": 0, "aliases": 0}
    robots = output_root / "robots.txt"
    expected_sitemap = f"Sitemap: {SITE_ORIGIN}/sitemap.xml"
    if not robots.is_file():
        errors.append("robots.txt is missing from the site root")
    elif expected_sitemap not in robots.read_text(encoding="utf-8"):
        errors.append(f"robots.txt does not advertise {expected_sitemap}")

    sitemap = output_root / "sitemap.xml"
    sitemap_urls: set[str] = set()
    if not sitemap.is_file():
        errors.append("sitemap.xml is missing from the site root")
    else:
        try:
            root = ET.parse(sitemap).getroot()
            sitemap_urls = {
                element.text
                for element in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if element.text
            }
        except ET.ParseError as error:
            errors.append(f"sitemap.xml is not valid XML: {error}")
        if not sitemap_urls:
            errors.append("sitemap.xml contains no URLs")

    for path in sorted(output_root.rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        is_graph = path == output_root / "graph" / "index.html"
        is_quartz_page = 'meta name="generator" content="Quartz"' in text
        is_alias_redirect = 'http-equiv="refresh"' in text
        if is_alias_redirect:
            stats["aliases"] += 1
            metadata = parse_metadata(path)
            if len(metadata.canonicals) != 1:
                errors.append(
                    f"{path}: alias redirect has {len(metadata.canonicals)} canonical links, expected 1"
                )
            continue
        if not (is_graph or is_quartz_page) or path.name == "404.html":
            continue

        if is_graph:
            stats["graph_pages"] += 1
        if is_quartz_page:
            stats["quartz_pages"] += 1

        metadata = parse_metadata(path)
        expected = expected_canonical(output_root, path)
        if metadata.canonicals != [expected]:
            errors.append(f"{path}: canonical {metadata.canonicals!r}, expected [{expected!r}]")
        for key in ("og:url",):
            if metadata.meta.get(key) != [expected]:
                errors.append(f"{path}: {key} {metadata.meta.get(key)!r}, expected [{expected!r}]")
        if is_quartz_page:
            if expected not in sitemap_urls:
                errors.append(f"{path}: canonical {expected!r} is missing from sitemap.xml")
            if metadata.meta.get("twitter:url") != [expected]:
                errors.append(
                    f"{path}: twitter:url {metadata.meta.get('twitter:url')!r}, expected [{expected!r}]"
                )
            image_types = metadata.meta.get("og:image:type")
            if image_types and image_types != ["image/png"]:
                errors.append(f"{path}: og:image:type is {image_types!r}, expected ['image/png']")

    if stats["quartz_pages"] == 0:
        errors.append("no rendered Quartz pages were found")
    if stats["graph_pages"] != 1:
        errors.append(f"found {stats['graph_pages']} graph pages, expected 1")
    return errors, stats


def validate(output_root: Path) -> list[str]:
    return validate_with_stats(output_root)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical and crawl metadata in a Quartz build.")
    parser.add_argument("output", nargs="?", type=Path, default=Path("public"))
    args = parser.parse_args()
    errors, stats = validate_with_stats(args.output)
    if errors:
        print("\n".join(errors))
        return 1
    print(
        "SEO output validation passed: "
        f"{stats['quartz_pages']} Quartz pages, {stats['graph_pages']} graph page, "
        f"and {stats['aliases']} aliases checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
