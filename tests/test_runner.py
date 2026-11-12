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
from jev_cascade.rulebook import QUESTION_TYPE, rule
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

    table = run_pairs(clauses(), [R1], client, cache)

    assert client.calls == 3
    # The table is keyed by Rule id, then by (document, Clause span).
    assert sorted(table) == ["R1"]
    assert len(table["R1"]) == 3
    assert set(table["R1"]) == {("D", "0-10"), ("D", "10-20"), ("D", "20-30")}
    assert all(0.0 <= p <= 1.0 for p in table["R1"].values())


def test_a_second_run_makes_zero_client_calls(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    first = run_pairs(clauses(), [R1], CountingJevClient(StubJevClient()), cache)

    second_client = CountingJevClient(StubJevClient())
    second = run_pairs(clauses(), [R1], second_client, cache)

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
    table = run_pairs(clauses(), [R1], resumed, cache)

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
    assert row["model_version"] == "stub-v1"
    # The question wording is not part of the key, so storing it is what makes a cache written
    # under different wording (ticket 08) detectable.
    assert row["question"] == R1.detection_question
    assert 0.0 <= row["p_yes"] <= 1.0


def test_a_cache_written_by_another_model_version_is_not_reused(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    run_pairs(clauses(), [R1], StubJevClient(model_version="stub-v1"), cache)

    newer = CountingJevClient(StubJevClient(model_version="stub-v2"))
    run_pairs(clauses(), [R1], newer, cache)

    assert newer.calls == 3


def test_the_stub_is_deterministic_across_clients():
    one = StubJevClient(seed=7)
    two = StubJevClient(seed=7)
    args = ("liability is capped", "1. Liability", R1.detection_question, QUESTION_TYPE)
    assert one.p_yes(*args) == two.p_yes(*args)
    assert StubJevClient(seed=8).p_yes(*args) != one.p_yes(*args)


def test_the_runner_reports_the_calls_it_made_and_the_time_it_took(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    table, stats = run_pairs(clauses(), [R1], StubJevClient(), cache, with_stats=True)

    assert stats.pairs == 3
    assert stats.calls_made == 3
    assert stats.cache_hits == 0
    assert stats.seconds >= 0.0

    _, again = run_pairs(clauses(), [R1], StubJevClient(), cache, with_stats=True)
    assert again.calls_made == 0
    assert again.cache_hits == 3
