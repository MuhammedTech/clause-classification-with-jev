"""The Jev runner: asks every (Clause, Rule) Pair once and caches every P(yes).

The cache is a JSONL file keyed by document, Clause, Rule, question type and model version. Answers
are appended and flushed per call, so a run interrupted midway keeps everything it had already
learned and the next run asks only the Pairs still missing.

The question wording is stored on each row but is deliberately not part of the key, which is the
key the spec fixes. Ticket 08 reviews the wording; storing it is what makes a cache written under
older wording detectable then.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .domain import Clause
from .evaluator import ClauseKey
from .jev import JevClient
from .rulebook import QUESTION_TYPE, Rule

#: A cached answer is identified by document, Clause span, Rule, question type and model version.
PairKey = tuple[str, int, int, str, str, str]

PYesTable = dict[str, dict[ClauseKey, float]]


@dataclass(frozen=True)
class RunStats:
    """What one run of the runner cost. Wall clock is recorded as the spec requires."""

    pairs: int
    calls_made: int
    cache_hits: int
    seconds: float


def _key(clause: Clause, rule: Rule, model_version: str) -> PairKey:
    return (
        clause.doc_id,
        clause.start,
        clause.end,
        rule.id,
        QUESTION_TYPE,
        model_version,
    )


def read_cache(path: Path) -> dict[PairKey, float]:
    """Load every answer already on disk.

    A truncated or malformed final line is skipped rather than fatal: an interruption can leave one
    half-written.
    """
    answers: dict[PairKey, float] = {}
    if not Path(path).exists():
        return answers

    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                key: PairKey = (
                    row["doc_id"],
                    row["clause_start"],
                    row["clause_end"],
                    row["rule_id"],
                    row["question_type"],
                    row["model_version"],
                )
                answers[key] = float(row["p_yes"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                # A half-written line from an interrupted run. The Pair is simply asked again.
                continue
    return answers


def run_pairs(
    clauses: Sequence[Clause],
    rules: Iterable[Rule],
    client: JevClient,
    cache_path: Path,
    with_stats: bool = False,
):
    """Ask Jev about every (Clause, Rule) Pair, skipping any already in the cache.

    Returns the P(yes) table, keyed by Rule id and then by (document, Clause span). With
    `with_stats` it returns `(table, RunStats)`.
    """
    rules = list(rules)
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cached = read_cache(cache_path)
    model_version = client.model_version

    table: PYesTable = {rule.id: {} for rule in rules}
    calls_made = 0
    cache_hits = 0
    started = time.monotonic()

    with cache_path.open("a", encoding="utf-8") as handle:
        for clause in clauses:
            for rule in rules:
                key = _key(clause, rule, model_version)
                if key in cached:
                    cache_hits += 1
                    table[rule.id][(clause.doc_id, clause.span_key)] = cached[key]
                    continue

                p_yes = client.p_yes(
                    clause_text=clause.text,
                    parent_line=clause.parent_line,
                    question=rule.detection_question,
                    question_type=QUESTION_TYPE,
                )
                calls_made += 1

                handle.write(
                    json.dumps(
                        {
                            "doc_id": clause.doc_id,
                            "clause_start": clause.start,
                            "clause_end": clause.end,
                            "rule_id": rule.id,
                            "question_type": QUESTION_TYPE,
                            "model_version": model_version,
                            "question": rule.detection_question,
                            "p_yes": p_yes,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                # Flushed per call so an interruption loses at most the Pair in flight.
                handle.flush()

                cached[key] = p_yes
                table[rule.id][(clause.doc_id, clause.span_key)] = p_yes

    stats = RunStats(
        pairs=len(clauses) * len(rules),
        calls_made=calls_made,
        cache_hits=cache_hits,
        seconds=time.monotonic() - started,
    )
    return (table, stats) if with_stats else table
