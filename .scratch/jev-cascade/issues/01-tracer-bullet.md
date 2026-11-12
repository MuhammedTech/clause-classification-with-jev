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

**Status:** resolved

- [x] The project installs with uv and runs tests with pytest.
- [x] One command produces a Markdown report with an R1 table showing Clause Recall, Precision, Lost
      Provisions and Binned Share, each beside its counts.
- [x] The Jev client is an interface. The stub returns deterministic, seeded P(yes) values.
- [x] P(yes) results are cached as JSONL keyed by document, Clause, Rule, question type and model
      version.
- [x] A second run makes zero client calls, and a run interrupted midway resumes from the cache.
- [x] An Evaluator test on a hand-made document shows a Clause overlapping a Highlight by one
      character holds it, and a Clause overlapping none does not.
- [x] An Evaluator test shows a Highlight whose only holding Clause is Binned is a Lost Provision.
- [x] An end-to-end test (Seam C) runs the command on 2–3 real documents with the stub, checks the
      report exists with the R1 table, and checks a rerun makes no client calls.

## Comments

**2026-11-12.** Built on branch `worktree-jev-cascade-01-tracer-bullet` (no remote on this repo).
Every stage of the spec runs end to end for R1 on three real documents with the stub: Corpus,
Splitter, Rulebook, Jev client, Jev runner, Evaluator, Report. **69 tests pass, plus 1 xfail**
handed to ticket 03. Status is `resolved` rather than `ready-for-human`, which
`docs/agents/triage-labels.md` defines as "requires human implementation".

Three findings worth carrying forward.

- **Clauses and Highlights must not be pooled across documents.** The first version compared
  character offsets without comparing documents while evaluating all three documents in one call,
  so a Highlight in one contract was held by any Clause in another whose offsets overlapped. That
  invented six holding relations against four real ones, two of them inside the Certified Negative
  document, and inflated the reported base rate to 3.5%. Corrected it reads 1.2%, which is the order
  `docs/cuad-ground-truth.md` measures for Cap On Liability. Found by code review, not by the tests:
  every Seam A case used a single `doc_id`. There are now tests at both seams.
- **Tracer documents were re-chosen.** The first pick included documents whose pages collapse to a
  single line, where the line-start splitter yields 4 Clauses for a whole contract. The three used
  now (WebMD, Sparkling Spring Water, DataCall) partition sensibly; two carry R1 Highlights and one
  is Certified Negative for R1. See the note appended to ticket 03.
- **The join needed an explicit extension strip.** `os.path.splitext` cuts a title like
  `..._EX-10.B(01)_Content License Agreement` at its last dot and discards most of the name, so only
  3 of 53 documents joined. Stripping a literal `.pdf` / `.txt` suffix resolves all 53, Pacira
  included.

Deliberately left for later tickets: the word ceiling and heading rules (03), the gate and the rest
of the ground-truth assertions (02), the Cutoff Curve, charts and report sections (05), the cost and
time estimate (06), the real HTTP client (07).

Two small liberties, both noted for the reviewer. `corpus.filter_counts()` and its test assert
ticket 02's three filter counts, written here because the join bug above had to be proved; ticket 02
inherits a passing check. And the report prints Provision Recall beside this ticket's four figures,
because Lost Provisions needs the same per-Highlight pass and printing Lost Provisions over
Highlights would have been the retired Miss Rate.
