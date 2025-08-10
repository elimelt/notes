import json
import string
import nltk

from nltk.stem import WordNetLemmatizer
from typing import List
from pathlib import Path
from keybert import KeyBERT

nltk.download("stopwords")
nltk.download("wordnet")


class DataReader:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.ROOT = root_dir
        self.IGNORED_PATHS = {
            ".git",
            "__pycache__",
            "node_modules",
            ".github",
            "venv",
            ".venv",
            "nlp.venv",
            "site",
            "README.md",
        }

        self.SUPPORTED_EXTENSIONS = {".md", ".txt"}

    def read_files(self) -> List[Path]:
        return self._walk_directory(self.root_dir)

    def _walk_directory(self, directory: Path):
        """Walk through directory while respecting ignored paths"""
        for item in directory.rglob("*"):
            if not any(ignored in item.parts for ignored in self.IGNORED_PATHS):
                if item.is_file() and item.suffix in self.SUPPORTED_EXTENSIONS:
                    yield item


class Normalizer:
    def __init__(self):
        self.lower_case = True
        self.remove_punctuation = False
        self.remove_stopwords = True

        self.stop_words = set(nltk.corpus.stopwords.words("english"))

    def normalize_doc(self, doc: str) -> str:
        if self.lower_case:
            doc = doc.lower()

        if self.remove_punctuation:
            doc = str.translate(doc, str.maketrans("", "", string.punctuation))

        if self.remove_stopwords:
            doc = " ".join(
                [word for word in doc.split() if word not in self.stop_words]
            )

        return doc


def get_kw_path_map(files: List[Path], model: KeyBERT) -> dict:
    reader = DataReader()
    normalizer = Normalizer()

    keyword_map = {}

    for i, file in enumerate(files):
        with open(file) as f:
            doc = normalizer.normalize_doc(f.read())

            keywords = model.extract_keywords(
                doc,
                keyphrase_ngram_range=(1, 1),
                stop_words="english",
                use_mmr=True,
                diversity=0.3,
            )

            keyword_map["/".join(file.parts)] = keywords

    return keyword_map


def deduplicate(file_to_keywords: dict) -> dict:
    wnl = WordNetLemmatizer()
    deduped = {}
    dedup_count = 0
    for f, kws in file_to_keywords.items():
        deduped[f] = []
        for kw, acc in kws:
            stem = wnl.lemmatize(kw)
            if stem != kw:
                print("stem", stem, "kw", kw)
                dedup_count += 1
            if stem not in deduped[f]:
                deduped[f].append((stem, acc))
    print("dedup count", dedup_count)
    return deduped


def aggregate(file_to_keywords: dict) -> dict:
    keyword_to_files = {}
    for file, keywords in file_to_keywords.items():
        for keyword in keywords:
            if keyword[0] not in keyword_to_files:
                keyword_to_files[keyword[0]] = []
            keyword_to_files[keyword[0]].append(file)
    return keyword_to_files


def write_idx_to_json_file(idx: dict, output_path: Path):
    if output_path.exists():
        output_path.unlink()

    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)

    with open(output_path, "w") as f:
        json.dump(idx, f)


if __name__ == "__main__":
    reader = DataReader()
    files = reader.read_files()
    model = KeyBERT()

    file_to_kw = deduplicate(get_kw_path_map(files, model))
    kw_to_file = aggregate(file_to_kw)
    write_idx_to_json_file(file_to_kw, Path("idx/file_to_keywords.json"))
    write_idx_to_json_file(kw_to_file, Path("idx/keyword_to_files.json"))
