"""Tests for the token counters."""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from linkdiscovery.errors import PreprocessError
from linkdiscovery.preprocess import HuggingFaceTokenCounter, SimpleTokenCounter


class TestSimpleTokenCounter:
    def test_counts_words_and_punctuation(self) -> None:
        counter = SimpleTokenCounter()
        assert counter.count_tokens("Hello, world!") == 4  # hello , world !
        assert counter.count_tokens("one two three") == 3
        assert counter.count_tokens("") == 0
        assert counter.count_tokens("   \n\t  ") == 0

    def test_counts_are_additive_across_whitespace(self) -> None:
        counter = SimpleTokenCounter()
        a, b = "alpha beta.", "gamma (delta)"
        assert counter.count_tokens(f"{a} {b}") == counter.count_tokens(a) + counter.count_tokens(b)
        assert counter.count_tokens(f"{a}\n\n{b}") == counter.count_tokens(
            a
        ) + counter.count_tokens(b)

    def test_deterministic(self) -> None:
        counter = SimpleTokenCounter()
        text = "Same text, same count: 42 tokens? no."
        assert counter.count_tokens(text) == counter.count_tokens(text)

    def test_fingerprint(self) -> None:
        assert SimpleTokenCounter().fingerprint == "simple-tokenizer:v1"


class TestHuggingFaceTokenCounter:
    def test_missing_transformers_raises_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real_import_module = importlib.import_module

        def fake_import_module(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "transformers":
                raise ImportError("No module named 'transformers'")
            return real_import_module(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", fake_import_module)
        with pytest.raises(PreprocessError, match="embeddings"):
            HuggingFaceTokenCounter("Qwen/Qwen3-Embedding-8B", "abc123")

    def test_empty_model_or_revision_rejected(self) -> None:
        with pytest.raises(PreprocessError, match="model_id"):
            HuggingFaceTokenCounter("", "rev")
        with pytest.raises(PreprocessError, match="revision"):
            HuggingFaceTokenCounter("model", "")

    def test_counts_via_auto_tokenizer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        transformers = pytest.importorskip("transformers")

        class FakeTokenizer:
            def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
                assert add_special_tokens is False
                return [0] * len(text.split())

        seen: dict[str, str] = {}

        def fake_from_pretrained(model_id: str, revision: str) -> FakeTokenizer:
            seen["model_id"] = model_id
            seen["revision"] = revision
            return FakeTokenizer()

        monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", fake_from_pretrained)
        counter = HuggingFaceTokenCounter("org/model", "rev123")
        assert counter.count_tokens("a b c") == 3
        assert seen == {"model_id": "org/model", "revision": "rev123"}

    def test_fingerprint_includes_model_and_revision(self, monkeypatch: pytest.MonkeyPatch) -> None:
        transformers = pytest.importorskip("transformers")
        monkeypatch.setattr(
            transformers.AutoTokenizer,
            "from_pretrained",
            lambda model_id, revision: object(),
        )
        counter = HuggingFaceTokenCounter("org/model", "rev123")
        assert counter.fingerprint == "hf-tokenizer:org/model@rev123"

    def test_tokenizer_load_failure_wrapped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        transformers = pytest.importorskip("transformers")

        def boom(model_id: str, revision: str) -> None:
            raise OSError("no such repo")

        monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", boom)
        with pytest.raises(PreprocessError, match="could not load tokenizer"):
            HuggingFaceTokenCounter("org/missing", "rev123")
