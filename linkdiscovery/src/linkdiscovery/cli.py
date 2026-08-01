"""Command-line interface for the missing-link discovery pipeline.

Standard-library ``argparse`` only. Three subcommands:

- ``run`` — execute a full batch run from a YAML configuration and print a
  human summary (counts, device, cache reuse, top proposals, report paths).
- ``evaluate`` — hide a stratified fraction of existing links, rerun
  discovery, and print held-out recovery metrics.
- ``review-queue`` — build the stratified human review queue from a
  ``proposals.jsonl`` file.

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
from linkdiscovery.config import load_config
from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.proposals import (
    SCHEMA_VERSION as PROPOSALS_SCHEMA_VERSION,
)
from linkdiscovery.contracts.proposals import (
    LinkProposal,
    ProposalSet,
)
from linkdiscovery.errors import ContractError, LinkDiscoveryError
from linkdiscovery.fingerprint import canonical_json
from linkdiscovery.pipeline import PRODUCER_VERSION, Pipeline, RunResult
from linkdiscovery.report import build_review_queue
from linkdiscovery.report._io import atomic_write_text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from linkdiscovery.contracts.manifests import RunManifest, StageStats

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
    return parser


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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
