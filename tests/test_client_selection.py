"""Which Jev client a run uses is configuration, and rebuilding from the cache never needs a key."""

from __future__ import annotations

import pytest

from jev_cascade.clients import build_client
from jev_cascade.jev import CacheOnlyJevClient, JevCallRefused, StubJevClient
from jev_cascade.typesafe import JevAuthError, TypeSafeJevClient


def test_stub_is_the_default_and_takes_its_seed():
    client = build_client("stub", seed=7, environ={})

    assert isinstance(client, StubJevClient)
    assert client.seed == 7


def test_real_reads_the_key_from_the_environment():
    client = build_client("real", environ={"JEV_API_KEY": "sk-from-env"})

    assert isinstance(client, TypeSafeJevClient)
    assert client.is_stub is False
    assert "sk-from-env" not in repr(client)


def test_real_without_a_key_says_where_to_put_it():
    with pytest.raises(JevAuthError, match="JEV_API_KEY"):
        build_client("real", environ={})


def test_rebuilding_from_the_cache_needs_no_key_and_cannot_ask_jev():
    client = build_client("real", from_cache=True, environ={})

    assert isinstance(client, CacheOnlyJevClient)
    # It lends the pinned model version, so the cache keys line up with a real run's.
    assert client.model_version == TypeSafeJevClient(api_key="x").model_version
    assert client.is_stub is False
    with pytest.raises(JevCallRefused):
        client.p_yes("clause", "parent", "question?", "binary")


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="gpt"):
        build_client("gpt", environ={})
