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

    def test_family_depth_zero_disables_the_cross_family_prior(
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
                "--family-depth",
                "0",
            ]
        )
        assert code == 0
        assert "baseline engine" in capsys.readouterr().out
        jsonl = tmp_path / "inline-proposals.jsonl"
        assert jsonl.is_file()
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            proposal = InlineProposal.from_dict(json.loads(line))
            assert "same_family" not in proposal.features

    def test_negative_family_depth_is_error(
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
                "--family-depth",
                "-1",
            ]
        )
        assert code == 2
        assert "depth must be >= 1" in capsys.readouterr().err

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


def write_review_decisions(path: Path, engines: tuple[str, ...] = ("baseline", "learned")) -> None:
    """A synthetic wire-format decisions.jsonl: accepts high, rejects low."""
    lines: list[dict[str, object]] = []
    for engine in engines:
        for index in range(8):
            lines.append(
                {
                    "engine": engine,
                    "id": f"sha256:{engine}-{index}",
                    "source": "systems/dynamo",
                    "target": "systems/consistency",
                    "anchor": "consistency",
                    "start": index * 10,
                    "end": index * 10 + 6,
                    "score": 0.55 + index * 0.04,
                    "flag": False,
                    "rank": index,
                    "verdict": "accept",
                    "target_ok": True,
                    "anchor_ok": True,
                    "placement_ok": True,
                    "reason": "good",
                    "note": "",
                }
            )
        lines.extend(
            {
                "engine": engine,
                "id": f"sha256:{engine}-r{index}",
                "source": "systems/dynamo",
                "target": "systems/consistency",
                "anchor": "consistency",
                "start": 200 + index * 10,
                "end": 200 + index * 10 + 6,
                "score": 0.15 + index * 0.05,
                "flag": True,
                "rank": 100 + index,
                "verdict": "reject",
                "target_ok": False,
                "anchor_ok": False,
                "placement_ok": False,
                "reason": "wrong_target",
                "note": "",
            }
            for index in range(6)
        )
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def write_benchmark_file(path: Path) -> None:
    """A two-case benchmark over the fixture corpus (anchor-text located)."""
    data = {
        "header": {
            "schema_version": 1,
            "run_id": "bm-test",
            "corpus_id": "corpus-test",
            "created_at": "2026-08-01T00:00:00+00:00",
            "config_fingerprint": "sha256:cfg",
            "producer_version": "test",
        },
        "cases": [
            {
                "id": "bm-natural",
                "kind": "natural_span",
                "source_document_id": "systems/dynamo",
                "span": None,
                "anchor_text": "consistency",
                "target_document_id": None,
                "expected": True,
                "hard_case": False,
                "note": "",
            },
            {
                "id": "bm-no-link",
                "kind": "no_link",
                "source_document_id": "systems/dynamo",
                "span": None,
                "anchor_text": "availability",
                "target_document_id": None,
                "expected": True,
                "hard_case": True,
                "note": "",
            },
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


class TestCalibrate:
    def test_fits_both_engines_and_writes_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reviews = tmp_path / "decisions.jsonl"
        write_review_decisions(reviews)
        out = tmp_path / "calibration.json"
        code = main(["inline", "calibrate", "--reviews", str(reviews), "--out", str(out)])
        assert code == 0
        captured = capsys.readouterr().out
        assert "temperature" in captured
        assert "baseline" in captured
        assert "learned" in captured
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data) == {"baseline", "learned"}
        for entry in data.values():
            assert entry["temperature"] > 0
            assert entry["n"] == 14
            assert "conformal" in entry

    def test_missing_reviews_file_is_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "calibrate",
                "--reviews",
                str(tmp_path / "missing.jsonl"),
                "--out",
                str(tmp_path / "calibration.json"),
            ]
        )
        assert code == 2
        assert "error:" in capsys.readouterr().err


