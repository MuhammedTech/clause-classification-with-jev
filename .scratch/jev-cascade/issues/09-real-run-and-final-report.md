# 09: Real run and final report

**What to build:** the actual result. Run the real Jev client, with the question type and heading
setting chosen in ticket 08, on every Clause for all seven Rules. Rebuild the full report from the
cache.

Expected size: 3,244 Clauses by 7 Rules is 22,708 calls, about 20 minutes at the published rate limit
and roughly $0.20 at the unverified price. The Clause count will move once the oversized split from
ticket 03 is in.

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
