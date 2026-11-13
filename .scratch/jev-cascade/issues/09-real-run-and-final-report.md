# 09: Real run and final report

**What to build:** the actual result. Run the real Jev client, with the question type and heading
setting chosen in ticket 08, on every Clause for all seven Rules. Rebuild the full report from the
cache.

Expected size: 3,246 Clauses, each sent once with all seven Rules' questions in the same call (the
fan-out, ADR-0006, decided 2026-11-13): **3,246 calls** for 22,722 Pairs, at most about $0.27 at the
published price. Superseded: the original text said 3,244 Clauses by 7 Rules, 22,708 calls, about
20 minutes and $0.20.

The gate was settled in ticket 02 from CUAD span counts, which do not depend on the splitter, so there
is nothing to re-check here and no backup Rule to swap in.

**Blocked by:** 05, 06, 08.

**Status:** resolved

- [x] Every (Clause, Rule) has a real P(yes) in the cache, tagged with the resolved model version.
- [x] The final report is generated from the cache by the single command, with real timings and the
      real Jev price.
- [x] No figure anywhere is still labelled as stub.
- [x] The report states the stub-to-real switch, the model version, the question type, the heading
      setting and the run date.
- [x] The report's per-Rule headline is the lowest P(yes) given to a held Clause and the Binned Share
      achievable below it, beside the Fully Binned Clause share and the net savings.

## Comments

**From ticket 11.** The runner is concurrent now, so `uv run jev-cascade --jev real` already uses 32
calls in flight, measured at 18.5 requests a second, about 20 minutes for the full run. Real Jev is
not exactly repeatable (up to 0.04 between runs on the same Pair, no decision flipping at 0.5), so say
in the final report that it is reproducible from the cache, not from scratch.

## Answer

Run on 2026-11-13 with `uv run jev-cascade --jev real --full --out out/real`, after the user chose the
fan-out (ADR-0006) and approved the paid run. The report is rebuilt from the cache with
`uv run jev-cascade --jev real --full --out out/real --from-cache` (0 calls, 0.01 s).

- 22,722 Pairs (3,246 Clauses by 7 Rules) in **3,246 calls**, 179 s, none retried. Every cache row is
  tagged `jev-1.14.0` and `binary`; P(yes) runs from 0.01 to 0.99.
- Jev reported **2,019,752 input tokens**, 31.5% of the 6,419,682 estimated: the shared Clause is billed
  about once a call. $0.085 at the published price. Check it against the TypeSafe invoice.
- The report opens with "From the stub to the real Jev", states the model version, question type,
  heading setting, run date and the time Jev was asking, and says it is reproducible from the cache,
  not from scratch. The word stub appears only in that section.
- Summary per Rule: lowest P(yes) of a holding Clause and the Binned Share below it (R3 96.1%, R1 83.7%,
  R7 74.1%, R5 70.8%, R2 67.2%, R8 60.1%, R6 32.5%), beside the Fully Binned Clause share (77.3%) and the
  net savings per 1,000 Clauses ($7.451 against Sonnet 5.5, $14.985 against Opus 5.5).
- Not measured: how far the fan-out moved probabilities against the one-question calls ticket 08 used.
  If a Rule looks off, `--rule` asks it alone.

**Code review (Standards and Spec), settled in the follow-up commit.** Fixed: the report still called
ticket 08's questions "drafted and awaiting the user's review" and "settled" (now approved and
settled, with a test); the net-savings paragraph now says Jev's part is the cautious estimate, so the
savings are if anything understated; `cli.py` import order; one over-long `config.py` line.

