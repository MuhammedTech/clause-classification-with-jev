"""The Jev runner: the JSONL cache skips answered Pairs and survives an interruption."""

import json

import pytest

from jev_cascade.domain import Clause
from jev_cascade.jev import (
    CountingJevClient,
    FailingJevClient,
    JevCallLimitReached,
    StubJevClient,
)
from jev_cascade.config import QUESTION_TYPE
from jev_cascade.rulebook import rule
from jev_cascade.runner import read_cache, run_pairs

R1 = rule("R1")


def clauses():
    return (
        Clause("D", 0, 0, 10, "liability is capped", "1. Liability"),
        Clause("D", 1, 10, 20, "fees are due monthly", "2. Fees"),
        Clause("D", 2, 20, 30, "notices go to the address", "3. Notices"),
    )


def test_every_pair_is_asked_once_on_a_cold_cache(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    client = CountingJevClient(StubJevClient())

    table, _ = run_pairs(clauses(), [R1], client, cache)

    assert client.calls == 3
    # The table is keyed by Rule id, then by (document, Clause span).
    assert sorted(table) == ["R1"]
    assert len(table["R1"]) == 3
    assert set(table["R1"]) == {("D", "0-10"), ("D", "10-20"), ("D", "20-30")}
    assert all(0.0 <= p <= 1.0 for p in table["R1"].values())


def test_a_second_run_makes_zero_client_calls(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    first, _ = run_pairs(clauses(), [R1], CountingJevClient(StubJevClient()), cache)

    second_client = CountingJevClient(StubJevClient())
    second, _ = run_pairs(clauses(), [R1], second_client, cache)

    assert second_client.calls == 0
    assert second == first


def test_a_run_interrupted_midway_resumes_from_the_cache(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    interrupted = FailingJevClient(StubJevClient(), limit=2)
    with pytest.raises(JevCallLimitReached):
        run_pairs(clauses(), [R1], interrupted, cache)

    # The two answers it did get were flushed per call, not held until the end.
    assert len(read_cache(cache)) == 2

    resumed = CountingJevClient(StubJevClient())
    table, _ = run_pairs(clauses(), [R1], resumed, cache)

    # Exactly the unanswered Pair is asked again.
    assert resumed.calls == 1
    assert len(table["R1"]) == 3


def test_the_cache_skips_a_truncated_final_line(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    run_pairs(clauses(), [R1], StubJevClient(), cache)
    with cache.open("a", encoding="utf-8") as handle:
        handle.write('{"doc_id": "D", "clause_start": 30, "clause_en')

    # An interruption can leave a half-written line. It is ignored, not fatal.
    assert len(read_cache(cache)) == 3

    client = CountingJevClient(StubJevClient())
    run_pairs(clauses(), [R1], client, cache)
    assert client.calls == 0


def test_a_cache_row_records_the_key_and_the_question_asked(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    run_pairs(clauses()[:1], [R1], StubJevClient(), cache)

    row = json.loads(cache.read_text(encoding="utf-8").splitlines()[0])
    assert row["doc_id"] == "D"
    assert row["clause_start"] == 0
    assert row["clause_end"] == 10
    assert row["rule_id"] == "R1"
    assert row["question_type"] == QUESTION_TYPE
    assert row["model_version"] == "stub-v1+seed0"
    # The question wording is not part of the key, so storing it is what makes a cache written
    # under different wording (ticket 08) detectable.
    assert row["question"] == R1.detection_question
    assert 0.0 <= row["p_yes"] <= 1.0


def test_a_cache_written_by_another_model_version_is_not_reused(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    run_pairs(clauses(), [R1], StubJevClient(name="stub-v1"), cache)

    newer = CountingJevClient(StubJevClient(name="stub-v2"))
    run_pairs(clauses(), [R1], newer, cache)

    assert newer.calls == 3


def test_a_cache_written_under_another_seed_is_not_reused(tmp_path):
    # Two seeds give different answers, so the seed belongs in the cache key by way of the model
    # version. Otherwise --seed 1 would be served seed 0's answers and report zero calls.
    cache = tmp_path / "pyes.jsonl"
    run_pairs(clauses(), [R1], StubJevClient(seed=0), cache)

    other_seed = CountingJevClient(StubJevClient(seed=1))
    run_pairs(clauses(), [R1], other_seed, cache)

    assert other_seed.calls == 3


def test_a_kill_mid_write_does_not_cost_an_answer(tmp_path):
    # A run killed mid-write leaves a line with no newline. The next run must terminate it before
    # appending, or its first answer is glued onto the fragment and lost too.
    cache = tmp_path / "pyes.jsonl"
    partial = FailingJevClient(StubJevClient(), limit=1)
    with pytest.raises(JevCallLimitReached):
        run_pairs(clauses(), [R1], partial, cache)
    with cache.open("a", encoding="utf-8") as handle:
        handle.write('{"doc_id": "D", "clause_start": 10, "clause_en')

    resumed = CountingJevClient(StubJevClient())
    run_pairs(clauses(), [R1], resumed, cache)
    assert resumed.calls == 2

    settled = CountingJevClient(StubJevClient())
    run_pairs(clauses(), [R1], settled, cache)
    assert settled.calls == 0


def test_the_stub_is_deterministic_across_clients():
    one = StubJevClient(seed=7)
    two = StubJevClient(seed=7)
    args = ("liability is capped", "1. Liability", R1.detection_question, QUESTION_TYPE)
    assert one.p_yes(*args) == two.p_yes(*args)
    assert StubJevClient(seed=8).p_yes(*args) != one.p_yes(*args)
    assert one.is_stub is True


def test_the_runner_reports_the_calls_it_made_and_the_time_it_took(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    table, stats = run_pairs(clauses(), [R1], StubJevClient(), cache)

    assert stats.pairs == 3
    assert stats.calls_made == 3
    assert stats.cache_hits == 0
    assert stats.seconds >= 0.0

    _, again = run_pairs(clauses(), [R1], StubJevClient(), cache)
    assert again.calls_made == 0
    assert again.cache_hits == 3


def _clause_under(parent_line):
    return Clause("D", 0, 0, 10, "(b) report quarterly", parent_line)


def test_the_same_span_under_a_different_parent_line_is_asked_again(tmp_path):
    # Ticket 10. Jev is shown Parent Line plus Clause text, so two prompts that differ only in the
    # Parent Line must not share a cached answer. Two sequential runs on one cache file, because
    # the P(yes) table is keyed by (document, span) and cannot hold two answers for one span.
    cache = tmp_path / "pyes.jsonl"
    sibling = _clause_under("(a) pay the fees.")
    section = _clause_under("2. Licensee commits to:")

    first_client = CountingJevClient(StubJevClient())
    first, _ = run_pairs([sibling], [R1], first_client, cache)
    second_client = CountingJevClient(StubJevClient())
    second, _ = run_pairs([section], [R1], second_client, cache)

    assert first_client.calls == 1
    assert second_client.calls == 1
    assert first["R1"][sibling.key] != second["R1"][section.key]


def test_a_cache_row_without_a_fingerprint_is_a_miss(tmp_path):
    # A cache written before the fingerprint existed cannot say what its prompt was, so the Pair is
    # asked again rather than guessed at.
    cache = tmp_path / "pyes.jsonl"
    clause = _clause_under("2. Licensee commits to:")
    run_pairs([clause], [R1], StubJevClient(), cache)
    rows = [json.loads(line) for line in cache.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        del row["prompt_fingerprint"]
    cache.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    client = CountingJevClient(StubJevClient())
    run_pairs([clause], [R1], client, cache)

    assert client.calls == 1


def test_a_cache_row_records_a_fingerprint_of_what_jev_was_shown(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    run_pairs([_clause_under("A")], [R1], StubJevClient(), cache)
    run_pairs([_clause_under("B")], [R1], StubJevClient(), cache)

    rows = [json.loads(line) for line in cache.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["prompt_fingerprint"] != rows[1]["prompt_fingerprint"]


def test_text_cannot_shift_across_the_parent_line_boundary():
    # "ab" + "c" and "a" + "bc" are different prompts and must not collide.
    from jev_cascade.runner import prompt_fingerprint

    assert prompt_fingerprint("ab", "c") != prompt_fingerprint("a", "bc")


class RecordingClient:
    is_stub = True
    model_version = "recording"

    def __init__(self):
        self.seen = []

    def p_yes(self, clause_text, parent_line, question, question_type):
        self.seen.append((parent_line, clause_text))
        return 0.5


def test_jev_receives_the_parent_line_and_the_clause_text(tmp_path):
    clause = _clause_under("2. Licensee commits to:")
    client = RecordingClient()
    run_pairs([clause], [R1], client, tmp_path / "pyes.jsonl")
    assert client.seen == [("2. Licensee commits to:", "(b) report quarterly")]


def test_the_question_type_is_asked_cached_and_keyed_per_run(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    seen = []

    class Recording(StubJevClient):
        def p_yes(self, clause_text, parent_line, question, question_type):
            seen.append(question_type)
            return super().p_yes(clause_text, parent_line, question, question_type)

    run_pairs(clauses(), [R1], Recording(), cache, question_type="score2")

    assert seen == ["score2"] * 3
    types = {json.loads(line)["question_type"] for line in cache.read_text().splitlines()}
    assert types == {"score2"}

    # An answer cached under one type is not served to another: it is a different question.
    other = CountingJevClient(StubJevClient())
    run_pairs(clauses(), [R1], other, cache, question_type="choice2")
    assert other.calls == 3
    again = CountingJevClient(StubJevClient())
    run_pairs(clauses(), [R1], again, cache, question_type="score2")
    assert again.calls == 0
