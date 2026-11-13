# 11: The runner asks one Pair at a time, so the real run would take hours

**What to build:** let the runner keep several Jev calls in flight at once, without changing a single
answer.

At about 0.4 to 1 second a call, 22,700 serial calls is 2.5 to 6 hours, against the "about 20
minutes" the request limit alone would allow. The wait is the network, not the limit.

- `run_pairs(..., workers=N)`: at most N calls outstanding, a new one submitted only as another
  returns. The default of 1 is the old serial behaviour.
- **One writer.** Only the runner's own thread writes the cache, so rows never interleave.
- **A failure keeps what was paid for.** On the first error, or Ctrl-C, stop submitting, wait for the
  calls already in flight (at most N), write the ones that succeeded, then re-raise. Never queue the
  corpus behind a failure.
- A Pair that appears twice is asked once.
- The real client's pacing is shared across threads: a slot is reserved under a lock and slept for
  outside it, so threads get consecutive slots rather than the same one.
- The real client counts its retries by cause, and the command prints them, because the real request
  limit is unverified and a 429 is how a lower one would show.
- `--workers N` on the command. Default 32 for `--jev real`, 1 for the stub.

**Blocked by:** 07.

**Status:** resolved

- [x] A test with a barrier proves N calls are really in flight together (no timing).
- [x] A concurrent run gives the same table and the same set of cache rows as a serial one.
- [x] A failure keeps every answer that returned, does not queue the rest, and the resume asks exactly
      what is missing.
- [x] Threads share one request budget; retries are counted by cause.
- [x] A live run on real Jev, to measure the speed and look for 429s.

## Comments

**Measured on real Jev, 2026-11-13** (432 Pairs: three tracer documents, R1 to R3):

| Workers | Pairs | Seconds | Requests a second | 429 / 529 / other retries |
| --- | --- | --- | --- | --- |
| 1 (serial) | 45 | 47.2 | 1.0 | 0 |
| 16 | 432 | 28.5 | 15.2 | 0 |
| 32 | 432 | 23.4 | 18.5 | 0 |

At 18.5 a second the full 22,700 calls take about 20 minutes, and 32 is the default. The pacer allows
20 a second, so more workers buy little. No 429 appeared at 32 workers, which says the organization's
limit is at least that, not what it is; the console still has the number.

**Jev is not exactly repeatable, and this is not the concurrency.** Two serial runs over the same 45
Pairs differ on 14 of them, by up to 0.010; serial against 16 workers differs on 11, up to 0.020; 16
against 32 workers over 432 Pairs differs on 158, up to 0.040. No Binned or Escalated decision flips
at a Cutoff of 0.5 in any of the three. The cache keeps the first answer a Pair got, so a run is
reproducible from its cache, but a re-run from scratch will not reproduce the report to the last
digit. Worth one sentence in the final report. It matters most to the free saving, which is the
lowest P(yes) among held Clauses, and to a Cutoff placed within about 0.04 of a Clause's P(yes).

**Code review (Standards and Spec).** No hard violations on either axis; the core of `run_pairs`
held up (no double write, no hang, no `KeyError`, one writer). Fixed: a test for a real main-thread
Ctrl-C (it passed, so the drain does what the ticket says); `settle` now writes an answer before it
leaves the in-flight set, so a write error cannot make the drain forget a paid-for call; a call is
counted as a retry only when another attempt follows it (six 429s are five retries); the command
prints the retry count when a run dies of rate limiting, which is when it matters most; the docstring
no longer says "kept", a retired glossary term; function-local imports in the tests moved to the top.

Left alone, as judgement calls:

- `run_pairs` is about 110 lines and `settle` is a closure over five outer names with `nonlocal`.
  Splitting the planning from the scheduler is real but is a refactor of working code; it belongs to
  a later tidy, not this ticket.
- **No shared backoff.** After a 429 each of the 32 threads retries on its own clock. Nothing here
  hit a 429, so there is nothing to tune against; if ticket 09's run does, the fix is a shared
  "cool down until" in the client, and the retry budget (six attempts, about 31s) may need raising.
- `workers=1` runs the call on a pool thread, so Ctrl-C waits for that one call. Output is the same.
- A Pair appearing twice counts the second as a cache hit. The run has no duplicates today.
- `wait` in the drain has no timeout; the real client's own 60s timeout bounds it. A custom client
  with no timeout could block it.
- `getattr(getattr(client, "inner", client), "retries", None)` unwraps one wrapper level, which is as
  many as the command ever stacks.
