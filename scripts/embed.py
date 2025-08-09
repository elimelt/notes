#!/usr/bin/env python3
"""
rag_embeddings.py

Sophisticated RAG embedding generator and simple vector store.

Features
- Segments markdown at directory/document/section/sentence levels
- Normalizes markdown (removes codeblocks optionally, inline markup)
- Strategy pattern for embedding providers:
  - Local: sentence-transformers (recommended: all-MiniLM-L6-v2) - works on Mac M3
  - OpenAI: uses OpenAI embeddings API if API key provided
- Saves embeddings to a JSONL + numpy .npz bundle or dumps into a simple sqlite DB
- Includes a tiny k-NN search helper (uses in-memory cosine search)

Usage examples:
  # local embeddings for a directory (recursively), save to embeddings.jsonl and store in sqlite
  python rag_embeddings.py --directory docs/ --recursive --output embeddings.jsonl --provider local --model all-MiniLM-L6-v2 --sqlite out.db

  # single file using OpenAI
  OPENAI_API_KEY=... python rag_embeddings.py --file README.md --provider openai --output readme_embeddings.jsonl

This script is intentionally dependency-friendly: if sentence-transformers is not available
and provider is 'local' the script will suggest how to install it.
"""

import argparse
import os
import re
import sys
import json
import logging
import sqlite3
import fnmatch
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# lazy imports (only when needed)

logger = logging.getLogger("rag_embeddings")

# ----------------------------- Utilities -----------------------------


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None


def chunk_text_by_size(
    text: str, max_tokens: int = 250, overlap: int = 50
) -> List[str]:
    """Simple chunker by characters that approximates token sizes.
    We chunk by words, aiming for ~max_tokens words per chunk.
    """
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        j = min(i + max_tokens, len(words))
        chunk = " ".join(words[i:j])
        chunks.append(chunk)
        # overlap
        i = j - overlap if j - overlap > i else j
    return chunks


def cosine_similarity(a, b):
    import numpy as np

    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    if a.ndim > 1:
        a = a.mean(axis=0)
    if b.ndim > 1:
        b = b.mean(axis=0)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float((a @ b) / denom) if denom != 0 else 0.0


# ----------------------------- Segment / Normalize -----------------------------

HEADER_RE = re.compile(r"^(#{1,6})\s*(.+)$", flags=re.MULTILINE)
CODEBLOCK_RE = re.compile(r"```.*?```", flags=re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`]+?)`")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")


def normalize_markdown(markdown_text: str, remove_codeblocks: bool = True) -> str:
    """Strip codeblocks, HTML tags and normalize whitespace."""
    text = markdown_text
    if remove_codeblocks:
        text = CODEBLOCK_RE.sub(" ", text)
    # remove inline code but keep contents
    text = INLINE_CODE_RE.sub(lambda m: m.group(1), text)
    # replace markdown links with link text
    text = MD_LINK_RE.sub(lambda m: m.group(1), text)
    # remove simple html
    text = HTML_TAG_RE.sub(" ", text)
    # normalize multiple blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    # strip
    return text.strip()


@dataclass
class Chunk:
    id: str
    file_path: str
    doc_title: Optional[str]
    heading: Optional[str]
    heading_level: Optional[int]
    start: int
    end: int
    text: str


def segment_markdown(
    markdown_text: str, file_path: str, max_words: int = 200, overlap: int = 40
) -> List[Chunk]:
    """Split a markdown document into hierarchical chunks.

    Strategy:
      - Find headers and split into sections by headers
      - For each section, further split into paragraph/sentence chunks
      - Ensure chunk size controlled by max_words with overlap
    """
    norm = normalize_markdown(markdown_text)

    # Find headers and their spans
    headers = []
    for m in HEADER_RE.finditer(markdown_text):
        lvl = len(m.group(1))
        title = m.group(2).strip()
        headers.append((m.start(), m.end(), lvl, title))

    sections: List[Tuple[Optional[str], Optional[int], int, int]] = (
        []
    )  # (title, lvl, start, end)
    if headers:
        # build sections from headers
        for idx, (h_start, h_end, lvl, title) in enumerate(headers):
            sec_start = h_end
            sec_end = (
                headers[idx + 1][0] if idx + 1 < len(headers) else len(markdown_text)
            )
            sections.append((title, lvl, sec_start, sec_end))
    else:
        # single section representing whole document
        sections.append((None, None, 0, len(markdown_text)))

    chunks: List[Chunk] = []
    # Try to detect a doc title: first H1
    doc_title = None
    for h_start, h_end, lvl, title in headers:
        if lvl == 1:
            doc_title = title
            break

    chunk_id = 0
    for title, lvl, s_start, s_end in sections:
        section_text = normalize_markdown(markdown_text[s_start:s_end])
        # split into paragraphs
        paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n", section_text) if p.strip()
        ]
        for p in paragraphs:
            if not p:
                continue
            # further chunk by size
            subchunks = chunk_text_by_size(p, max_tokens=max_words, overlap=overlap)
            for sc in subchunks:
                cid = f"{os.path.basename(file_path)}::{chunk_id}"
                # compute approximate start/end by searching in section_text (best-effort)
                start = section_text.find(sc)
                if start >= 0:
                    start_abs = s_start + start
                    end_abs = start_abs + len(sc)
                else:
                    start_abs = s_start
                    end_abs = s_end
                chunks.append(
                    Chunk(
                        id=cid,
                        file_path=file_path,
                        doc_title=doc_title,
                        heading=title,
                        heading_level=lvl,
                        start=start_abs,
                        end=end_abs,
                        text=sc,
                    )
                )
                chunk_id += 1
    return chunks


