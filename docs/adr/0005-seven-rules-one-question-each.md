# Seven rules, one question each

## The decision

The Rulebook holds **seven** Rules, each mapped to one CUAD category and asked as **one** positively
phrased Detection Question. No sub-questions.

| Rule | CUAD category | Detection Question |
| --- | --- | --- |
| R1 | Cap On Liability | Does this clause cap or limit a party's liability? |
| R2 | Post-Termination Services | Does this clause require help or obligations after termination? |
| R3 | Termination For Convenience | Does this clause let a party terminate without cause? |
| R5 | Exclusivity | Does this clause grant or require exclusivity? |
| R6 | Minimum Commitment | Does this clause commit a party to a minimum purchase, payment or volume? |
| R7 | Change Of Control | Does this clause give a right or trigger on a change of control? |
| R8 | Anti-Assignment | Does this clause restrict assigning or transferring the agreement? |

Numbering keeps the gap at R4 so these ids stay comparable with the earlier notes. The wording above
was **approved by the user on 2026-11-13** (ticket 08), as drafted, with no edits.

Every question is positive, so a high P(yes) always means Jev thinks the Clause is relevant. Outside
testing reports that a yes/no question whose true answer means "no" is answered worse.

## Why R4 is dropped

> **Corrected 2026-11-12 — see the note at the bottom.** Two of the three arguments in this section
> are withdrawn. The gate argument no longer holds: on all 53 documents Uncapped Liability measures
> 17 documents and 26 spans and passes. Being compound does not discriminate either, since R2 and R6
> were also compound and both survive. The independence argument stands, and is the only standing
> reason.

Uncapped Liability is the only rule that fails the gate of at least 15 documents with a span and at
least 25 spans: measured, **16 documents and 23 spans** on this corpus. It is also not independent of
R1, because uncapped liability appears in these contracts as a carve-out from a cap, so the two rules
mark overlapping text and cannot be read separately. It was also one of the three compound rules.
Dropping it removes the thinnest rule, the co-occurrence reporting requirement, and a third of the
sub-question work at once.

Neither backup is needed. For the record, both would have passed: Audit Rights at 28 documents and 86
spans, IP Ownership Assignment at 16 and 45.

## Why sub-questions go

R2, R4 and R6 were to be asked as several sub-questions with the Rule's P(yes) taken as the maximum.
That cannot be calibrated: each Rule maps to one CUAD category, so no sub-question-level highlight
exists to score against. Under or-semantics the maximum also understates the probability of the union,
so a compound Rule reads as under-confident for a reason that has nothing to do with Jev.

The cost is real and should be stated in the report: third-party testing found splitting a compound
question lifted accuracy substantially, so R2 and R6 are being asked a blunter question than they
could be. If a later run shows those two trailing, splitting them is the first thing to try.

## Consequences

- Seven Jev calls per Clause rather than eight-plus. Measured, **22,708 calls** over the corpus, about
  20 minutes at the published rate limit.
- R5 and R8 changed meaning from the original notes: Exclusivity replaced Non-Compete and
  Anti-Assignment replaced Volume Restriction, both because the originals had too few documents. The
  report must say so, so nobody compares them to the old rules.
- The gate is settled here, at corpus-loading time, from CUAD span counts. Those counts do not depend
  on the splitter, so there is no need to re-check the gate after the real run.
- The rules that survive were chosen partly for having clean definitions, which will make results read
  optimistically. The report must say that too.

## Correction, 2026-11-12: Uncapped Liability passes the gate

Measured by the ticket 02 corpus loader over all 53 documents, **Uncapped Liability is 17 documents
and 26 spans**, one span above the gate. The 16 and 23 recorded above were measured before Pacira
joined the corpus — it joins only once the filename-to-title comparison normalises `A&R` against
`A_R` — and Pacira carries **3** Uncapped Liability spans, which is the whole of the difference
between 23 and 26. (It also carries 35 spans across the seven Rulebook rules, and 83 across all 41
CUAD categories, but those are not what moved this row.)

**The decision does not change.** R4 stays out on the second argument above, which the new counts do
not touch: uncapped liability appears in these contracts as a carve-out from an R1 cap, so the two
rules mark overlapping text and cannot be read separately.

Being compound is **not** a reason to single R4 out, and should not be cited as one: R2 and R6 were
also to be asked as sub-questions and both survive. Dropping R4 removed a third of the sub-question
work, which is a consequence of the decision, not a ground for it. Independence is the only argument
that distinguishes R4 from the rules that stayed.

**The first argument must not be repeated.** "The only rule failing the gate" is now false, and
calling it that in the report would be a measured claim contradicted by the data. The report prints
R4's real counts beside the reason instead. Also corrected: the backups read 29 / 92 and 17 / 52, and
the seven Rulebook rules read as in the table in `docs/cuad-ground-truth.md`.

If the user wants R4 back, the gate no longer blocks it; the independence problem and ticket 08's
wording work are what to weigh.

## Amended 2026-11-14: R6 is dropped too

After the real run, **Minimum Commitment (R6) was removed**, knowing how it performed and with no
lawyer or further data to check its labels. The Rulebook now holds six Rules, and the table above is
the Rule set that was agreed, not the one now asked. See
[ADR-0008](0008-minimum-commitment-dropped-after-the-real-run.md), which says plainly that this departs
from the agreement and makes the six-Rule figures more favourable than a Rule set fixed in advance.
The title of this ADR is left as it was, since the other ADRs and the glossary link to its file name.
