#!/usr/bin/env python3
"""
search.py

CLI search tool for markdown content using embeddings.
"""

import argparse
import os
import sys
import json
import sqlite3
import pickle
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

sys.path.append(os.path.dirname(__file__))
from embed import (
    generate_embeddings_for_directory,
    get_provider,
    LocalSentenceTransformerProvider,
    cosine_similarity,
    load_embeddings,
    dump_embeddings_into_sqlite
)

DEFAULT_INDEX_FILE = "search_index.db"
DEFAULT_EMBEDDINGS_FILE = "search_embeddings.jsonl"
CONTENT_DIR = "content"

class SearchIndex:
    """Manages the search index and provides search functionality."""

    def __init__(self, index_file: str = DEFAULT_INDEX_FILE):
        self.index_file = index_file
        self.provider = None
        self._init_provider()

    def _init_provider(self):
        try:
            self.provider = get_provider("local", model="all-MiniLM-L6-v2")
        except Exception as e:
            print(f"Error initializing embedding provider: {e}")
            print("Make sure sentence-transformers is installed: pip install sentence-transformers")
            sys.exit(1)

    def build_index(self, content_dir: str = CONTENT_DIR, force_rebuild: bool = False):
        if os.path.exists(self.index_file) and not force_rebuild:
            print(f"Index already exists at {self.index_file}. Use --rebuild to force rebuild.")
            return

        print(f"Building search index from {content_dir}...")

        embeddings = generate_embeddings_for_directory(
            content_dir,
            self.provider,
            recursive=True,
            max_words=200,
            overlap=40
        )

        if not embeddings:
            print("No embeddings generated. Check if content directory exists and contains markdown files.")
            return

        dump_embeddings_into_sqlite(embeddings, self.index_file)
        print(f"Index built successfully with {len(embeddings)} chunks.")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[float, Dict[str, Any]]]:
        if not os.path.exists(self.index_file):
            print(f"Index not found at {self.index_file}. Run with --rebuild to build the index.")
            return []

        query_embedding = self.provider.embed_texts([query])[0]

        conn = sqlite3.connect(self.index_file)
        cur = conn.cursor()
        cur.execute("SELECT id, file_path, doc_title, heading, text, embedding FROM embeddings")

        results = []
        for row in cur.fetchall():
            id_, file_path, doc_title, heading, text, embedding_blob = row
            embedding = pickle.loads(embedding_blob)

            similarity = cosine_similarity(query_embedding, embedding)

            results.append((
                similarity,
                {
                    "id": id_,
                    "file_path": file_path,
                    "doc_title": doc_title,
                    "heading": heading,
                    "text": text,
                    "similarity": similarity
                }
            ))

        conn.close()

        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        if not os.path.exists(self.index_file):
            return {"error": "Index not found"}

        conn = sqlite3.connect(self.index_file)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM embeddings")
        total_chunks = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT file_path) FROM embeddings")
        unique_files = cur.fetchone()[0]

        cur.execute("SELECT file_path, COUNT(*) FROM embeddings GROUP BY file_path ORDER BY COUNT(*) DESC LIMIT 10")
        top_files = cur.fetchall()

        conn.close()

        return {
            "total_chunks": total_chunks,
            "unique_files": unique_files,
            "top_files": top_files
        }

def format_search_result(result: Tuple[float, Dict[str, Any]], show_full_text: bool = False) -> str:
    similarity, data = result

    text = data["text"]
    if not show_full_text and len(text) > 200:
        text = text[:200] + "..."

    file_path = data["file_path"]
    if file_path.startswith("content/"):
        file_path = file_path[8:]

    output = []
    output.append(f"File: {file_path}")
    if data["doc_title"]:
        output.append(f"Title: {data['doc_title']}")
    if data["heading"]:
        output.append(f"Heading: {data['heading']}")
    output.append(f"Similarity: {similarity:.3f}")
    output.append(f"Text: {text}")
    output.append("-" * 80)

    return "\n".join(output)

def interactive_search(index: SearchIndex):
    print("Interactive Search Mode")
    print("Type your search query and press Enter. Type 'quit' or 'exit' to stop.")
    print("Commands: 'stats' - show index statistics, 'help' - show this help")
    print("-" * 80)

    while True:
        try:
            query = input("\nSearch: ").strip()

            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            elif query.lower() == 'stats':
                stats = index.get_stats()
                if "error" in stats:
                    print(f"Error: {stats['error']}")
                else:
                    print(f"Index Statistics:")
                    print(f"   Total chunks: {stats['total_chunks']}")
                    print(f"   Unique files: {stats['unique_files']}")
                    print(f"   Top files by chunk count:")
                    for file_path, count in stats['top_files']:
                        print(f"     {file_path}: {count} chunks")
                continue
            elif query.lower() == 'help':
                print("Available commands:")
                print("  - Type any search query to search")
                print("  - 'stats' - show index statistics")
                print("  - 'quit', 'exit', or 'q' - exit the program")
                continue
            elif not query:
                continue

            print(f"\nSearching for: '{query}'")
            results = index.search(query, top_k=5)

            if not results:
                print("No results found.")
                continue

            print(f"Found {len(results)} results:")
            print("-" * 80)

            for i, result in enumerate(results, 1):
                print(f"\n{i}. {format_search_result(result)}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Search markdown content using embeddings")
    parser.add_argument("--query", type=str, help="Search query (non-interactive mode)")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the search index")
    parser.add_argument("--index", type=str, default=DEFAULT_INDEX_FILE, help="Index file path")
    parser.add_argument("--content-dir", type=str, default=CONTENT_DIR, help="Content directory to index")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results to return")
    parser.add_argument("--full-text", action="store_true", help="Show full text in results")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")

    args = parser.parse_args()

    index = SearchIndex(args.index)

    if args.stats:
        stats = index.get_stats()
        if "error" in stats:
            print(f"Error: {stats['error']}")
            sys.exit(1)
        else:
            print(f"Index Statistics:")
            print(f"   Total chunks: {stats['total_chunks']}")
            print(f"   Unique files: {stats['unique_files']}")
            print(f"   Top files by chunk count:")
            for file_path, count in stats['top_files']:
                print(f"     {file_path}: {count} chunks")
        return

    if args.rebuild:
        index.build_index(args.content_dir, force_rebuild=True)
        return

    if not os.path.exists(args.index):
        print(f"Index not found. Building index from {args.content_dir}...")
        index.build_index(args.content_dir)

    if args.query:
        print(f"Searching for: '{args.query}'")
        results = index.search(args.query, top_k=args.top_k)

        if not results:
            print("No results found.")
            return

        print(f"Found {len(results)} results:")
        print("-" * 80)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {format_search_result(result, show_full_text=args.full_text)}")

    else:
        interactive_search(index)

if __name__ == "__main__":
    main()
