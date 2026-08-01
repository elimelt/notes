"""CLI tests: happy paths and error paths via direct ``main([...])`` calls."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from linkdiscovery import __version__
from linkdiscovery.cli import main
from linkdiscovery.contracts.proposals import LinkProposal

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "markdown_corpus"


def config_data() -> dict[str, Any]:
    """The hashing-provider configuration the CLI tests write to YAML."""
    return {
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


@dataclass(frozen=True)
class CliWorkspace:
    """Paths produced by one CLI run shared across the read-only tests."""

    config_path: Path
    artifacts: Path
    proposals_jsonl: Path


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> CliWorkspace:
    """Write a config, run ``linkdiscovery run`` once, and expose the outputs."""
    base = tmp_path_factory.mktemp("cli")
    config_path = base / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data()), encoding="utf-8")
    artifacts = base / "artifacts"
    code = main(
        ["run", "--config", str(config_path), "--artifacts", str(artifacts), "--run-id", "cli"]
    )
    assert code == 0
    return CliWorkspace(
        config_path=config_path,
        artifacts=artifacts,
        proposals_jsonl=artifacts / "reports" / "proposals.jsonl",
    )


class TestRunCommand:
    def test_summary_output(
        self, workspace: CliWorkspace, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Re-running into the same store is cheap (full cache reuse) and
        # exercises the summary against a warm cache.
        code = main(
            [
                "run",
                "--config",
                str(workspace.config_path),
                "--artifacts",
                str(workspace.artifacts),
                "--run-id",
                "cli",
            ]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "Run cli complete." in out
        assert "documents" in out and "units" in out and "vectors" in out
        assert "candidates" in out and "proposals" in out
        assert "device" in out and "fallbacks: none" in out
        assert "cache:" in out and "misses" in out
        assert "Top" in out and "1." in out  # ranked proposal lines with scores
        assert "Reports written to" in out and "proposals.jsonl" in out
        # warm cache: zero misses on the second run
        assert "0 misses" in out

    def test_config_not_found(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(
            [
                "run",
                "--config",
                str(tmp_path / "missing.yaml"),
                "--artifacts",
                str(tmp_path / "artifacts"),
            ]
        )
        captured = capsys.readouterr()
        assert code == 2
        assert captured.err.startswith("error: ")
        assert "missing.yaml" in captured.err

    def test_unknown_config_field(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        data = config_data()
        data["embedding"]["mystery_field"] = True
        config_path = tmp_path / "bad.yaml"
        config_path.write_text(yaml.safe_dump(data), encoding="utf-8")
        code = main(
            ["run", "--config", str(config_path), "--artifacts", str(tmp_path / "artifacts")]
        )
        captured = capsys.readouterr()
        assert code == 2
        assert captured.err.startswith("error: ")
        assert "mystery_field" in captured.err

    def test_missing_required_argument_exits_2(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(["run", "--config", "whatever.yaml"])  # --artifacts missing
        assert excinfo.value.code == 2


class TestEvaluateCommand:
    def test_metrics_table(
        self, workspace: CliWorkspace, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "evaluate",
                "--config",
                str(workspace.config_path),
                "--artifacts",
                str(workspace.artifacts),
                "--holdout-fraction",
                "0.5",
                "--seed",
                "7",
                "--k",
                "1,5",
            ]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "Held-out link recovery" in out
        assert "recall@1" in out and "recall@5" in out
        assert "mrr" in out
        assert "held-out links" in out
        assert "Recovery by visible source out-degree" in out

    def test_invalid_fraction_is_a_clean_error(
        self, workspace: CliWorkspace, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "evaluate",
                "--config",
                str(workspace.config_path),
                "--artifacts",
                str(workspace.artifacts),
                "--holdout-fraction",
                "1.5",
                "--seed",
                "7",
            ]
        )
        captured = capsys.readouterr()
        assert code == 2
        assert "holdout_fraction" in captured.err

    def test_malformed_k_exits_2(self, workspace: CliWorkspace) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(
                [
                    "evaluate",
                    "--config",
                    str(workspace.config_path),
                    "--artifacts",
                    str(workspace.artifacts),
                    "--holdout-fraction",
                    "0.5",
                    "--seed",
                    "7",
                    "--k",
                    "abc",
                ]
            )
        assert excinfo.value.code == 2


class TestReviewQueueCommand:
    def test_writes_queue_file(
        self, workspace: CliWorkspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out_path = tmp_path / "queue.jsonl"
        code = main(
            [
                "review-queue",
                "--proposals",
                str(workspace.proposals_jsonl),
                "--size",
                "5",
                "--seed",
                "3",
                "--out",
                str(out_path),
            ]
        )
        captured = capsys.readouterr()
        assert code == 0
        assert str(out_path) in captured.out
        lines = out_path.read_text(encoding="utf-8").splitlines()
        total = len(workspace.proposals_jsonl.read_text(encoding="utf-8").splitlines())
        assert len(lines) == min(5, total)
        for line in lines:
            LinkProposal.from_dict(json.loads(line))

    def test_prints_queue_to_stdout(
        self, workspace: CliWorkspace, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "review-queue",
                "--proposals",
                str(workspace.proposals_jsonl),
                "--size",
                "3",
                "--seed",
                "3",
            ]
        )
        out = capsys.readouterr().out
        assert code == 0
        lines = [line for line in out.splitlines() if line.strip()]
        assert len(lines) == 3
        for line in lines:
            LinkProposal.from_dict(json.loads(line))

    def test_same_seed_same_queue(
        self, workspace: CliWorkspace, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = [
            "review-queue",
            "--proposals",
            str(workspace.proposals_jsonl),
            "--size",
            "4",
            "--seed",
            "11",
        ]
        assert main(args) == 0
        first = capsys.readouterr().out
        assert main(args) == 0
        second = capsys.readouterr().out
        assert first == second

    def test_missing_proposals_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "review-queue",
                "--proposals",
                str(tmp_path / "nope.jsonl"),
                "--size",
                "5",
                "--seed",
                "1",
            ]
        )
        captured = capsys.readouterr()
        assert code == 2
        assert captured.err.startswith("error: ")

    def test_corrupt_jsonl_line(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        bad = tmp_path / "bad.jsonl"
        bad.write_text("not-json\n", encoding="utf-8")
        code = main(["review-queue", "--proposals", str(bad), "--size", "5", "--seed", "1"])
        captured = capsys.readouterr()
        assert code == 2
        assert "bad.jsonl:1" in captured.err


class TestTopLevel:
    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])
        assert excinfo.value.code == 0
        assert f"linkdiscovery {__version__}" in capsys.readouterr().out

    def test_no_command_exits_2(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main([])
        assert excinfo.value.code == 2

    def test_unknown_command_exits_2(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(["frobnicate"])
        assert excinfo.value.code == 2
