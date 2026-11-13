# Clause Classification with Jev

Measures how much contract-review work Jev, a cheap decision model, can take off an expensive model,
and how accurate it is against lawyer labels, per rule, on CUAD license agreements.

Decisions behind this vocabulary: [ADR-0001](docs/adr/0001-jev-only-evaluation.md) (Jev only),
[ADR-0003](docs/adr/0003-recall-precision-on-one-cutoff.md) (how grading works),
[ADR-0004](docs/adr/0004-document-partition-into-clauses.md) (what a Clause is),
[ADR-0005](docs/adr/0005-seven-rules-one-question-each.md) (the Rulebook). Measured facts about the
data are in [docs/cuad-ground-truth.md](docs/cuad-ground-truth.md).

## Language

### Corpus

**License Agreement Set**:
The 53 CUAD v1 documents whose CSV `Document Name` contains "licen". Joining them to the annotation
JSON needs the filename compared on alphanumerics only, which is what matches Pacira's "A&R" to its
"A_R".
_Avoid_: license docs, the 52, the 44 (the 44 is the `Filename` column, a different filter)

**Clause**:
A numbered or lettered item of a contract (`1.`, `1.1`, `(a)`), the unit every judgement is made on.
Clauses **partition** the document: every character belongs to exactly one.
_Avoid_: chunk, window, segment, passage

**Word Ceiling**:
The most words a Clause may hold: **600**, so a Clause of exactly 600 stands and one of 601 is split.
A Clause over it is split again at paragraph breaks, then line breaks, sentence ends and word breaks,
until none exceeds it. Words are counted by whitespace, the same count the Binned Share uses.
_Avoid_: max chunk size, token limit, length cap

**Highlight**:
A span of contract text a CUAD lawyer marked as an instance of a CUAD category. The only ground truth
there is.
_Avoid_: annotation, answer, span

**Parent Line**:
The introductory line a Clause sits under ("Licensee commits to:"), or its section heading. Shown to
Jev as context, never used in grading. One level only. It is the item one level up, never a sibling,
and it is empty when the numbering gives no parent: a numbered item after a gap (`7.2` with no `7.`
above it) takes none rather than naming the wrong section. The pieces of a split Clause keep the whole
Clause's Parent Line.
_Avoid_: lead-in, header, intro, stem

### Rules and labels

**Rule**:
One of the Rulebook's seven detection questions about a Clause, each mapped to one CUAD category.
_Avoid_: check, criterion, category (when meaning the rule)

**Rulebook**:
The fixed set of seven Rules the experiment scores.

**Gate**:
The minimum ground truth a Rule needs to be worth asking: at least 15 documents carrying a
Highlight and at least 25 Highlights in total. Counted from CUAD annotations, never from the
Splitter, so it is settled once when the Corpus loads and never re-checked after a run.
_Avoid_: threshold (which means a Cutoff), sanity check, viability test

**Detection Question**:
The single positively phrased yes/no question asked of a Clause for one Rule. Positive phrasing means
a high P(yes) always means "relevant".
_Avoid_: compliance question, verdict, sub-question

**Holds**:
A Clause holds a Highlight when their character ranges overlap by one character or more. Pure
arithmetic, no threshold.
_Avoid_: touch, overlap threshold, present, contains

**Certified Negative**:
A Clause holding nothing, in a document CUAD flags `is_impossible` for that Rule, meaning lawyers
checked and the contract has no such clause anywhere. A verified negative.

**Inferred Negative**:
A Clause holding nothing, in a document that does have Highlights for that Rule elsewhere. Strong
evidence, resting on the annotators having been exhaustive within the document.

**Compliance Reading**:
A document-level interpretation against the licensee's position ("has a non-compete, so violates R5");
outside the scored experiment.

### Jev

**Jev**:
A decision model that, given a question and a fixed answer set, returns one answer with a probability.
_Avoid_: classifier, the model, LLM

**P(yes)**:
The probability Jev returns that a Clause's Detection Question is answered yes.
_Avoid_: confidence, score, certainty

