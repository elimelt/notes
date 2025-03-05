from dataclasses import dataclass
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
import shutil
import markdown
import logging
from datetime import datetime
from urllib.parse import quote
import re
from collections import defaultdict
from jinja2 import Environment, BaseLoader, TemplateNotFound, select_autoescape
from template.html import BASE_TEMPLATE, INDEX_TEMPLATE, STYLES_TEMPLATE

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
@dataclass
class Page:
    """Represents a page in the static site"""
    title: str
    path: Path
    content: str
    modified_date: datetime
    category: Optional[str]
    tags: List[str]
    description: Optional[str]
    is_index: bool = False

class JinjaTemplateLoader(BaseLoader):
    def __init__(self, templates):
        self.templates = templates

    def get_source(self, environment, template):
        if template not in self.templates:
            raise TemplateNotFound(template)
        return self.templates[template], None, lambda: True


class SiteGenerator:
    """Generates a static site from a directory of mixed content"""

    MARKDOWN_EXTENSIONS = [
        "meta", "toc", "fenced_code", "tables",
        "attr_list", "footnotes", "def_list", "admonition",
    ]
    SUPPORTED_CONTENT = {".md", ".markdown"}
    IGNORED_DIRECTORIES = {
        ".git", "__pycache__", "node_modules", ".github",
        "nlp.venv", "site", "venv", ".venv",
    }

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        site_domain: str = "https://notes.elimelt.com",
    ):
        self.site_domain = site_domain
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.markdown_converter = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
        self.pages: Dict[Path, Page] = {}
        self.categories: Dict[str, List[Page]] = defaultdict(list)
        self.tags: Dict[str, List[Page]] = defaultdict(list)
        self._setup_jinja()

    def _setup_jinja(self):
        """Initialize Jinja2 environment with templates"""
        templates = {
            'base': BASE_TEMPLATE,
            'index': INDEX_TEMPLATE,
            'styles': STYLES_TEMPLATE,
        }

        self.jinja_env = Environment(
            loader=JinjaTemplateLoader(templates),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        self.jinja_env.filters['urlencode'] = quote

    def generate_site(self) -> None:
        """Main method to generate the static site"""
        try:
            self._prepare_output_directory()
            self._process_content()
            self._organize_content()
            self._copy_assets()
            self._generate_special_pages()
            self._generate_html_pages()
            logger.info(f"Site generated successfully in {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to generate site: {str(e)}")
            raise

    def _prepare_output_directory(self) -> None:
        """Prepare the output directory with proper permissions"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)
        self.output_dir.chmod(0o755)

        assets_dir = self.output_dir / "assets"
        assets_dir.mkdir(parents=True)
        assets_dir.chmod(0o755)

    def _walk_directory(self, directory: Path) -> List[Path]:
        """Walk through directory while respecting ignored paths"""
        return [
            item for item in directory.rglob("*")
            if not any(ignored in item.parts for ignored in self.IGNORED_DIRECTORIES)
            and item.is_file()
        ]

    def _extract_metadata(self, file_path: Path, content: str) -> dict:
        """Extract metadata from markdown file"""
        md = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
        md.convert(content)

        if not hasattr(md, "Meta"):
            return {
                "title": file_path.stem.replace("-", " ").title(),
                "category": None,
                "tags": [],
                "description": None,
            }

        return {
            "title": md.Meta.get("title", [file_path.stem.replace("-", " ").title()])[0],
            "category": md.Meta.get("category", [None])[0],
            "tags": md.Meta.get("tags", [""])[0].split(",") if "tags" in md.Meta else [],
            "description": md.Meta.get("description", [None])[0],
        }

    def _process_markdown(self, file_path: Path) -> None:
        """Process a markdown file into a Page object"""
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = self._extract_metadata(file_path, content)
            html_content = self.markdown_converter.convert(content)

            relative_path = file_path.relative_to(self.input_dir)
            is_index = file_path.stem.lower() == "index"
            tags = [tag.strip().lower() for tag in metadata["tags"] if tag.strip()]

            page = Page(
                title=metadata["title"],
                path=relative_path,
                content=html_content,
                modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
                category=metadata["category"],
                tags=tags,
                description=metadata["description"],
                is_index=is_index,
            )

            self.pages[relative_path] = page

            if page.category:
                self.categories[page.category].append(page)
            for tag in page.tags:
                self.tags[tag].append(page)

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    def _process_content(self) -> None:
        """Process all content in the input directory"""
        for file_path in self._walk_directory(self.input_dir):
            if file_path.suffix in self.SUPPORTED_CONTENT:
                self._process_markdown(file_path)

    def _organize_content(self) -> None:
        """Organize pages by category and tags"""
        for category in self.categories:
            self.categories[category].sort(key=lambda p: p.title)
        for tag in self.tags:
            self.tags[tag].sort(key=lambda p: p.title)

    def _copy_assets(self) -> None:
        """Copy non-markdown files to output directory"""
        for file_path in self._walk_directory(self.input_dir):
            if file_path.suffix not in self.SUPPORTED_CONTENT:
                relative_path = file_path.relative_to(self.input_dir)
                output_path = self.output_dir / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.parent.chmod(0o755)
                shutil.copy2(file_path, output_path)
                output_path.chmod(0o644)

    def _get_page_context(self, page: Page) -> dict:
        """Generate context for page template"""
        meta_description = page.description
        if not meta_description and page.content:
            plain_content = re.sub(r"<[^>]+>", "", page.content)
            meta_description = (
                plain_content[:160].strip() + "..."
                if len(plain_content) > 160
                else plain_content
            )

        schema_json = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": page.title,
            "dateModified": page.modified_date.isoformat(),
            "description": meta_description,
        }
        if page.category:
            schema_json["articleSection"] = page.category
        if page.tags:
            schema_json["keywords"] = ",".join(page.tags)

        canonical_url = f"{self.site_domain}/{page.path.with_suffix('.html')}"

        return {
            "title": page.title,
            "content": page.content,
            "modified_date": page.modified_date,
            "category": page.category,
            "tags": page.tags,
            "meta_description": meta_description,
            "schema_json": json.dumps(schema_json),
            "canonical_url": canonical_url,
            "navigation": self._generate_navigation(page),
            "breadcrumbs": self._generate_breadcrumbs(page),
            "current_year": datetime.now().year
        }

    def _generate_navigation(self, current_page: Page) -> str:
        """Generate navigation links"""
        nav_items = []

        if not current_page.is_index:
            nav_items.append('<a href="/index.html">Home</a>')
        if self.categories:
            nav_items.append('<a href="/categories/index.html">Categories</a>')
        if self.tags:
            nav_items.append('<a href="/tags/index.html">Tags</a>')

        return "\n".join(nav_items)

    def _generate_breadcrumbs(self, page: Page) -> str:
        """Generate breadcrumb navigation"""
        parts = ['<a href="/index.html">Home</a>']

        if page.category:
            parts.append(
                f'<a href="/categories/{quote(page.category.lower())}.html">'
                f'{page.category}</a>'
            )
        if not page.is_index:
            parts.append(page.title)

        return " » ".join(parts)

    def _generate_special_pages(self) -> None:
        """Generate special pages like main index, category index and tag index"""
        self._generate_main_index()
        self._generate_taxonomy_pages()

    def _generate_taxonomy_pages(self) -> None:
        """Generate category and tag index pages"""
        # Generate categories index
        if self.categories:
            content = "<ul>"
            for category, pages in sorted(self.categories.items()):
                content += f'\n<li><a href="/categories/{quote(category.lower())}.html">{category}</a> ({len(pages)} pages)</li>'
            content += "</ul>"

            categories_page = Page(
                title="Categories",
                path=Path("categories/index.md"),
                content=content,
                modified_date=datetime.now(),
                category=None,
                tags=[],
                description="Index of all categories",
                is_index=True,
            )
            self.pages[categories_page.path] = categories_page

        # Generate tags index
        if self.tags:
            content = "<ul>"
            for tag, pages in sorted(self.tags.items()):
                content += f'\n<li><a href="/tags/{quote(tag.lower())}.html">{tag}</a> ({len(pages)} pages)</li>'
            content += "</ul>"

            tags_page = Page(
                title="Tags",
                path=Path("tags/index.md"),
                content=content,
                modified_date=datetime.now(),
                category=None,
                tags=[],
                description="Index of all tags",
                is_index=True,
            )
            self.pages[tags_page.path] = tags_page

    def _generate_main_index(self) -> None:
        """Generate the main index.html page"""
        regular_pages = [
            p for p in self.pages.values()
            if not (p.is_index or str(p.path).startswith(("categories/", "tags/")))
        ]
        recent_pages = sorted(
            regular_pages,
            key=lambda p: p.modified_date,
            reverse=True
        )[:10]

        tag_counts = {tag: len(pages) for tag, pages in self.tags.items()}
        popular_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:20]

        context = {
            "stats": {
                "notes": len(regular_pages),
                "categories": len(self.categories),
                "tags": len(self.tags)
            },
            "recent_pages": [
                {
                    "url": f"/{page.path.with_suffix('.html')}",
                    "title": page.title,
                    "date": page.modified_date.strftime("%Y-%m-%d"),
                    "category": page.category
                }
                for page in recent_pages
            ],
            "categories": [
                {
                    "url": f"/categories/{quote(category.lower())}.html",
                    "name": category,
                    "count": len(pages)
                }
                for category, pages in sorted(self.categories.items())
            ],
            "popular_tags": [
                {
                    "url": f"/tags/{quote(tag.lower())}.html",
                    "name": tag,
                    "count": count,
                    "size_class": min(count, 5)
                }
                for tag, count in popular_tags
            ]
        }

        content = self.jinja_env.get_template('index').render(**context)
        index_page = Page(
            title="",
            path=Path("index.md"),
            content=content,
            modified_date=datetime.now(),
            category=None,
            tags=[],
            description="So so many notes",
            is_index=True,
        )

        output_path = self.output_dir / "index.html"
        html_content = self.jinja_env.get_template('base').render(
            **self._get_page_context(index_page)
        )
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(0o644)

    def _generate_html_pages(self) -> None:
        """Generate HTML pages for all processed content"""
        for page in self.pages.values():
            self._generate_page(page)

        # Generate category pages
        for category, pages in self.categories.items():
            self._generate_category_page(category, pages)

        # Generate tag pages
        for tag, pages in self.tags.items():
            self._generate_tag_page(tag, pages)

    def _generate_page(self, page: Page) -> None:
        """Generate a single HTML page"""
        output_path = self.output_dir / page.path.with_suffix(".html")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.parent.chmod(0o755)

        html_content = self.jinja_env.get_template('base').render(
            **self._get_page_context(page)
        )
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(0o644)

    def _generate_category_page(self, category: str, pages: List[Page]) -> None:
        """Generate a page for a specific category"""
        output_path = self.output_dir / "categories" / f"{category.lower()}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.parent.chmod(0o755)

        content = f"<h2>Category: {category}</h2>\n<ul>"
        for page in sorted(pages, key=lambda p: p.title):
            page_url = f"/{page.path.with_suffix('.html')}"
            content += f'\n<li><a href="{page_url}">{page.title}</a></li>'
        content += "</ul>"

        page = Page(
            title=f"Category: {category}",
            path=Path(f"categories/{category.lower()}.md"),
            content=content,
            modified_date=datetime.now(),
            category=None,
            tags=[],
            description=f"Pages in category {category}",
            is_index=False,
        )

        html_content = self.jinja_env.get_template('base').render(
            **self._get_page_context(page)
        )
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(0o644)

    def _generate_tag_page(self, tag: str, pages: List[Page]) -> None:
        """Generate a page for a specific tag"""
        output_path = self.output_dir / "tags" / f"{tag.lower()}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.parent.chmod(0o755)

        content = f"<h2>Tag: {tag}</h2>\n<ul>"
        for page in sorted(pages, key=lambda p: p.title):
            page_url = f"/{page.path.with_suffix('.html')}"
            content += f'\n<li><a href="{page_url}">{page.title}</a></li>'
        content += "</ul>"

        page = Page(
            title=f"Tag: {tag}",
            path=Path(f"tags/{tag.lower()}.md"),
            content=content,
            modified_date=datetime.now(),
            category=None,
            tags=[],
            description=f"Pages tagged with {tag}",
            is_index=False,
        )

        html_content = self.jinja_env.get_template('base').render(
            **self._get_page_context(page)
        )
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(0o644)


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a static site from markdown files"
    )
    parser.add_argument("input_dir", help="Input directory containing content")
    parser.add_argument("output_dir", help="Output directory for generated site")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        generator = SiteGenerator(args.input_dir, args.output_dir)
        generator.generate_site()
    except Exception as e:
        logger.error(f"Failed to generate site: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()