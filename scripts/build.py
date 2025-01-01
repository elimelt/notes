from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
import shutil
import markdown
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Page:
    """Represents a page in the static site"""
    title: str
    path: Path
    content: str
    modified_date: datetime
    is_index: bool = False

class SiteGenerator:
    """Generates a static site from a directory of mixed content"""

    MARKDOWN_EXTENSIONS = ['meta', 'toc', 'fenced_code', 'tables']
    SUPPORTED_CONTENT = {'.md'}  # Expandable for future content types
    IGNORED_DIRECTORIES = {'.git', '__pycache__', 'node_modules'}

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.markdown_converter = markdown.Markdown(extensions=self.MARKDOWN_EXTENSIONS)
        self.pages: Dict[Path, Page] = {}

    def generate_site(self) -> None:
        """Main method to generate the static site"""
        try:
            self._prepare_output_directory()
            self._process_content()
            self._copy_assets()
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
        # Set directory permissions to 755 (rwxr-xr-x)
        self.output_dir.chmod(0o755)

    def _process_content(self) -> None:
        """Process all content in the input directory"""
        for file_path in self._walk_directory(self.input_dir):
            if file_path.suffix in self.SUPPORTED_CONTENT:
                self._process_markdown(file_path)

    def _walk_directory(self, directory: Path) -> List[Path]:
        """Walk through directory while respecting ignored paths"""
        files = []
        for item in directory.rglob('*'):
            if not any(ignored in item.parts for ignored in self.IGNORED_DIRECTORIES):
                if item.is_file():
                    files.append(item)
        return files

    def _process_markdown(self, file_path: Path) -> None:
        """Process a markdown file into a Page object"""
        try:
            content = file_path.read_text(encoding='utf-8')
            self.markdown_converter.reset()
            html_content = self.markdown_converter.convert(content)

            # Get title from metadata or filename
            if hasattr(self.markdown_converter, 'Meta') and 'title' in self.markdown_converter.Meta:
                title = self.markdown_converter.Meta['title'][0]
            else:
                title = file_path.stem.replace('-', ' ').title()

            relative_path = file_path.relative_to(self.input_dir)
            is_index = file_path.stem.lower() == 'index'

            self.pages[relative_path] = Page(
                title=title,
                path=relative_path,
                content=html_content,
                modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
                is_index=is_index
            )
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    def _copy_assets(self) -> None:
        """Copy non-markdown files to output directory"""
        for file_path in self._walk_directory(self.input_dir):
            if file_path.suffix not in self.SUPPORTED_CONTENT:
                relative_path = file_path.relative_to(self.input_dir)
                output_path = self.output_dir / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                # Set directory permissions to 755 (rwxr-xr-x)
                output_path.parent.chmod(0o755)
                shutil.copy2(file_path, output_path)
                # Set file permissions to 644 (rw-r--r--)
                output_path.chmod(0o644)

    def _generate_html_pages(self) -> None:
        """Generate HTML pages for all processed content"""
        for page in self.pages.values():
            output_path = self.output_dir / page.path.with_suffix('.html')
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Set directory permissions to 755 (rwxr-xr-x)
            output_path.parent.chmod(0o755)

            html_content = self._render_template(page)
            output_path.write_text(html_content, encoding='utf-8')
            # Set file permissions to 644 (rw-r--r--)
            output_path.chmod(0o644)

    def _generate_navigation(self, current_page: Page) -> str:
        """Generate navigation links"""
        nav_items = []

        # Add home link if not on index
        if not current_page.is_index:
            nav_items.append('<a href="/index.html">Home</a>')

        # Add other pages
        for page in sorted(self.pages.values(), key=lambda p: p.title):
            if not page.is_index:
                relative_url = f"/{page.path.with_suffix('.html')}"
                nav_items.append(f'<a href="{relative_url}">{page.title}</a>')

        return '\n'.join(nav_items)

    def _render_template(self, page: Page) -> str:
        """Render HTML template for a page"""
        navigation = self._generate_navigation(page)

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title}</title>
    <style>
        :root {{
            --text-color: #2c3e50;
            --background-color: #ffffff;
            --accent-color: #3498db;
            --border-color: #ecf0f1;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --text-color: #ecf0f1;
                --background-color: #2c3e50;
                --accent-color: #3498db;
                --border-color: #34495e;
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
            background: var(--background-color);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 0;
            margin-bottom: 2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
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

        .content {{
            margin-top: 2rem;
        }}

        h1, h2, h3, h4, h5, h6 {{
            margin-top: 2rem;
            margin-bottom: 1rem;
        }}

        code {{
            background: var(--border-color);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-size: 0.9em;
        }}

        pre code {{
            display: block;
            padding: 1rem;
            overflow-x: auto;
        }}

        img {{
            max-width: 100%;
            height: auto;
        }}

        .meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 2rem;
        }}
    </style>
</head>
<body>
    <nav>
        {navigation}
    </nav>
    <main>
        <h1>{page.title}</h1>
        <div class="meta">
            Last modified: {page.modified_date.strftime('%Y-%m-%d')}
        </div>
        <div class="content">
            {page.content}
        </div>
    </main>
</body>
</html>'''

def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate a static site from markdown files')
    parser.add_argument('input_dir', help='Input directory containing content')
    parser.add_argument('output_dir', help='Output directory for generated site')
    args = parser.parse_args()

    try:
        generator = SiteGenerator(args.input_dir, args.output_dir)
        generator.generate_site()
    except Exception as e:
        logger.error(f"Failed to generate site: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()