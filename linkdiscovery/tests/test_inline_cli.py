"""CLI tests for the ``linkdiscovery inline`` subcommand group.

Every test drives :func:`linkdiscovery.cli.main` directly. A module-scoped
temporary workspace holds one YAML configuration and one shared artifact
store, so the embedding cache is reused across commands and the suite stays
fast. Interactive annotation is exercised by feeding scripted stdin.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from linkdiscovery.cli import main
from linkdiscovery.inline.audit.annotate import save_audit_labels
from linkdiscovery.inline.audit.tiers import derive_tier
from linkdiscovery.inline.records import AuditLabel, AuditSample, InlineProposal

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "markdown_corpus"


@dataclass(frozen=True)
class Workspace:
    """Shared on-disk layout for the CLI tests."""

    config: Path
    artifacts: Path
    audit: Path
    sample: Path


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Workspace:
    """Config file + artifact store + a pre-built audit sample."""
    root = tmp_path_factory.mktemp("inline-cli")
    config_path = root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
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
        ),
        encoding="utf-8",
    )
    workspace = Workspace(
        config=config_path,
        artifacts=root / "artifacts",
        audit=root / "audit",
        sample=root / "audit" / "audit-sample.json",
    )
    code = main(
        [
            "inline",
            "audit-sample",
            "--config",
            str(workspace.config),
            "--artifacts",
            str(workspace.artifacts),
            "--size",
            "50",
            "--seed",
            "7",
            "--out",
            str(workspace.audit),
        ]
    )
    assert code == 0
    return workspace


def load_sample(workspace: Workspace) -> AuditSample:
    return AuditSample.from_dict(json.loads(workspace.sample.read_text(encoding="utf-8")))


def write_synthetic_labels(workspace: Workspace, directory: Path) -> tuple[Path, Path]:
    """Two annotator label files over the shared sample; bob disputes some anchors."""
    sample = load_sample(workspace)
    per_annotator: dict[str, list[AuditLabel]] = {"alice": [], "bob": []}
    for position, item in enumerate(sample.items):
        for annotator, labels in per_annotator.items():
            natural = not (annotator == "bob" and position % 5 == 0)
            tier = derive_tier(True, natural, True, item.region_kind)
            labels.append(
                AuditLabel(
                    item_id=item.id,
                    annotator=annotator,
                    target_correct=True,
                    anchor_natural=natural,
                    placement_valid=True,
                    tier=tier,
                )
            )
    alice = directory / "labels-alice.jsonl"
    bob = directory / "labels-bob.jsonl"
    save_audit_labels(per_annotator["alice"], alice)
    save_audit_labels(per_annotator["bob"], bob)
    return alice, bob


class TestAuditSample:
    def test_writes_both_artifacts(self, workspace: Workspace) -> None:
        assert workspace.sample.is_file()
        assert (workspace.audit / "audit-sample.md").is_file()
        assert load_sample(workspace).items


class TestAnnotate:
    def test_quit_immediately(
        self,
        workspace: Workspace,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO("q\n"))
        code = main(
            [
                "inline",
                "annotate",
                "--sample",
                str(workspace.sample),
                "--annotator",
                "alice",
                "--labels",
                str(tmp_path / "labels.jsonl"),
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "pending" in out
        assert "labeled 0 item(s)" in out


class TestAuditReport:
    def test_prints_kappa_and_verdict(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        alice, bob = write_synthetic_labels(workspace, tmp_path)
        code = main(
            [
                "inline",
                "audit-report",
                "--sample",
                str(workspace.sample),
                "--labels",
                str(alice),
                "--labels2",
                str(bob),
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "kappa_anchor_natural" in out
        assert "alpha_tier" in out
        assert "Tier distribution" in out
        # The tiny fixture cannot reach 150 clean positives, so the honest
        # verdict is NO-GO with an explanatory note.
        assert "Verdict: NO-GO" in out
        assert "below threshold" in out

    def test_missing_labels_file_is_error(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "audit-report",
                "--sample",
                str(workspace.sample),
                "--labels",
                str(tmp_path / "nope.jsonl"),
            ]
        )
        assert code == 2
        assert "error:" in capsys.readouterr().err


class TestAnchors:
    def test_writes_dictionary_and_stats(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "anchors",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--out",
                str(tmp_path),
            ]
        )
        assert code == 0
        assert (tmp_path / "anchor-dictionary.json").is_file()
        assert (tmp_path / "anchor-stats.json").is_file()
        assert "mentions" in capsys.readouterr().out


class TestRecallCheck:
    def test_prints_recall_and_gate(
        self, workspace: Workspace, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "recall-check",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--sample",
                str(workspace.sample),
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "overlap recall" in out
        assert "PASS" in out

    def test_missing_sample_file_is_error(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "recall-check",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--sample",
                str(tmp_path / "missing.json"),
            ]
        )
        assert code == 2
        assert "error:" in capsys.readouterr().err


class TestProposeBaseline:
    def test_writes_report_files(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "propose",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--engine",
                "baseline",
                "--out",
                str(tmp_path),
                "--threshold",
                "0.2",
                "--budget-words",
                "150",
                "--max-per-note",
                "5",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "baseline engine" in out
        assert "accepted" in out
        jsonl = tmp_path / "inline-proposals.jsonl"
        assert jsonl.is_file()
        assert (tmp_path / "inline-proposals.md").is_file()
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            InlineProposal.from_dict(json.loads(line))

    def test_unknown_engine_is_usage_error(self, workspace: Workspace) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(
                [
                    "inline",
                    "propose",
                    "--config",
                    str(workspace.config),
                    "--artifacts",
                    str(workspace.artifacts),
                    "--engine",
                    "quantum",
                    "--out",
                    "unused",
                ]
            )
        assert excinfo.value.code == 2

    def test_learned_without_heads_is_error(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "propose",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--engine",
                "learned",
                "--out",
                str(tmp_path),
            ]
        )
        assert code == 2
        assert "--heads is required" in capsys.readouterr().err


class TestTrainAndProposeLearned:
    def test_train_then_propose(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        alice, bob = write_synthetic_labels(workspace, tmp_path)
        merged = tmp_path / "labels.jsonl"
        merged.write_text(
            alice.read_text(encoding="utf-8") + bob.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        heads_dir = tmp_path / "heads"
        code = main(
            [
                "inline",
                "train",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--sample",
                str(workspace.sample),
                "--labels",
                str(merged),
                "--out",
                str(heads_dir),
                "--epochs",
                "2",
                "--seed",
                "0",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "Trained heads saved" in out
        assert "final loss" in out
        assert (heads_dir / "weights.pt").is_file()

        report_dir = tmp_path / "report"
        code = main(
            [
                "inline",
                "propose",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--engine",
                "learned",
                "--heads",
                str(heads_dir),
                "--out",
                str(report_dir),
                "--threshold",
                "0.2",
            ]
        )
        assert code == 0
        assert "learned engine" in capsys.readouterr().out
        assert (report_dir / "inline-proposals.jsonl").is_file()
        assert (report_dir / "inline-proposals.md").is_file()
