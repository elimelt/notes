"""Command-line interface for the missing-link discovery pipeline.

Standard-library ``argparse`` only. Top-level subcommands:

- ``run`` — execute a full batch run from a YAML configuration and print a
  human summary (counts, device, cache reuse, top proposals, report paths).
- ``evaluate`` — hide a stratified fraction of existing links, rerun
  discovery, and print held-out recovery metrics.
- ``review-queue`` — build the stratified human review queue from a
  ``proposals.jsonl`` file.
- ``export-embeddings`` — join a completed run's vectors and metadata into a
  self-contained NumPy bundle for reranking experiments.
- ``inline <sub>`` — the learned inline-link subsystem
  (SPEC-INLINE-LINKING.md §11): ``audit-sample``, ``annotate``,
  ``audit-report``, ``anchors``, ``recall-check``, ``train``, and
  ``propose``.

Exit codes: ``0`` on success; ``2`` for usage errors (via argparse) and for
any :class:`~linkdiscovery.errors.LinkDiscoveryError` or I/O failure, which
are printed to stderr as ``error: <message>``. ``-v/--verbose`` (repeatable)
configures :mod:`logging` on stderr at INFO then DEBUG; library code never
prints — all diagnostics flow through logging.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from linkdiscovery import __version__
from linkdiscovery.artifacts.cache import ArtifactCache
from linkdiscovery.artifacts.store import ArtifactStore
from linkdiscovery.config import load_config
from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.proposals import (
    SCHEMA_VERSION as PROPOSALS_SCHEMA_VERSION,
)
from linkdiscovery.contracts.proposals import (
    LinkProposal,
    ProposalSet,
)
from linkdiscovery.errors import ConfigError, ContractError, LinkDiscoveryError
from linkdiscovery.experiment_export import export_experiment_embeddings
from linkdiscovery.fingerprint import canonical_json
from linkdiscovery.inline import workflow
from linkdiscovery.inline.anchors import AnchorConfig
from linkdiscovery.inline.audit.annotate import load_audit_labels, run_annotation_session
from linkdiscovery.inline.audit.tiers import build_audit_report
from linkdiscovery.inline.baseline import BaselineConfig
from linkdiscovery.inline.heads import TrainedHeads
from linkdiscovery.inline.report import write_inline_report
from linkdiscovery.inline.select import SelectionConfig
from linkdiscovery.inline.spans import SpanConfig
from linkdiscovery.inline.train import TrainConfig
from linkdiscovery.pipeline import PRODUCER_VERSION, Pipeline, RunResult
from linkdiscovery.report import build_review_queue
from linkdiscovery.report._io import atomic_write_text

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from linkdiscovery.contracts.manifests import RunManifest, StageStats
    from linkdiscovery.inline.encode import TokenStateEncoder
    from linkdiscovery.inline.records import AuditLabel

__all__ = ["build_parser", "main"]

_DIRECTION_ARROWS = {
    "source-to-target": "->",
    "target-to-source": "<-",
    "undirected": "<->",
}
_TOP_PROPOSALS = 10


def _k_values(text: str) -> tuple[int, ...]:
    """Parse ``--k`` as a comma-separated list of positive integers."""
    try:
        values = tuple(int(part) for part in text.split(",") if part.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid k list {text!r}; expected comma-separated integers such as 1,5,10,25"
        ) from None
    if not values or any(k <= 0 for k in values):
        raise argparse.ArgumentTypeError(
            f"invalid k list {text!r}; every k must be a positive integer"
        )
    return values


def build_parser() -> argparse.ArgumentParser:
    """Build the ``linkdiscovery`` argument parser (exposed for tests and docs)."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="log INFO to stderr; repeat (-vv) for DEBUG",
    )

    parser = argparse.ArgumentParser(
        prog="linkdiscovery",
        description="Propose missing links between documents, with inspectable evidence.",
    )
    parser.add_argument("--version", action="version", version=f"linkdiscovery {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    run = commands.add_parser(
        "run",
        parents=[common],
        help="run the full pipeline from a YAML configuration",
        description="Run adapter, preprocess, embed, candidates, rank, and report.",
    )
    run.add_argument("--config", required=True, type=Path, help="pipeline YAML configuration")
    run.add_argument("--artifacts", required=True, type=Path, help="artifact store root directory")
    run.add_argument(
        "--reviews", type=Path, default=None, help="review history JSON (optional feedback)"
    )
    run.add_argument(
        "--run-id", default=None, help="override the derived run id (for reproducibility)"
    )
    run.set_defaults(handler=_cmd_run)

    evaluate = commands.add_parser(
        "evaluate",
        parents=[common],
        help="measure held-out link recovery",
        description="Hide a fraction of existing links, rerun discovery, report recovery.",
    )
    evaluate.add_argument("--config", required=True, type=Path, help="pipeline YAML configuration")
    evaluate.add_argument(
        "--artifacts", required=True, type=Path, help="artifact store root directory"
    )
    evaluate.add_argument(
        "--holdout-fraction",
        required=True,
        type=float,
        help="fraction of existing links to hide, in (0, 1)",
    )
    evaluate.add_argument("--seed", required=True, type=int, help="holdout sampling seed")
    evaluate.add_argument(
        "--k",
        type=_k_values,
        default=(1, 5, 10, 25),
        help="comma-separated recall cutoffs (default: 1,5,10,25)",
    )
    evaluate.set_defaults(handler=_cmd_evaluate)

    queue = commands.add_parser(
        "review-queue",
        parents=[common],
        help="build a stratified human review queue from proposals.jsonl",
        description="Select a stratified sample of proposals for human review.",
    )
    queue.add_argument(
        "--proposals", required=True, type=Path, help="proposals.jsonl written by a run"
    )
    queue.add_argument("--size", required=True, type=int, help="number of proposals to queue")
    queue.add_argument("--seed", required=True, type=int, help="random-stratum sampling seed")
    queue.add_argument(
        "--out", type=Path, default=None, help="write the queue here as JSONL (default: stdout)"
    )
    queue.set_defaults(handler=_cmd_review_queue)

    export = commands.add_parser(
        "export-embeddings",
        parents=[common],
        help="export document and semantic-unit embeddings for experiments",
        description=(
            "Export a completed run's document matrix, full unit matrix, and "
            "inline-link metadata to one compressed NumPy archive."
        ),
    )
    export.add_argument(
        "--artifacts", required=True, type=Path, help="artifact store root directory"
    )
    export.add_argument("--run-id", required=True, help="completed run ID, e.g. run-...")
    export.add_argument("--out", required=True, type=Path, help="output .npz path")
    export.set_defaults(handler=_cmd_export_embeddings)

    _add_inline_commands(commands, common)
    return parser


