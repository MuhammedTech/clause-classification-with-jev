"""The Jev runner: asks every (Clause, Rule) Pair once and caches every P(yes).

The cache is a JSONL file. A row's key identifies **everything the client was shown and asked**:

- the document and the Clause span, which is what the Evaluator grades on and keeps a row readable;
- the Rule, the question type and the model version;
- a **prompt fingerprint**, a hash of the Parent Line and the Clause text.

The Parent Line has to be in the key because Jev is shown Parent Line plus Clause text, and the
Parent Line is a function of how the document is cut, not of the span. Two prompts that differ only
in their Parent Line share a span, so without the fingerprint the second would be served the first's
P(yes) silently, and a real client is billed per call (ticket 10). The Clause text is implied by the
document and the span, but it is hashed too, so a re-extracted `context` or a different whitespace
normalisation cannot quietly reuse answers either.

A row written before the fingerprint existed has none, and is a **miss**: the Pair is asked again
rather than guessed at.

Answers are appended and flushed per call, so a run interrupted midway keeps everything it had
already learned and the next run asks only the Pairs still missing.

The question wording is stored on each row but is deliberately not part of the key. Ticket 08
reviews the wording; storing it is what makes a cache written under older wording detectable then.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .domain import Clause
from .jev import JevClient
from .rulebook import QUESTION_TYPE, Rule

#: A cached answer is identified by document, Clause span, Rule, question type, model version and
#: the fingerprint of what Jev was shown. See the module docstring.
PairKey = tuple[str, int, int, str, str, str, str]

#: P(yes) by Rule id, then by Clause key (document plus span).
PYesTable = dict[str, dict[tuple[str, str], float]]


@dataclass(frozen=True)
class RunStats:
    """What one run of the runner cost. Wall clock is recorded as the spec requires."""

    pairs: int
    calls_made: int
    cache_hits: int
    seconds: float


def prompt_fingerprint(parent_line: str, clause_text: str) -> str:
    """A hash of the two pieces of text Jev is shown, Parent Line first.

    Joined with a unit separator so text cannot shift across the boundary: `("ab", "c")` and
    `("a", "bc")` are different prompts.
    """
    payload = "\x1f".join([parent_line, clause_text])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _key(clause: Clause, rule: Rule, model_version: str) -> PairKey:
    return (
        clause.doc_id,
        clause.start,
        clause.end,
        rule.id,
        QUESTION_TYPE,
        model_version,
        prompt_fingerprint(clause.parent_line, clause.text),
    )


def read_cache(path: Path) -> dict[PairKey, float]:
    """Load every answer already on disk.

    A truncated or malformed final line is skipped rather than fatal: an interruption can leave one
    half-written. A row with no `prompt_fingerprint` is skipped too, so it is a miss (ticket 10).
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
                    row["prompt_fingerprint"],
                )
                answers[key] = float(row["p_yes"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                # A half-written line, or one written before the fingerprint existed. Either way
                # the Pair is simply asked again.
                continue
    return answers


def _close_dangling_line(path: Path) -> None:
    """Terminate a half-written final line before appending to it.

    A run killed mid-write leaves a line with no newline. Appending straight onto it would glue
    the next answer to the fragment, making that row unparseable too, so the Pair would be asked
    again on every later run.
    """
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb") as handle:
        handle.seek(-1, 2)
        if handle.read(1) == b"\n":
            return
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")


def run_pairs(
    clauses: Sequence[Clause],
    rules: Iterable[Rule],
    client: JevClient,
    cache_path: Path,
) -> tuple[PYesTable, RunStats]:
    """Ask Jev about every (Clause, Rule) Pair, skipping any already in the cache.

    Returns the P(yes) table — keyed by Rule id, then by (document, Clause span) — and the run's
    counts and wall clock.
    """
    rules = list(rules)
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cached = read_cache(cache_path)
    model_version = client.model_version
    _close_dangling_line(cache_path)

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
                    table[rule.id][clause.key] = cached[key]
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
                            "prompt_fingerprint": key[-1],
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
                table[rule.id][clause.key] = p_yes

    stats = RunStats(
        pairs=len(clauses) * len(rules),
        calls_made=calls_made,
        cache_hits=cache_hits,
        seconds=time.monotonic() - started,
    )
    return table, stats
