# 10: Real Jev client

**What to build:** a real TypeSafe Jev client behind the existing Jev client interface, so swapping it in changes nothing else.

- It sends one question per call, as yes/no, 2-level score or yes/no choice, and returns P(yes).
- It records the exact model version (`jev-latest` resolved to e.g. `jev-1.13.0`).
- It respects the published rate limit (about 1,200 requests per minute) and retries transient errors.
- It reads the key from the environment, never from the repo.
- Confirm the endpoint and request shape against TypeSafe's official docs when the key arrives; third-party sources give POST `/v1/systemone` with a bearer token.

**Blocked by:** 01, and the user providing the Jev key.

**Status:** ready-for-agent (needs the user's Jev key before it can be finished)

- [ ] The real client satisfies the same interface as the stub, and the pipeline selects between them by configuration.
- [ ] A smoke run on a handful of clauses writes real P(yes) values to the cache with the resolved model version.
- [ ] Rate limiting and retries are in place, and an interrupted run resumes from the cache.
- [ ] The key is read from the environment and is ignored by git.
- [ ] The official request shape and the price per token are recorded, with sources, in the price configuration from ticket 07 if it exists by then.
