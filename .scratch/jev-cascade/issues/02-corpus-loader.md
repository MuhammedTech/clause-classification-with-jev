# 02: Corpus loader, the full 53 documents, and the Rulebook

**What to build:** the Corpus module and the Rulebook, with the gate settled here for good.

The dataset is **not in this repo**. It is at `~/personal_coding/playground/cuad/CUAD_v1/`. Make the
path configuration, not a constant.

**Corpus.** Filter the CSV on `Document Name` containing "licen", which gives 53 rows. Join each to
`CUAD_v1.json` by comparing `Filename` (extension stripped) to the JSON `title` on **alphanumerics
only, lowercased**. All 53 then resolve. Without that normalisation exactly one fails: Pacira, whose
filename says `A&R` where the title says `A_R`.

**Rulebook.** The seven Rules and their Detection Questions are in ADR-0005. Hold the drafted wording
ready for the user's review in ticket 08.

**Gate.** Compute each Rule's document and span counts from CUAD and show them in the report. These
counts come from CUAD annotations, not from the splitter, so the gate is settled once here and never
re-checked later.

Every number below is already measured in `docs/cuad-ground-truth.md`. Turn them into assertions
rather than re-deriving them.

**Blocked by:** 01.

**Status:** resolved

- [x] The corpus loads exactly 53 documents including Pacira, and the report states the filter and the
      normalisation.
- [x] A test asserts the three filter counts so the difference stays documented: `Document Name` gives
      53, `Filename` gives 44, JSON `title` gives 44.
- [x] A test asserts all 429 span offsets across the seven Rules land exactly on their answer text,
      and that none contains `<omitted>`.
- [x] A test asserts the per-Rule document and span counts from `docs/cuad-ground-truth.md`.
- [x] A test asserts `is_impossible` documents carry zero answers, and the loader exposes which
      documents are Certified Negative per Rule.
- [x] All seven Rules appear in the report with their counts and a passing gate. Uncapped Liability is
      absent; the report says it was dropped and why (ADR-0005).
- [x] The report notes that R5 and R8 replaced Non-Compete and Volume Restriction, so nobody compares
      them to the old rules.

## Comments

**2026-11-12.** Built on branch `worktree-jev-cascade-01-tracer-bullet`, continuing from ticket 01.
**83 tests pass, plus the 1 xfail ticket 01 handed to ticket 03.** The Corpus module now owns the
gate: `gate_counts()` gives each Rule's document count, span count, Certified Negative document ids
and gate result over all 53 documents, and `corpus_facts()` gathers what the report states. Both
count from CUAD annotations only, so nothing here moves when ticket 03 changes the Splitter.

**The gate argument for dropping R4 is no longer true, and the ticket's "turn the measured numbers
into assertions" is what surfaced it.** Measured over all 53 documents, Uncapped Liability is **17
documents and 26 spans** — one span above the gate of 15 and 25. ADR-0005's first reason, that it is
the only Rule to fail, was measured before Pacira joined; Pacira alone carries 35 spans across the
categories, 2 of them Uncapped Liability. R4 stays dropped on ADR-0005's second reason, which the
new counts do not touch: it is not independent of R1, since uncapped liability appears here as a
carve-out from a cap. That is a decision for the user to revisit, not for this ticket.

Corrected in four places rather than restated: `docs/cuad-ground-truth.md` (the whole per-Rule table
is now Pacira-inclusive, with the old figures kept in a "was, without Pacira" column), a dated
correction note in ADR-0005 plus a pointer at the stale paragraph, the retired-terms row in
`GLOSSARY.md`, and the `rulebook.py` docstring and `rule("R4")` error message. The report prints
R4's real counts beside the standing reason, and a Seam C test fails if the words "only Rule
failing" reappear in it.

Other corrections the assertions forced, all now exact rather than floors:

- **Every per-Rule count moved.** R8 is 41/85, R1 34/82, R2 26/76, R5 24/58, R3 22/33, R7 20/44, R6
  17/51 certified 36. The backups, which stay unneeded, read 29/92 and 17/52.
- **R2 gained the most.** 58 spans to 76: Pacira carries 18 Post-Termination Services spans by
  itself.
- **A new invariant catches a silent loader failure.** For every Rule, documents with a span plus
  documents certified as having none is exactly 53. The loader skips a category it cannot find in a
  document's annotations, so without this check a missing category would read as a smaller
  denominator rather than an error.
- **The `is_impossible` test was proving nothing.** The loader returns on `is_impossible` before it
  reads `answers`, so asserting "no Highlights" through it only re-ran its own control flow. It now
  asserts on the raw CUAD records, and over all 510 documents: 20,910 document-category pairs,
  14,208 impossible, every one with zero answers. That is the fact that makes a Certified Negative
  verified.
- **The offset test covers all seven Rules**, exactly 429 spans, zero drift, no `<omitted>`.

Two things in the report worth a reviewer's eye. The run header now says plainly which sections are
corpus-wide and which cover only the documents this run scored, because the gate table reads 53
documents while the tracer run scores 3. And the Detection Questions are printed marked as drafts
awaiting ticket 08, so the report cannot be mistaken for a run on approved wording.

Also fixed in passing: the `corpus.py` docstring still said `full_contract_txt/` "can differ in
whitespace", the claim ticket 01's commit had already corrected in the notes. The real reason to
split the JSON `context` is that it is the string the offsets are measured against and that the
`.txt` set is far too incomplete to use. And `GLOSSARY.md` had no entry for **Gate**, a term the
spec and all nine tickets use; it has one now.

Deliberately not done here: the run still scores R1 on the three tracer documents. Asking all seven
Rules over all 53 documents is ticket 09, and the Splitter is ticket 03.
