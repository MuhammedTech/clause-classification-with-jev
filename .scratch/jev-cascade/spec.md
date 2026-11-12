Status: ready-for-agent

# Spec: Jev cascade on CUAD license agreements

Supersedes the original 63-story version of this file. The method changed substantially; see
ADR-0003, ADR-0004 and ADR-0005 for the decisions and why the old ones were dropped. Measured facts
about the corpus are in `docs/cuad-ground-truth.md` and should not be re-derived.

## Problem statement

Reviewing contracts clause by clause with a strong LLM is expensive. Jev is a cheap decision model
that answers one typed question about a clause with a probability. I want to know, per rule, how much
of the contract text Jev could take off the expensive model by discarding it on its own, and what that
costs in provisions nobody would ever look at, judged against lawyer highlights rather than against
another model.

## The method in one paragraph

Partition each of 53 contracts into Clauses. Ask Jev one question per (Clause, Rule) and cache every
P(yes). Label each Clause from CUAD's highlight offsets: it either holds a Highlight for that Rule or
it does not. Then sweep one Cutoff per Rule across every observed P(yes), and at each one report Clause
Recall, Provision Recall, Precision, Lost Provisions and Binned Share. Nothing is tuned, so nothing
can overfit, and the output is a curve rather than a single number.

## What is measured

Per Rule, at every observed P(yes), each figure printed with its counts:

- **Clause Recall** — of Clauses holding a Highlight, the share Escalated.
- **Provision Recall** — of Highlights, the share with at least one holding Clause Escalated.
- **Precision** — of Escalated Clauses, the share holding a Highlight.
- **Lost Provisions** — Highlights whose every holding Clause was Binned.
- **Binned Share** — the share of contract words Binned.

Plus, separately:

- **False-alarm rate on Certified Negative documents** — the share of Clauses Escalated inside
  documents CUAD flags as having no such clause. Bulletproof, because that text certainly holds
  nothing. If it agrees with full-corpus Precision, the Inferred Negatives are sound.
- **Fully Binned Clause share** — Clauses Binned by all seven Rules. The only figure that becomes
  money, and it cannot be derived from the per-Rule numbers.
- **The lowest P(yes) Jev gave to a Clause holding a Highlight**, per Rule, with the Binned Share
  achievable below it. This is the free-saving figure and the single most useful number in the report.
- **Estimated savings and wall-clock time**, from token counts at list prices. No expensive model runs.

Not measured, and the report says so: whether Jev's confident yes answers are trustworthy (we never
act on a yes), whether the expensive model would actually find a provision once its Clause is
Escalated, and whether the lawyers highlighted everything.

## Implementation decisions

- **Language and tooling:** Python with uv and pytest.
- **Corpus** loads the 53 documents, filtering CSV `Document Name` on "licen" and joining to the JSON
  on filename compared as alphanumerics only. It owns the Rulebook gate check, which runs off CUAD
  span counts and so does not depend on the splitter.
- **Splitter** partitions one document into Clauses per ADR-0004, splitting oversized Clauses at
  paragraph breaks until all are under the word ceiling. Each Clause carries its span, word count and
  immediate Parent Line.
- **Rulebook** holds the seven Rules per ADR-0005: id, CUAD category and one Detection Question.
- **Jev client** is an interface taking a Clause with its Parent Line, a question and a question type,
  returning P(yes). A deterministic seeded stub first, the real HTTP client later.
- **Jev runner** asks every (Clause, Rule) and appends to a JSONL cache keyed by document, Clause,
  Rule, question type and model version. It skips cached keys, resumes after interruption, and records
  wall-clock time.
- **Evaluator** is pure: given Clauses, Highlights and the P(yes) table it returns the per-Rule curve
  and the separate figures above. No folds, no tuning, no randomness.
- **Report** renders the Evaluator's output to Markdown plus PNG charts, rebuildable from the cache
  with no network.
- Jev is called once per (Clause, Rule), never with two questions in one call.
- Prices live in one configuration place, each with a source and a date. Jev's $0.042 per million
  input tokens is from one unverified blog and must be confirmed.

## Testing decisions

Good tests check behaviour at a seam, with inputs and expected outputs a person can verify by hand.

- **Seam A, the Evaluator**, is the main seam. Tiny hand-made documents with chosen P(yes) values,
  asserting the per-Rule results. Required cases: one-character overlap counts as holding; a Highlight
  across three Clauses is Lost only when all three are Binned; Provision Recall exceeds Clause Recall
  on that case; Precision counts Escalated Clauses; Binned Share counts words not Clauses; a Fully
  Binned Clause needs every Rule Binned; the curve has one row per distinct P(yes); Certified Negative
  documents are separated from Inferred ones.
- **Seam B, the Splitter.** Every character lands in exactly one Clause, no Clause exceeds the word
  ceiling, opening text becomes its own Clause, trailing text joins the item above, a heading's words
  go to the first Clause beneath it. Corpus-wide, report the share of Highlights inside one Clause.
- **Seam C, end to end.** The command runs on two or three real documents with the stub and produces
  the expected report sections; a second run makes no client calls.
- Facts in `docs/cuad-ground-truth.md` become assertions in the Corpus tests, not scripts.

## Out of scope

- Running any strong LLM. Savings are estimated, not measured.
- Compliance Readings and any licensee-facing verdict.
- Auditing or correcting the lawyers' highlights. CUAD already ran a completeness sweep to
  convergence; see `docs/cuad-ground-truth.md`.
- Contract types outside the License Agreement Set, and CUAD categories outside the Rulebook.
- Fine-tuning, prompt optimisation beyond the wording review, recalibrating Jev's probabilities.
- Acting on a confident yes, cross-fitting, calibration charts, the plain-chunk sensitivity rerun, and
  document-bootstrap intervals. All dropped or deferred; intervals are the cheapest to add back.
- Any user interface. The output is a report.

## Further notes

- The Jev key comes from the user. Everything runs on the stub until then.
- The whole run is 22,722 Jev calls (3,246 Clauses × 7 Rules), about 19 minutes and roughly $0.27.
  Ticket 06 re-derived the cost with the Parent Lines counted: about 6.4 million input tokens, an
  estimate at 4 characters a token. The earlier $0.20 predates them.
- Third-party findings worth citing: tuned cutoffs matter a lot (Arize); 34.7% escalation for Jev
  against 2.7% for Haiku (wotai.co); splitting compound questions lifted accuracy from 62.6% to 95%
  and probabilities needed recalibrating per question (Beri); the same question asked as different
  types gave very different probabilities. Also TypeSafe's documented prompt-injection limitation, and
  that its calibration evaluations were self-run.
