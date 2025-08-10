from dataclasses import dataclass, field
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

# Import templates (these need to be defined separately)
try:
    from template.html import BASE_TEMPLATE, INDEX_TEMPLATE
    from template.css import STYLES_TEMPLATE
    from template.js import TAXONOMY_JS
except ImportError:
    # Fallback templates if imports fail
    BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <meta name="description" content="{{ meta_description }}">
    <link rel="canonical" href="{{ canonical_url }}">
    <link rel="stylesheet" href="/css/styles.css">
    {% if schema_json %}
    <script type="application/ld+json">{{ schema_json|safe }}</script>
    {% endif %}
</head>
<body>
    <header>
        <nav>{{ navigation|safe }}</nav>
        <div class="breadcrumbs">{{ breadcrumbs|safe }}</div>
    </header>
    <main class="{{ css_selector }}">
        <h1>{{ title }}</h1>
        {{ content|safe }}
    </main>
    <footer>
        <p>&copy; {{ current_year }} Notes Site</p>
    </footer>
</body>
</html>
    """

    INDEX_TEMPLATE = """
<div class="stats">
    <p>{{ stats.notes }} notes, {{ stats.categories }} categories, {{ stats.tags }} tags</p>
</div>

<section class="recent-pages">
    <h2>Recent Pages</h2>
    <ul>
    {% for page in recent_pages %}
        <li>
            <a href="{{ page.url }}">{{ page.title }}</a>
            <span class="date">{{ page.date }}</span>
            {% if page.category %}<span class="category">{{ page.category }}</span>{% endif %}
        </li>
    {% endfor %}
    </ul>
</section>

<section class="categories">
    <h2>Categories</h2>
    <ul>
    {% for category in categories %}
        <li><a href="{{ category.url }}">{{ category.name }}</a> ({{ category.count }})</li>
    {% endfor %}
    </ul>
</section>

<section class="popular-tags">
    <h2>Popular Tags</h2>
    <div class="tag-cloud">
    {% for tag in popular_tags %}
        <a href="{{ tag.url }}" class="tag-{{ tag.size_class }}">{{ tag.name }}</a>
    {% endfor %}
    </div>
</section>
    """

    STYLES_TEMPLATE = """
