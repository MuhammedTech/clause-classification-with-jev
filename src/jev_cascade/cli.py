"""The command. Thin wrapper over `pipeline.run`."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config
from .jev import StubJevClient
from .pipeline import DEFAULT_CUTOFF, TRACER_DOC_IDS, run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jev-cascade",
        description=(
            "Tracer bullet: takes a few CUAD license agreements through every stage of the Jev "
            "cascade on the stub client and writes a Markdown report."
        ),
    )
    parser.add_argument(
        "--rule",
        action="append",
        dest="rule_ids",
        metavar="R1",
        help="Rule to ask. Repeatable. Defaults to R1.",
    )
    parser.add_argument(
        "--doc",
        action="append",
        dest="doc_ids",
        metavar="TITLE",
        help="Document to run, by JSON title. Repeatable. Defaults to the three tracer documents.",
    )
    parser.add_argument(
        "--cutoff",
        type=float,
        default=DEFAULT_CUTOFF,
        help=f"The single Cutoff to report at. A Pair at or below it is Binned. Default {DEFAULT_CUTOFF}.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(config.DEFAULT_OUT_DIR),
        help=f"Where the cache and report go. Default {config.DEFAULT_OUT_DIR}/.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Seed for the stub Jev client. Default 0.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not config.cuad_is_available():
        parser = build_parser()
        parser.error(
            f"CUAD v1 not found at {config.cuad_dir()}. The dataset is not in this repo; set "
            "CUAD_DIR to where CUAD_v1.json and master_clauses.csv live."
        )

    result = run(
        client=StubJevClient(seed=args.seed),
        doc_ids=tuple(args.doc_ids) if args.doc_ids else TRACER_DOC_IDS,
        rule_ids=tuple(args.rule_ids) if args.rule_ids else ("R1",),
        cutoff=args.cutoff,
        out_dir=args.out,
    )

    print(f"Wrote {result.report_path}")
    print(
        f"{result.stats.pairs} Pairs: {result.stats.calls_made} Jev calls, "
        f"{result.stats.cache_hits} from cache, {result.stats.seconds:.2f}s"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
