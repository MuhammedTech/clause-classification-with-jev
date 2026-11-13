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

**Status:** ready-for-agent

- [ ] Every (Clause, Rule) has a real P(yes) in the cache, tagged with the resolved model version.
- [ ] The final report is generated from the cache by the single command, with real timings and the
      real Jev price.
- [ ] No figure anywhere is still labelled as stub.
- [ ] The report states the stub-to-real switch, the model version, the question type, the heading
      setting and the run date.
- [ ] The report's per-Rule headline is the lowest P(yes) given to a held Clause and the Binned Share
      achievable below it, beside the Fully Binned Clause share and the net savings.

## Comments

**From ticket 11.** The runner is concurrent now, so `uv run jev-cascade --jev real` already uses 32
calls in flight, measured at 18.5 requests a second, about 20 minutes for the full run. Real Jev is
not exactly repeatable (up to 0.04 between runs on the same Pair, no decision flipping at 0.5), so say
in the final report that it is reproducible from the cache, not from scratch.
