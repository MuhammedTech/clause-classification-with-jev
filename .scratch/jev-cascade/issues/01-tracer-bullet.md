# 01: Tracer bullet: one rule, end to end, on the stub

**What to build:** one command that takes 2–3 real CUAD documents through every stage of the pipeline for R1 (Cap On Liability):

1. Load the documents and their R1 highlights.
2. Split them into Clauses with a simple splitter (numbered and lettered items at line start is enough here).
3. Ask the stub Jev client for P(yes) per Pair and cache every answer to disk.
4. Grade at fixed placeholder cutoffs with the two questions: Found or Missed Highlight, and False Alarm.
5. Write a Markdown report with one R1 table, counts first.

This ticket also sets up the Python project (uv, pytest) and the module skeleton from the spec: Corpus, Splitter, Rulebook, Jev client with a stub, Jev runner, Evaluator, Report. Every later ticket deepens something that already runs end to end. See `.scratch/jev-cascade/spec.md` and `GLOSSARY.md`.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The project installs with uv and runs tests with pytest.
- [ ] One command produces a Markdown report with an R1 table showing highlights found, highlights missed, False Alarms and kept/escalated counts.
- [ ] The Jev client is an interface. The stub returns deterministic, seeded P(yes) values.
- [ ] P(yes) results are cached as JSONL keyed by document, unit, rule, sub-question, question type and model version.
- [ ] A second run makes zero client calls.
- [ ] A run interrupted midway resumes from the cache.
- [ ] An Evaluator test with a hand-made document shows a highlight touching one clause kept as "yes" is found, and kept as "no" is missed.
- [ ] An Evaluator test shows a kept "yes" on a clause touching no highlight is a False Alarm.
- [ ] An end-to-end test (Seam C) runs the command on 2–3 real documents with the stub, checks that the report exists with the R1 table, and checks that a rerun makes no client calls.
