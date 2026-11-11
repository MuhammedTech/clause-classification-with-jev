# 07: Cost and time

**What to build:** "how much could we have saved" and "how fast", per 1,000 clauses. No expensive model is ever called.

- **Tokens:** count tokens per clause, including the Lead-in context and the question text.
- **Expensive model:** price one call per clause that has at least one Escalated rule, asking only the escalated rules. Use Claude Sonnet 5.5 list price, with Opus 5.5 as a second row, each in batch and non-batch pricing.
- **Jev:** subtract Jev's cost. Its price is configuration, with its source and date stated; the current value is $0.042 per million input tokens from one unverified blog.
- **Time:** report Jev's wall-clock time per 1,000 clauses from the runner's timing.

**Blocked by:** 05.

**Status:** ready-for-agent

- [ ] An Evaluator test shows the cost model charges exactly one expensive call per clause with any escalated rule, sized to only the escalated questions, and nothing for Fully Cleared Clauses.
- [ ] The report shows a cost table per 1,000 clauses with these rows:
  - expensive model alone
  - cascade expensive part
  - Jev part
  - net savings

  Each row has Sonnet and Opus versions, batch and non-batch.
- [ ] Prices live in one configuration place with a source and a date for each.
- [ ] The report shows Jev time per 1,000 clauses. With the stub it is labelled as stub timing.
