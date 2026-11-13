"""The command. Thin wrapper over `pipeline.run`."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config
from .clients import KINDS, build_client, default_workers
from .jev import JevCallRefused
from .rulebook import RULEBOOK
from .pipeline import DEFAULT_CUTOFF, DEFAULT_RULE_IDS, TRACER_DOC_IDS, run
from .typesafe import JevError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jev-cascade",
        description=(
            "Takes CUAD license agreements through every stage of the Jev cascade and writes a "
            "Markdown report. By default it runs three tracer documents on one Rule with the "
            "stub; --full --jev real is the real run."
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
        "--full",
        action="store_true",
        help=(
            "The whole run: all 53 documents against every Rule in the Rulebook. Cannot be "
            "combined with --doc or --rule."
        ),
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
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Jev calls in flight at once. Changes the speed of a run, never its answers. Default "
            f"{default_workers('real')} for --jev real and 1 for the stub."
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


def _print_retries(client) -> None:
    """Say how many calls were retried and why, if the client keeps count.

    A 429 here would mean the request limit is lower than the 1,200 a minute assumed, and the count
    matters most when a run could not finish, so it is printed on the failure path too.
    """
    retries = getattr(getattr(client, "inner", client), "retries", None)
    if retries:
        causes = ", ".join(f"{count} x {cause}" for cause, count in sorted(retries.items()))
        print(f"Retries: {causes}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not config.cuad_is_available():
        parser.error(
            f"CUAD v1 not found at {config.cuad_dir()}. The dataset is not in this repo; set "
            "CUAD_DIR to where CUAD_v1.json and master_clauses.csv live."
        )

    if args.full and (args.doc_ids or args.rule_ids):
        parser.error("--full runs every document and every Rule; drop --doc and --rule")

    workers = args.workers if args.workers is not None else default_workers(args.jev)
    if workers < 1:
        parser.error("--workers must be at least 1")

    try:
        client = build_client(args.jev, seed=args.seed, from_cache=args.from_cache)
    except JevError as error:
        parser.error(str(error))

    try:
        result = run(
            client=client,
            doc_ids=None if args.full else tuple(args.doc_ids) if args.doc_ids else TRACER_DOC_IDS,
            rule_ids=(
                tuple(r.id for r in RULEBOOK)
                if args.full
                else tuple(args.rule_ids) if args.rule_ids else DEFAULT_RULE_IDS
            ),
            cutoff=args.cutoff,
            out_dir=args.out,
            workers=workers,
        )
    except JevCallRefused:
        parser.error(
            f"--from-cache: the cache in {args.out} does not hold every Pair this run needs. "
            "Run once without --from-cache to fill it."
        )
    except JevError as error:
        _print_retries(client)
        parser.error(
            f"Jev failed: {error}. Answers already received are in the cache, so running the "
            "same command again resumes."
        )

    print(f"Wrote {result.report_path}")
    print(
        f"{result.stats.pairs} Pairs: {result.stats.calls_made} Jev calls, "
        f"{result.stats.cache_hits} from cache, {result.stats.seconds:.2f}s"
    )
    _print_retries(client)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
