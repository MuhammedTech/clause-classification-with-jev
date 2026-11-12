"""The real Jev client: TypeSafe's System One endpoint behind the `JevClient` interface.

One Detection Question per call, asked as a `noul` question, which returns the probability of yes.
Jev is shown the Parent Line and the Clause text as its `state`, Parent Line first.

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
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from . import config

#: The environment variable the key is read from. It is never read from the repo.
API_KEY_ENV = "JEV_API_KEY"

#: What the client sends for each question type the runner can ask. Ticket 08 adds the others.
_QUESTION_TYPES = {"binary": "noul"}

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
    _next_call_at: float = field(default=0.0, init=False, repr=False)

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
        try:
            jev_type = _QUESTION_TYPES[question_type]
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
                "questions": {_QUESTION_ID: {"type": jev_type, "instructions": question}},
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
            return float(reply["answers"][_QUESTION_ID]["noul"])
        except (KeyError, TypeError, ValueError) as error:
            raise JevError(f"unexpected reply shape from Jev: {str(reply)[:200]}") from error

    def _pace(self) -> None:
        """Wait, if need be, so calls start at least one interval apart."""
        interval = 60.0 / self.requests_per_minute
        now = self.clock()
        if self._next_call_at > now:
            self.sleep(self._next_call_at - now)
            now = self._next_call_at
        self._next_call_at = now + interval

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
                continue

            if status == 200:
                try:
                    return json.loads(payload)
                except ValueError:  # a cut-off body: JSON or UTF-8 decoding failed
                    last = "HTTP 200 with a body that is not JSON"
                    continue
            text = payload.decode("utf-8", errors="replace")[:200]
            if status in _RETRYABLE_STATUSES or status >= 500:
                last = f"HTTP {status}"
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
