# 01: Tracer bullet: one rule, end to end, on the stub

**What to build:** one command that takes 2–3 real CUAD documents through every stage for R1 (Cap On
Liability):

1. Load the documents and their R1 Highlights.
2. Partition them into Clauses with a simple splitter (line-start markers is enough here).
3. Ask the stub Jev client for P(yes) per Pair and cache every answer to disk.
4. Label each Clause as holding an R1 Highlight or not, from character overlap.
5. At one fixed Cutoff, report Clause Recall, Precision, Lost Provisions and Binned Share.
6. Write a Markdown report with one R1 table, counts first.

This also sets up the Python project (uv, pytest) and the module skeleton from the spec: Corpus,
Splitter, Rulebook, Jev client with a stub, Jev runner, Evaluator, Report. Every later ticket deepens
something that already runs end to end. See `.scratch/jev-cascade/spec.md`, `GLOSSARY.md` and
ADR-0003.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The project installs with uv and runs tests with pytest.
- [ ] One command produces a Markdown report with an R1 table showing Clause Recall, Precision, Lost
      Provisions and Binned Share, each beside its counts.
- [ ] The Jev client is an interface. The stub returns deterministic, seeded P(yes) values.
- [ ] P(yes) results are cached as JSONL keyed by document, Clause, Rule, question type and model
      version.
- [ ] A second run makes zero client calls, and a run interrupted midway resumes from the cache.
- [ ] An Evaluator test on a hand-made document shows a Clause overlapping a Highlight by one
      character holds it, and a Clause overlapping none does not.
- [ ] An Evaluator test shows a Highlight whose only holding Clause is Binned is a Lost Provision.
- [ ] An end-to-end test (Seam C) runs the command on 2–3 real documents with the stub, checks the
      report exists with the R1 table, and checks a rerun makes no client calls.
