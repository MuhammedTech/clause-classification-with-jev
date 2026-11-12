"""The command. Thin wrapper over `pipeline.run`."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config
from .clients import KINDS, build_client
from .jev import JevCallRefused
from .pipeline import DEFAULT_CUTOFF, DEFAULT_RULE_IDS, TRACER_DOC_IDS, run
from .typesafe import JevError


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
        help="Rule to ask. Repeatable. Defaults to {}.".format(", ".join(DEFAULT_RULE_IDS)),
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
        "--jev",
        choices=KINDS,
        default="stub",
        help=(
            "Which Jev to ask: the signal-free stub (default) or the real TypeSafe client, which "
            "reads its key from JEV_API_KEY in the environment."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Seed for the stub Jev client (ignored by --jev real). Default 0.",
    )
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help=(
            "Rebuild the report from the P(yes) cache alone. Jev is never asked: a Pair missing "
            "from the cache is an error, not a call."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not config.cuad_is_available():
        parser.error(
            f"CUAD v1 not found at {config.cuad_dir()}. The dataset is not in this repo; set "
            "CUAD_DIR to where CUAD_v1.json and master_clauses.csv live."
        )

    try:
        client = build_client(args.jev, seed=args.seed, from_cache=args.from_cache)
    except JevError as error:
        parser.error(str(error))

    try:
        result = run(
            client=client,
            doc_ids=tuple(args.doc_ids) if args.doc_ids else TRACER_DOC_IDS,
            rule_ids=tuple(args.rule_ids) if args.rule_ids else DEFAULT_RULE_IDS,
            cutoff=args.cutoff,
            out_dir=args.out,
        )
    except JevCallRefused:
        parser.error(
            f"--from-cache: the cache in {args.out} does not hold every Pair this run needs. "
            "Run once without --from-cache to fill it."
        )
    except JevError as error:
        parser.error(
            f"Jev failed: {error}. Answers already received are in the cache, so running the "
            "same command again resumes."
        )

    print(f"Wrote {result.report_path}")
    print(
        f"{result.stats.pairs} Pairs: {result.stats.calls_made} Jev calls, "
        f"{result.stats.cache_hits} from cache, {result.stats.seconds:.2f}s"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
