"""The Jev client: one typed question about one Clause, answered with a probability.

Jev is called once per (Clause, Rule), never with two questions in one call. Jev sees the Parent
Line plus the Clause text; grading uses only the Clause's own span.

This module holds the interface and a deterministic seeded stub. The real HTTP client arrives in
ticket 07, once the user supplies the key; everything runs on the stub until then, and every figure
derived from it is labelled as stub in the report.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class JevClient(Protocol):
    """What the Jev runner needs from a client, real or stubbed."""

    @property
    def model_version(self) -> str:
        """Identifies the answering model. Part of the P(yes) cache key."""
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


@dataclass(frozen=True)
class StubJevClient:
    """A deterministic seeded stand-in for Jev.

    The same inputs always give the same P(yes), so a run is reproducible and the cache can be
    checked for correctness. The values carry **no signal**: they are a hash of the inputs spread
    uniformly over [0, 1]. Nothing derived from them says anything about how Jev would behave, and
    the report labels every such figure as stub.
    """

    seed: int = 0
    model_version: str = "stub-v1"
    #: P(yes) is rounded to this many decimals, as a real client's output would be.
    decimals: int = 4

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

    def p_yes(
        self,
        clause_text: str,
        parent_line: str,
        question: str,
        question_type: str,
    ) -> float:
        self.calls += 1
        return self.inner.p_yes(clause_text, parent_line, question, question_type)


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
