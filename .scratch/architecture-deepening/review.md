# Architecture review: deepening candidates (parked)

Date: 2026-11-13. Produced by `/improve-codebase-architecture` on `src/jev_cascade` (19 modules, ~5.3k
lines) at the end of ticket 09. **Parked, not started.** The visual report is saved beside this file as
`architecture-review.html`.

## Next step

Take candidates **2 then 1** into `/grill-with-docs` as one design thread. Candidate 1 builds on the
usage seam from candidate 2, so settle that seam once. If it is a multi-session build: `/to-spec`, then
`/to-tickets` (2 blocks 1), then `/implement` per ticket. Start from a fresh branch off `main`, not from
the tracer-bullet branch. No interfaces are proposed here on purpose; that is the grilling's job.

Opening question for the grill: do retries and token usage belong in the one `JevClient` interface, or
should the answer cache own usage?

## Candidates

Terms follow `/codebase-design` (module, interface, depth, seam, adapter, leverage, locality) and
`GLOSSARY.md`. Line numbers were read at commit `9a54cc4`.

### 1. Deepen the answer cache: one owner for "what Jev was shown" (Strong, local-substitutable)

- Files: `runner.py` (`PairKey`:43, `_key`:115, `_call_id`:127, `read_cache_with_stamps`:141, `_row`:199,
  `_billed_tokens`:228, `run_pairs`:238-386), `typesafe.py`:194, `jev.py`:113, `cost.py`:101.
- Friction: `PairKey` is a 7-tuple read by magic index (`key[0],key[1],key[2],key[6]` at `runner.py`:129
  and :293). A call is rebuilt from rows by matching `asked_at` stamps. Four modules each define the text
  Jev is shown (runner key, typesafe wire text, jev stub hash, cost token count). Question wording and
  call shape are not in the key; ADR-0006's "mixing cache rows is wrong" is prose only. This is the
  ticket-10 bug class (cache key ignores the Parent Line) waiting to recur.
- Deeper module: one cache module that owns key, row format, read/write, per-call grouping, timing and
  billed usage, with `run_pairs` left as scheduling. The shown text, wording and call shape are defined
  once; both the adapter's request and the cache identity derive from that.
- Tests: ticket-10 and fan-out cache cases in `test_runner.py` move to the cache interface; add one test
  that everything the adapter sends is covered by the key. Concurrency tests stay on the scheduler.
- ADR: none; reinforces ADR-0006 and the one-row-per-Pair cache.

### 2. Give JevClient one head: ask several questions, get answers plus usage (Strong, ports and adapters)

- Files: `jev.py` (`JevClient`:21-42, `ask_many`:57-75, `FanOutAnswers`:45, wrappers:141-264),
  `typesafe.py`:160-171, `cli.py`:95-117, `runner.py`:326.
- Friction: the Protocol declares only `p_yes`, but the runner goes through `ask_many`, which finds
  `p_yes_many` with `getattr` (`jev.py`:69). `p_yes` survives for test fakes written before the fan-out
  (`test_runner.py`:230, 247, 413; `test_runner_concurrent.py`:47). Every wrapper and the stub carry both
  shapes. Usage rides on a `dict` subclass read with `getattr(answers, "input_tokens")`
  (`runner.py`:326); the CLI unwraps `.inner` with `getattr` (`cli.py`:101, 114), which ticket 11
  flagged.
- Deeper module: one interface, "ask one Clause several questions, get answers plus usage", with retry
  and usage telemetry part of it. The single-question path and `getattr` discovery go.
- It is a real seam: two production adapters (stub, TypeSafe over an injected transport) plus the
  cache-only guard.
- Tests: fakes lose their dual method sets; counting, failing and cache-only become one test double or
  hook instead of three copies.
- ADR: none; ADR-0006 describes the fan-out as the call shape.

### 3. Build the scored corpus once (Worth exploring, in-process)

