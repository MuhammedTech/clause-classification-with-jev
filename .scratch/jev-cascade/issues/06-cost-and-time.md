# 06: Cost and time

**What to build:** "how much could we have saved" and "how fast", per 1,000 Clauses. No expensive
model is ever called.

- **Tokens:** count tokens per Clause, including its Parent Line and the question text. Count output
  tokens for the expensive model too, not only input.
- **Expensive model:** price one call per Clause that is Escalated for at least one Rule, sized to only
  the Escalated questions. Claude Sonnet 5.5 list price, with Opus 5.5 as a second row, each in batch
  and non-batch.
- **Jev:** subtract Jev's cost. Its price is configuration with a source and a date. The current value,
  $0.042 per million input tokens, is from one unverified blog; the whole run is roughly $0.20 at that
  figure.
- **Time:** Jev wall-clock per 1,000 Clauses from the runner's timing. The full run is 22,708 calls,
  about 20 minutes at the published rate limit.

**Blocked by:** 04.

**Status:** ready-for-agent

- [ ] An Evaluator test shows the cost model charges exactly one expensive call per Clause with any
      Escalated Rule, sized to only those Rules, and nothing for a Fully Binned Clause.
- [ ] The cost table per 1,000 Clauses has rows for the expensive model alone, the cascade's expensive
      part, the Jev part, and net savings, each with Sonnet and Opus versions in batch and non-batch.
- [ ] Output tokens are included in the expensive-model estimate.
- [ ] Prices live in one configuration place, each with a source and a date.
- [ ] The report shows Jev time per 1,000 Clauses, labelled as stub timing while on the stub.
- [ ] The report states that savings track the Fully Binned Clause share, not per-Rule Binned Share.
