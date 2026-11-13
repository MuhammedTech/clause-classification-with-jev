"""The real Jev client: TypeSafe's System One endpoint behind the `JevClient` interface.

Every Detection Question about a Clause goes in **one call** (`p_yes_many`), each asked as a `noul`
question, which returns the probability of yes. Jev is shown the Parent Line and the Clause text as
its `state`, Parent Line first, once per call. `p_yes` is the same call with one question in it.

The model is **pinned** (`config.JEV_MODEL`), never `jev-latest`. The runner reads
`model_version` once, before the first call, and keys every cached answer on it, so the client has
to know it without asking the network, and `--from-cache` must never need one. The reply's `model`
field is checked against the pin, so a server that answers with a different model is an error
rather than a silently mixed cache.

The network, the clock and the sleep are injected so the tests never touch TypeSafe. The default
transport is stdlib `urllib`: no new dependency.
"""

from __future__ import annotations

import http.client
import json
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Mapping

from . import config

#: The environment variable the key is read from. It is never read from the repo.
API_KEY_ENV = "JEV_API_KEY"

def _read_noul(answer: dict) -> float:
    return float(answer["noul"])


def _read_score_top(answer: dict) -> float:
    return float(answer["probabilities"]["1"])


def _read_choice_yes(answer: dict) -> float:
    return float(answer["probabilities"]["yes"])


@dataclass(frozen=True)
class _QuestionType:
    """How one question type is sent, and where P(yes) is read from in its answer."""

    #: The fields beside `instructions` in the question object, if any.
    extra: dict
    #: The `type` field.
    jev_type: str
    read: Callable[[dict], float]


#: What the client sends for each question type the runner can ask. The type's id is the cache
#: key's only record of this wording, so **changing a `criteria` here means giving the type a new
#: id**, or old answers would be served to the new question. The instruction is the Rule's approved
#: Detection Question, word for word, in all three, so the type is the only thing that varies.
#:
#: - `binary`: Jev's yes/no type. P(yes) is its one number.
#: - `score2`: a two-level score, `No` then `Yes`. P(yes) is the probability of level 1.
#: - `choice2`: a choice between `yes` and `no`, with no option descriptions. P(yes) is the
#:   probability of `yes`.
_QUESTION_TYPES = {
    "binary": _QuestionType({}, "noul", _read_noul),
    "score2": _QuestionType({"criteria": ["No", "Yes"]}, "score", _read_score_top),
    "choice2": _QuestionType({"criteria": {"yes": None, "no": None}}, "choice", _read_choice_yes),
}

#: The id the one question goes under in the request, and is read back from in the reply.
_QUESTION_ID = "q"

#: Statuses worth another try: request timeout, rate limited (429), and server errors including the
#: vendor's 529 "overloaded".
_RETRYABLE_STATUSES = {408, 429}

#: `transport(url, headers, body, timeout) -> (status, body)`. It raises `OSError` when the
#: connection fails or times out, and returns any HTTP status, error statuses included.
Transport = Callable[[str, dict, bytes, float], "tuple[int, bytes]"]


class JevError(RuntimeError):
    """Base for everything the real client refuses to continue past."""


class JevAuthError(JevError):
    """The key is missing or rejected (HTTP 401). Retrying cannot help."""


class JevRequestRejected(JevError):
    """TypeSafe rejected the request itself (HTTP 400/413/415/422). Retrying cannot help."""


class ContextTooLong(JevRequestRejected):
    """The Parent Line plus Clause plus question is longer than the model's context length."""


class JevUnavailable(JevError):
    """Still failing after every retry: rate limited, overloaded, a server error or no network."""


class ModelMismatch(JevError):
    """The reply came from a different model than the one the cache key says."""


def urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except urllib.error.URLError as error:
        raise OSError(str(error.reason)) from error