# ----------------------------- Embedding Providers (Strategy) -----------------------------


class EmbeddingProvider:
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError()


class LocalSentenceTransformerProvider(EmbeddingProvider):
    """Uses sentence-transformers under the hood.

    Model defaults to 'all-MiniLM-L6-v2' (small and high-quality; runs on CPU easily and on macOS M1/M2/M3 with smaller memory).
    """

    def __init__(
        self, model_name: str = "all-MiniLM-L6-v2", device: Optional[str] = None
    ):
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            logger.error(
                "sentence-transformers not installed. Install with: pip install sentence-transformers"
            )
            raise
        self.model_name = model_name
        self.model = (
            SentenceTransformer(model_name, device=device)
            if device
            else SentenceTransformer(model_name)
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # The model returns numpy arrays; convert to list
        embs = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embs.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Uses OpenAI embeddings via openai package. Requires OPENAI_API_KEY in env or passed via client."""

    def __init__(
        self, model: str = "text-embedding-3-small", api_key: Optional[str] = None
    ):
        try:
            import openai
        except Exception as e:
            logger.error(
                "openai package not installed. Install with: pip install openai"
            )
            raise
        if api_key:
            openai.api_key = api_key
        # else the user should have set OPENAI_API_KEY
        self.openai = __import__("openai")
        self.model = model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results = []
        B = 32
        for i in range(0, len(texts), B):
            batch = texts[i : i + B]
            resp = self.openai.Embedding.create(input=batch, model=self.model)
            for datum in resp["data"]:
                results.append(datum["embedding"])
        return results


def get_provider(
    name: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    device: Optional[str] = None,
) -> EmbeddingProvider:
    if name == "local":
        return LocalSentenceTransformerProvider(
            model_name=model or "all-MiniLM-L6-v2", device=device
        )
    elif name == "openai":
        return OpenAIEmbeddingProvider(
            model=model or "text-embedding-3-small", api_key=api_key
        )
    else:
        raise ValueError(f"Unknown provider: {name}")


# ----------------------------- Persistence -----------------------------


def save_embeddings(embeddings: List[Dict[str, Any]], output_file: str):
    """Save as JSONL where each line is a JSON object with 'meta' and 'embedding' keys."""
    ensure_dir(output_file)
    with open(output_file, "w", encoding="utf-8") as f:
        for item in embeddings:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logger.info("Saved %d embedding items to %s", len(embeddings), output_file)


def load_embeddings(input_file: str) -> List[Dict[str, Any]]:
    items = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            items.append(json.loads(line))
    return items


def dump_embeddings_into_sqlite(embeddings: List[Dict[str, Any]], output_file: str):
    """Create a simple sqlite DB with schema and store embedding vectors as blobs (JSON).

    This is intentionally simple: for small/medium collections it is fine. For larger datasets use FAISS / PGVector.
    """
    ensure_dir(output_file)
    conn = sqlite3.connect(output_file)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id TEXT PRIMARY KEY,
            file_path TEXT,
            doc_title TEXT,
            heading TEXT,
            heading_level INTEGER,
            start INTEGER,
            end INTEGER,
            text TEXT,
            embedding BLOB
        )
        """
    )
    conn.commit()

    import pickle

    inserted = 0
    for item in embeddings:
        meta = item["meta"]
        emb = item["embedding"]
        try:
            cur.execute(
                "INSERT OR REPLACE INTO embeddings (id,file_path,doc_title,heading,heading_level,start,end,text,embedding) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    meta["id"],
                    meta.get("file_path"),
                    meta.get("doc_title"),
                    meta.get("heading"),
                    meta.get("heading_level"),
                    meta.get("start"),
                    meta.get("end"),
                    meta.get("text_snippet"),
                    pickle.dumps(emb),
                ),
            )
            inserted += 1
        except Exception:
            logger.exception("Failed to insert %s", meta.get("id"))
    conn.commit()
    conn.close()
    logger.info("Wrote %d rows to sqlite database %s", inserted, output_file)


# ----------------------------- Generation Helpers -----------------------------


