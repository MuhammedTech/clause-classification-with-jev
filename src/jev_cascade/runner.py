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
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from . import config
from .domain import Clause
from .jev import JevClient, ask_many
from .rulebook import Rule

#: A cached answer is identified by document, Clause span, Rule, question type, model version and
#: the fingerprint of what Jev was shown. See the module docstring.
PairKey = tuple[str, int, int, str, str, str, str]

#: P(yes) by Rule id, then by Clause key (document plus span).
PYesTable = dict[str, dict[tuple[str, str], float]]


#: A gap between two consecutive answers longer than this is a pause (a resumed run, a closed
#: laptop), not Jev's time. With 32 calls in flight answers arrive many a second, so a minute is far
#: beyond anything a running call sequence produces.
PAUSE_SECONDS = 60.0


@dataclass(frozen=True)
class AnswerTiming:
    """When the answers behind a table arrived, read from the cache's per-row timestamps.

    This is the **original** run's timing, recoverable on a `--from-cache` rebuild, which makes no
    calls and so times only a file read. `active_seconds` leaves out the pauses (gaps over
    `PAUSE_SECONDS`) between sessions of a resumed run; `longest_pause_seconds` is the longest gap
    of any size, so a report can say when a run was resumed.
    """

    #: Calls, not rows: the rows of one call share a timestamp, and a call is one Clause.
    answers: int
    first_at: float
    last_at: float
    active_seconds: float
    longest_pause_seconds: float


@dataclass(frozen=True)
class RunStats:
    """What one run of the runner cost. Wall clock is recorded as the spec requires."""

    pairs: int
    calls_made: int
    cache_hits: int
    seconds: float
    #: When every answer behind the table arrived, or `None` if the cache has no timestamps for
    #: them (a cache written before ticket 09).
    timing: AnswerTiming | None = None
    #: The input tokens Jev reported billing for every call behind the table, counted once per call,
    #: or `None` if any of those calls has no recorded usage (an older cache, or a client that does
    #: not report it): a partial sum would understate the bill.
    billed_input_tokens: int | None = None


def answer_timing(stamps: Iterable[float]) -> AnswerTiming | None:
    """Summarise answer timestamps, or `None` when there are none."""
    ordered = sorted(stamps)
    if not ordered:
        return None
    gaps = [later - earlier for earlier, later in zip(ordered, ordered[1:])]
    return AnswerTiming(
        answers=len(ordered),
        first_at=ordered[0],
        last_at=ordered[-1],
        active_seconds=sum(gap for gap in gaps if gap <= PAUSE_SECONDS),
        longest_pause_seconds=max(gaps, default=0.0),
    )


def prompt_fingerprint(parent_line: str, clause_text: str) -> str:
    """A hash of the two pieces of text Jev is shown, Parent Line first.

    Joined with a unit separator so text cannot shift across the boundary: `("ab", "c")` and
    `("a", "bc")` are different prompts.
    """
    payload = "\x1f".join([parent_line, clause_text])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _key(clause: Clause, rule: Rule, model_version: str, question_type: str) -> PairKey:
    return (
        clause.doc_id,
        clause.start,
        clause.end,
        rule.id,
        question_type,
        model_version,
        prompt_fingerprint(clause.parent_line, clause.text),
    )


def _call_id(key: PairKey, asked_at: float) -> tuple:
    """What identifies the call a row came from: what Jev was shown, and when it answered."""
    return (key[0], key[1], key[2], key[6], asked_at)


def read_cache(path: Path) -> dict[PairKey, float]:
    """Load every answer already on disk.

    A truncated or malformed final line is skipped rather than fatal: an interruption can leave one
    half-written. A row with no `prompt_fingerprint` is skipped too, so it is a miss (ticket 10).
    """
    return read_cache_with_stamps(path)[0]


