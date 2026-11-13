"""The real Jev client, tested at its public seam: `p_yes`, with the network replaced by a fake
transport and the clock replaced by a fake clock. No test here reaches TypeSafe."""

from __future__ import annotations

import json
import threading
import time

import pytest

from jev_cascade.typesafe import (
    ContextTooLong,
    JevAuthError,
    JevRequestRejected,
    JevUnavailable,
    ModelMismatch,
    TypeSafeJevClient,
)

MODEL = "jev-1.14.0"


class FakeTransport:
    """Plays back a script of (status, body) replies or exceptions and records every request."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests: list[tuple[str, dict, dict]] = []

    def __call__(self, url, headers, body, timeout):
        self.requests.append((url, headers, json.loads(body)))
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, BaseException):
            raise reply
        status, payload = reply
        return status, json.dumps(payload).encode()


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def ok(p, model=MODEL):
    return 200, {
        "model": model,
        "answers": {"q": {"type": "noul", "noul": p}},
        "usage": {"input_tokens": 10, "output_tokens": 1},
    }


def client(transport, clock=None, **kwargs):
    clock = clock or FakeClock()
    return TypeSafeJevClient(
        api_key="sk-secret-value",
        transport=transport,
        sleep=clock.sleep,
        clock=clock.time,
        **kwargs,
    )


def ask(c, **overrides):
    args = dict(
        clause_text="Liability is capped at fees paid.",
        parent_line="12. LIMITATION OF LIABILITY",
        question="Does this clause cap or limit a party's liability?",
        question_type="binary",
    )
    args.update(overrides)
    return c.p_yes(**args)


def test_asks_one_noul_question_with_a_bearer_key_and_returns_its_probability():
    transport = FakeTransport(ok(0.83))

    p = ask(client(transport))

    assert p == 0.83
    ((url, headers, body),) = transport.requests
    assert url == "https://api.typesafe.ai/v1/systemone"
    assert headers["Authorization"] == "Bearer sk-secret-value"
    assert body["model"] == MODEL
    assert len(body["questions"]) == 1
    (question,) = body["questions"].values()
    assert question == {
        "type": "noul",
        "instructions": "Does this clause cap or limit a party's liability?",
    }
    # Jev is shown Parent Line plus Clause text, Parent Line first.
    assert "12. LIMITATION OF LIABILITY" in body["state"]
    assert body["state"].index("12. LIMITATION") < body["state"].index("Liability is capped")


def test_the_model_version_is_pinned_and_known_before_any_call():
    transport = FakeTransport(ok(0.1))
    c = client(transport)

    assert c.model_version == MODEL
    assert c.is_stub is False
    assert transport.requests == []


def test_a_reply_from_a_different_model_is_refused():
    transport = FakeTransport(ok(0.5, model="jev-1.15.0"))

    with pytest.raises(ModelMismatch):
        ask(client(transport))


def test_a_question_type_other_than_binary_is_refused_not_quietly_asked_as_noul():
    transport = FakeTransport(ok(0.5))

    with pytest.raises(ValueError, match="score"):
        ask(client(transport), question_type="score")
    assert transport.requests == []


# --- retries ---------------------------------------------------------------------------------


def test_a_rate_limited_or_overloaded_call_is_retried_with_growing_backoff_then_succeeds():
    transport = FakeTransport((429, {}), (529, {}), (503, {}), ok(0.4))
    clock = FakeClock()

    assert ask(client(transport, clock)) == 0.4

    assert len(transport.requests) == 4
    waits = [s for s in clock.sleeps if s >= 0.5]  # backoff waits, not rate spacing
    assert len(waits) == 3
    assert waits == sorted(waits) and waits[0] < waits[-1]


def test_a_dropped_connection_is_retried():
    transport = FakeTransport(ConnectionResetError("reset"), TimeoutError("slow"), ok(0.9))

    assert ask(client(transport)) == 0.9
    assert len(transport.requests) == 3


def test_a_truncated_reply_is_retried():
    import http.client

    class Truncated:
        """A 200 whose body is cut off, then a body that is not JSON, then a good one."""

        def __init__(self):
            self.calls = 0

        def __call__(self, url, headers, body, timeout):
            self.calls += 1
            if self.calls == 1:
                raise http.client.IncompleteRead(b"{")
            if self.calls == 2:
                return 200, b'{"model": "jev-1.14'
            return 200, json.dumps(ok(0.7)[1]).encode()

    transport = Truncated()

    assert ask(client(transport)) == 0.7
    assert transport.calls == 3


def test_it_gives_up_after_the_retry_budget_and_says_so():
    transport = FakeTransport((429, {}))
    c = client(transport, max_attempts=3)

    with pytest.raises(JevUnavailable):
        ask(c)
    assert len(transport.requests) == 3
    # Three attempts is two retries: the last failure is given up on, not retried.
    assert c.retries == {"429": 2}


def test_a_rejected_key_is_not_retried_and_the_key_is_not_in_the_message():
    transport = FakeTransport((401, {"error": "bad key"}))

    with pytest.raises(JevAuthError) as caught:
        ask(client(transport))
    assert len(transport.requests) == 1
    assert "sk-secret-value" not in str(caught.value)


def test_a_malformed_request_is_not_retried():
    transport = FakeTransport((422, {"error": "malformed question"}))

    with pytest.raises(JevRequestRejected):
        ask(client(transport))
    assert len(transport.requests) == 1


def test_a_too_long_clause_is_reported_as_too_long_not_retried():
    transport = FakeTransport((400, {"error": "max_tokens_exceeded"}))

    with pytest.raises(ContextTooLong):
        ask(client(transport))
    assert len(transport.requests) == 1


def test_threads_share_one_request_budget():
    class RecordingClock:
        """Time stands still and sleeps are only recorded, so the waits show the reserved slots."""

        def __init__(self):
            self.sleeps = []
            self._lock = threading.Lock()

        def time(self):
            # Yield here, between a thread reading the budget and claiming a slot, which is
            # exactly where an unlocked pacer lets two threads take the same one.
            time.sleep(0.005)
            return 0.0

        def sleep(self, seconds):
            time.sleep(0.005)  # a real sleep yields, as the real one does
            with self._lock:
                self.sleeps.append(seconds)

    clock = RecordingClock()
    c = client(FakeTransport(ok(0.1)), clock, requests_per_minute=1200)

    threads = [threading.Thread(target=ask, args=(c,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Five threads at 50 ms a call must be given five different slots, 0, 50, 100, 150, 200 ms
    # from now, never the same one twice.
    assert sorted(round(w, 3) for w in clock.sleeps) == [0.05, 0.1, 0.15, 0.2]


def test_retries_are_counted_by_what_caused_them():
    transport = FakeTransport((429, {}), (429, {}), (529, {}), ConnectionResetError("x"), ok(0.2))
    c = client(transport)

    ask(c)

    assert c.retries == {"429": 2, "529": 1, "connection": 1}


# --- through the runner ----------------------------------------------------------------------


def test_an_interrupted_real_run_resumes_from_the_cache_and_records_the_model_version(tmp_path):
    from jev_cascade.domain import Clause
    from jev_cascade.jev import CountingJevClient, FailingJevClient, JevCallLimitReached
    from jev_cascade.rulebook import rule
    from jev_cascade.runner import read_cache, run_pairs

    clauses = [Clause("D", i, i * 10, i * 10 + 10, f"clause {i}", f"{i}. Heading") for i in range(4)]
    cache = tmp_path / "pyes.jsonl"

    interrupted = FailingJevClient(client(FakeTransport(many_reply({"R1": 0.3}))), limit=2)
    with pytest.raises(JevCallLimitReached):
        run_pairs(clauses, [rule("R1")], interrupted, cache)

    transport = FakeTransport(many_reply({"R1": 0.6}))
    resumed = CountingJevClient(client(transport))
    table, _ = run_pairs(clauses, [rule("R1")], resumed, cache)

    assert resumed.calls == 2  # only the Pairs the first run had not reached
    assert len(table["R1"]) == 4
    assert {key[5] for key in read_cache(cache)} == {MODEL}


# --- rate -----------------------------------------------------------------------------------


def test_calls_are_spaced_to_stay_under_the_request_limit():
    transport = FakeTransport(ok(0.1))
    clock = FakeClock()
    c = client(transport, clock, requests_per_minute=1200)

    for _ in range(5):
        ask(c)

    # 1,200 a minute is one every 50 ms, so five calls take at least four gaps.
    assert clock.now >= 4 * 0.05 - 1e-9
    assert len(transport.requests) == 5


# --- ticket 08: the other two question types -------------------------------------------------------
#
# Reply shapes are the ones in TypeSafe's Score and Choice docs (docs.typesafe.ai/primitives/score.md
# and choice.md, read 2026-11-13).


def score_reply(p_no, p_yes):
    return 200, {
        "model": MODEL,
        "answers": {
            "q": {
                "type": "score",
                "score": p_yes,
                "confidence": 0.5,
                "legend": {"0": "No", "1": "Yes"},
                "probabilities": {"0": p_no, "1": p_yes},
            }
        },
        "usage": {"input_tokens": 10, "output_tokens": 1},
    }


def choice_reply(p_yes, p_no):
    return 200, {
        "model": MODEL,
        "answers": {
            "q": {
                "type": "choice",
                "choice": "yes" if p_yes >= p_no else "no",
                "confidence": 0.5,
                "probabilities": {"no": p_no, "yes": p_yes},
            }
        },
        "usage": {"input_tokens": 10, "output_tokens": 1},
    }


QUESTION = "Does this clause cap or limit a party's liability?"


def test_a_two_level_score_asks_the_same_question_and_reads_the_probability_of_the_top_level():
    transport = FakeTransport(score_reply(0.3, 0.7))

    p = ask(client(transport), question_type="score2")

    assert p == 0.7
    ((_, _, body),) = transport.requests
    assert body["questions"]["q"] == {
        "type": "score",
        "instructions": QUESTION,
        "criteria": ["No", "Yes"],
    }


def test_a_yes_no_choice_asks_the_same_question_and_reads_the_probability_of_yes():
    transport = FakeTransport(choice_reply(0.9, 0.1))

    p = ask(client(transport), question_type="choice2")

    assert p == 0.9
    ((_, _, body),) = transport.requests
    assert body["questions"]["q"] == {
        "type": "choice",
        "instructions": QUESTION,
        "criteria": {"yes": None, "no": None},
    }


def test_the_state_is_identical_for_all_three_types():
    states = []
    for question_type, reply in (
        ("binary", ok(0.5)),
        ("score2", score_reply(0.5, 0.5)),
        ("choice2", choice_reply(0.5, 0.5)),
    ):
        transport = FakeTransport(reply)
        ask(client(transport), question_type=question_type)
        states.append(transport.requests[0][2]["state"])
    assert len(set(states)) == 1


def test_a_reply_missing_the_probability_is_an_error_not_a_zero():
    from jev_cascade.typesafe import JevError

    bad = 200, {"model": MODEL, "answers": {"q": {"type": "choice", "probabilities": {"no": 1.0}}}}
    with pytest.raises(JevError):
        ask(client(FakeTransport(bad)), question_type="choice2")


# ---- Fan-out: several questions about one Clause in one request ----------------------------------

QUESTIONS = {
    "R1": "Does this clause cap or limit a party's liability?",
    "R2": "Does this clause name the governing law?",
}


def many_reply(probabilities, model=MODEL, input_tokens=40):
    return 200, {
        "model": model,
        "answers": {qid: {"type": "noul", "noul": p} for qid, p in probabilities.items()},
        "usage": {"input_tokens": input_tokens, "output_tokens": 2},
    }


def ask_many(c, questions=QUESTIONS, **overrides):
    args = dict(
        clause_text="Liability is capped at fees paid.",
        parent_line="12. LIMITATION OF LIABILITY",
        questions=questions,
        question_type="binary",
    )
    args.update(overrides)
    return c.p_yes_many(**args)


def test_every_question_goes_in_one_request_and_each_answer_is_read_by_its_id():
    transport = FakeTransport(many_reply({"R1": 0.9, "R2": 0.1}))

    answers = ask_many(client(transport))

    assert answers == {"R1": 0.9, "R2": 0.1}
    ((_, _, body),) = transport.requests  # one request, not two
    assert body["state"] == "12. LIMITATION OF LIABILITY\n\nLiability is capped at fees paid."
    assert body["questions"] == {
        "R1": {"type": "noul", "instructions": QUESTIONS["R1"]},
        "R2": {"type": "noul", "instructions": QUESTIONS["R2"]},
    }


def test_a_reply_that_leaves_a_question_unanswered_is_an_error_not_a_zero():
    from jev_cascade.typesafe import JevError

    with pytest.raises(JevError):
        ask_many(client(FakeTransport(many_reply({"R1": 0.9}))))


def test_the_input_tokens_the_replies_report_are_added_up():
    c = client(FakeTransport(many_reply({"R1": 0.9, "R2": 0.1}, input_tokens=40)))
    ask_many(c)
    ask_many(c)
    assert c.input_tokens == 80


def test_a_single_question_is_the_same_request_as_before_the_fan_out():
    transport = FakeTransport(ok(0.83))
    assert ask(client(transport)) == 0.83
    ((_, _, body),) = transport.requests
    assert list(body["questions"]) == ["q"]
