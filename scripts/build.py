from dataclasses import dataclass
import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set, Callable
import shutil
import markdown
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
import re
from collections import defaultdict
from jinja2 import Environment, BaseLoader, TemplateNotFound, select_autoescape
from template.html import BASE_TEMPLATE, INDEX_TEMPLATE
from template.css import STYLES_TEMPLATE
from template.js import TAXONOMY_JS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Page:
    title: str
    path: Path
    content: str
    modified_date: datetime
    category: Optional[str]
    tags: List[str]
    description: Optional[str]
    is_index: bool = False
    css_classes: List[str] = None


class JinjaTemplateLoader(BaseLoader):
    def __init__(self, templates):
        self.templates = templates

    def get_source(self, environment, template):
        if template not in self.templates:
            raise TemplateNotFound(template)
        return self.templates[template], None, lambda: True


class SiteGenerator:

    MARKDOWN_EXTENSIONS = [
        "meta",
        "toc",
        "fenced_code",
        "tables",
        "attr_list",
        "footnotes",
        "def_list",
        "admonition",
        "mdx_truly_sane_lists",
    ]
    SUPPORTED_CONTENT = {".md", ".markdown"}
    IGNORED_DIRECTORIES = {
        ".git",
        "__pycache__",
        "node_modules",
        ".github",
        "nlp.venv",
        "site",
        "venv",
        ".venv",
    }
    DEFAULT_CSS_CLASSES = ["markdown-content", "content"]
    DEFAULT_PERMISSIONS = {"directory": 0o755, "file": 0o644}

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

        templates = {
            "base": BASE_TEMPLATE,
            "index": INDEX_TEMPLATE,
        }

        self.jinja_env = Environment(
            loader=JinjaTemplateLoader(templates),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.jinja_env.filters["urlencode"] = quote

    def generate_site(self) -> None:

        try:
            self._prepare_output_directory()
            self._process_content()
            self._organize_content()
            self._copy_assets()
            self._generate_special_pages()
            self._generate_html_pages()
            self._copy_themes()
            logger.info(f"Site generated successfully in {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to generate site: {str(e)}")
            raise

    def _prepare_output_directory(self) -> None:

        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self._create_directory(self.output_dir)
        self._create_directory(self.output_dir / "assets")

    def _create_directory(self, directory: Path) -> None:

        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(self.DEFAULT_PERMISSIONS["directory"])

    def _walk_directory(self, directory: Path) -> List[Path]:

        return [
            item
            for item in directory.rglob("*")
            if not any(ignored in item.parts for ignored in self.IGNORED_DIRECTORIES)
        ]

    def _extract_metadata(self, file_path: Path, content: str) -> dict:

        md = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
        md.convert(content)

        default_title = file_path.stem.replace("-", " ").title()

        if not hasattr(md, "Meta"):
            return {
                "title": default_title,
                "category": None,
                "tags": [],
                "description": None,
            }

        metadata = {
            "title": md.Meta.get("title", [default_title])[0],
            "category": md.Meta.get("category", [None])[0],
            "tags": [],
            "description": md.Meta.get("description", [None])[0],
        }

        if "tags" in md.Meta and md.Meta["tags"][0]:
            metadata["tags"] = [
                tag.strip() for tag in md.Meta["tags"][0].split(",") if tag.strip()
            ]

        return metadata

    def _process_markdown(self, file_path: Path) -> None:

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
                css_classes=self.DEFAULT_CSS_CLASSES,
            )

            self._add_page_to_collections(page)

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    def _add_page_to_collections(self, page: Page) -> None:

        self.pages[page.path] = page

        if page.category:
            self.categories[page.category].append(page)

        for tag in page.tags:
            self.tags[tag].append(page)

    def _process_html(self, file_path: Path) -> None:

        try:
            relative_path = file_path.relative_to(self.input_dir)
            output_path = self.output_dir / relative_path
            self._ensure_parent_directory(output_path)
            shutil.copy2(file_path, output_path)
            output_path.chmod(self.DEFAULT_PERMISSIONS["file"])

            page = Page(
                title=file_path.stem,
                path=relative_path,
                content="",
                modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
                category=None,
                tags=[],
                description=None,
                is_index=False,
            )

            self.pages[relative_path] = page

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    def _ensure_parent_directory(self, path: Path) -> None:

        parent = path.parent
        if not parent.exists():
            self._create_directory(parent)

    def _process_content(self) -> None:

        for file_path in self._walk_directory(self.input_dir):
            if file_path.is_file() and file_path.suffix in self.SUPPORTED_CONTENT:
                if file_path.suffix in {".md", ".markdown"}:
                    self._process_markdown(file_path)
            elif file_path.is_dir() and file_path.name not in self.IGNORED_DIRECTORIES:
                self._process_directory(file_path)

    def _process_directory(self, directory: Path) -> None:

        links_html = self._create_directory_index_links(directory)
        if links_html:
            self._generate_dir_index(directory / "index.html", links_html)

    def _create_directory_index_links(self, directory: Path) -> str:

        links = []
        for item in directory.iterdir():
            if item.is_file():
                links.append(
                    f'<li><a href="{item.name.replace(".md", ".html")}">{item.name}</a></li>'
                )
        return "\n".join(links)

    def _organize_content(self) -> None:

        for category in self.categories:
            self.categories[category].sort(key=lambda p: p.title)
        for tag in self.tags:
            self.tags[tag].sort(key=lambda p: p.title)

    def _copy_assets(self) -> None:

        for file_path in self._walk_directory(self.input_dir):
            if file_path.is_file() and file_path.suffix not in self.SUPPORTED_CONTENT:
                self._copy_file_to_output(file_path)

    def _copy_file_to_output(self, file_path: Path) -> None:

        relative_path = file_path.relative_to(self.input_dir)
        output_path = self.output_dir / relative_path
        self._ensure_parent_directory(output_path)
        shutil.copy2(file_path, output_path)
        output_path.chmod(self.DEFAULT_PERMISSIONS["file"])

    def _get_page_context(self, page: Page) -> dict:

        meta_description = self._generate_meta_description(page)
        schema_json = self._generate_schema_json(page, meta_description)
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
            "current_year": datetime.now().year,
            "css_selector": (
                " ".join(page.css_classes) if page.css_classes else "content"
            ),
        }

    def _generate_meta_description(self, page: Page) -> str:

        if page.description:
            return page.description

        if page.content:
            plain_content = re.sub(r"<[^>]+>", "", page.content)
            return (
                plain_content[:160].strip() + "..."
                if len(plain_content) > 160
                else plain_content
            )

        return ""

    def _generate_schema_json(self, page: Page, description: str) -> dict:

        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": page.title,
            "dateModified": page.modified_date.isoformat(),
            "description": description,
        }

        if page.category:
            schema["articleSection"] = page.category

        if page.tags:
            schema["keywords"] = ",".join(page.tags)

        return schema

    def _generate_navigation(self, current_page: Page) -> str:

        nav_items = []

        if not current_page.is_index:
            nav_items.append('<a href="/index.html">Home</a>')
        if self.categories:
            nav_items.append('<a href="/categories/index.html">Categories</a>')
        if self.tags:
            nav_items.append('<a href="/tags/index.html">Tags</a>')

        return "\n".join(nav_items)

    def _generate_breadcrumbs(self, page: Page) -> str:

        parts = ['<a href="/index.html">Home</a>']

        if page.category:
            parts.append(
                f'<a href="/categories/{quote(page.category.lower())}.html">'
                f"{page.category}</a>"
            )
        if not page.is_index:
            parts.append(page.title)

        return " » ".join(parts)

    def _generate_special_pages(self) -> None:

        self._generate_main_index()
        self._generate_taxonomy_pages()

    def _generate_taxonomy_pages(self) -> None:

        if self.categories:
            self._generate_taxonomy_index("categories", self.categories)

        if self.tags:
            self._generate_taxonomy_index("tags", self.tags)

        self._ensure_taxonomy_js()
        self._ensure_css()

    def _generate_taxonomy_index(
        self, taxonomy_type: str, taxonomy_items: Dict[str, List[Page]]
    ) -> None:

        content = self._create_taxonomy_list_html(taxonomy_type, taxonomy_items)

        index_page = Page(
            title=taxonomy_type.capitalize(),
            path=Path(f"{taxonomy_type}/index.md"),
            content=content,
            modified_date=datetime.now(),
            category=None,
            tags=[],
            description=f"Browse all content {taxonomy_type}",
            is_index=True,
        )

        self.pages[index_page.path] = index_page

    def _create_taxonomy_list_html(
        self, taxonomy_type: str, taxonomy_items: Dict[str, List[Page]]
    ) -> str:

        html = """
        <div class="taxonomy-container">
            <ul class="original-taxonomy-list" style="display:none;">
        """

        for name, pages in sorted(taxonomy_items.items()):
            html += f'\n<li><a href="/{taxonomy_type}/{quote(name.lower())}.html">{name}</a> ({len(pages)} pages)</li>'

        html += """
            </ul>
            <noscript>
                <ul>
        """

        for name, pages in sorted(taxonomy_items.items()):
            html += f'\n<li><a href="/{taxonomy_type}/{quote(name.lower())}.html">{name}</a> ({len(pages)} pages)</li>'

        html += """
                </ul>
            </noscript>
        </div>
        <script src="/js/taxonomy.js" defer></script>
        """

        return html

    def _ensure_css(self) -> None:

        self._ensure_static_file("css", "styles.css", STYLES_TEMPLATE)

    def _ensure_taxonomy_js(self) -> None:

        self._ensure_static_file("js", "taxonomy.js", TAXONOMY_JS)

    def _ensure_static_file(self, subdir: str, filename: str, content: str) -> None:

        directory = self.output_dir / subdir
        self._create_directory(directory)

        file_path = directory / filename

        if not file_path.exists() or datetime.fromtimestamp(
            file_path.stat().st_mtime
        ) < datetime.now() - timedelta(minutes=5):
            with open(file_path, "w") as f:
                f.write(content)

    def _generate_main_index(self) -> None:

        regular_pages = self._get_regular_pages()
        recent_pages = sorted(
            regular_pages, key=lambda p: p.modified_date, reverse=True
        )[:10]

        tag_counts = {tag: len(pages) for tag, pages in self.tags.items()}
        popular_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:20]

        context = self._build_main_index_context(recent_pages, popular_tags)
        content = self.jinja_env.get_template("index").render(**context)

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
        html_content = self.jinja_env.get_template("base").render(
            **self._get_page_context(index_page)
        )
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(self.DEFAULT_PERMISSIONS["file"])

    def _get_regular_pages(self) -> List[Page]:

        return [
            p
            for p in self.pages.values()
            if not (p.is_index or str(p.path).startswith(("categories/", "tags/")))
        ]

    def _build_main_index_context(
        self, recent_pages: List[Page], popular_tags: List[Tuple[str, int]]
    ) -> dict:

        regular_pages = self._get_regular_pages()

        return {
            "stats": {
                "notes": len(regular_pages),
                "categories": len(self.categories),
                "tags": len(self.tags),
            },
            "recent_pages": [
                {
                    "url": f"/{page.path.with_suffix('.html')}",
                    "title": page.title,
                    "date": page.modified_date.strftime("%Y-%m-%d"),
                    "category": page.category,
                }
                for page in recent_pages
            ],
            "categories": [
                {
                    "url": f"/categories/{quote(category.lower())}.html",
                    "name": category,
                    "count": len(pages),
                }
                for category, pages in sorted(self.categories.items())
            ],
            "popular_tags": [
                {
                    "url": f"/tags/{quote(tag.lower())}.html",
                    "name": tag,
                    "count": count,
                    "size_class": min(count, 5),
                }
                for tag, count in popular_tags
            ],
            "top_level_dirs": [
                {
                    "name": dir.name,
                    "url": f"/{dir.name}/index.html",
                }
                for dir in self.input_dir.iterdir()
                if dir.is_dir() and dir.name not in self.IGNORED_DIRECTORIES
            ],
        }

    def _generate_dir_index(self, dir_path: Path, links_html: str) -> None:

        output_path = self.output_dir / dir_path.with_suffix(".html")
        self._ensure_parent_directory(output_path)

        content = f"<ul>{links_html}</ul>"
        page = Page(
            title=f"Index of {dir_path.parent.name}",
            path=dir_path,
            content=content,
            modified_date=datetime.now(),
            category=None,
            tags=[],
            description=f"Index of {dir_path.parent.name}",
            is_index=False,
        )

        html_content = self.jinja_env.get_template("base").render(
            **self._get_page_context(page)
        )
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(self.DEFAULT_PERMISSIONS["file"])
        logger.info(f"Generated index page for {dir_path}")

    def _generate_html_pages(self) -> None:

        for page in self.pages.values():
            self._generate_page(page)

        self._generate_taxonomy_collection_pages("category", self.categories)
        self._generate_taxonomy_collection_pages("tag", self.tags)

    def _generate_taxonomy_collection_pages(
        self, taxonomy_type: str, collection: Dict[str, List[Page]]
    ) -> None:

        taxonomy_plural = f"{taxonomy_type}s"

        for name, pages in collection.items():
            output_path = self.output_dir / taxonomy_plural / f"{name.lower()}.html"
            self._ensure_parent_directory(output_path)

            content = f"<h2>{taxonomy_type.title()}: {name}</h2>\n<ul>"
            for page in sorted(pages, key=lambda p: p.title):
                page_url = f"/{page.path.with_suffix('.html')}"
                content += f'\n<li><a href="{page_url}">{page.title}</a></li>'
            content += "</ul>"

            page = Page(
                title=f"{taxonomy_type.title()}: {name}",
                path=Path(f"{taxonomy_plural}/{name.lower()}.md"),
                content=content,
                modified_date=datetime.now(),
                category=None,
                tags=[],
                description=f"Pages in {taxonomy_type} {name}",
                is_index=False,
            )

            html_content = self.jinja_env.get_template("base").render(
                **self._get_page_context(page)
            )
            output_path.write_text(html_content, encoding="utf-8")
            output_path.chmod(self.DEFAULT_PERMISSIONS["file"])

    def _generate_page(self, page: Page) -> None:

        output_path = self.output_dir / page.path.with_suffix(".html")
        self._ensure_parent_directory(output_path)

        html_content = self.jinja_env.get_template("base").render(
            **self._get_page_context(page)
        )
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(self.DEFAULT_PERMISSIONS["file"])

    def _copy_themes(self) -> None:

        from_dir = self.input_dir / "scripts" / "template" / "themes"
        to_dir = self.output_dir / "css" / "themes"

        self._create_directory(to_dir)

        for theme_file in self._walk_directory(from_dir):
            if theme_file.is_file():
                relative_path = theme_file.relative_to(from_dir)
                output_path = to_dir / relative_path
                self._ensure_parent_directory(output_path)
                shutil.copy2(theme_file, output_path)
                output_path.chmod(self.DEFAULT_PERMISSIONS["file"])

    def _generate_slides(self) -> None:

        input_dir = "slides/"
        output_dir = "site/slides/"

        os.makedirs(output_dir, exist_ok=True)

        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith(".md"):
                    input_file = os.path.join(root, file)
                    output_file = os.path.join(
                        output_dir,
                        os.path.relpath(root, input_dir),
                        file[:-3] + ".html",
                    )
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    subprocess.run(
                        [
                            "npx",
                            "@marp-team/marp-cli",
                            "--html",
                            input_file,
                            "-o",
                            output_file,
                        ]
                    )

        shutil.copytree("slides/assets", "site/slides/assets", dirs_exist_ok=True)


def main():

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

    shutil.copy("sitemap.xml", "site/sitemap.xml")
    shutil.copy("robots.txt", "site/robots.txt")