def _add_inline_commands(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
    common: argparse.ArgumentParser,
) -> None:
    """Register the ``inline`` subcommand group (SPEC-INLINE-LINKING.md §11)."""
    inline = commands.add_parser(
        "inline",
        parents=[common],
        help="learned inline-link discovery (audit, anchors, train, propose)",
        description="Phased inline-link subsystem: audit -> recall check -> train -> propose.",
    )
    subcommands = inline.add_subparsers(dest="inline_command", required=True, metavar="SUBCOMMAND")

    def pipeline_args(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--config", required=True, type=Path, help="pipeline YAML configuration")
        sub.add_argument(
            "--artifacts", required=True, type=Path, help="artifact store root directory"
        )

    audit_sample = subcommands.add_parser(
        "audit-sample",
        parents=[common],
        help="draw the stratified audit sample of existing links (phase 1)",
        description="Sample existing links for the data audit and write JSON+Markdown.",
    )
    pipeline_args(audit_sample)
    audit_sample.add_argument(
        "--size", type=int, default=150, help="sample size (default: 150, per the spec)"
    )
    audit_sample.add_argument("--seed", required=True, type=int, help="stratified sampling seed")
    audit_sample.add_argument("--out", required=True, type=Path, help="output directory")
    audit_sample.set_defaults(handler=_cmd_inline_audit_sample)

    annotate = subcommands.add_parser(
        "annotate",
        parents=[common],
        help="label the audit sample interactively (phase 1)",
        description="Run the terminal annotation session over an audit sample.",
    )
    annotate.add_argument("--sample", required=True, type=Path, help="audit-sample.json path")
    annotate.add_argument("--annotator", required=True, help="annotator name recorded on labels")
    annotate.add_argument("--labels", required=True, type=Path, help="labels JSONL path (appended)")
    annotate.set_defaults(handler=_cmd_inline_annotate)

    audit_report = subcommands.add_parser(
        "audit-report",
        parents=[common],
        help="agreement, tier distribution, and the GO/NO-GO verdict (phase 1)",
        description="Merge label files and print the audit go/no-go decision.",
    )
    audit_report.add_argument("--sample", required=True, type=Path, help="audit-sample.json path")
    audit_report.add_argument(
        "--labels",
        required=True,
        type=Path,
        action="append",
        help="labels JSONL path (repeatable: one per annotator file)",
    )
    audit_report.add_argument(
        "--labels2",
        type=Path,
        action="append",
        default=[],
        help="additional labels JSONL path(s) to merge",
    )
    audit_report.set_defaults(handler=_cmd_inline_audit_report)

    anchors = subcommands.add_parser(
        "anchors",
        parents=[common],
        help="build the anchor dictionary and keyphraseness statistics",
        description="Mine the self-corpus anchor dictionary and write its artifacts.",
    )
    pipeline_args(anchors)
    anchors.add_argument("--out", required=True, type=Path, help="output directory")
    anchors.set_defaults(handler=_cmd_inline_anchors)

    recall = subcommands.add_parser(
        "recall-check",
        parents=[common],
        help="span-generator recall over audited prose anchors (phase 2 gate)",
        description="Verify the high-recall span generator covers the audited anchors.",
    )
    pipeline_args(recall)
    recall.add_argument("--sample", required=True, type=Path, help="audit-sample.json path")
    recall.set_defaults(handler=_cmd_inline_recall_check)

    train = subcommands.add_parser(
        "train",
        parents=[common],
        help="train the three frozen-encoder heads on audited labels (phase 3)",
        description="Assemble tier-routed training data and train Architecture A heads.",
    )
    pipeline_args(train)
    train.add_argument("--sample", required=True, type=Path, help="audit-sample.json path")
    train.add_argument("--labels", required=True, type=Path, help="labels JSONL path")
    train.add_argument("--out", required=True, type=Path, help="trained-heads output directory")
    train.add_argument("--epochs", type=int, default=30, help="training epochs (default: 30)")
    train.add_argument("--seed", type=int, default=0, help="training seed (default: 0)")
    train.add_argument(
        "--token-encoder",
        choices=("hashing", "qwen"),
        default="hashing",
        help=(
            "frozen token-state encoder: dependency-free hashing (default) or the "
            "windowed Qwen model from the config's embedding pin"
        ),
    )
    train.set_defaults(handler=_cmd_inline_train)

    propose = subcommands.add_parser(
        "propose",
        parents=[common],
        help="propose inline links with the baseline or learned engine",
        description="Run span proposal, scoring, and global selection; write review files.",
    )
    pipeline_args(propose)
    propose.add_argument(
        "--engine",
        required=True,
        choices=("baseline", "learned"),
        help="scoring engine: deterministic baseline or trained heads",
    )
    propose.add_argument(
        "--heads", type=Path, default=None, help="trained-heads directory (learned engine)"
    )
    propose.add_argument("--out", required=True, type=Path, help="report output directory")
    propose.add_argument(
        "--threshold", type=float, default=None, help="override the accept threshold"
    )
    propose.add_argument(
        "--budget-words", type=int, default=None, help="override words-per-link budget"
    )
    propose.add_argument(
        "--max-per-note", type=int, default=None, help="override the per-note link cap"
    )
    propose.add_argument(
        "--token-encoder",
        choices=("hashing", "qwen"),
        default="hashing",
        help=(
            "frozen token-state encoder for --engine learned: hashing (default) or the "
            "windowed Qwen model from the config's embedding pin"
        ),
    )
    propose.set_defaults(handler=_cmd_inline_propose)


_LOG_LEVELS = (logging.WARNING, logging.INFO, logging.DEBUG)


def _configure_logging(verbosity: int) -> None:
    """Route library logging to stderr at WARNING/INFO/DEBUG by ``-v`` count."""
    level = _LOG_LEVELS[min(verbosity, len(_LOG_LEVELS) - 1)]
    logging.basicConfig(
        stream=sys.stderr, level=level, format="%(levelname)s %(name)s: %(message)s"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code.

    Usage errors exit 2 via argparse (``SystemExit``); pipeline errors are
    caught here, printed to stderr as ``error: <message>``, and return 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    handler = args.handler
    try:
        result: int = handler(args)
    except (LinkDiscoveryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return result


# --------------------------------------------------------------------- run


def _stage(manifest: RunManifest, name: str) -> StageStats | None:
    """The named stage's stats from the manifest, or ``None``."""
    for stage in manifest.stages:
        if stage.stage == name:
            return stage
    return None


def _counter(stage: StageStats | None, name: str) -> int:
    """A stage counter with a zero default for missing stages or counters."""
    if stage is None:
        return 0
    return stage.counters.get(name, 0)


def _print_run_summary(result: RunResult) -> None:
    """The human summary the ``run`` command prints to stdout."""
    manifest = result.manifest
    source = _stage(manifest, "source")
    preprocess = _stage(manifest, "preprocess")
    embed = _stage(manifest, "embed")
    candidates = _stage(manifest, "candidates")
    device = manifest.environment.get("device", "unknown")
    fallbacks = tuple(embed.warnings) if embed is not None else ()
    print(f"Run {result.run_id} complete.")
    print()
    print(
        f"  documents   {_counter(source, 'documents'):>6}"
        f"  ({_counter(preprocess, 'skipped_excluded')} excluded)"
    )
    print(f"  units       {_counter(preprocess, 'units'):>6}")
    hits = embed.cache_hits if embed is not None else 0
    misses = embed.cache_misses if embed is not None else 0
    print(f"  vectors     {_counter(embed, 'vectors'):>6}  (cache: {hits} hits, {misses} misses)")
    print(f"  candidates  {_counter(candidates, 'pairs'):>6} pairs")
    print(f"  proposals   {len(result.proposals.proposals):>6}")
    print(
        f"  device      {device:>6}  fallbacks: " + ("; ".join(fallbacks) if fallbacks else "none")
    )
    print()
    top = sorted(result.proposals.proposals, key=lambda p: (p.rank, p.id))[:_TOP_PROPOSALS]
    if top:
        print(f"Top {len(top)} proposals:")
        for proposal in top:
            arrow = _DIRECTION_ARROWS[proposal.direction]
            print(
                f"  {proposal.rank:>3}. {proposal.score:.4f}  "
                f"{proposal.source_document_id} {arrow} {proposal.target_document_id}  "
                f"[{proposal.confidence.value}]"
            )
    else:
        print("No proposals were generated (a successful empty result).")
    print()
    names = ", ".join(ref.key for ref in result.report.outputs)
    print(f"Reports written to {result.report_dir}: {names}")
    print(f"Artifacts stored under {result.artifacts_root}")


def _cmd_run(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery run``."""
    config = load_config(args.config)
    result = Pipeline().run(
        config,
        artifacts_root=args.artifacts,
        reviews_path=args.reviews,
        run_id=args.run_id,
    )
    _print_run_summary(result)
    return 0


# ---------------------------------------------------------------- evaluate


def _cmd_evaluate(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery evaluate``."""
    config = load_config(args.config)
    metrics = Pipeline().evaluate_holdout(
        config,
        artifacts_root=args.artifacts,
        holdout_fraction=args.holdout_fraction,
        seed=args.seed,
        k_values=args.k,
    )
    print(
        f"Held-out link recovery (fraction={args.holdout_fraction}, seed={args.seed}, "
        f"run {metrics['run_id']})"
    )
    print()
    rows: list[tuple[str, str]] = [
        ("visible links", f"{metrics['visible_count']}"),
        ("held-out links", f"{metrics['holdout_count']:.0f}"),
        ("recovered (any rank)", f"{metrics['recovered_count']:.0f}"),
        ("proposals", f"{metrics['proposal_count']}"),
        ("mrr", f"{metrics['mrr']:.4f}"),
    ]
    rows.extend((f"recall@{k}", f"{metrics[f'recall_at_{k}']:.4f}") for k in args.k)
    width = max(len(name) for name, _ in rows)
    for name, value in rows:
        print(f"  {name:<{width}}  {value}")
    print()
    print("Recovery by visible source out-degree (recall@10):")
    by_degree: dict[str, dict[str, float]] = metrics["recovery_by_degree"]
    print(f"  {'bucket':<8}{'held-out':>10}{'recovered':>11}{'recall':>9}")
    for bucket, values in by_degree.items():
        print(
            f"  {bucket:<8}{values['holdout_count']:>10.0f}"
            f"{values['recovered_count']:>11.0f}{values['recall_at_k']:>9.2f}"
        )
    return 0


# ------------------------------------------------------------ review-queue


def _read_proposals_jsonl(path: Path) -> tuple[LinkProposal, ...]:
    """Read a ``proposals.jsonl`` file back into contract objects.

    Raises :class:`~linkdiscovery.errors.ContractError` naming the line when
    a line is not valid JSON or violates the proposal contract; ``OSError``
    propagates for unreadable files (both are handled by :func:`main`).
    """
    proposals: list[LinkProposal] = []
    text = path.read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except ValueError as exc:
            raise ContractError(f"{path}:{number}: not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ContractError(f"{path}:{number}: expected a JSON object per line")
        proposals.append(LinkProposal.from_dict(data))
    return tuple(proposals)


def _cmd_review_queue(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery review-queue``."""
    proposals = _read_proposals_jsonl(args.proposals)
    proposal_set = ProposalSet(
        header=ArtifactHeader(
            schema_version=PROPOSALS_SCHEMA_VERSION,
            run_id="review-queue",
            corpus_id="",
            created_at=utc_now_iso(),
            config_fingerprint="",
            producer_version=PRODUCER_VERSION,
        ),
        proposals=proposals,
    )
    queue = build_review_queue(proposal_set, size=args.size, seed=args.seed)
    lines = [canonical_json(proposal.to_dict()) for proposal in queue]
    if args.out is not None:
        out: Path = args.out
        content = "\n".join(lines) + ("\n" if lines else "")
        # Atomic like every other artifact write: a crashed queue write must
        # not leave a partial file that looks complete.
        atomic_write_text(out, content)
        print(f"Wrote {len(queue)} of {len(proposals)} proposals to {out}")
    else:
        for line in lines:
            print(line)
    return 0


def _cmd_export_embeddings(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery export-embeddings``."""
    result = export_experiment_embeddings(args.artifacts, args.run_id, args.out)
    print(f"Wrote experiment embedding bundle to {result['output']}")
    print(
        f"  documents  {result['documents']}  matrix {tuple(result['document_shape'])}; "
        f"units  {result['units']}  matrix {tuple(result['unit_shape'])}"
    )
    return 0


# ------------------------------------------------------------------- inline


def _print_rows(rows: list[tuple[str, str]]) -> None:
    """Print aligned ``name  value`` rows (the house summary style)."""
    width = max(len(name) for name, _ in rows)
    for name, value in rows:
        print(f"  {name:<{width}}  {value}")


def _inline_inputs(args: argparse.Namespace) -> workflow.InlineInputs:
    """Load the shared v1-stage inputs for an inline subcommand."""
    config = load_config(args.config)
    return workflow.load_inline_inputs(config, artifacts_root=args.artifacts)


def _token_encoder_setup(
    args: argparse.Namespace, inputs: workflow.InlineInputs
) -> tuple[Callable[[], TokenStateEncoder] | None, ArtifactCache | None]:
    """Resolve ``--token-encoder`` into an encoder factory and a state cache.

    ``hashing`` returns ``(None, None)`` so the workflow keeps its
    dependency-free default. ``qwen`` builds the windowed Qwen encoder from
    the config's pinned model/revision on the best qualified device (mps
    first, cpu fallback — the choice is printed because it is not part of
    the fingerprint) and wires the artifact store's cache group so expensive
    token states persist across runs.
    """
    if args.token_encoder != "qwen":
        return None, None
    encoder, device = workflow.build_qwen_token_encoder(inputs.config)
    print(f"token encoder: windowed qwen on {device}")
    cache = ArtifactCache(ArtifactStore(Path(args.artifacts)))
    return (lambda: encoder), cache


def _cmd_inline_audit_sample(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery inline audit-sample``."""
    inputs = _inline_inputs(args)
    sample = workflow.build_audit_artifacts(
        inputs, size=args.size, seed=args.seed, out_dir=args.out
    )
    print(f"Audit sample written to {args.out}")
    print()
    _print_rows(
        [
            ("items", str(len(sample.items))),
            ("strata", str(len(sample.strata_counts))),
            ("requested size", str(args.size)),
            ("seed", str(args.seed)),
            ("files", "audit-sample.json, audit-sample.md"),
        ]
    )
    return 0


def _cmd_inline_annotate(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery inline annotate`` (interactive)."""
    sample = workflow.load_audit_sample(args.sample)
    run_annotation_session(sample, annotator=args.annotator, labels_path=args.labels)
    return 0


def _cmd_inline_audit_report(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery inline audit-report``."""
    sample = workflow.load_audit_sample(args.sample)
    label_paths = [*args.labels, *args.labels2]
    labels: list[AuditLabel] = []
    for path in label_paths:
        if not Path(path).exists():
            raise ContractError(f"labels file {path} does not exist")
        labels.extend(load_audit_labels(path))
    report = build_audit_report(sample, labels)
    print(f"Audit report over {report.n_labeled} labeled of {report.n_items} sampled item(s)")
    print()
    print("Tier distribution (consensus per item):")
    _print_rows(
        [(f"tier {tier.upper()}", str(count)) for tier, count in sorted(report.tier_counts.items())]
    )
    print()
    if report.agreement:
        print("Agreement (Cohen's kappa / Krippendorff's alpha per field):")
        _print_rows([(name, f"{value:.3f}") for name, value in sorted(report.agreement.items())])
    else:
        print("Agreement: unavailable (no item labeled by two or more annotators)")
    print()
    clean = report.tier_counts.get("a", 0) + report.tier_counts.get("b", 0)
    verdict = "GO" if report.go else "NO-GO"
    print(
        f"Verdict: {verdict}  (thresholds: every kappa >= 0.6 and "
        f"Tier A+B positives >= 150; observed clean positives: {clean})"
    )
    for note in report.notes:
        print(f"  note: {note}")
    return 0


def _cmd_inline_anchors(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery inline anchors``."""
    inputs = _inline_inputs(args)
    dictionary = workflow.build_anchor_artifacts(inputs, config=AnchorConfig(), out_dir=args.out)
    mentions = dictionary.mentions()
    eligible = sum(1 for mention in mentions if dictionary.eligible(mention))
    print(f"Anchor dictionary written to {args.out}")
    print()
    _print_rows(
        [
            ("mentions", str(len(mentions))),
            ("eligible", str(eligible)),
            ("keyphraseness floor", f"{dictionary.config.keyphraseness_floor:.3f}"),
            ("files", "anchor-dictionary.json, anchor-stats.json"),
        ]
    )
    return 0


def _cmd_inline_recall_check(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery inline recall-check``."""
    inputs = _inline_inputs(args)
    sample = workflow.load_audit_sample(args.sample)
    metrics = workflow.check_span_recall(
        inputs, sample, anchor_config=AnchorConfig(), span_config=SpanConfig()
    )
    gate = 0.85
    verdict = "PASS" if metrics["overlap_recall"] >= gate else "FAIL"
    print("Span-generator recall over audited prose anchors (spec §11 phase 2)")
    print()
    _print_rows(
        [
            ("prose items", f"{metrics['n_prose_items']:.0f}"),
            ("exact recall", f"{metrics['exact_recall']:.3f}"),
            ("overlap recall", f"{metrics['overlap_recall']:.3f}"),
            ("gate (>= 0.85)", verdict),
        ]
    )
    if verdict == "FAIL":
        print()
        print("Recall below the §12 ceiling: fix span generation before any modeling.")
    return 0


def _cmd_inline_train(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery inline train``."""
    inputs = _inline_inputs(args)
    encoder_factory, token_state_cache = _token_encoder_setup(args, inputs)
    train_config = TrainConfig(epochs=args.epochs)
    heads = workflow.train_inline_heads(
        inputs,
        args.labels,
        args.sample,
        train_config=train_config,
        seed=args.seed,
        out_dir=args.out,
        encoder_factory=encoder_factory,
        token_state_cache=token_state_cache,
    )
    print(f"Trained heads saved to {args.out}")
    print()
    rows: list[tuple[str, str]] = [
        ("epochs", str(args.epochs)),
        ("seed", str(args.seed)),
        ("token encoder", args.token_encoder),
        ("encoder", heads.encoder_fingerprint[:24] + "..."),
        ("model version", heads.model_version[:24] + "..."),
    ]
    for head, losses in sorted(heads.loss_history.items()):
        rows.append((f"{head} final loss", f"{losses[-1]:.4f}" if losses else "n/a (no data)"))
    _print_rows(rows)
    return 0


def _selection_config(args: argparse.Namespace) -> SelectionConfig:
    """Selection defaults with the CLI overrides applied."""
    defaults = SelectionConfig()
    return SelectionConfig(
        accept_threshold=(
            args.threshold if args.threshold is not None else defaults.accept_threshold
        ),
        words_per_link=(
            args.budget_words if args.budget_words is not None else defaults.words_per_link
        ),
        max_links_per_note=(
            args.max_per_note if args.max_per_note is not None else defaults.max_links_per_note
        ),
    )


def _cmd_inline_propose(args: argparse.Namespace) -> int:
    """Handle ``linkdiscovery inline propose``."""
    inputs = _inline_inputs(args)
    selection = _selection_config(args)
    run_id = f"inline-{args.engine}"
    if args.engine == "learned":
        if args.heads is None:
            raise ConfigError("inline propose: --heads is required with --engine learned")
        heads = TrainedHeads.load(args.heads)
        encoder_factory, token_state_cache = _token_encoder_setup(args, inputs)
        proposals = workflow.propose_inline_learned(
            inputs,
            heads,
            anchor_config=AnchorConfig(),
            span_config=SpanConfig(),
            selection_config=selection,
            run_id=run_id,
            encoder_factory=encoder_factory,
            token_state_cache=token_state_cache,
        )
    else:
        proposals = workflow.propose_inline_baseline(
            inputs,
            anchor_config=AnchorConfig(),
            span_config=SpanConfig(),
            baseline_config=BaselineConfig(),
            selection_config=selection,
            run_id=run_id,
        )
    paths = write_inline_report(proposals, inputs.corpus, out_dir=args.out)
    accepted = [p for p in proposals.proposals if not p.abstained]
    flagged = sum(1 for p in accepted if p.features.get("suggest_better_anchor", 0.0))
    print(f"Inline proposals ({args.engine} engine) written to {args.out}")
    print()
    _print_rows(
        [
            ("accepted", str(len(accepted))),
            ("abstained", str(len(proposals.proposals) - len(accepted))),
            ("anchor-improvement flags", str(flagged)),
            ("source notes", str(len({p.source_document_id for p in accepted}))),
            ("accept threshold", f"{selection.accept_threshold:.2f}"),
            ("files", ", ".join(path.name for path in paths)),
        ]
    )
    top = accepted[:5]
    if top:
        print()
        print(f"Top {len(top)} accepted proposals:")
        for proposal in top:
            print(
                f"  {proposal.combined_score:.3f}  {proposal.source_document_id}"
                f" [{proposal.anchor_text!r}] -> {proposal.target_document_id}"
            )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