body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
.content { max-width: 800px; margin: 0 auto; }
nav a { margin-right: 15px; }
.breadcrumbs { margin: 10px 0; color: #666; }
.tag-cloud a { margin: 5px; padding: 5px; background: #eee; }
.stats { background: #f5f5f5; padding: 10px; border-radius: 5px; }
    """

    TAXONOMY_JS = """
document.addEventListener('DOMContentLoaded', function() {
    const list = document.querySelector('.original-taxonomy-list');
    if (list) {
        list.style.display = 'block';
    }
});
    """

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Page:
    """Represents a page in the site with its metadata and content."""

    title: str
    path: Path
    content: str
    modified_date: datetime
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    is_index: bool = False
    css_classes: List[str] = field(default_factory=lambda: ["content"])


class JinjaTemplateLoader(BaseLoader):
    """Custom Jinja2 template loader for in-memory templates."""

    def __init__(self, templates: Dict[str, str]):
        self.templates = templates

    def get_source(self, environment, template):
        if template not in self.templates:
            raise TemplateNotFound(template)
        return self.templates[template], None, lambda: True


class SiteGenerator:
    """Static site generator that converts Markdown files to HTML pages."""

    MARKDOWN_EXTENSIONS = [
        "meta",
        "toc",
        "fenced_code",
        "tables",
        "attr_list",
        "footnotes",
        "def_list",
        "admonition",
    ]
    SUPPORTED_CONTENT = {".md", ".markdown"}
    SUPPORTED_HTML = {".html", ".htm"}
    IGNORED_DIRECTORIES = {
        ".git",
        "__pycache__",
        "node_modules",
        ".github",
        "nlp.venv",
        "site",
        "venv",
        ".venv",
        ".DS_Store",
    }
    DEFAULT_CSS_CLASSES = ["content"]
    DEFAULT_PERMISSIONS = {"directory": 0o755, "file": 0o644}

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        site_domain: str = "https://notes.elimelt.com",
    ):
        self.site_domain = site_domain.rstrip("/")
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()

        # Validate input directory exists
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        self.markdown_converter = markdown.Markdown(
            extensions=self.MARKDOWN_EXTENSIONS,
            extension_configs={"toc": {"anchorlink": True}},
        )
        self.pages: Dict[Path, Page] = {}
        self.categories: Dict[str, List[Page]] = defaultdict(list)
        self.tags: Dict[str, List[Page]] = defaultdict(list)
        self._setup_jinja()

    def _setup_jinja(self) -> None:
        """Initialize Jinja2 environment with templates."""
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
        """Generate the complete static site."""
        try:
            logger.info("Starting site generation...")
            self._prepare_output_directory()
            self._process_content()
            self._organize_content()
            self._copy_assets()
            self._generate_special_pages()
            self._generate_html_pages()
            self._copy_themes()
            self._copy_static_files()
            logger.info(f"Site generated successfully in {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to generate site: {str(e)}")
            raise

    def _prepare_output_directory(self) -> None:
        """Prepare the output directory by cleaning and creating necessary subdirectories."""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

        self._create_directory(self.output_dir)

        # Create standard subdirectories
        for subdir in ["css", "js", "assets", "categories", "tags"]:
            self._create_directory(self.output_dir / subdir)

    def _create_directory(self, directory: Path) -> None:
        """Create a directory with proper permissions."""
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.chmod(self.DEFAULT_PERMISSIONS["directory"])
        except (OSError, AttributeError):
            # Skip chmod on systems where it's not supported
            pass

    def _walk_directory(self, directory: Path) -> List[Path]:
        """Walk directory and return all files/directories not in ignored list."""
        if not directory.exists():
            return []

        return [
            item
            for item in directory.rglob("*")
            if not any(ignored in item.parts for ignored in self.IGNORED_DIRECTORIES)
            and not item.name.startswith(".")
        ]

    def _extract_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract metadata from markdown file."""
        # Create a fresh markdown instance for metadata extraction
        md = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
        md.convert(content)

        default_title = file_path.stem.replace("-", " ").replace("_", " ").title()

        metadata = {
            "title": default_title,
            "category": None,
            "tags": [],
            "description": None,
        }

        if hasattr(md, "Meta") and md.Meta:
            metadata["title"] = md.Meta.get("title", [default_title])[0]
            metadata["category"] = md.Meta.get("category", [None])[0]
            metadata["description"] = md.Meta.get("description", [None])[0]

            # Process tags
            if "tags" in md.Meta and md.Meta["tags"] and md.Meta["tags"][0]:
                raw_tags = md.Meta["tags"][0]
                if isinstance(raw_tags, str):
                    metadata["tags"] = [
                        tag.strip().lower()
                        for tag in raw_tags.split(",")
                        if tag.strip()
                    ]

        return metadata

    def _process_markdown(self, file_path: Path) -> None:
        """Process a markdown file and convert it to a Page object."""
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = self._extract_metadata(file_path, content)

            # Convert markdown to HTML
            html_content = self.markdown_converter.convert(content)

            # Reset markdown converter for next file
            self.markdown_converter.reset()

            relative_path = file_path.relative_to(self.input_dir)
            is_index = file_path.stem.lower() == "index"

            page = Page(
                title=metadata["title"],
                path=relative_path,
                content=html_content,
                modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
                category=metadata["category"],
                tags=metadata["tags"],
                description=metadata["description"],
                is_index=is_index,
                css_classes=self.DEFAULT_CSS_CLASSES.copy(),
            )

            self._add_page_to_collections(page)
            logger.debug(f"Processed markdown: {file_path}")

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    def _add_page_to_collections(self, page: Page) -> None:
        """Add a page to the appropriate collections (pages, categories, tags)."""
        self.pages[page.path] = page

        if page.category:
            self.categories[page.category].append(page)

        for tag in page.tags:
            self.tags[tag].append(page)

    def _process_html(self, file_path: Path) -> None:
        """Process an HTML file by copying it to output directory."""
        try:
            relative_path = file_path.relative_to(self.input_dir)
            output_path = self.output_dir / relative_path
            self._ensure_parent_directory(output_path)

            shutil.copy2(file_path, output_path)
            self._set_file_permissions(output_path)

            # Create a page entry for the HTML file
            page = Page(
                title=file_path.stem.replace("-", " ").replace("_", " ").title(),
                path=relative_path,
                content="",
                modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
                category=None,
                tags=[],
                description=None,
                is_index=file_path.stem.lower() == "index",
            )

            self.pages[relative_path] = page
            logger.debug(f"Processed HTML: {file_path}")

        except Exception as e:
            logger.error(f"Failed to process HTML file {file_path}: {str(e)}")

    def _ensure_parent_directory(self, path: Path) -> None:
        """Ensure the parent directory of a path exists."""
        parent = path.parent
        if not parent.exists():
            self._create_directory(parent)

    def _set_file_permissions(self, file_path: Path) -> None:
        """Set file permissions, with error handling for unsupported systems."""
        try:
            file_path.chmod(self.DEFAULT_PERMISSIONS["file"])
        except (OSError, AttributeError):
            # Skip chmod on systems where it's not supported
            pass

    def _process_content(self) -> None:
        """Process all content files in the input directory."""
        for file_path in self._walk_directory(self.input_dir):
            if not file_path.is_file():
                continue

            if file_path.suffix in self.SUPPORTED_CONTENT:
                self._process_markdown(file_path)
            elif file_path.suffix in self.SUPPORTED_HTML:
                self._process_html(file_path)

    def _organize_content(self) -> None:
        """Sort content in categories and tags by title."""
        for category_pages in self.categories.values():
            category_pages.sort(key=lambda p: p.title.lower())

        for tag_pages in self.tags.values():
            tag_pages.sort(key=lambda p: p.title.lower())

    def _copy_assets(self) -> None:
        """Copy non-content files to the output directory."""
        for file_path in self._walk_directory(self.input_dir):
            if (
                file_path.is_file()
                and file_path.suffix not in self.SUPPORTED_CONTENT
                and file_path.suffix not in self.SUPPORTED_HTML
            ):
                self._copy_file_to_output(file_path)

    def _copy_file_to_output(self, file_path: Path) -> None:
        """Copy a file to the output directory maintaining structure."""
        try:
            relative_path = file_path.relative_to(self.input_dir)
            output_path = self.output_dir / relative_path
            self._ensure_parent_directory(output_path)

            shutil.copy2(file_path, output_path)
            self._set_file_permissions(output_path)
            logger.debug(f"Copied asset: {file_path}")

        except Exception as e:
            logger.error(f"Failed to copy file {file_path}: {str(e)}")

    def _get_page_context(self, page: Page) -> Dict[str, Any]:
        """Get template context for a page."""
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
            "css_selector": " ".join(page.css_classes),
        }

    def _generate_meta_description(self, page: Page) -> str:
        """Generate meta description for a page."""
        if page.description:
            return page.description[:160]

        if page.content:
            # Remove HTML tags and get first 160 characters
            plain_content = re.sub(r"<[^>]+>", "", page.content)
            plain_content = re.sub(r"\s+", " ", plain_content).strip()
            return (
                plain_content[:157] + "..."
                if len(plain_content) > 160
                else plain_content
            )

        return f"Page: {page.title}"

    def _generate_schema_json(self, page: Page, description: str) -> Dict[str, Any]:
        """Generate JSON-LD schema for a page."""
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": page.title,
            "dateModified": page.modified_date.isoformat(),
            "description": description,
            "url": f"{self.site_domain}/{page.path.with_suffix('.html')}",
        }

        if page.category:
            schema["articleSection"] = page.category

        if page.tags:
            schema["keywords"] = ",".join(page.tags)

        return schema

    def _generate_navigation(self, current_page: Page) -> str:
        """Generate navigation HTML for a page."""
        nav_items = []

        # Add GitHub link
        nav_items.append(
            '<a href="https://github.com/elimelt/notes" '
            'style="font-size:24px; color: white;" class="fa">&#xf09b;</a>'
        )

        nav_items.append('<a href="/index.html">Home</a>')

        # Add categories link if categories exist
        if self.categories:
            nav_items.append('<a href="/categories/index.html">Categories</a>')

        # Add tags link if tags exist
        if self.tags:
            nav_items.append('<a href="/tags/index.html">Tags</a>')

        return " | ".join(nav_items)

    def _generate_breadcrumbs(self, page: Page) -> str:
        """Generate breadcrumb navigation for a page."""
        parts = ['<a href="/index.html">Home</a>']

        # Add category if present
        if page.category:
            category_url = f"/categories/{quote(page.category.lower())}.html"
            parts.append(f'<a href="{category_url}">{page.category}</a>')

        # Add page title if not index
        if not page.is_index:
            parts.append(page.title)

        return " » ".join(parts)

    def _generate_special_pages(self) -> None:
        """Generate special pages like index, categories, and tags."""
        self._generate_main_index()
        self._generate_taxonomy_pages()

    def _generate_taxonomy_pages(self) -> None:
        """Generate taxonomy index pages for categories and tags."""
        if self.categories:
            self._generate_taxonomy_index("categories", self.categories)

        if self.tags:
            self._generate_taxonomy_index("tags", self.tags)

        # Ensure CSS and JS files are created
        self._ensure_css()
        self._ensure_taxonomy_js()

    def _generate_taxonomy_index(
        self, taxonomy_type: str, taxonomy_items: Dict[str, List[Page]]
    ) -> None:
        """Generate an index page for a taxonomy (categories or tags)."""
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

        # Add to pages collection
        self.pages[index_page.path] = index_page

        # Generate the HTML file immediately
        output_path = self.output_dir / taxonomy_type / "index.html"
        self._ensure_parent_directory(output_path)

        try:
            html_content = self.jinja_env.get_template("base").render(
                **self._get_page_context(index_page)
            )
            output_path.write_text(html_content, encoding="utf-8")
            self._set_file_permissions(output_path)
            logger.info(f"Generated {taxonomy_type} index page")
        except Exception as e:
            logger.error(f"Failed to generate {taxonomy_type} index: {str(e)}")

    def _create_taxonomy_list_html(
        self, taxonomy_type: str, taxonomy_items: Dict[str, List[Page]]
    ) -> str:
        """Create HTML for taxonomy list with JavaScript enhancement."""
        html_parts = [
            '<div class="taxonomy-container">',
            '    <ul class="original-taxonomy-list" style="display:none;">',
        ]

        # Add items to the list
        for name, pages in sorted(taxonomy_items.items()):
            url = f"/{taxonomy_type}/{quote(name.lower())}.html"
            html_parts.append(
                f'        <li><a href="{url}">{name}</a> ({len(pages)} pages)</li>'
            )

        html_parts.extend(["    </ul>", "    <noscript>", "        <ul>"])

        # Fallback for no-JS users
        for name, pages in sorted(taxonomy_items.items()):
            url = f"/{taxonomy_type}/{quote(name.lower())}.html"
            html_parts.append(
                f'            <li><a href="{url}">{name}</a> ({len(pages)} pages)</li>'
            )

        html_parts.extend(
            [
                "        </ul>",
                "    </noscript>",
                "</div>",
                '<script src="/js/taxonomy.js" defer></script>',
            ]
        )

        return "\n".join(html_parts)

    def _ensure_css(self) -> None:
        """Ensure CSS file exists in output directory."""
        self._ensure_static_file("css", "styles.css", STYLES_TEMPLATE)

    def _ensure_taxonomy_js(self) -> None:
        """Ensure JavaScript file exists in output directory."""
        self._ensure_static_file("js", "taxonomy.js", TAXONOMY_JS)

    def _ensure_static_file(self, subdir: str, filename: str, content: str) -> None:
        """Ensure a static file exists and is up to date."""
        directory = self.output_dir / subdir
        self._create_directory(directory)

        file_path = directory / filename

        # Always write the file to ensure it's current
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._set_file_permissions(file_path)
            logger.debug(f"Created static file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to create static file {file_path}: {str(e)}")

    def _generate_main_index(self) -> None:
        """Generate the main index page."""
        regular_pages = self._get_regular_pages()
        recent_pages = sorted(
            regular_pages, key=lambda p: p.modified_date, reverse=True
        )[:10]

        # Calculate tag popularity
        tag_counts = {tag: len(pages) for tag, pages in self.tags.items()}
        popular_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:20]

        context = self._build_main_index_context(recent_pages, popular_tags)
        content = self.jinja_env.get_template("index").render(**context)

        index_page = Page(
            title="Notes",
            path=Path("index.md"),
            content=content,
            modified_date=datetime.now(),
            category=None,
            tags=[],
            description="A collection of notes and documentation",
            is_index=True,
        )

        # Generate the HTML file
        output_path = self.output_dir / "index.html"
        html_content = self.jinja_env.get_template("base").render(
            **self._get_page_context(index_page)
        )

        try:
            output_path.write_text(html_content, encoding="utf-8")
            self._set_file_permissions(output_path)
            logger.info("Generated main index page")
        except Exception as e:
            logger.error(f"Failed to generate main index: {str(e)}")

    def _get_regular_pages(self) -> List[Page]:
        """Get all regular pages (excluding special pages)."""
        return [
            page
            for page in self.pages.values()
            if not (
                page.is_index or str(page.path).startswith(("categories/", "tags/"))
            )
        ]

    def _build_main_index_context(
        self, recent_pages: List[Page], popular_tags: List[Tuple[str, int]]
    ) -> Dict[str, Any]:
        """Build context for main index template."""
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
        }

    def _generate_html_pages(self) -> None:
        """Generate HTML for all pages."""
        # Generate regular pages (excluding taxonomy index pages that were already generated)
        for page in self.pages.values():
            # Skip taxonomy index pages as they're generated in _generate_taxonomy_index
            if not (
                str(page.path).endswith("/index.md")
                and str(page.path).startswith(("categories/", "tags/"))
            ):
                self._generate_page(page)

        # Generate taxonomy collection pages (individual category/tag pages)
        self._generate_taxonomy_collection_pages("category", self.categories)
        self._generate_taxonomy_collection_pages("tag", self.tags)

    def _generate_taxonomy_collection_pages(
        self, taxonomy_type: str, collection: Dict[str, List[Page]]
    ) -> None:
        """Generate individual pages for each taxonomy item."""
        # Proper pluralization
        taxonomy_plural = "categories" if taxonomy_type == "category" else "tags"

        for name, pages in collection.items():
            output_path = self.output_dir / taxonomy_plural / f"{name.lower()}.html"
            self._ensure_parent_directory(output_path)

            # Create content for the taxonomy page
            content_parts = [f"<h2>{taxonomy_type.title()}: {name}</h2>", "<ul>"]

            for page in sorted(pages, key=lambda p: p.title.lower()):
                page_url = f"/{page.path.with_suffix('.html')}"
                content_parts.append(
                    f'    <li><a href="{page_url}">{page.title}</a></li>'
                )

            content_parts.append("</ul>")
            content = "\n".join(content_parts)

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

            try:
                html_content = self.jinja_env.get_template("base").render(
                    **self._get_page_context(page)
                )
                output_path.write_text(html_content, encoding="utf-8")
                self._set_file_permissions(output_path)
                logger.debug(f"Generated {taxonomy_type} page: {name}")
            except Exception as e:
                logger.error(
                    f"Failed to generate {taxonomy_type} page {name}: {str(e)}"
                )

    def _generate_page(self, page: Page) -> None:
        """Generate HTML file for a single page."""
        output_path = self.output_dir / page.path.with_suffix(".html")
        self._ensure_parent_directory(output_path)

        try:
            html_content = self.jinja_env.get_template("base").render(
                **self._get_page_context(page)
            )
            output_path.write_text(html_content, encoding="utf-8")
            self._set_file_permissions(output_path)
            logger.debug(f"Generated page: {page.path}")
        except Exception as e:
            logger.error(f"Failed to generate page {page.path}: {str(e)}")

    def _copy_themes(self) -> None:
        """Copy theme files if they exist."""
        logger.info("copying themes")
        themes_source = self.input_dir / "scripts" / "template" / "themes"
        if not themes_source.exists():
            themes_source = self.input_dir / "themes"

        if not themes_source.exists():
            logger.debug("No themes directory found, skipping theme copy")
            return

        themes_dest = self.output_dir / "css" / "themes"
        self._create_directory(themes_dest)

        try:
            for theme_file in self._walk_directory(themes_source):
                if theme_file.is_file():
                    relative_path = theme_file.relative_to(themes_source)
                    output_path = themes_dest / relative_path
                    self._ensure_parent_directory(output_path)
                    shutil.copy2(theme_file, output_path)
                    self._set_file_permissions(output_path)
            logger.info("Copied theme files")
        except Exception as e:
            logger.error(f"Failed to copy themes: {str(e)}")

    def _copy_static_files(self) -> None:
        """Copy static files like sitemap.xml and robots.txt."""
        static_files = ["sitemap.xml", "robots.txt"]

        for filename in static_files:
            source_path = self.input_dir / filename
            if source_path.exists():
                dest_path = self.output_dir / filename
                try:
                    shutil.copy2(source_path, dest_path)
                    self._set_file_permissions(dest_path)
                    logger.debug(f"Copied static file: {filename}")
                except Exception as e:
                    logger.error(f"Failed to copy {filename}: {str(e)}")

    def generate_slides(self) -> None:
        """Generate slides using Marp (optional feature)."""
        slides_input = self.input_dir / "slides"
        if not slides_input.exists():
            logger.debug("No slides directory found, skipping slide generation")
            return

        slides_output = self.output_dir / "slides"
        self._create_directory(slides_output)

        try:
            # Check if Marp CLI is available
            subprocess.run(
                ["npx", "@marp-team/marp-cli", "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Marp CLI not available, skipping slide generation")
            return

        # Process all markdown files in slides directory
        for md_file in slides_input.rglob("*.md"):
            try:
                relative_path = md_file.relative_to(slides_input)
                output_file = slides_output / relative_path.with_suffix(".html")
                self._ensure_parent_directory(output_file)

                subprocess.run(
                    [
                        "npx",
                        "@marp-team/marp-cli",
                        "--html",
                        str(md_file),
                        "-o",
                        str(output_file),
                    ],
                    check=True,
                    capture_output=True,
                )
                logger.debug(f"Generated slide: {relative_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to generate slide {md_file}: {e}")

        # Copy slide assets if they exist
        slides_assets = slides_input / "assets"
        if slides_assets.exists():
            dest_assets = slides_output / "assets"
            try:
                if dest_assets.exists():
                    shutil.rmtree(dest_assets)
                shutil.copytree(slides_assets, dest_assets)
                logger.info("Copied slide assets")
            except Exception as e:
                logger.error(f"Failed to copy slide assets: {e}")


def main():
    """Main entry point for the site generator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a static site from markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s content/ site/              # Basic usage
  %(prog)s content/ site/ --verbose    # With verbose logging
  %(prog)s content/ site/ --slides     # Include slide generation
        """,
    )
    parser.add_argument("input_dir", help="Input directory containing content")
    parser.add_argument("output_dir", help="Output directory for generated site")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--slides", action="store_true", help="Generate slides using Marp CLI"
    )
    parser.add_argument(
        "--domain",
        default="https://notes.elimelt.com",
        help="Site domain for canonical URLs (default: %(default)s)",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.getLogger().setLevel(log_level)

    try:
        # Validate arguments
        input_path = Path(args.input_dir)
        if not input_path.exists():
            logger.error(f"Input directory does not exist: {input_path}")
            return 1

        if not input_path.is_dir():
            logger.error(f"Input path is not a directory: {input_path}")
            return 1

        # Generate the site
        generator = SiteGenerator(args.input_dir, args.output_dir, args.domain)
        generator.generate_site()

        # Generate slides if requested
        if args.slides:
            generator.generate_slides()

        return 0

    except KeyboardInterrupt:
        logger.info("Site generation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Site generation failed: {str(e)}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
