# Clause Classification with Jev

Measures how much contract-review work Jev, a decision model, can take off an expensive model, and how accurate it is against lawyer labels, per rule, on CUAD license agreements.

## Language

### Corpus

**License Agreement Set**:
The 53 CUAD v1 documents whose CSV `Document Name` contains "licen", including Pacira (whose name differs between the CSV and the JSON).
_Avoid_: license docs, the 52, the 44

**Clause**:
A numbered or lettered item of a contract (`1.`, `1.1`, `(a)`), the unit every judgement is made on.
_Avoid_: chunk, window, segment, passage

**Highlight**:
A span of contract text a CUAD lawyer marked as an instance of a CUAD category.
_Avoid_: annotation, answer, span

### Rules and labels

**Rule**:
One of the rulebook's detection questions about a clause, each mapped to one CUAD category.
_Avoid_: check, criterion, category (when meaning the rule)

**Rulebook**:
The fixed set of rules the experiment scores.

**Detection Question**:
The yes/no question asked of a clause for one rule: "does this clause contain X?"
_Avoid_: compliance question, verdict

**Present**:
A clause is present for a rule when a highlight of that rule's category overlaps it, or when it sits directly under a lead-in whose only highlight is that lead-in; this is the gold label, derived from offsets rather than labelled by a lawyer per clause.
_Avoid_: positive (in prose), match, hit

**Lead-in**:
The introductory line of a clause that has lettered or numbered items under it ("Licensee commits to:").
_Avoid_: header, intro, stem

**Compliance Reading**:
A document-level interpretation of detections against the licensee's position (e.g. "has a non-compete → violates R5"); outside the scored experiment.

### Jev

**Jev**:
A decision model that, given a question and a fixed answer set, returns one answer with a probability.
_Avoid_: classifier, the model, LLM

**P(yes)**:
The probability Jev returns that a pair's detection question is answered yes.
_Avoid_: confidence, score, certainty

### Cascade

**Pair**:
One clause judged against one rule; the unit every outcome is counted on.

**Lower Cutoff**:
The P(yes) at or below which Jev's "no" for a rule is kept; it governs misses.
_Avoid_: threshold (in prose), gate

**Upper Cutoff**:
The P(yes) at or above which Jev's "yes" for a rule is kept; it governs false alarms.
_Avoid_: threshold (in prose), gate

**Kept**:
A pair whose P(yes) is at or below the lower cutoff or at or above the upper cutoff, so Jev's answer stands and the expensive model never sees it.
_Avoid_: accepted, auto-decided

**Escalated**:
A pair whose P(yes) lies between the two cutoffs, so it would go to the expensive model; never scored for accuracy.
_Avoid_: routed, deferred, abstained

**Fully Cleared Clause**:
A clause whose pairs are kept for every rule, so the expensive model would never be called on it.

**Keep Share**:
Kept pairs as a share of all pairs for a rule; the work Jev takes off the expensive model.
_Avoid_: coverage, automation rate

**Catch**:
A kept pair where Jev says yes and the clause is present.
_Avoid_: true positive (in prose), hit

**Miss**:
A kept pair where Jev says no but the clause is present; a problem nobody will look at.
_Avoid_: false negative (in prose), leak

**False Alarm**:
A kept pair where Jev says yes but the clause is not present.
_Avoid_: false positive (in prose)

**Clear**:
A kept pair where Jev says no and the clause is not present.
_Avoid_: true negative (in prose)

**Miss Rate**:
Misses as a share of all present pairs for a rule, kept or escalated.

**Fold**:
One of five fixed groups of documents; a fold is always reported with a cutoff tuned on the other four.
_Avoid_: split, half
