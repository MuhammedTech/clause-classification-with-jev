# 08: Question wording review and two small pre-run checks

**What to build:** settle how Jev is asked, before spending the real run.

1. **Wording review (human checkpoint).** Present the drafted wording of all seven Detection Questions
   to the user. Stop until they approve or edit it. The drafts are in ADR-0005.

2. **Question type.** Ask a small sample as Jev's yes/no type, a 2-level score, and a yes/no choice.
   Pick **one** type for all Rules on **separation per Rule only** — how well P(yes) ranks Clauses that
   hold a Highlight above those that do not. Do not pick on Binned Share or Precision: the sample is
   small and deliberately enriched with held Clauses, so its base rate is wrong and those figures do
   not transfer.

3. **Heading context, on or off.** ADR-0004 leaves this open deliberately. Run the same sample with
   the section heading included as Parent Line and excluded, and compare separation. A heading gives
   real context on a genuine liability cap and also stamps the section label onto every unrelated
   Clause beneath it.

Both checks are cheap: a few hundred calls against 22,708 for the full run.

**Blocked by:** 02, 07.

**Status:** resolved

- [x] The user has approved the final wording, and the Rulebook holds it.
- [x] Sample results are cached like any other run.
- [x] A short report compares the three question types by separation per Rule, with counts, and states
      the chosen type.
- [x] The same report compares heading context on against off, and states the choice.
- [x] The pipeline's question type and heading setting are both read from configuration, set from this
      ticket's outcome.
- [x] The final report discloses that both choices were made on Pairs that are later scored, a small
      selection leak.

## Comments

**2026-11-12, from ticket 03.** The heading-in / heading-out comparison this ticket asks for cannot
be run until ticket 10 is fixed: the P(yes) cache key does not include the Parent Line, so the two
arms of that comparison collide in the cache and the second is served the first's answers. See
`10-cache-key-ignores-the-parent-line.md`.

**Done (2026-11-13).** The user approved the seven Detection Questions **exactly as ADR-0005 drafted
them**, no edits. Nothing in the Rulebook changed except its docstring.

**Outcome: `binary`, heading context on. Both are what the configuration already held, so no
pipeline behaviour changes.** Full tables, counts and intervals are in
`docs/question-type-and-heading-sample.md`, rebuildable from `out/sample/pyes.jsonl` with
`jev-cascade-sample --jev real --from-cache`.

| | Mean separation, 7 Rules |
| --- | --- |
| `binary`, heading on | 0.980 |
| `score2`, heading on | 0.973 |
| `choice2`, heading on | 0.973 |
| `binary`, heading off | 0.980 |

The decision rule was fixed in `sample_study.py` before any real call: highest mean separation, a type
must beat `binary` by 0.02, and the heading comes out only if that gains 0.02. Neither threshold was
met. 1,357 real calls, `jev-1.14.0`, about 100 seconds, a few cents.

**Read this before trusting "no difference".** Every Rule scored at least 0.938 in every arm, so the
sample is near its ceiling and has little room to separate anything. `choice2` was a hair below
`binary` (interval -0.016 to -0.000), `score2` indistinguishable. The heading check moved nothing:
only 97 of the 420 sampled Clauses have a heading Parent Line, and the sample holds only 40 near misses
in all, because few not-held Clauses share a heading with a held one under a four-per-document cap.
The harm ADR-0004 worried about, a section label stamped on unrelated Clauses, would show over the
full corpus's many unrelated Clauses, which separation on a held-enriched sample does not measure. If
ticket 09 shows a Rule with many unexpected escalations under a heading, heading off is the first
thing to try, and it is a one-line config change plus a fresh cache.

**Decisions that differ from the ticket text:**

- **"Heading" is a section heading, not every Parent Line.** ADR-0004 and this ticket are about the
  heading. A Parent Line can also be a lead-in ("10.1 Licensee shall:"), and blanking those would test
  something else. The Splitter now records which it is (`Clause.parent_is_heading`, true for a single
  short label after a marker with no colon, the Splitter's own heading test); only those are taken out.
- **Separation is a new Evaluator figure** (`evaluator.separation`, glossary entry added): the chance a
  holding Clause outscores a non-holding one, ties half. Real Jev answers cluster, so ties are counted.
- **The two other types are `score2` and `choice2`, with minimal criteria** (`["No", "Yes"]` and
  `{"yes": null, "no": null}`) and the approved question as `instructions`, word for word, so the type
  is the only thing that varies. The criteria text is not in the cache key, so the type id carries it:
  changing the criteria means a new id. `binary` keeps its id, so ticket 11's cached real answers
  still serve.
- **Near-miss negatives.** Half the not-held Clauses sit under a held Clause's heading. Plain random
  negatives are boilerplate every type scores near zero on.

**Added:** `sample_study.py`, `sample_report.py`, `sample_cli.py` (`jev-cascade-sample`); the pipeline's
report gains a "How Jev is asked" section with the selection-leak disclosure; `run_pairs` and
`pipeline.run` take `question_type` and `heading_context`, defaulting to `config`. No type checker is
configured in `pyproject.toml`, so none was run; the full test suite was.
