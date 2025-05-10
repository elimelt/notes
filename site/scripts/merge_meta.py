from dataclasses import dataclass
import subprocess
import markdown
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set, Callable
import shutil
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
import re
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


from typing import List, Tuple, Dict


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.
    This is a measure of how many single-character edits are needed to change one string into another.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Calculate insertions, deletions and substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)

            # Get minimum to append to current row
            current_row.append(min(insertions, deletions, substitutions))

        # Previous row becomes the current row
        previous_row = current_row

    return previous_row[-1]


def edit_distance_similarity(s1: str, s2: str) -> float:
    """
    Calculate the similarity between two strings using edit distance
    """
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    len_s1 = len(s1)
    len_s2 = len(s2)
    max_len = max(len_s1, len_s2)
    distance = levenshtein_distance(s1, s2)
    return 1 - (distance / max_len)


def get_merge_candidates(
    strings: List[str], threshold: float = 0.8
) -> List[Tuple[str, str, float]]:
    """
    Find pairs of strings that are similar enough to be merged
    Returns tuples of (string1, string2, similarity_score)
    """
    candidates = []
    for i in range(len(strings)):
        for j in range(i + 1, len(strings)):
            similarity = edit_distance_similarity(strings[i], strings[j])
            if similarity >= threshold:
                candidates.append((strings[i], strings[j], similarity))

    # Sort by similarity (highest first)
    return sorted(candidates, key=lambda x: x[2], reverse=True)


def merge_similar_strings(strings: List[str], threshold: float = 0.8) -> Dict[str, str]:
    """
    Interactively merge similar strings into a dictionary
    Returns a dictionary mapping original strings to their merged values
    """
    merged = {}
    remaining_strings = strings.copy()

    while True:
        candidates = get_merge_candidates(remaining_strings, threshold)
        if not candidates:
            print("No more candidates to merge.")
            break

        print(f"\nFound {len(candidates)} potential merge candidates.")
        print("Top 5 candidates by similarity:")
        for i, (s1, s2, similarity) in enumerate(candidates[:5], 1):
            print(f"{i}. '{s1}' and '{s2}' (similarity: {similarity:.2f})")

        if input("\nContinue merging? (y/n): ").lower() != "y":
            break

        # Process the highest similarity candidate
        s1, s2, similarity = candidates[0]
        print(f"\nMerging candidates: '{s1}' and '{s2}'")
        print(f"1. Keep '{s1}'")
        print(f"2. Keep '{s2}'")
        print(f"3. Enter custom value")
        print("4. Skip this pair")

        choice = input("Choose an option (1-4): ")

        if choice == "1":
            merged_value = s1
        elif choice == "2":
            merged_value = s2
        elif choice == "3":
            merged_value = input("Enter custom value: ")
        elif choice == "4":
            # Skip this pair but keep both strings in the pool
            remaining_strings.remove(s1)
            remaining_strings.insert(
                0, s1
            )  # Re-insert at beginning to avoid immediate re-comparison
            continue
        else:
            print("Invalid choice, skipping.")
            continue

        # Update the merged dictionary for both strings
        merged[s1] = merged_value
        merged[s2] = merged_value

        # Remove the merged strings from the remaining pool
        if s1 in remaining_strings:
            remaining_strings.remove(s1)
        if s2 in remaining_strings:
            remaining_strings.remove(s2)

        print(f"Merged '{s1}' and '{s2}' into '{merged_value}'")
        print(f"Remaining strings to process: {len(remaining_strings)}")

    return merged


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


class MetadataIndex:

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

    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.pages: Dict[Path, Page] = {}
        self.categories: Dict[str, List[Page]] = defaultdict(list)
        self.tags: Dict[str, List[Page]] = defaultdict(list)
        self.markdown_converter = markdown.Markdown(
            extensions=self.MARKDOWN_EXTENSIONS,
            output_format="html5",
            tab_length=4,
        )

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

            self.pages[file_path] = page
            self.categories[page.category].append(page)
            self.tags[page.title] = page

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    def _index_all_markdown_files(self) -> None:
        """
        Walk through the input directory and process all markdown files
        """
        print(f"Indexing markdown files in {self.input_dir.resolve()}...")
        for file_path in self._walk_directory(self.input_dir):

            if file_path.suffix in self.SUPPORTED_CONTENT:
                self._process_markdown(file_path)

    def _get_all_tags(self) -> Set[str]:
        """
        Get all unique tags from the indexed pages
        """
        all_tags = set()
        for page in self.pages.values():
            all_tags.update(page.tags)
        return all_tags


if __name__ == "__main__":
    idx = MetadataIndex(".")

    print("Indexing markdown files...")
    idx._index_all_markdown_files()
    print(f"Indexed {len(idx.pages)} pages.")

    print(f"Found {len(idx.categories)} categories.")
    print(f"Found {len(idx.tags)} tags.")

    merge_similar_strings(list(idx.tags.keys()), threshold=0.5)
