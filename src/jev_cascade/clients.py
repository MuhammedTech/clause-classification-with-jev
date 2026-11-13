"""Chooses the Jev client for a run: the stub or the real TypeSafe client.

Selection is configuration (the `--jev` option), and everything downstream sees only the
`JevClient` interface, so swapping one for the other changes nothing else.
"""

from __future__ import annotations

import os
from typing import Mapping

from .jev import CacheOnlyJevClient, JevClient, StubJevClient
from .typesafe import API_KEY_ENV, JevAuthError, TypeSafeJevClient

KINDS = ("stub", "real")

#: Calls in flight when `--workers` is not given. The real client waits on the network, and under
#: load a call took about a second, so it needs a wide window to reach its request limit
#: (1,200 a minute is 20 a second). Measured on 432 real Pairs on 2026-11-13: 16 workers gave 15.2
#: requests a second, 32 gave 18.5, neither drew a single 429. The stub answers instantly, so
#: concurrency would only reorder its cache.
DEFAULT_REAL_WORKERS = 32


def default_workers(kind: str) -> int:
    return DEFAULT_REAL_WORKERS if kind == "real" else 1


def build_client(
    kind: str = "stub",
    seed: int = 0,
    from_cache: bool = False,
    environ: Mapping[str, str] | None = None,
) -> JevClient:
    """The client for this run.

    `from_cache` wraps it so it can only be served from the cache. For the real client that needs
    **no key**, because the model version it lends is pinned in configuration rather than asked of
    the network: rebuilding a report must not need credentials or reach out.
    """
    environ = os.environ if environ is None else environ
    if kind == "stub":
        client: JevClient = StubJevClient(seed=seed)
    elif kind == "real":
        key = environ.get(API_KEY_ENV, "").strip()
        if key:
            client = TypeSafeJevClient(api_key=key)
        elif from_cache:
            client = TypeSafeJevClient(api_key="")
        else:
            raise JevAuthError(
                f"{API_KEY_ENV} is not set. Put the Jev key in the environment (a git-ignored "
                ".env file loaded into the shell works); it is never read from the repo."
            )
    else:
        raise ValueError(f"unknown Jev client {kind!r}; choose one of {', '.join(KINDS)}")
    return CacheOnlyJevClient(client) if from_cache else client
