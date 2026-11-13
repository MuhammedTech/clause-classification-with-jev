# Ask every Rule in one call per Clause

## The decision

Jev is called **once per Clause**, with all seven Rules' Detection Questions in the same request
(the **fan-out**). The Clause and its Parent Line go once as the `state`; each question is sent under
its own id (the Rule id) and answered separately. A full run is **3,246 calls** for **22,722 Pairs**.
The P(yes) cache is unchanged: one row per Pair, and a call writes its Rules' rows together.

Decided by the user on 2026-11-13, before the real run.

## What it replaces

The spec said Jev is called once per (Clause, Rule), "never with two questions in one call", on a
third-party finding that splitting compound questions lifted accuracy from 62.6% to 95% and that
probabilities needed recalibrating per question. That finding is about **one compound question**.
The fan-out does not build one: Jev's API answers each question separately, so each Rule still gets
its own question, wording and P(yes).

## What it costs us, said plainly

- **Ticket 08 is not the same experiment.** The question type, wording and heading were settled on
  one question a call. A probability can move when other questions ride in the same call, and nothing
  measures by how much. The report says so. If a Rule's figures look off, asking that Rule alone is the
  first thing to try (`--rule`), and the cache keeps both.
- **Mixing cache rows is wrong.** Answers from one-question calls and from fan-out calls share a
  cache key. Keep a fan-out run's cache in its own directory (`out/real`), as the README does.
- **The token estimate is now an upper bound.** The cost model still counts the Clause once per
  question, in case Jev bills it that way. The replies carry `usage`, the client adds it up and the
  command prints it, so the real figure is known after the first run.
- **A call is all or nothing.** If one fails, none of its Rules is cached, and a resume asks only the
  Rules still missing for that Clause.

## What it buys

Fewer calls to wait for and to rate-limit: 3,246 rather than 22,722, so the run is bound by Jev's
latency for seven questions a call and not by seven times as many requests. Whether it is also
cheaper depends on how Jev bills the shared Clause, which the first run answers.
