# 07: Real Jev client

**What to build:** a real TypeSafe Jev client behind the existing interface, so swapping it in changes
nothing else.

- One question per call, returning P(yes).
- Records the exact model version (`jev-latest` resolved to e.g. `jev-1.13.0`).
- Respects the published rate limit (about 1,200 requests per minute) and retries transient errors.
- Reads the key from the environment, never from the repo.
- Confirm the endpoint and request shape against TypeSafe's official docs when the key arrives;
  third-party sources give POST `/v1/systemone` with a bearer token.
- Record Jev's **real** published price and its input limit, and correct the configuration from
  ticket 06. The current $0.042 per million input tokens is unverified, and the real input limit is
  unknown, which matters because a Clause plus its Parent Line can be long.

**Blocked by:** 01, and the user providing the Jev key.

**Status:** ready-for-agent (needs the user's Jev key before it can be finished)

- [ ] The real client satisfies the same interface as the stub, and the pipeline selects between them
      by configuration.
- [ ] A smoke run on a handful of Clauses writes real P(yes) values to the cache with the resolved
      model version.
- [ ] Rate limiting and retries are in place, and an interrupted run resumes from the cache.
- [ ] The key is read from the environment and is ignored by git.
- [ ] The official request shape, the price per token and the input limit are recorded with sources in
      the price configuration.
