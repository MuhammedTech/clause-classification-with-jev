# 5-fold document cross-fitting and derived gold labels

> **Status: superseded by [ADR-0003](0003-recall-precision-on-one-cutoff.md).** Kept as a record of
> what was tried. Do not implement from this file. Three things in it are now reversed: there *is* a
> per-clause label, there is only one cutoff, and there is no cross-fitting because nothing is tuned.
> The first paragraph below is also internally inconsistent with the second, describing the miss
> budget as a share of "present pairs" and the gate in "present clauses" where the rest of the design
> counted highlights. ADR-0003 explains why each was dropped.

The notes planned one 50/50 split by document; on the 53-document License Agreement Set that leaves 5–9 present documents per half for most rules, so a per-rule cutoff tuned on one half is noise. We use 5-fold cross-fitting by document instead, with documents assigned to folds stratified so every fold holds a fair share of each rule's present documents (a random assignment left one fold with zero R4 documents): each fold is reported with per-rule cutoffs tuned on the other four. Jev returns P(yes), so each rule gets two cutoffs: the lower cutoff is the highest value keeping misses ≤ 5% of present pairs, and the upper cutoff is the lowest value keeping false alarms ≤ 20% of kept "yes" answers, because a miss is far costlier than a false alarm, the folds are pooled, and intervals come from a bootstrap over documents. Rules must have ≥ 15 present documents and ≥ 25 present clauses, which is why Non-Compete and Volume Restriction were replaced by Exclusivity and Anti-Assignment.

There is no per-clause gold label. Grading asks two questions against the lawyers' highlights: a highlight is found if any clause it touches (shares any text with, or sits directly under a highlighted lead-in) is kept as "yes", and missed only if every touching clause is kept as "no"; a clause kept as "yes" is a false alarm only if it touches no highlight. Misses are counted per highlight, false alarms per clause, and keep share in tokens, so the conclusions do not hinge on where the splitter cuts or on overlap thresholds. The miss budget is ≤ 5% of highlights missed. A rerun on plain 120-word chunks is reported as a splitter-sensitivity check; a keyword dry run showed it moves R8 by 11 highlights, so clauses stay the unit.

## Considered Options

- 50/50 split: rejected, too few report documents for thin rules.
- Per-clause gold labels with overlap thresholds (min 5 words, half the clause): rejected, the thresholds are arbitrary, depend on the splitter, and charge extra misses when one highlight spans several clauses (39 of 455 highlights in a dry run).
