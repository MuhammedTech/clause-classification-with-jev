"""The Operating Point command: choose a Cutoff on one half of the documents, report it on the other.

    jev-cascade-operating-point --out out/real      # reads the stored answers; never asks Jev

Needs the real run's cache (`out/real/pyes.jsonl`). It rebuilds `out/real/report.md` from that cache
as a side effect, exactly as `jev-cascade --jev real --full --out out/real --from-cache` does, and
writes `docs/operating-point.md`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config
from .clients import build_client
from .jev import JevCallRefused
from .operating_point import BUDGETS, study
from .operating_point_report import OperatingPointInputs, render_operating_point
from .pipeline import run
from .rulebook import RULEBOOK

DEFAULT_REPORT = Path("docs/operating-point.md")
FIXED_CUTOFF = 0.5


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jev-cascade-operating-point",
        description="Choose a Cutoff for a stated loss on one half of the documents and report it on the other.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(config.DEFAULT_OUT_DIR) / "real",
        help="The real run's output directory, holding pyes.jsonl. Default %(default)s.",
    )
    parser.add_argument(
        "--report", type=Path, default=DEFAULT_REPORT, help="Where to write. Default %(default)s."
    )
    args = parser.parse_args(argv)

    if not (args.out / "pyes.jsonl").exists():
        parser.error(f"{args.out / 'pyes.jsonl'} not found: run the real run first")

    client = build_client("real", seed=0, from_cache=True)
    try:
        result = run(
            client=client,
            doc_ids=None,
            rule_ids=tuple(r.id for r in RULEBOOK),
            out_dir=args.out,
            cutoff=FIXED_CUTOFF,
        )
    except JevCallRefused:
        parser.error("the cache is missing answers for this run; it cannot be read without asking Jev")

    questions = {r.id: r.detection_question for r in RULEBOOK}
    highlights = list(result.highlights)
    studies = [
        study(result.clauses, highlights, result.p_yes, questions, budget) for budget in BUDGETS
    ]

    inputs = OperatingPointInputs(
        studies=studies,
        documents=len({c.doc_id for c in result.clauses}),
        clauses=len(result.clauses),
        provisions=len(highlights),
        model_version=client.model_version,
        fixed_skipped_share=result.fully_binned.clause_share or 0.0,
        fixed_lost=sum(m.lost_provisions for m in result.metrics),
        fixed_provisions=sum(m.highlights for m in result.metrics),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_operating_point(inputs), encoding="utf-8")
    print(f"wrote {args.report}")
    for s in studies:
        print(
            f"budget {s.budget_share:.0%}: skipped {s.skipped_share:.1%}, lost {s.lost}/{s.provisions} "
            f"({s.lost_share:.1%}), cutoffs {[d.cutoff for d in s.directions]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
