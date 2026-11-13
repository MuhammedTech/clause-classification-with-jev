"""The Jev client: typed questions about one Clause, each answered with a probability.

Jev is called **once per Clause, with every Rule's question in the same call** (the fan-out): the
Clause is sent once and each question is answered separately, keyed by its id. A client that cannot
fan out only has `p_yes` and is asked one question at a time; `ask_many` chooses. Jev sees the
Parent Line plus the Clause text; grading uses only the Clause's own span.

This module holds the interface, a deterministic seeded stub and the test wrappers. The real HTTP
client is in `typesafe.py`, and `clients.py` chooses between the two. Every figure derived from the
stub is labelled as stub in the report.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable


@runtime_checkable
class JevClient(Protocol):
    """What the Jev runner needs from a client, real or stubbed."""

    @property
    def model_version(self) -> str:
        """Identifies the answering model. Part of the P(yes) cache key."""
        ...

    @property
    def is_stub(self) -> bool:
        """Whether the answers carry no signal, so the report can label every figure."""
        ...

    def p_yes(
        self,
        clause_text: str,
        parent_line: str,
        question: str,
        question_type: str,
    ) -> float:
        """The probability Jev returns that the Detection Question is answered yes."""
        ...


class FanOutAnswers(dict):
    """P(yes) by question id, and the input tokens Jev reported billing for the call, if it did.

    A plain `dict` of answers is just as good to the runner, which records `input_tokens` only when
    the client supplies it.
    """

    def __init__(self, answers: Mapping[str, float], input_tokens: int | None = None):
        super().__init__(answers)
        self.input_tokens = input_tokens


def ask_many(
    client: JevClient,
    clause_text: str,
    parent_line: str,
    questions: Mapping[str, str],
    question_type: str,
) -> dict[str, float]:
    """P(yes) for every question about one Clause, keyed by the question's id.

    One call when the client has `p_yes_many`, otherwise one call per question. The runner goes
    through here so a client written before the fan-out keeps working.
    """
    many = getattr(client, "p_yes_many", None)
    if many is not None:
        return many(clause_text, parent_line, questions, question_type)
    return {
        question_id: client.p_yes(clause_text, parent_line, question, question_type)
        for question_id, question in questions.items()
    }


@dataclass(frozen=True)
class StubJevClient:
    """A deterministic seeded stand-in for Jev.

    The same inputs always give the same P(yes), so a run is reproducible and the cache can be
    checked for correctness. The values carry **no signal**: they are a hash of the inputs spread
    uniformly over [0, 1]. Nothing derived from them says anything about how Jev would behave, and
    the report labels every such figure as stub.
    """

    seed: int = 0
    name: str = "stub-v1"
    #: P(yes) is rounded to this many decimals, as a real client's output would be.
    decimals: int = 4

    @property
    def model_version(self) -> str:
        """The seed is part of this, and so of the cache key.

        Two seeds give different answers, so a cache written under one must not be served to the
        other.
        """
        return f"{self.name}+seed{self.seed}"

    @property
    def is_stub(self) -> bool:
        return True

    def p_yes(
        self,
        clause_text: str,
        parent_line: str,
        question: str,
        question_type: str,
    ) -> float:
        payload = "\x1f".join(
            [
                str(self.seed),
                self.model_version,
                question_type,
                question,
                parent_line,
                clause_text,
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        draw = int.from_bytes(digest[:8], "big") / float(1 << 64)
        return round(draw, self.decimals)

    def p_yes_many(
        self,
        clause_text: str,
        parent_line: str,
        questions: Mapping[str, str],
        question_type: str,
    ) -> dict[str, float]:
        """Each answer is what the question would get alone, so fanning out changes no stub figure."""
        return {
            question_id: self.p_yes(clause_text, parent_line, question, question_type)
            for question_id, question in questions.items()
        }


@dataclass
class CountingJevClient:
    """Wraps a client and counts the calls it passes through.

    Used by the tests to assert that a second run makes zero client calls.
    """

    inner: JevClient
    calls: int = 0

    @property
    def model_version(self) -> str:
        return self.inner.model_version

    @property
    def is_stub(self) -> bool:
        return self.inner.is_stub

    def p_yes(
        self,
        clause_text: str,
        parent_line: str,
        question: str,
        question_type: str,
    ) -> float:
        self.calls += 1
        return self.inner.p_yes(clause_text, parent_line, question, question_type)

    def p_yes_many(
        self,
        clause_text: str,
        parent_line: str,
        questions: Mapping[str, str],
        question_type: str,
    ) -> dict[str, float]:
        """One call, however many questions it carries."""
        self.calls += 1
        return ask_many(self.inner, clause_text, parent_line, questions, question_type)


class JevCallLimitReached(RuntimeError):
    """Raised by `FailingJevClient` to stand in for a run interrupted midway."""


@dataclass
class FailingJevClient:
    """Answers `limit` calls, then raises. Stands in for an interrupted run in the tests."""

    inner: JevClient
    limit: int
    calls: int = 0

    @property
    def model_version(self) -> str:
        return self.inner.model_version

    @property
    def is_stub(self) -> bool:
        return self.inner.is_stub

    def p_yes(
        self,
        clause_text: str,
        parent_line: str,
        question: str,
        question_type: str,
    ) -> float:
        if self.calls >= self.limit:
            raise JevCallLimitReached(f"stopped after {self.limit} calls")
        self.calls += 1
        return self.inner.p_yes(clause_text, parent_line, question, question_type)

    def p_yes_many(
        self,
        clause_text: str,
        parent_line: str,
        questions: Mapping[str, str],
        question_type: str,
    ) -> dict[str, float]:
        if self.calls >= self.limit:
            raise JevCallLimitReached(f"stopped after {self.limit} calls")
        self.calls += 1
        return ask_many(self.inner, clause_text, parent_line, questions, question_type)


class JevCallRefused(RuntimeError):
    """Raised by `CacheOnlyJevClient` when a Pair is not in the cache."""


@dataclass
class CacheOnlyJevClient:
    """Wraps a client and refuses every call, so a run can only be served from the cache.

    It lends the wrapped client's model version, which is part of the cache key, and nothing else:
    rebuilding a report from the cache must never reach the network.
    """

    inner: JevClient

    @property
    def model_version(self) -> str:
        return self.inner.model_version

    @property
    def is_stub(self) -> bool:
        return self.inner.is_stub

    def p_yes(
        self,
        clause_text: str,
        parent_line: str,
        question: str,
        question_type: str,
    ) -> float:
        raise JevCallRefused("this Pair is not in the cache and the run may not ask Jev")

    def p_yes_many(
        self,
        clause_text: str,
        parent_line: str,
        questions: Mapping[str, str],
        question_type: str,
    ) -> dict[str, float]:
        raise JevCallRefused("this Clause is not fully in the cache and the run may not ask Jev")
