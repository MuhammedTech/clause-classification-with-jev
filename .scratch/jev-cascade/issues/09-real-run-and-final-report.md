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
