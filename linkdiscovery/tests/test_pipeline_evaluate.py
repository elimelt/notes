"""Tests for ``Pipeline.evaluate_holdout`` over the fixture corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from linkdiscovery import ConfigError, Pipeline, PipelineConfig, config_from_dict
from linkdiscovery.evaluate import DEGREE_BUCKETS

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "markdown_corpus"


def make_config() -> PipelineConfig:
    """A hashing-provider configuration over the fixture corpus."""
    data: dict[str, Any] = {
        "schema_version": 1,
        "source": {
            "adapter": "linkdiscovery_markdown.adapter:MarkdownSourceAdapter",
            "options": {"root": str(FIXTURE_ROOT), "exclude": ["templates/**"]},
        },
        "preprocess": {
            "parser": "linkdiscovery_markdown.parser:MarkdownRegionParser",
            "target_tokens": 128,
            "max_tokens": 192,
            "overlap_tokens": 16,
        },
        "embedding": {
            "provider": "hashing",
            "model": "hashing-baseline",
            "revision": "v1",
            "dimensions": 256,
            "precision": "float32",
            "device_preference": ["cpu"],
        },
    }
    return config_from_dict(data)


def test_holdout_metrics_are_sane(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    metrics = Pipeline().evaluate_holdout(
        make_config(),
        artifacts_root=root,
        holdout_fraction=0.5,
        seed=7,
        run_id="holdout",
    )
    assert metrics["holdout_count"] > 0
    assert metrics["visible_count"] > 0
    assert metrics["proposal_count"] > 0
    for k in (1, 5, 10, 25):
        assert 0.0 <= metrics[f"recall_at_{k}"] <= 1.0
    assert 0.0 <= metrics["mrr"] <= 1.0
    assert 0 <= metrics["recovered_count"] <= metrics["holdout_count"]
    assert metrics["seed"] == 7
    assert metrics["holdout_fraction"] == 0.5

    by_degree = metrics["recovery_by_degree"]
    assert set(by_degree) == set(DEGREE_BUCKETS)
    total_held = sum(bucket["holdout_count"] for bucket in by_degree.values())
    assert total_held == metrics["holdout_count"]
    for bucket in by_degree.values():
        assert 0.0 <= bucket["recall_at_k"] <= 1.0

    # metrics are persisted under runs/eval-<run_id> as JSON
    stored_path = root / "runs" / "eval-holdout"
    assert stored_path.is_file()
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    assert stored["run_id"] == "holdout"
    assert stored["holdout_count"] == metrics["holdout_count"]


def test_holdout_is_deterministic_for_a_seed(tmp_path: Path) -> None:
    config = make_config()
    first = Pipeline().evaluate_holdout(
        config, artifacts_root=tmp_path / "a", holdout_fraction=0.5, seed=7, run_id="x"
    )
    second = Pipeline().evaluate_holdout(
        config, artifacts_root=tmp_path / "b", holdout_fraction=0.5, seed=7, run_id="x"
    )
    assert first == second


def test_custom_k_values(tmp_path: Path) -> None:
    metrics = Pipeline().evaluate_holdout(
        make_config(),
        artifacts_root=tmp_path / "artifacts",
        holdout_fraction=0.5,
        seed=3,
        k_values=(2, 4),
        run_id="ks",
    )
    assert "recall_at_2" in metrics
    assert "recall_at_4" in metrics
    assert "recall_at_1" not in metrics


@pytest.mark.parametrize("fraction", [0.0, 1.0, -0.2, 1.5])
def test_invalid_holdout_fraction_is_a_config_error(tmp_path: Path, fraction: float) -> None:
    with pytest.raises(ConfigError, match="holdout_fraction"):
        Pipeline().evaluate_holdout(
            make_config(),
            artifacts_root=tmp_path / "artifacts",
            holdout_fraction=fraction,
            seed=1,
        )