def read_cache_with_stamps(
    path: Path,
) -> tuple[dict[PairKey, float], dict[PairKey, float], dict[PairKey, int]]:
    """Every answer on disk, when each arrived, and the input tokens its call was billed.

    Rows written before ticket 09 have no stamp, and before the fan-out had no usage.
    """
    answers: dict[PairKey, float] = {}
    stamps: dict[PairKey, float] = {}
    usages: dict[PairKey, int] = {}
    if not Path(path).exists():
        return answers, stamps, usages

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
                if "asked_at" in row:
                    stamps[key] = float(row["asked_at"])
                if "input_tokens" in row:
                    usages[key] = int(row["input_tokens"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                # A half-written line, or one written before the fingerprint existed. Either way
                # the Pair is simply asked again.
                continue
    return answers, stamps, usages


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


def _row(
    clause: Clause,
    rule: Rule,
    model_version: str,
    question_type: str,
    p_yes: float,
    asked_at: float,
    input_tokens: int | None = None,
) -> str:
    row = {
        "doc_id": clause.doc_id,
        "clause_start": clause.start,
        "clause_end": clause.end,
        "rule_id": rule.id,
        "question_type": question_type,
        "model_version": model_version,
        "prompt_fingerprint": prompt_fingerprint(clause.parent_line, clause.text),
        "question": rule.detection_question,
        "p_yes": p_yes,
        # Neither of these is part of the key. They are what lets a rebuild report the run's own
        # timing and what Jev billed, which are unrecoverable once the calls are paid for.
        "asked_at": round(asked_at, 3),
    }
    if input_tokens is not None:
        # The whole call's figure, repeated on each of its rows. Count it once per call.
        row["input_tokens"] = input_tokens
    return json.dumps(row, ensure_ascii=False) + "\n"


def _billed_tokens(
    keys: set[PairKey], stamps: dict[PairKey, float], usages: dict[PairKey, int]
) -> int | None:
    """What Jev billed for the calls behind `keys`, once per call, or `None` if any is unknown."""
    if not keys or any(key not in usages or key not in stamps for key in keys):
        return None
    per_call = {_call_id(key, stamps[key]): usages[key] for key in keys}
    return sum(per_call.values())


def run_pairs(
    clauses: Sequence[Clause],
    rules: Iterable[Rule],
    client: JevClient,
    cache_path: Path,
    workers: int = 1,
    question_type: str = config.QUESTION_TYPE,
    now: Callable[[], float] = time.time,
) -> tuple[PYesTable, RunStats]:
    """Ask Jev about every (Clause, Rule) Pair, skipping any already in the cache.

    Each Clause is one call carrying every Rule still missing for it, so `calls_made` counts
    Clauses (or fewer, when some Pairs were cached), not Pairs. The cache still holds one row per
    Pair.

    Returns the P(yes) table, keyed by Rule id then by (document, Clause span), and the run's
    counts and wall clock.

    `workers` is how many calls may be in flight at once. It changes how fast the run goes and
    nothing else: the answers are the same, and so is the set of cache rows, though their order may
    differ. The client must be safe to call from several threads when `workers` is above one. Only
    this function's own thread ever writes the cache, so rows never interleave.

    The window is bounded: at most `workers` calls are outstanding, and a new one is submitted only
    when another returns. So a failure (or Ctrl-C) never leaves the rest of the corpus queued behind
    it, and the calls already in flight are waited for and written to the cache, because they were paid for.
    The first failure is re-raised once they have landed. Because answers are flushed as they
    arrive, the next run asks only what is still missing.
    """
    if workers < 1:
        raise ValueError(f"workers must be at least 1, got {workers}")
    rules = list(rules)
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cached, stamps, usages = read_cache_with_stamps(cache_path)
    model_version = client.model_version
    _close_dangling_line(cache_path)

    # Everything this run needs, in order, and the subset that is not in the cache, grouped by what
    # Jev is shown: one call per Clause carrying every Rule still missing for it (the fan-out). A
    # Pair that appears twice is asked once: concurrent workers would otherwise race to ask it twice.
    needed: list[tuple[str, tuple[str, str], PairKey]] = []
    to_ask: dict[tuple, tuple[Clause, list[tuple[Rule, PairKey]]]] = {}
    queued: set[PairKey] = set()
    cache_hits = 0
    for clause in clauses:
        for rule in rules:
            key = _key(clause, rule, model_version, question_type)
            needed.append((rule.id, clause.key, key))
            if key in cached or key in queued:
                cache_hits += 1
                continue
            queued.add(key)
            # The key's document, span and prompt fingerprint: everything Jev is shown, not the Rule.
            shown = (key[0], key[1], key[2], key[6])
            to_ask.setdefault(shown, (clause, []))[1].append((rule, key))

    started = time.monotonic()
    calls_made = 0
    first_error: BaseException | None = None
    pending = iter(to_ask.values())
    in_flight: dict[Future, tuple[Clause, list[tuple[Rule, PairKey]]]] = {}

    with cache_path.open("a", encoding="utf-8") as handle:

        def settle(future: Future) -> None:
            """Record one finished call: keep its answers, or remember the first failure.

            A call is all or nothing: every Rule it carried is written, or none is, so a failure
            never leaves a Clause half answered.
            """
            nonlocal calls_made, first_error
            clause, asked = in_flight[future]
            try:
                answers = future.result()
                values = [float(answers[rule.id]) for rule, _ in asked]
            except BaseException as error:  # noqa: BLE001 - re-raised below, after the drain
                first_error = first_error or error
                del in_flight[future]
                return
            # One stamp for the whole call: the rows of a call arrived together, and the timing
            # counts calls.
            asked_at = now()
            calls_made += 1
            # Written before it leaves `in_flight`, so an error while writing cannot also make the
            # drain forget the call. Flushed per call so an interruption loses at most the calls
            # still in flight.
            billed = getattr(answers, "input_tokens", None)
            for (rule, key), p_yes in zip(asked, values):
                cached[key] = p_yes
                stamps[key] = asked_at
                if billed is not None:
                    usages[key] = billed
                handle.write(
                    _row(clause, rule, model_version, question_type, p_yes, asked_at, billed)
                )
            handle.flush()
            del in_flight[future]

        pool = ThreadPoolExecutor(max_workers=workers)
        try:
            while True:
                while first_error is None and len(in_flight) < workers:
                    item = next(pending, None)
                    if item is None:
                        break
                    clause, asked = item
                    future = pool.submit(
                        ask_many,
                        client,
                        clause_text=clause.text,
                        parent_line=clause.parent_line,
                        questions={rule.id: rule.detection_question for rule, _ in asked},
                        question_type=question_type,
                    )
                    in_flight[future] = item
                if not in_flight:
                    break
                done, _ = wait(in_flight, return_when=FIRST_COMPLETED)
                for future in done:
                    settle(future)
        finally:
            # Reached on a failure, on Ctrl-C and on success alike: collect every call still in
            # flight, so what was paid for is written before anything is raised.
            for future in list(in_flight):
                wait([future])
                settle(future)
            pool.shutdown(wait=True)

    if first_error is not None:
        raise first_error

    table: PYesTable = {rule.id: {} for rule in rules}
    for rule_id, clause_key, key in needed:
        table[rule_id][clause_key] = cached[key]

    needed_keys = {key for _, _, key in needed}
    stats = RunStats(
        pairs=len(clauses) * len(rules),
        calls_made=calls_made,
        cache_hits=cache_hits,
        seconds=time.monotonic() - started,
        # Distinct stamps are calls: the rows of one call share a stamp. Two calls landing in the
        # same millisecond would count as one, which is negligible beside thousands of calls.
        timing=answer_timing({stamps[key] for key in needed_keys if key in stamps}),
        billed_input_tokens=_billed_tokens(needed_keys, stamps, usages),
    )
    return table, stats