**Question type**:
The form Jev is asked a Detection Question in, one for every Rule: `binary` (Jev's yes/no type),
`score2` (a two-level score, No then Yes) or `choice2` (a choice between yes and no). The same
question as a different type gives different P(yes), so the type is part of the cache key. Ticket 08
chose `binary`.
_Avoid_: prompt style, mode, format

**Heading context**:
Whether Jev is shown a section heading as the Parent Line. Only a **standalone** heading (a single
short label after its marker, no colon) is taken out when this is off. A Parent Line that introduces a
list ("Licensee shall:") and a longer line with body text on it are shown either way. Over the corpus
that is 459 of the 1,269 Parent Lines. Ticket 08 left it on.
_Avoid_: header, title context

**Held**:
Said of a Clause in the ticket 08 sample tables: it holds at least one Highlight of the Rule. **Not
held** means it holds none, whether or not its document is a Certified Negative.
_Avoid_: positive, relevant

**Near miss**:
A not-held Clause that sits under the same section heading as a held Clause. Ticket 08 draws them on
purpose, because plain not-held Clauses are mostly boilerplate that every question type scores near
zero, and because they are where a heading can mislead Jev.
_Avoid_: hard negative, decoy

**Heading-affected Clause**:
A Clause whose Parent Line is a standalone section heading: the only kind the heading setting can
change.

**Arm**:
One way of asking in the ticket 08 sample: a question type and a heading setting.
_Avoid_: variant, condition

**Separation**:
For one Rule, the chance that a Clause holding a Highlight scores a higher P(yes) than one that does
not, drawn at random, with a tie counting half. 1.0 ranks every holding Clause above every other, 0.5
is a coin. It needs no Cutoff and does not depend on the base rate, so ticket 08 can read it on a
sample enriched with holding Clauses where Binned Share and Precision would not transfer.
_Avoid_: AUC (in prose), accuracy, discrimination

### Cascade

**Pair**:
One Clause judged against one Rule; the unit every outcome is counted on.

**Cutoff**:
The P(yes) at or below which a Clause is Binned. One per Rule. In plain speech, "the line". It is a
discard-risk threshold, **not** a yes/no threshold: a Clause just above it is a weak "no" we do not
trust enough to act on.
_Avoid_: threshold (in prose), gate, lower cutoff, upper cutoff

**Binned**:
A Pair whose P(yes) is at or below the Cutoff. The Clause is discarded and nobody reads it again. The
only place work is saved.
_Avoid_: kept, skipped, cleared, accepted

**Escalated**:
A Pair above the Cutoff, so the Clause goes to the expensive model. Being Escalated is not a detection;
it means Jev could not rule the Clause out.
_Avoid_: kept, routed, deferred, flagged

**Binned Share**:
The share of contract **words** Binned for a Rule. The saving, measured in text rather than unit count
so it does not depend on where the splitter cuts.
_Avoid_: keep share, coverage, automation rate

**Fully Binned Clause**:
A Clause Binned for every Rule, so the expensive model is never called on it. The only figure that
turns into money; per-Rule Binned Share does not combine into it.
_Avoid_: fully cleared clause

**Lost Provision**:
A Highlight whose every holding Clause was Binned, so nobody will ever look at it. The only failure
the evaluation counts as permanent.
_Avoid_: missed highlight, miss, false negative (in prose), leak

**Clause Recall**:
Of Clauses that hold a Highlight for a Rule, the share Escalated.

**Provision Recall**:
Of Highlights for a Rule, the share with at least one holding Clause Escalated. Always at least Clause
Recall; the two diverge only on the ~3% of Highlights spanning several Clauses.

**Precision**:
Of Clauses Escalated for a Rule, the share that hold a Highlight. Measures the expensive model's
wasted reading, not wrong final answers. At a ~1% base rate it reads in single digits by arithmetic.
_Avoid_: false positive rate, accuracy

**Free Saving**:
The share of contract words Binned strictly below the lowest P(yes) Jev gave to any Clause holding a
Highlight, per Rule. No Highlight is Lost there, so it costs nothing. It is read off the Cutoff Curve
after seeing it, so it is a headline and never a tuned Cutoff.
_Avoid_: safe cutoff, optimal cutoff, operating point

**Classifier Reading / Cascade Reading**:
The two ways to read the Cutoff Curve. The classifier reading is around a Cutoff of 0.5, where
P(yes) is taken as a yes/no answer and Recall and Precision mean what they usually do. The cascade
reading is at the low end, just under the Free Saving point, where nearly everything is Escalated and
Precision is low by design. Quoting Precision at a low Cutoff as Jev's accuracy would be wrong.

**Cutoff Curve**:
The table of Clause Recall, Provision Recall, Precision, Lost Provisions and Binned Share at every
observed P(yes) for a Rule. The result of the experiment. Nothing is fitted, so nothing can overfit.
_Avoid_: operating point, tuned cutoff, ROC

## Retired terms

These appear in `docs/adr/0002-*` and in older notes. They are gone, and two of them inverted, so do
not reuse them.

| Retired | Why |
| --- | --- |
| Lower Cutoff / Upper Cutoff | One Cutoff now; see ADR-0003 |
| Kept / Keep Share | **Inverted.** "Kept" used to mean Jev's answer stands and the text is discarded. That is now **Binned**, and "Escalated" is its opposite |
| Found Highlight / Pending Highlight | No longer distinguished; a Highlight is either Lost or it is not |
| False Alarm | Replaced by Precision, plus the false-alarm rate on Certified Negative documents |
| Fold | No cross-fitting, because nothing is tuned |
| Miss Rate | Use Lost Provisions with its count, or Provision Recall |
| Fully Cleared Clause | Renamed Fully Binned Clause to match Binned |
| Touch | Renamed Holds |
| Lead-in | Renamed Parent Line, and the lead-in touch rule is dropped (ADR-0004) |
| Sub-question | Dropped; one question per Rule (ADR-0005) |
| Uncapped Liability / R4 | Dropped as not independent of R1 (ADR-0005). It was dropped for failing the gate, but on all 53 documents it passes at 17 documents and 26 Highlights; see the correction note in ADR-0005 |
