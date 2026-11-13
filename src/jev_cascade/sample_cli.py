"""Ticket 08's command: ask a small sample three ways, then with and without the heading.

    jev-cascade-sample --jev real          # needs JEV_API_KEY; at most 1,680 calls (1,357 on the real run)
    jev-cascade-sample --jev real --from-cache   # rebuild the report with no key and no calls

The plan (Pairs per arm, the total, the decision rules) is printed before the first call, so the
spend is visible. The command never writes the pipeline's configuration: it reports its choices and
`config.py` is edited by hand from the report.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from . import config
from .clients import KINDS, build_client, default_workers
from .corpus import load_corpus
from .jev import JevCallRefused, JevClient
from .rulebook import RULEBOOK
from .runner import read_cache
from .sample_report import StudyInputs, render_study
from .sample_study import (
    HELD_PER_RULE,
    MARGIN,
    NOT_HELD_PER_RULE,
    DEFAULT_TYPE,
    QUESTION_TYPES,
    Arm,
    bootstrap_difference,
    choose_heading,
    choose_type,
    draw_sample,
    run_arm,
)
from .splitter import split_document
from .typesafe import JevError

DEFAULT_REPORT = Path("docs/question-type-and-heading-sample.md")
DEFAULT_OUT = Path(config.DEFAULT_OUT_DIR) / "sample"


def run_study(
    client: JevClient,
    out_dir: Path,
    held: int = HELD_PER_RULE,
    not_held: int = NOT_HELD_PER_RULE,
    workers: int = 1,
    announce: Callable[[str], None] = lambda text: None,
    cuad_directory: Path | None = None,
) -> StudyInputs:
    """Draw the sample, ask the four arms, make both choices, and return everything the report needs."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / "pyes.jsonl"

    documents = load_corpus(rules=RULEBOOK, directory=cuad_directory)
    clauses = [c for d in documents for c in split_document(d.doc_id, d.text)]
    highlights = {r.id: [h for d in documents for h in d.highlights if h.rule_id == r.id] for r in RULEBOOK}
    sample = draw_sample(clauses, highlights, RULEBOOK, held=held, not_held=not_held)

    announce(
        f"Pairs per arm: {sample.pairs} ({', '.join(f'{k} {len(v)}' for k, v in sample.by_rule.items())})."
    )
    announce(
        f"Arms: {', '.join(QUESTION_TYPES)} with the heading shown, then the chosen type with it "
        f"taken out: at most {sample.pairs * 4} calls, fewer where a prompt is identical or cached."
    )
    announce(
        f"Rule fixed in advance: highest mean separation wins; a type must beat binary by "
        f"{MARGIN:.2f}, and the heading comes out only if that gains {MARGIN:.2f}."
    )

    type_results = []
    for question_type in QUESTION_TYPES:
        result = run_arm(Arm(question_type, True), sample, highlights, client, cache, workers)
        type_results.append(result)
        announce(f"  {result.arm.label}: mean separation {result.mean_separation:.3f}")

    chosen = choose_type(type_results)
    chosen_result = next(r for r in type_results if r.arm.question_type == chosen.question_type)
    heading_off = run_arm(Arm(chosen.question_type, False), sample, highlights, client, cache, workers)
    announce(f"  {heading_off.arm.label}: mean separation {heading_off.mean_separation:.3f}")

    base = next(r for r in type_results if r.arm.question_type == DEFAULT_TYPE)
    return StudyInputs(
        sample=sample,
        type_results=type_results,
        chosen_type=chosen.question_type,
        heading_off=heading_off,
        heading_context=choose_heading(chosen_result, heading_off),
        type_differences={
            r.arm.question_type: bootstrap_difference(base, r, sample, highlights)
            for r in type_results
            if r.arm.question_type != DEFAULT_TYPE
        },
        heading_difference=bootstrap_difference(chosen_result, heading_off, sample, highlights),
        model_version=client.model_version,
        is_stub=client.is_stub,
        documents=len(documents),
        parent_lines=_parent_line_kinds(clauses),
        answers=len(read_cache(cache)),
    )


def _parent_line_kinds(clauses) -> dict[str, int]:
    """How many Parent Lines are a standalone heading, introduce a list, or are something longer."""
    with_parent = [c for c in clauses if c.parent_line]
    heading = sum(1 for c in with_parent if c.parent_is_heading)
    list_intro = sum(
        1 for c in with_parent if not c.parent_is_heading and c.parent_line.rstrip().endswith(":")
    )
    return {
        "clauses": len(clauses),
        "with_parent": len(with_parent),
        "heading": heading,
        "list_intro": list_intro,
        "other": len(with_parent) - heading - list_intro,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jev-cascade-sample",
        description="Ticket 08: compare Jev's three question types and heading context on a sample.",
    )
    parser.add_argument("--jev", choices=KINDS, default="stub", help="Which Jev to ask. Default stub.")
    parser.add_argument("--workers", type=int, default=None, metavar="N", help="Calls in flight.")
    parser.add_argument("--seed", type=int, default=0, help="Seed for the stub (ignored by real).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"The sample's own cache. Default {DEFAULT_OUT}.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help=f"Where the report goes. Default {DEFAULT_REPORT}.")
    parser.add_argument("--held", type=int, default=HELD_PER_RULE, help="Held Clauses per Rule.")
    parser.add_argument("--not-held", type=int, default=NOT_HELD_PER_RULE, help="Not-held Clauses per Rule.")
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Rebuild the report from the cache alone: Jev is never asked and no key is needed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not config.cuad_is_available():
        parser.error(f"CUAD v1 not found at {config.cuad_dir()}; set CUAD_DIR.")
    workers = args.workers if args.workers is not None else default_workers(args.jev)
    if workers < 1:
        parser.error("--workers must be at least 1")

    try:
        client = build_client(args.jev, seed=args.seed, from_cache=args.from_cache)
    except JevError as error:
        parser.error(str(error))

    try:
        inputs = run_study(client, args.out, args.held, args.not_held, workers, announce=print)
    except JevCallRefused:
        parser.error(f"--from-cache: the cache in {args.out} does not hold every Pair. Run without it once.")
    except JevError as error:
        parser.error(f"Jev failed: {error}. Answers received are cached; run the same command to resume.")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_study(inputs), encoding="utf-8")
    print(f"Wrote {args.report}")
    print(f"Chosen: {inputs.chosen_type}, heading {'on' if inputs.heading_context else 'off'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
