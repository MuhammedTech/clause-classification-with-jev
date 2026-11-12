"""The real Jev client, tested at its public seam: `p_yes`, with the network replaced by a fake
transport and the clock replaced by a fake clock. No test here reaches TypeSafe."""

from __future__ import annotations

import json

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

    with pytest.raises(JevUnavailable):
        ask(client(transport, max_attempts=3))
    assert len(transport.requests) == 3


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


# --- through the runner ----------------------------------------------------------------------


def test_an_interrupted_real_run_resumes_from_the_cache_and_records_the_model_version(tmp_path):
    from jev_cascade.domain import Clause
    from jev_cascade.jev import CountingJevClient, FailingJevClient, JevCallLimitReached
    from jev_cascade.rulebook import rule
    from jev_cascade.runner import read_cache, run_pairs

    clauses = [Clause("D", i, i * 10, i * 10 + 10, f"clause {i}", f"{i}. Heading") for i in range(4)]
    cache = tmp_path / "pyes.jsonl"

    interrupted = FailingJevClient(client(FakeTransport(ok(0.3))), limit=2)
    with pytest.raises(JevCallLimitReached):
        run_pairs(clauses, [rule("R1")], interrupted, cache)

    transport = FakeTransport(ok(0.6))
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
