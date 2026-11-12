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

**Status:** ready-for-agent (contains a human checkpoint: the user approves the wording first)

- [ ] The user has approved the final wording, and the Rulebook holds it.
- [ ] Sample results are cached like any other run.
- [ ] A short report compares the three question types by separation per Rule, with counts, and states
      the chosen type.
- [ ] The same report compares heading context on against off, and states the choice.
- [ ] The pipeline's question type and heading setting are both read from configuration, set from this
      ticket's outcome.
- [ ] The final report discloses that both choices were made on Pairs that are later scored, a small
      selection leak.

## Comments

**2026-11-12, from ticket 03.** The heading-in / heading-out comparison this ticket asks for cannot
be run until ticket 10 is fixed: the P(yes) cache key does not include the Parent Line, so the two
arms of that comparison collide in the cache and the second is served the first's answers. See
`10-cache-key-ignores-the-parent-line.md`.
