# Grade with recall and precision on one cutoff, reported as a curve

**Supersedes ADR-0002.** This reverses two of its decisions deliberately: it introduces the
per-clause label that ADR-0002 refused, and it drops the 5-fold cross-fitting and the second cutoff
that ADR-0002 introduced. ADR-0002's own first paragraph also still described a miss budget in
"present pairs" while its second paragraph said "highlights", so its numbers were not usable as
written.

## The decision

**One cutoff per rule, not two.** A clause whose P(yes) is at or below the cutoff is **Binned**:
discarded, and nobody reads it again. Above the cutoff it is **Escalated** to the expensive model. We
act only on Jev's "no", because under 1% of clauses are relevant to any one rule, so nearly all of
the saving sits on the discard side; because a bare "yes" is not a finished review answer; and
because a wrong "no" destroys a provision permanently while a wrong "yes" only wastes reading.

**Per-clause labels from character overlap.** A clause *holds* a highlight when their character
ranges overlap by one character or more. No threshold, no word minimum. This is the label precision
needs, and it is safe to use because all 429 span offsets in the corpus are exact (see
`docs/cuad-ground-truth.md`).

**Three numbers per rule, each with its counts:**

- **Clause Recall** — of clauses that hold a highlight, the share Escalated. The standard metric.
- **Provision Recall** — of highlights, the share with at least one holding clause Escalated. Always
  at least Clause Recall; they diverge only on the ~3% of highlights spanning several clauses. This is
  the one that answers whether a lawyer would still see the provision.
- **Precision** — of Escalated clauses, the share that hold a highlight.

Plus **Binned Share**, the share of contract *words* Binned, which is the saving. It is a volume, not
an accuracy, and neither recall nor precision says anything about it.

**No tuned operating point.** Report the whole curve: one row per observed P(yes), since the piles
only change when the cutoff crosses a score Jev actually gave. Any single figure quoted off that curve
was chosen after seeing it and must be labelled as such.

**A separate false-alarm rate on certified-negative documents.** A clause holding nothing is either a
*Certified Negative*, where CUAD flags the whole document as having no such clause, or an *Inferred
Negative*, where the document has spans elsewhere. The certified share ranges from 54% of negatives
for Minimum Commitment down to 5% for Anti-Assignment. So report, separately from precision, the share
of clauses Jev Escalates inside certified-negative documents. That number rests on nothing but CUAD's
explicit negatives. If it broadly agrees with the full-corpus precision, the inferred negatives are
sound.

## Why

The two-cutoff design could not be made to work. The cutoffs were tuned independently, so on rules Jev
separates well the lower cutoff rises above the upper one and a band of scores has no defined outcome.
The upper cutoff's rule, "lowest value whose false alarms are within 20% of kept yes", is not monotone
in the cutoff and can land on a fluke point; requiring the budget to hold at every higher value instead
fails outright whenever the top-scoring clause is a false alarm, which a 1% base rate makes likely, and
then nothing is ever kept. The 5% miss budget is also an integer budget: on a thin rule's tuning folds
it allows zero misses at 19 highlights and one at 20, so the cutoff jumps between two scores on fold
composition alone.

Reporting the curve removes all of that, because nothing is fitted. Cross-fitting exists to make a
*tuned* number honest; with no tuning there is nothing to hold out.

## Consequences

- Folds, fold stratification, the fold seed and the cross-fitting machinery are all gone.
- False Alarm as the old spec defined it is gone, along with kept-"yes" precision. Precision now
  measures wasted reading by the expensive model, not wrong final answers.
- Reading precision at a low cutoff and calling it Jev's accuracy would be wrong. Around 0.5 the curve
  gives the ordinary classifier reading; at the low end it gives the cascade reading, where precision
  is low by design. Report both ends and name which is which.
- Accuracy and ROC AUC must not be reported: at a 1% base rate, answering no to everything scores 99%
  accuracy and ROC AUC flatters rare problems the same way. Use the precision-recall curve and, if one
  summary number is wanted, average precision.
- Per-rule Binned Share does not combine into a saving. A clause is only genuinely free when every
  rule Binned it, so the share Binned by all seven at once is a separate measurement and is the only
  one that becomes money.
- Confidence intervals become optional. If wanted, resample whole documents with replacement and
  recompute; whole contracts move together because clauses within one are not independent.

## Considered and rejected

- **Two cutoffs, acting on confident "yes" answers too.** Rejected for a proof of concept: it buys a
  few hundred clauses against thousands on the discard side, and a bare yes is not a finished answer.
  Worth reopening for a rule that is near-universal boilerplate, where Anti-Assignment at 40 of 53
  documents is the likeliest candidate.
- **A high cutoff, escalating only confident hits.** Rejected because everything not escalated is
  destroyed, so demanding confidence before escalating loses provisions wholesale.
- **Per-clause gold labels with overlap thresholds**, as ADR-0002 rejected them. Still rejected. The
  one-character rule needs no threshold and the thresholds depended on the splitter.
