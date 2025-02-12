from dataclasses import dataclass
import json
from pathlib import Path
from typing import List, Dict, Optional
import shutil
import markdown
import logging
from datetime import datetime
from urllib.parse import quote
import re
from collections import defaultdict

# Set up logging
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


class SiteGenerator:
    """Generates a static site from a directory of mixed content"""

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

    def __init__(self, input_dir: str, output_dir: str, site_domain: str = "https://notes.elimelt.com"):
        self.site_domain = site_domain
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.markdown_converter = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
        self.pages: Dict[Path, Page] = {}
        self.categories: Dict[str, List[Page]] = defaultdict(list)
        self.tags: Dict[str, List[Page]] = defaultdict(list)

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

        # Create assets directory
        assets_dir = self.output_dir / "assets"
        assets_dir.mkdir(parents=True)
        assets_dir.chmod(0o755)

    def _process_content(self) -> None:
        """Process all content in the input directory"""
        for file_path in self._walk_directory(self.input_dir):
            if file_path.suffix in self.SUPPORTED_CONTENT:
                self._process_markdown(file_path)

    def _walk_directory(self, directory: Path) -> List[Path]:
        """Walk through directory while respecting ignored paths"""
        files = []
        for item in directory.rglob("*"):
            if not any(ignored in item.parts for ignored in self.IGNORED_DIRECTORIES):
                if item.is_file():
                    files.append(item)
        return files

    def _extract_metadata(self, file_path: Path) -> dict:
        """Extract metadata from markdown file"""
        content = file_path.read_text(encoding="utf-8")
        # Create a new converter instance for metadata extraction
        md = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
        md.convert(content)

        metadata = {}
        if hasattr(md, "Meta"):
            metadata = {
                "title": md.Meta.get("title", [file_path.stem.replace("-", " ").title()])[0],
                "category": md.Meta.get("category", [None])[0],
                "tags": (
                    md.Meta.get("tags", [""])[0].split(",")
                    if "tags" in md.Meta
                    else []
                ),
                "description": md.Meta.get("description", [None])[0],
            }
        else:
            metadata = {
                "title": file_path.stem.replace("-", " ").title(),
                "category": None,
                "tags": [],
                "description": None,
            }

        return metadata

    def _process_markdown(self, file_path: Path) -> None:
        """Process a markdown file into a Page object"""
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = self._extract_metadata(file_path)

            # Create a new converter instance for content conversion
            md = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
            html_content = md.convert(content)

            relative_path = file_path.relative_to(self.input_dir)
            is_index = file_path.stem.lower() == "index"

            # Clean and normalize tags
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

            # Organize by category and tags
            if page.category:
                self.categories[page.category].append(page)
            for tag in page.tags:
                self.tags[tag].append(page)

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    def _organize_content(self) -> None:
        """Organize pages by category and tags"""
        # Sort pages within categories and tags
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

    def _generate_special_pages(self) -> None:
        """Generate special pages like main index, category index and tag index"""
        # Generate main index
        self._generate_main_index()

        # Generate categories and tags pages
        # Generate categories index
        if self.categories:
            categories_content = self._render_categories_index()
            categories_page = Page(
                title="Categories",
                path=Path("categories/index.md"),
                content=categories_content,
                modified_date=datetime.now(),
                category=None,
                tags=[],
                description="Index of all categories",
                is_index=True,
            )
            self.pages[categories_page.path] = categories_page

        # Generate tags index
        if self.tags:
            tags_content = self._render_tags_index()
            tags_page = Page(
                title="Tags",
                path=Path("tags/index.md"),
                content=tags_content,
                modified_date=datetime.now(),
                category=None,
                tags=[],
                description="Index of all tags",
                is_index=True,
            )
            self.pages[tags_page.path] = tags_page

    def _render_categories_index(self) -> str:
        """Render the categories index page"""
        content = "<ul>"
        for category, pages in sorted(self.categories.items()):
            category_url = f"/categories/{quote(category.lower())}.html"
            content += f'\n<li><a href="{category_url}">{category}</a> ({len(pages)} pages)</li>'
        content += "</ul>"
        return content

    def _render_tags_index(self) -> str:
        """Render the tags index page"""
        content = "<ul>"
        for tag, pages in sorted(self.tags.items()):
            tag_url = f"/tags/{quote(tag.lower())}.html"
            content += f'\n<li><a href="{tag_url}">{tag}</a> ({len(pages)} pages)</li>'
        content += "</ul>"
        return content

    def _generate_html_pages(self) -> None:
        """Generate HTML pages for all processed content"""
        # Generate regular pages
        for page in self.pages.values():
            output_path = self.output_dir / page.path.with_suffix(".html")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.parent.chmod(0o755)

            html_content = self._render_template(page)
            output_path.write_text(html_content, encoding="utf-8")
            output_path.chmod(0o644)

        # Generate category pages
        for category, pages in self.categories.items():
            self._generate_category_page(category, pages)

        # Generate tag pages
        for tag, pages in self.tags.items():
            self._generate_tag_page(tag, pages)

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

        html_content = self._render_template(page)
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

        html_content = self._render_template(page)
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(0o644)

    def _generate_breadcrumbs(self, page: Page) -> str:
        """Generate breadcrumb navigation"""
        parts = []
        parts.append('<a href="/index.html">Home</a>')

        if page.category:
            parts.append(
                f'<a href="/categories/{quote(page.category.lower())}.html">{page.category}</a>'
            )

        if not page.is_index:
            parts.append(page.title)

        return " » ".join(parts)

    def _generate_navigation(self, current_page: Page) -> str:
        """Generate navigation links"""
        nav_items = []

        # Add home link if not on index
        if not current_page.is_index:
            nav_items.append('<a href="/index.html">Home</a>')

        # Add categories link
        if self.categories:
            nav_items.append('<a href="/categories/index.html">Categories</a>')

        # Add tags link
        if self.tags:
            nav_items.append('<a href="/tags/index.html">Tags</a>')

        return "\n".join(nav_items)

    def _generate_main_index(self) -> None:
        """Generate the main index.html page"""
        # Get recent pages (excluding special pages)
        regular_pages = [
            p
            for p in self.pages.values()
            if not (p.is_index or str(p.path).startswith(("categories/", "tags/")))
        ]
        recent_pages = sorted(
            regular_pages, key=lambda p: p.modified_date, reverse=True
        )[
            :10
        ]  # Show 10 most recent

        # Generate recent posts section
        recent_content = "<h2>Recent</h2>\n<ul class='recent-posts'>"
        for page in recent_pages:
            page_url = f"/{page.path.with_suffix('.html')}"
            date_str = page.modified_date.strftime("%Y-%m-%d")
            recent_content += f"""
                <li>
                    <a href="{page_url}">{page.title}</a>
                    <span class="date">{date_str}</span>
                    {f'<span class="category">{page.category}</span>' if page.category else ''}
                </li>"""
        recent_content += "</ul>"

        # Generate categories section
        categories_content = "<h2>Categories</h2>\n<ul class='categories-list'>"
        for category, pages in sorted(self.categories.items()):
            category_url = f"/categories/{quote(category.lower())}.html"
            categories_content += f"""
                <li>
                    <a href="{category_url}">{category}</a>
                    <span class="count">({len(pages)})</span>
                </li>"""
        categories_content += "</ul>"

        # Generate popular tags section (show top 20 most used tags)
        tag_counts = {tag: len(pages) for tag, pages in self.tags.items()}
        popular_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:20]

        tags_content = "<h2>Featured Tags</h2>\n<div class='tags-cloud'>"
        for tag, count in popular_tags:
            tag_url = f"/tags/{quote(tag.lower())}.html"
            tags_content += f'<a href="{tag_url}" class="tag-{min(count, 5)}">{tag} <span>({count})</span></a>'
        tags_content += "</div>"

        # Calculate some statistics
        total_notes = len(regular_pages)
        total_categories = len(self.categories)
        total_tags = len(self.tags)

        # Create the landing page content
        content = f"""
            <div class="landing-stats">
                <div class="stat-item">
                    <span class="stat-value">{total_notes}</span>
                    <span class="stat-label">Notes</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{total_categories}</span>
                    <span class="stat-label">Categories</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{total_tags}</span>
                    <span class="stat-label">Tags</span>
                </div>
            </div>
            <div class="landing-grid">
                <div class="recent-section">
                    {recent_content}
                </div>
                <div class="categories-section">
                    {categories_content}
                </div>
                <div class="tags-section">
                    {tags_content}
                </div>
            </div>
        """

        # Create the index page
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

        # Generate the HTML
        output_path = self.output_dir / "index.html"
        html_content = self._render_template(index_page)
        output_path.write_text(html_content, encoding="utf-8")
        output_path.chmod(0o644)

    def _render_template(self, page: Page) -> str:
        """Render HTML template for a page"""
        navigation = self._generate_navigation(page)
        breadcrumbs = self._generate_breadcrumbs(page)

        meta_description = page.description
        if not meta_description and page.content:
            # Strip HTML tags and get first 160 characters
            plain_content = re.sub(r'<[^>]+>', '', page.content)
            meta_description = plain_content[:160].strip() + '...' if len(plain_content) > 160 else plain_content

        # Generate schema.org JSON-LD
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

        # Generate canonical URL
        canonical_url = f"{self.site_domain}/{page.path.with_suffix('.html')}"

        # Generate tags section if page has tags
        tags_section = ""
        if page.tags:
            tags_section = (
                "<div class='tags'>Tags: "
                + ", ".join(
                    f'<a href="/tags/{quote(tag.lower())}.html">{tag}</a>'
                    for tag in sorted(page.tags)
                )
                + "</div>"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title + ' | Elijah\'s Notes' if page.title else 'Elijah\'s Notes'}</title>

    <!-- SEO Meta Tags -->
    <meta name="description" content="{meta_description if meta_description else ''}">
    <meta name="author" content="Elijah Melton">
    <meta name="robots" content="index, follow">
    <meta name="generator" content="Custom Static Site Generator">
    <link rel="canonical" href="{canonical_url}">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="{page.title}">
    <meta property="og:description" content="{meta_description if meta_description else ''}">
    <meta property="og:url" content="{canonical_url}">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{page.title}">
    <meta name="twitter:description" content="{meta_description if meta_description else ''}">

    <!-- Keywords from tags -->
    {f'<meta name="keywords" content="{",".join(page.tags)}">' if page.tags else ''}

    <!-- Schema.org JSON-LD -->
    <script type="application/ld+json">
    {json.dumps(schema_json)}
    </script>
    <style>
        :root {{
            --text-color: #1a1a1a;
            --background-color: #ffffff;
            --accent-color: #2563eb;
            --border-color: #e5e7eb;
            --nav-background: rgba(255, 255, 255, 0.95);
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --text-color: #f3f4f6;
                --background-color: #1a1a1a;
                --accent-color: #60a5fa;
                --border-color: #374151;
                --nav-background: rgba(26, 26, 26, 0.95);
            }}
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 50rem;
            margin: 0 auto;
            padding: 2rem;
            color: var(--text-color);
            background: var(--background-color);
        }}

        nav {{
            position: sticky;
            top: 0;
            background: var(--nav-background);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 0;
            margin-bottom: 2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            z-index: 1000;
        }}

        nav a {{
            color: var(--accent-color);
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            transition: background-color 0.2s;
        }}

        nav a:hover {{
            background-color: var(--border-color);
        }}

        .breadcrumbs {{
            margin-bottom: 2rem;
            color: var(--text-color);
            opacity: 0.8;
        }}

        .breadcrumbs a {{
            color: var(--accent-color);
            text-decoration: none;
        }}

        .content {{
            margin-top: 2rem;
        }}

        h1, h2, h3, h4, h5, h6 {{
            margin-top: 2rem;
            margin-bottom: 1rem;
            line-height: 1.3;
        }}

        code {{
            background: var(--border-color);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-size: 0.9em;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
        }}

        pre {{
            background: var(--border-color);
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            margin: 1.5rem 0;
        }}

        pre code {{
            background: none;
            padding: 0;
            border-radius: 0;
        }}

        img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin: 1.5rem 0;
        }}

        .meta {{
            color: var(--text-color);
            opacity: 0.8;
            font-size: 0.9em;
            margin-bottom: 2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .tags {{
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }}

        .tags a {{
            display: inline-block;
            background: var(--border-color);
            color: var(--text-color);
            padding: 0.2rem 0.6rem;
            border-radius: 3px;
            text-decoration: none;
            font-size: 0.9em;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
        }}

        .tags a:hover {{
            background: var(--accent-color);
            color: white;
        }}

        a {{
            color: #3391ff;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
        }}

        th, td {{
            padding: 0.75rem;
            border: 1px solid var(--border-color);
        }}

        th {{
            background: var(--border-color);
        }}

        blockquote {{
            margin: 1.5rem 0;
            padding-left: 1rem;
            border-left: 4px solid var(--accent-color);
            color: var(--text-color);
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <header>
        <nav role="navigation" aria-label="Main navigation">
            {navigation}
        </nav>
        <div class="breadcrumbs" role="navigation" aria-label="Breadcrumb">
            {breadcrumbs}
        </div>
    </header>
    <main role="main">
        <article>
            <h1>{page.title}</h1>
            <div class="meta">
                <time datetime="{page.modified_date.isoformat()}">
                    Last modified: {page.modified_date.strftime('%Y-%m-%d')}
                </time>
                {f'<span>Category: <a href="/categories/{quote(page.category.lower())}.html">{page.category}</a></span>' if page.category else ''}
            </div>
            <div class="content">
                {page.content}
            </div>
            {tags_section}
        </article>
    </main>
    <footer role="contentinfo">
        <p>&copy; {datetime.now().year} Your Site Name. All rights reserved.</p>
    </footer>
</body>
</html>"""

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
