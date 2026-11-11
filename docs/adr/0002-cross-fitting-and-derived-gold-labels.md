# 5-fold document cross-fitting and derived gold labels

The notes planned one 50/50 split by document; on the 53-document License Agreement Set that leaves 5–9 present documents per half for most rules, so a per-rule cutoff tuned on one half is noise. We use 5-fold cross-fitting by document instead, with documents assigned to folds stratified so every fold holds a fair share of each rule's present documents (a random assignment left one fold with zero R4 documents): each fold is reported with per-rule cutoffs tuned on the other four. Jev returns P(yes), so each rule gets two cutoffs: the lower cutoff is the highest value keeping misses ≤ 5% of present pairs, and the upper cutoff is the lowest value keeping false alarms ≤ 20% of kept "yes" answers, because a miss is far costlier than a false alarm, the folds are pooled, and intervals come from a bootstrap over documents. Rules must have ≥ 15 present documents and ≥ 25 present clauses, which is why Non-Compete and Volume Restriction were replaced by Exclusivity and Anti-Assignment.

Gold labels are derived from highlight offsets, not labelled per clause: a clause is present when its overlap with a highlight is at least min(5 words, half the highlight) or at least half the clause's own words (the second arm keeps short list items such as "(1) United Kingdom;" inside an exclusivity highlight), and when a highlight covers only a lead-in, the lead-in's direct sub-items are present too. Every lead-in propagation is listed in the report.

## Considered Options

- 50/50 split: rejected, too few report documents for thin rules.
- Strict "any overlap" gold label: rejected, it marks lead-ins present and their substantive sub-items absent, penalising Jev for correct answers.
