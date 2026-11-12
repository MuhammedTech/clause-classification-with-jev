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

**Status:** ready-for-agent

- [ ] The corpus loads exactly 53 documents including Pacira, and the report states the filter and the
      normalisation.
- [ ] A test asserts the three filter counts so the difference stays documented: `Document Name` gives
      53, `Filename` gives 44, JSON `title` gives 44.
- [ ] A test asserts all 429 span offsets across the seven Rules land exactly on their answer text,
      and that none contains `<omitted>`.
- [ ] A test asserts the per-Rule document and span counts from `docs/cuad-ground-truth.md`.
- [ ] A test asserts `is_impossible` documents carry zero answers, and the loader exposes which
      documents are Certified Negative per Rule.
- [ ] All seven Rules appear in the report with their counts and a passing gate. Uncapped Liability is
      absent; the report says it was dropped and why (ADR-0005).
- [ ] The report notes that R5 and R8 replaced Non-Compete and Volume Restriction, so nobody compares
      them to the old rules.
