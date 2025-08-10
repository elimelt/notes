import numpy as np
import os
from typing import Dict, List, Tuple


def read_markdown_files(root_dir: str, max_depth: int = 8) -> Dict[str, str]:

    corpus = {}

    def process_dir(path: str, depth: int = 0):
        if depth > max_depth:
            return

        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    process_dir(full_path, depth + 1)
                elif entry.endswith(".md"):
                    try:
                        with open(full_path, "r") as f:
                            corpus[full_path] = f.read()
                    except Exception:
                        continue
        except Exception:
            return

    process_dir(root_dir)
    return corpus


def create_index(corpus: Dict[str, str]) -> Tuple[Dict[str, Dict[str, int]], List[str]]:

    inv_idx = {}
    for doc_name, content in corpus.items():
        words = content.split()
        for word in words:
            if word not in inv_idx:
                inv_idx[word] = {}
            inv_idx[word][doc_name] = inv_idx[word].get(doc_name, 0) + 1

    return inv_idx, list(inv_idx.keys())


def calculate_tfidf(
    corpus: Dict[str, str], inv_idx: Dict[str, Dict[str, int]], word_list: List[str]
) -> Dict[str, np.ndarray]:

    N = len(corpus)
    tfidf = {}

    for doc_name, content in corpus.items():
        doc_words = content.split()
        doc_len = len(doc_words)
        tfidf[doc_name] = np.zeros(len(word_list))

        for i, word in enumerate(word_list):
            if word in inv_idx and doc_name in inv_idx[word]:
                tf = inv_idx[word][doc_name] / doc_len
                idf = np.log(N / len(inv_idx[word]))
                tfidf[doc_name][i] = tf * idf

    return tfidf


def search(
    query: str,
    tfidf: Dict[str, np.ndarray],
    word_list: List[str],
    inv_idx: Dict[str, Dict[str, int]],
    num_results: int = 5,
) -> List[Tuple[str, float]]:

    N = len(tfidf)
    query_vec = np.zeros(len(word_list))

    for i, word in enumerate(word_list):
        if word in query.split() and word in inv_idx:
            query_vec[i] = np.log(N / len(inv_idx[word]))

    similarities = [
        (doc_name, float(np.dot(doc_vec, query_vec)))
        for doc_name, doc_vec in tfidf.items()
    ]

    return sorted(similarities, key=lambda x: x[1], reverse=True)[:num_results]


def main():

    try:
        root_dir = (
            input("Enter root directory to search (default '.'): ").strip() or "."
        )
        print(f"Reading markdown files from {root_dir}...")

        corpus = read_markdown_files(root_dir)
        if not corpus:
            print("No markdown files found!")
            return

        print(f"Found {len(corpus)} markdown files")
        print("Building search index...")

        inv_idx, word_list = create_index(corpus)
        tfidf = calculate_tfidf(corpus, inv_idx, word_list)

        print("Search system ready!")

        while True:
            query = input('\nEnter search query (or "exit" to quit): ').strip()
            if query.lower() == "exit":
                break

            results = search(query, tfidf, word_list, inv_idx)

            print("\nSearch results:")
            for doc_name, similarity in results:
                print(f"{doc_name}: {similarity:.4f}")

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