@dataclass
class TypeSafeJevClient:
    """Jev over HTTP. See the module docstring."""

    #: Never shown in a repr or an error message.
    api_key: str = field(repr=False)
    model: str = str(config.JEV_MODEL.value)
    endpoint: str = str(config.JEV_ENDPOINT.value)
    transport: Transport = urllib_transport
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    timeout: float = 60.0
    #: Spaces calls so the run stays under this. The figure is third-party (see `config`): the
    #: official docs say only that limits are per organization and shown in the console.
    requests_per_minute: float = float(config.JEV_RATE_LIMIT_PER_MINUTE.value)
    #: Tries per call, the first included, before giving up on a transient failure.
    max_attempts: int = 6
    #: The first backoff wait, doubled on each later retry and capped at `max_backoff`.
    backoff: float = 1.0
    max_backoff: float = 30.0
    #: Retries so far, by what caused them (`"429"`, `"529"`, `"connection"`, ...). The run prints
    #: it, because the real rate limit is unverified and a 429 is how it would show.
    retries: Counter = field(default_factory=Counter, init=False, repr=False, compare=False)
    #: Input tokens the replies' `usage` reported, over every call this client made. The run prints
    #: it, since the token estimate behind the cost figures is a guess at characters a token.
    input_tokens: int = field(default=0, init=False, repr=False, compare=False)
    _next_call_at: float = field(default=0.0, init=False, repr=False)
    #: Guards `_next_call_at` and `retries`: the runner may call `p_yes` from several threads.
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False, compare=False
    )

    @property
    def model_version(self) -> str:
        return self.model

    @property
    def is_stub(self) -> bool:
        return False

    def p_yes(
        self,
        clause_text: str,
        parent_line: str,
        question: str,
        question_type: str,
    ) -> float:
        """One question about one Clause: the fan-out with a single question in it."""
        answers = self.p_yes_many(
            clause_text, parent_line, {_QUESTION_ID: question}, question_type
        )
        return answers[_QUESTION_ID]

    def p_yes_many(
        self,
        clause_text: str,
        parent_line: str,
        questions: Mapping[str, str],
        question_type: str,
    ) -> dict[str, float]:
        """Every question about one Clause in a single request, each answered under its own id.

        The Clause goes once, as the `state`; each question is sent and answered separately, so
        the answers are per question and not one answer to a compound question. A question the
        reply leaves unanswered is an error, never a zero.
        """
        try:
            spec = _QUESTION_TYPES[question_type]
        except KeyError:
            raise ValueError(
                f"question type {question_type!r} is not supported by the real client yet; "
                f"known: {', '.join(sorted(_QUESTION_TYPES))}"
            ) from None

        state = f"{parent_line}\n\n{clause_text}" if parent_line else clause_text
        body = json.dumps(
            {
                "model": self.model,
                "state": state,
                "questions": {
                    question_id: {
                        "type": spec.jev_type,
                        "instructions": question,
                        **spec.extra,
                    }
                    for question_id, question in questions.items()
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        reply = self._post(body, headers)
        if reply.get("model") != self.model:
            raise ModelMismatch(
                f"asked {self.model!r} but the reply came from {reply.get('model')!r}"
            )
        try:
            answers = {
                question_id: spec.read(reply["answers"][question_id]) for question_id in questions
            }
        except (KeyError, TypeError, ValueError) as error:
            raise JevError(f"unexpected reply shape from Jev: {str(reply)[:200]}") from error
        self._count_usage(reply)
        return answers

    def _count_usage(self, reply: dict) -> None:
        """Add up the input tokens Jev says it billed, so the run can check its price estimate."""
        try:
            tokens = int(reply["usage"]["input_tokens"])
        except (KeyError, TypeError, ValueError):
            return  # a reply with no usage is not an error: the answers are what matter
        with self._lock:
            self.input_tokens += tokens

    def _pace(self) -> None:
        """Wait, if need be, so calls start at least one interval apart, across all threads.

        The slot is **reserved under the lock and slept for outside it**, so concurrent callers are
        handed consecutive slots instead of all taking the same one, and none waits on another's
        sleep.
        """
        interval = 60.0 / self.requests_per_minute
        with self._lock:
            now = self.clock()
            start = max(now, self._next_call_at)
            self._next_call_at = start + interval
        if start > now:
            self.sleep(start - now)

    def _count_retry(self, cause: str, attempt: int) -> None:
        """Count a failure as a retry only if another attempt follows it."""
        if attempt + 1 < self.max_attempts:
            with self._lock:
                self.retries[cause] += 1

    def _post(self, body: bytes, headers: dict) -> dict:
        """One request, retried on transient failures; anything else raises at once."""
        last = "no attempt made"
        for attempt in range(self.max_attempts):
            if attempt:
                self.sleep(min(self.backoff * 2 ** (attempt - 1), self.max_backoff))
            self._pace()
            try:
                status, payload = self.transport(self.endpoint, headers, body, self.timeout)
            except (OSError, http.client.HTTPException) as error:
                # Timeouts, dropped connections and a body cut off mid-read.
                last = f"connection failed: {error!r}"
                self._count_retry("connection", attempt)
                continue

            if status == 200:
                try:
                    return json.loads(payload)
                except ValueError:  # a cut-off body: JSON or UTF-8 decoding failed
                    last = "HTTP 200 with a body that is not JSON"
                    self._count_retry("bad body", attempt)
                    continue
            text = payload.decode("utf-8", errors="replace")[:200]
            if status in _RETRYABLE_STATUSES or status >= 500:
                last = f"HTTP {status}"
                self._count_retry(str(status), attempt)
                continue
            if status == 401:
                raise JevAuthError(f"Jev rejected the key (HTTP 401): {text}")
            if status == 400 and "max_tokens_exceeded" in text:
                raise ContextTooLong(
                    "the Parent Line plus Clause plus question is longer than the model's "
                    f"context length (HTTP 400): {text}"
                )
            raise JevRequestRejected(f"Jev rejected the request (HTTP {status}): {text}")
        raise JevUnavailable(f"Jev still failing after {self.max_attempts} attempts: {last}")