def generate_embeddings_for_file(
    file_path: str, provider: EmbeddingProvider, max_words: int = 220, overlap: int = 40
) -> List[Dict[str, Any]]:
    logger.info("Processing file %s", file_path)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    chunks = segment_markdown(
        text, file_path=file_path, max_words=max_words, overlap=overlap
    )
    if not chunks:
        return []

    texts = [c.text for c in chunks]
    embeddings = provider.embed_texts(texts)

    out = []
    for c, emb in zip(chunks, embeddings):
        meta = {
            "id": c.id,
            "file_path": c.file_path,
            "doc_title": c.doc_title,
            "heading": c.heading,
            "heading_level": c.heading_level,
            "start": c.start,
            "end": c.end,
            "text_snippet": c.text[:500],
        }
        out.append({"meta": meta, "embedding": emb})
    return out


def generate_embeddings_for_directory(
    directory_path: str,
    provider: EmbeddingProvider,
    recursive: bool = True,
    exts: Tuple[str] = (".md", ".markdown"),
    max_words: int = 220,
    overlap: int = 40,
    ignore: List[str] = [],
) -> List[Dict[str, Any]]:
    all_embeddings: List[Dict[str, Any]] = []
    for root, dirs, files in os.walk(directory_path):
        if ignore:
            # Filter directories using pattern matching
            dirs[:] = [
                d
                for d in dirs
                if not any(
                    fnmatch.fnmatch(d, pattern)
                    or fnmatch.fnmatch(os.path.join(root, d), pattern)
                    for pattern in ignore
                )
            ]
            # Filter files using pattern matching
            files[:] = [
                f
                for f in files
                if not any(
                    fnmatch.fnmatch(f, pattern)
                    or fnmatch.fnmatch(os.path.join(root, f), pattern)
                    for pattern in ignore
                )
            ]
        for fn in files:
            if os.path.splitext(fn)[1].lower() in exts:
                fp = os.path.join(root, fn)
                try:
                    embs = generate_embeddings_for_file(
                        fp, provider, max_words=max_words, overlap=overlap
                    )
                    all_embeddings.extend(embs)
                except Exception:
                    logger.exception("Failed to process %s", fp)
        if not recursive:
            break
    return all_embeddings


# ----------------------------- Simple Search -----------------------------


def search_embeddings(
    embeddings: List[Dict[str, Any]],
    query: str,
    provider: EmbeddingProvider,
    top_k: int = 5,
) -> List[Tuple[float, Dict[str, Any]]]:
    """Return top_k items sorted by cosine similarity to query."""
    q_emb = provider.embed_texts([query])[0]
    scored = []
    for item in embeddings:
        sim = cosine_similarity(q_emb, item["embedding"])  # higher is better
        scored.append((sim, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# ----------------------------- CLI / Main -----------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate embeddings for markdown files using pluggable providers."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file", type=str, help="Generate embeddings for a single markdown file."
    )
    group.add_argument(
        "--directory",
        type=str,
        help="Generate embeddings for a directory containing markdown files.",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Ignore files or directories matching this pattern. Can be specified multiple times. Supports glob patterns like '*.txt' or 'site/*'",
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When using --directory, recurse into subdirectories.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="embeddings.jsonl",
        help="Output JSONL file to write embeddings to.",
    )
    parser.add_argument(
        "--sqlite",
        type=str,
        default=None,
        help="Optional: also write embeddings to this sqlite database file.",
    )
    parser.add_argument(
        "--provider",
        choices=("local", "openai"),
        default="local",
        help="Embedding provider strategy to use.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name for the provider (local model name or openai model name).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device to run local model on (e.g., cpu or cuda or mps). Leave empty to auto-detect.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for remote providers if needed.",
    )
    parser.add_argument(
        "--max-words", type=int, default=220, help="Approximate words per chunk."
    )
    parser.add_argument(
        "--overlap", type=int, default=40, help="Overlap words between chunks."
    )
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.quiet:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    provider = get_provider(
        args.provider, model=args.model, api_key=args.api_key, device=args.device
    )

    embeddings = []
    if args.file:
        if not os.path.exists(args.file):
            logger.error("File not found: %s", args.file)
            sys.exit(2)
        embeddings = generate_embeddings_for_file(
            args.file, provider, max_words=args.max_words, overlap=args.overlap
        )
    elif args.directory:
        if not os.path.isdir(args.directory):
            logger.error("Directory not found: %s", args.directory)
            sys.exit(2)
        embeddings = generate_embeddings_for_directory(
            args.directory,
            provider,
            recursive=args.recursive,
            max_words=args.max_words,
            overlap=args.overlap,
            ignore=args.ignore or [],
        )

    if not embeddings:
        logger.warning("No embeddings generated.")
    else:
        save_embeddings(embeddings, args.output)
        if args.sqlite:
            dump_embeddings_into_sqlite(embeddings, args.sqlite)

    logger.info("Done. Generated %d embedding vectors.", len(embeddings))


if __name__ == "__main__":
    main()
