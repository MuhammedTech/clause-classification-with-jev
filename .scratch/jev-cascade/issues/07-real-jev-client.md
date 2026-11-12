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

**Status:** resolved

- [x] The real client satisfies the same interface as the stub, and the pipeline selects between them
      by configuration.
- [x] A smoke run on a handful of Clauses writes real P(yes) values to the cache with the resolved
      model version.
- [x] Rate limiting and retries are in place, and an interrupted run resumes from the cache.
- [x] The key is read from the environment and is ignored by git.
- [x] The official request shape, the price per token and the input limit are recorded with sources in
      the price configuration.

## Comments

**Built (2026-11-12).** `src/jev_cascade/typesafe.py` is the client; `clients.py` picks stub or real;
the CLI takes `--jev stub|real` (default stub). Tests: `tests/test_typesafe_client.py` and
`tests/test_client_selection.py`, all on a fake transport and clock, none reaching the network.

**Confirmed against the official docs** (docs.typesafe.ai, read 2026-11-12), recorded with sources
in `config.py`:

- `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer <key>`, body
  `{model, state, questions: {id: {type: "noul", instructions}}}`; the reply is
  `{model, answers: {id: {type: "noul", noul: <0-1>}}, usage}`. The third-party shape was right.
- **Price: $0.042 per million input tokens, output free**, on the vendor's models page. The ticket-06
  figure stands and is now sourced to the vendor rather than a blog.
- **Input limit: 64k tokens a request and 32k a question** (state plus that one question); 262k with
  an opt-in header the client does not send. Over it: HTTP 400 `max_tokens_exceeded`, which the client
  raises as `ContextTooLong` and does not retry. On the full corpus the largest Clause plus Parent
  Line is about 4.2k estimated tokens (chars over 4), so none comes near 32k.
- **Rate limit: not confirmed.** The vendor says limits are per organization, in tokens and requests
  per second, shown in the developer console. "1,200 a minute" is still third-party and is labelled
  unverified in the report. The client spaces calls to it and backs off on 429/529.

**Decisions that differ from the ticket text:**

- **The model is pinned to `jev-1.14.0`, not sent as `jev-latest`.** The runner keys the cache on
  `model_version` before the first call, and `--from-cache` must not need the network, so the version
  cannot be resolved from a reply. A moved alias would otherwise serve old answers under a new model.
  The reply's `model` is checked against the pin. `jev-1.13.0` in the ticket text is out of date;
  `jev-latest` is 1.14.0 as of 2026-10-14. Moving to a newer version is a one-line config edit and a
  fresh cache.
- The key is read from `JEV_API_KEY` in the environment only, never repr'd or put in an error.
  `.env` was already git-ignored. `--jev real --from-cache` needs no key.
- Only the `binary` question type (sent as `noul`) is supported. Any other raises; ticket 08 adds
  score and choice if it picks one.

**Smoke run.** One tracer document, R1, real Jev: 45 Pairs, 45 calls, 17.7s (about 0.4s a call),
every cache row `jev-1.14.0`, no stub label in the report. A second run made 0 calls, including
`--from-cache` with no key set. Interrupt-and-resume is covered by a test through the runner.

**For ticket 09: the runner is serial.** At about 0.4s a call, 22,700 calls is roughly 2.5 hours, not
the "about 20 minutes" the rate limit alone would give. Reaching 20 minutes needs concurrent calls
in the runner (about 20 in flight), which this ticket did not add; it is a runner change, not a
client one. The cost is unchanged (roughly $0.27). Raised for the user to decide before the real run.