- Files: `pipeline.py`:116-138, 173-178, 205-208; `sample_cli.py`:58-61, 107-120; `partition.py`:133.
- Friction: `run()` loads the corpus three times and splits it twice more (once in `partition_facts`).
  Per-Rule highlight filtering appears three times and `certified_by_rule` is hand-built although
  `Document` has `highlights_for` and `is_certified_negative`. The `without_heading` toggle is applied
  separately in `pipeline.run` and `sample_study.run_arm`.
- Deeper module: a loaded and split corpus (documents, Clauses, per-Rule highlights, Certified Negative
  sets, heading setting) built once and handed to pipeline, cost sizing, partition facts and the study.

### 4. One owner for Binned, Escalated and "holds" (Worth exploring, in-process)

- Files: `evaluator.py`:124, 158, 281, 288, 331, 371; `cost.py`:144; `sample_study.py`:127;
  `pipeline.py`:145-169.
- Friction: the Binned test is written in three places (`_at_cutoff`, `fully_binned`, `cost_usage`);
  "holds" in four. `cost_usage` recomputes the Fully Binned Clauses the evaluator already computes, and
  the report prints both. Callers pass the same five inputs to `evaluate_rule`, `cutoff_curve` and
  `free_saving`, each rebuilding ground truth. `free_saving`'s `math.nextafter` trick depends on the
  "at or below" rule living elsewhere. Inputs are assembled in `pipeline.py`, invisible to the pure
  functions' tests.
- Deeper module: a per-Rule evaluation taking Clauses, Highlights, P(yes) and certified documents once,
  owning the Binned and held definitions; cost consumes its Escalated sets.
- Tests: the six `test_evaluator_*.py` files plus `test_curve`/`test_gate` go through one interface; add
  one test that cost and evaluator agree on the Fully Binned count. Enforces ADR-0003 definitions.

### 5. Share the run shell and the billing arithmetic (Speculative, in-process)

- `cli.py`:120-175 vs `sample_cli.py`:143-168 repeat the CUAD check, workers check, `build_client` and
  the `JevCallRefused`/`JevError` messages. Tokens-to-dollars at Jev's price is computed in `cli.py`:116,
  `report.py`:~445 and `cost.py` `_dollars`. Do after candidate 2; it depends on that telemetry seam.

### 6. Keep or archive the sample_* trio (Speculative, not a deepening)

- `sample_study.py`:159-187, `sample_cli.py`, `sample_report.py` (~700 lines plus three test files).
  Ticket 08 is resolved and its outputs live in config constants, but the trio is still a shipped
  command (`pyproject.toml`:12). `run_arm` calls `run_pairs` once per Rule, so it bypasses the fan-out;
  a separate cache directory is the only guard against ADR-0006's mixing hazard. Deletion test: removing
  it concentrates nothing. Decide as a scope question. The report duplication with `report.py` is
  weaker than it looks: they share an idiom, not logic.

## Checked and fine: do not churn

- `splitter.py`: one public `split_document`, four ordered passes behind it. The many `test_splitter*`
  files are topic splits, not leakage.
- `TypeSafeJevClient`: retry, pacing, model pin, usage and reply validation behind one method;
  transport, clock and sleep injected, so tests use a fake transport.
- `report.render(ReportInputs)`: pure, one-function interface; long but local.
- No test imports an underscore name, so the friction is in the source modules, not the tests.

## Confidence

The survey sub-agent read in full: `runner`, `jev`, `clients`, `typesafe`, `pipeline`, `cli`,
`sample_cli`, `sample_study`, `evaluator`, `cost`, `config`, `domain`, `partition`, tickets 10 and 11 and
`GLOSSARY.md`. It only skimmed `report`, `sample_report`, `splitter`, `corpus` and the ADRs, did not
read `charts` or `rulebook`, and read tests by grep, not by body. Candidates touching those are less
certain. The tuple indexing, `getattr` discovery, repeated corpus loads and the repeated Binned test were
re-checked against the source.