class TestProposeWithCalibration:
    def test_baseline_calibration_populates_calibrated_probability(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reviews = tmp_path / "decisions.jsonl"
        write_review_decisions(reviews, engines=("baseline",))
        calibration = tmp_path / "calibration.json"
        assert (
            main(["inline", "calibrate", "--reviews", str(reviews), "--out", str(calibration)]) == 0
        )
        capsys.readouterr()
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
                "baseline",
                "--out",
                str(report_dir),
                "--threshold",
                "0.2",
                "--calibration",
                str(calibration),
            ]
        )
        assert code == 0
        assert "baseline engine" in capsys.readouterr().out
        jsonl = report_dir / "inline-proposals.jsonl"
        proposals = [
            InlineProposal.from_dict(json.loads(line))
            for line in jsonl.read_text(encoding="utf-8").splitlines()
        ]
        assert proposals
        assert all(p.calibrated_probability is not None for p in proposals)

    def test_engine_absent_from_calibration_file_is_error(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reviews = tmp_path / "decisions.jsonl"
        write_review_decisions(reviews, engines=("learned",))
        calibration = tmp_path / "calibration.json"
        assert (
            main(["inline", "calibrate", "--reviews", str(reviews), "--out", str(calibration)]) == 0
        )
        capsys.readouterr()
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
                str(tmp_path / "report"),
                "--calibration",
                str(calibration),
            ]
        )
        assert code == 2
        assert "no entry for engine" in capsys.readouterr().err


class TestBenchmark:
    def test_writes_scores_and_prints_per_kind_rows(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        benchmark_path = tmp_path / "benchmark.json"
        write_benchmark_file(benchmark_path)
        out = tmp_path / "scores.json"
        code = main(
            [
                "inline",
                "benchmark",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--benchmark",
                str(benchmark_path),
                "--engine",
                "baseline",
                "--out",
                str(out),
            ]
        )
        assert code == 0
        captured = capsys.readouterr().out
        assert "natural_span" in captured
        assert "overall" in captured
        scores = json.loads(out.read_text(encoding="utf-8"))
        assert scores["overall"]["total"] == 2.0
        assert scores["overall"]["evaluated"] == 2.0
        assert scores["natural_span"]["total"] == 1.0
        assert scores["hard_case"]["total"] == 1.0

    def test_learned_without_heads_is_error(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        benchmark_path = tmp_path / "benchmark.json"
        write_benchmark_file(benchmark_path)
        code = main(
            [
                "inline",
                "benchmark",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--benchmark",
                str(benchmark_path),
                "--engine",
                "learned",
                "--out",
                str(tmp_path / "scores.json"),
            ]
        )
        assert code == 2
        assert "--heads is required" in capsys.readouterr().err

    def test_missing_benchmark_file_is_error(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "inline",
                "benchmark",
                "--config",
                str(workspace.config),
                "--artifacts",
                str(workspace.artifacts),
                "--benchmark",
                str(tmp_path / "missing.json"),
                "--engine",
                "baseline",
                "--out",
                str(tmp_path / "scores.json"),
            ]
        )
        assert code == 2
        assert "error:" in capsys.readouterr().err


class TestTrainWithReviews:
    def test_train_accepts_a_reviews_file(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        alice, _ = write_synthetic_labels(workspace, tmp_path)
        reviews = tmp_path / "decisions.jsonl"
        write_review_decisions(reviews, engines=("learned",))
        heads_dir = tmp_path / "heads-reviews"
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
                str(alice),
                "--out",
                str(heads_dir),
                "--epochs",
                "1",
                "--reviews",
                str(reviews),
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "review decisions" in out
        assert "14" in out
        assert (heads_dir / "weights.pt").is_file()

    def test_missing_reviews_file_is_error(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        alice, _ = write_synthetic_labels(workspace, tmp_path)
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
                str(alice),
                "--out",
                str(tmp_path / "heads"),
                "--reviews",
                str(tmp_path / "missing.jsonl"),
            ]
        )
        assert code == 2
        assert "error:" in capsys.readouterr().err


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

    def test_explicit_hashing_token_encoder_is_the_default_path(
        self, workspace: Workspace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        alice, _ = write_synthetic_labels(workspace, tmp_path)
        heads_dir = tmp_path / "heads-hashing"
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
                str(alice),
                "--out",
                str(heads_dir),
                "--epochs",
                "1",
                "--token-encoder",
                "hashing",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "token encoder    hashing" in out or "hashing" in out
        assert (heads_dir / "metadata.json").is_file()

    def test_unknown_token_encoder_is_usage_error(
        self, workspace: Workspace, tmp_path: Path
    ) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(
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
                    str(tmp_path / "missing.jsonl"),
                    "--out",
                    str(tmp_path / "heads"),
                    "--token-encoder",
                    "bert",
                ]
            )
        assert excinfo.value.code == 2
