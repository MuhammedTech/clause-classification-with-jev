"""The runner with several Jev calls in flight at once.

Concurrency must change how fast a run goes and nothing else: the same answers, the same cache, an
interruption that keeps what was paid for, and a resume that asks only what is missing. The tests
avoid timing: overlap is proved with a barrier, not a sleep.
"""

from __future__ import annotations

import json
import threading

import pytest

from jev_cascade import runner
from jev_cascade.domain import Clause
from jev_cascade.jev import StubJevClient
from jev_cascade.rulebook import rule
from jev_cascade.runner import read_cache, run_pairs

R1 = rule("R1")


def many_clauses(n=12):
    return [Clause("D", i, i * 10, i * 10 + 10, f"clause {i}", f"{i}. Heading") for i in range(n)]


class ThreadSafeCounting:
    """Wraps a client, counts calls under a lock and records the peak calls in flight."""

    def __init__(self, inner, hook=None):
        self.inner = inner
        self.hook = hook
        self.calls = 0
        self.in_flight = 0
        self.peak = 0
        self._lock = threading.Lock()

    @property
    def model_version(self):
        return self.inner.model_version

    @property
    def is_stub(self):
        return self.inner.is_stub

    def p_yes(self, clause_text, parent_line, question, question_type):
        with self._lock:
            self.calls += 1
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
            number = self.calls
        try:
            if self.hook:
                self.hook(number)
            return self.inner.p_yes(clause_text, parent_line, question, question_type)
        finally:
            with self._lock:
                self.in_flight -= 1


def test_calls_really_overlap_up_to_the_worker_count(tmp_path):
    barrier = threading.Barrier(4, timeout=5)
    # Every one of the first four calls waits for the others, so the test only passes if four
    # calls are in flight together. A serial runner would break the barrier.
    client = ThreadSafeCounting(StubJevClient(), hook=lambda n: barrier.wait() if n <= 4 else None)

    run_pairs(many_clauses(), [R1], client, tmp_path / "pyes.jsonl", workers=4)

    assert client.peak == 4
    assert client.calls == 12


def test_the_answers_and_the_cache_are_the_same_as_a_serial_run(tmp_path):
    clauses = many_clauses(30)
    serial_table, _ = run_pairs(clauses, [R1], StubJevClient(), tmp_path / "serial.jsonl")
    parallel_table, stats = run_pairs(
        clauses, [R1], StubJevClient(), tmp_path / "parallel.jsonl", workers=8
    )

    assert parallel_table == serial_table
    assert stats.calls_made == 30 and stats.cache_hits == 0
    # Row order may differ; the set of answers may not.
    assert read_cache(tmp_path / "parallel.jsonl") == read_cache(tmp_path / "serial.jsonl")
    lines = (tmp_path / "parallel.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 30
    assert all(json.loads(line)["p_yes"] is not None for line in lines)  # no interleaved rows


def test_a_second_concurrent_run_makes_zero_calls(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    run_pairs(many_clauses(), [R1], StubJevClient(), cache, workers=4)

    again = ThreadSafeCounting(StubJevClient())
    _, stats = run_pairs(many_clauses(), [R1], again, cache, workers=4)

    assert again.calls == 0
    assert stats.cache_hits == 12


def test_a_failure_keeps_every_answer_that_returned_and_stops_asking(tmp_path):
    cache = tmp_path / "pyes.jsonl"
    clauses = many_clauses(200)

    def fail_on_the_fifth(number):
        if number == 5:
            raise RuntimeError("Jev went away")

    client = ThreadSafeCounting(StubJevClient(), hook=fail_on_the_fifth)
    with pytest.raises(RuntimeError, match="Jev went away"):
        run_pairs(clauses, [R1], client, cache, workers=4)

    # It did not queue the whole corpus behind the failure: only calls already in flight finish.
    assert client.calls < 5 + 4 + 1
    # Every call that returned was paid for, so every one is on disk.
    assert len(read_cache(cache)) == client.calls - 1

    resumed = ThreadSafeCounting(StubJevClient())
    table, _ = run_pairs(clauses, [R1], resumed, cache, workers=4)
    assert resumed.calls == 200 - (client.calls - 1)
    assert len(table["R1"]) == 200


def test_ctrl_c_in_the_runner_keeps_what_was_paid_for_and_resumes(tmp_path, monkeypatch):
    cache = tmp_path / "pyes.jsonl"
    clauses = many_clauses(200)

    real_wait = runner.wait
    waits = {"n": 0}

    def interrupted_on_the_third_wait(futures, **kwargs):
        waits["n"] += 1
        if waits["n"] == 3:
            raise KeyboardInterrupt  # the user pressed Ctrl-C in the main thread
        return real_wait(futures, **kwargs)

    monkeypatch.setattr(runner, "wait", interrupted_on_the_third_wait)
    client = ThreadSafeCounting(StubJevClient())

    with pytest.raises(KeyboardInterrupt):
        run_pairs(clauses, [R1], client, cache, workers=4)
    monkeypatch.undo()

    # Calls in flight when it hit were waited for and written: nothing paid for is lost, and it did
    # not carry on asking.
    assert len(read_cache(cache)) == client.calls
    assert client.calls < 20

    resumed = ThreadSafeCounting(StubJevClient())
    table, _ = run_pairs(clauses, [R1], resumed, cache, workers=4)
    assert resumed.calls == 200 - client.calls
    assert len(table["R1"]) == 200


def test_a_pair_that_appears_twice_is_asked_once(tmp_path):
    clauses = many_clauses(3)
    client = ThreadSafeCounting(StubJevClient())

    run_pairs(clauses + clauses, [R1], client, tmp_path / "pyes.jsonl", workers=4)

    assert client.calls == 3


def test_one_worker_is_the_serial_runner(tmp_path):
    client = ThreadSafeCounting(StubJevClient())

    run_pairs(many_clauses(), [R1], client, tmp_path / "pyes.jsonl", workers=1)

    assert client.peak == 1


def test_workers_must_be_at_least_one(tmp_path):
    with pytest.raises(ValueError, match="workers"):
        run_pairs(many_clauses(), [R1], StubJevClient(), tmp_path / "pyes.jsonl", workers=0)