Left alone, as judgement calls: the `p_yes_many` fallback in `ask_many` and `FanOutAnswers(dict)` stay
(an old-client path costs little and `ask_many` is the single place that decides); `PairKey` indexing,
`read_cache_with_stamps`'s three parallel dicts and `_Ground`'s string kinds are a refactor for
`/improve-codebase-architecture`, not this ticket. Known and harmless: `timing.answers` counts distinct
millisecond stamps, so it is 12 under the 3,246 calls (about 0.4% on the Jev wall-clock figure); and
`--rule R1` rebuilt from the fan-out cache would set a whole call's reported tokens against a one-Rule
estimate, so read the billed ratio only on the full run. A few other added lines run past 100
columns; no tooling enforces it.

### Afterwards, same day: reading the result, and what is still open

**An explainer page** for a reader new to the project: what "77% Binned" means, recall and precision
with the real counts, an interactive Cutoff, how the result was checked, and where to be careful.
Private artifact https://claude.ai/artifact/3Cg59wmFZPDAt4cSS8P5xX; the file is
`out/real/results-explained.html` (git-ignored, like all of `out/`).

**Not in the report, computed for the page** from `out/real/pyes.jsonl` with throwaway scripts (not kept
in the repo): one Cutoff applied to all seven Rules at once, Fully Binned Clauses against provisions
lost, out of 3,246 Clauses and 429 Highlights.

| Cutoff | Fully Binned Clauses | Highlights lost |
| --- | --- | --- |
| 0.03 | 2 (0.1%) | 0 |
| 0.04 | 39 | 3 |
| 0.10 | 876 | 11 |
| 0.20 | 1,833 (56.5%) | 15 (3.5%) |
| 0.30 | 2,160 | 24 |
| 0.50 | 2,510 (77.3%) | 44 (10.3%) |
| 0.70 | 2,676 | 70 |
| 0.90 | 2,959 | 148 |

- **The 77.3% costs 10.3% of the Highlights.** At 0.5 the 44 lost are R1 4, R2 4, R3 2, R5 2, R6 18,
  R7 8, R8 6. Losing nothing across all seven Rules needs a Cutoff of 0.03 or lower, because R6's lowest
  held P(yes) is 0.04, and then only 2 Clauses are skipped. The report prints per-Rule free savings and
  the Fully Binned share at 0.5, but not this joint trade-off; it is the figure a reader needs to choose
  a Cutoff.
- **Some misses and false alarms are the answer key, not Jev.** Among R1's lowest-scoring held Clauses (of the
  short ones; I did not rank the long ones) are a "Warranty Period" (0.23) and a "Limitation Period" (0.25), which lawyers highlighted under Cap On
  Liability. A false alarm at 0.97 is "IN NO EVENT WILL CHANGEPOINT BE LIABLE FOR SPECIAL, INCIDENTAL,
  INDIRECT, OR CONSEQUENTIAL LOSS…", which does limit liability and carries no Highlight. So recall is
  probably understated in places and precision understated in others. Not quantified.
- **Recount.** The counts for all seven Rules (the four boxes, 2,510 Fully Binned, 44 lost, 429
  Highlights) were rebuilt from the raw cache and CUAD and match the report. The recount reuses the
  repo's splitter and overlap rule, so it checks the arithmetic and not the splitter.

**Open, none of it blocking this ticket**

- Fan-out against one question a call is **unmeasured**. Cheapest test: `--rule R6` into a separate
  `--out` directory (the caches must not be mixed, ADR-0006), then compare P(yes) per Pair.
- The TypeSafe invoice for 2026-11-13 has not been compared with the measured $0.085.
- The expensive model was never run, so "Escalated" is not shown to find anything, and the dollar savings
  are token estimates (characters over 4, assumed output length). Sample some Escalated and some Binned
  Clauses through it.
- Only 53 license agreements; nothing says it holds on other CUAD contract types.
- A lawyer's look at about 30 false alarms and 30 misses would say how much of the error is label noise.
- R6 (Minimum Commitment) recall is 60% at 0.5 and R7 (Change Of Control) 75%; the other five are
  92 to 94%. Decide whether to keep R6 and R7 in the Rulebook or ask them differently.
- The report does not yet print the joint Cutoff trade-off above.
