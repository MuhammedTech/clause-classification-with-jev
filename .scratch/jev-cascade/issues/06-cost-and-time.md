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

**Status:** resolved

- [x] An Evaluator test shows the cost model charges exactly one expensive call per Clause with any
      Escalated Rule, sized to only those Rules, and nothing for a Fully Binned Clause.
- [x] The cost table per 1,000 Clauses has rows for the expensive model alone, the cascade's expensive
      part, the Jev part, and net savings, each with Sonnet and Opus versions in batch and non-batch.
- [x] Output tokens are included in the expensive-model estimate.
- [x] Prices live in one configuration place, each with a source and a date.
- [x] The report shows Jev time per 1,000 Clauses, labelled as stub timing while on the stub.
- [x] The report states that savings track the Fully Binned Clause share, not per-Rule Binned Share.

## Comments

**2026-11-12, resolved.** `cost.py` is a pure module beside the Evaluator: `cost_usage` counts calls
and tokens for the expensive model alone, the cascade's expensive part and Jev; `price_usage` turns
them into dollars for one model, batch or not; `jev_time` scales the runner's clock; and
`full_run_estimate` sizes the whole corpus. The report's new "Cost and time" section sits between
Fully Binned Clauses and Reading the curve. The first acceptance test is in `tests/test_cost.py`
(Seam A, the same seam as the Evaluator's tests) with values added up by hand from a one-token-a-word
counter; `tests/test_report_cost.py` checks the section end to end and cross-checks the cascade call
count against `evaluator.fully_binned`.

Decisions worth knowing:

- **Tokens are estimated, not counted.** No tokenizer exists in the code and `--from-cache` must
  rebuild with no network, so tokens are characters over 4 (`config.CHARS_PER_TOKEN`). Every figure
  built on it is labelled an estimate. A `count_tokens` run over the real prompts would replace it.
- **Three numbers are assumptions, not prices**, each in `config.py` with its reason: 200 overhead
  tokens per expensive call, 100 output tokens per question asked, and the 4 characters a token.
  The output per question is the softest number, and reasoning tokens are not in it, so every
  expensive-model dollar is probably low. The share saved is steadier than the dollars, because the
  baseline and the cascade share every assumption.
- **The Claude prices are unverified.** $2 / $10 (Sonnet 5.5) and $4 / $20 (Opus 5.5), batch at half,
  come from the claude-api skill's cached table dated 2026-11-03, not from the pricing page. The
  source string says so; confirm before quoting. Jev is not batched.
- **"The expensive model alone" carries every Rule asked in the run**, so the two rows compare like
  with like. On the default one-Rule run that is one Rule, and the section says "1 Rule".
- **Jev's measured time is `n/a` on a cache-only run**, not zero: the clock then timed a file read.
  The rate-limit projection (1,000 calls at 1,200 a minute) is always shown.
- **The spec's "$0.20" is replaced.** The full run is 22,722 calls and about 6.4 million estimated
  input tokens, so about $0.27 and 19 minutes at the published rate. The spec and
  `docs/cuad-ground-truth.md` are corrected; this ticket's own text ("22,708 calls, about 20
  minutes", "roughly $0.20") is left as the record of what was asked.
- **Added beyond the ticket:** a "Saved, share of the baseline" row and the full-run section. Both
  are cheap and the full-run figure is what corrects the spec.

**Code review (Standards and Spec).** No hard violations on either axis. Fixed: the calls table
carries the stub label; `_usd` no longer prints `-$0.000`; the report takes its document count from
`CorpusFacts` instead of hard-coding 53 and no longer repeats the superseded $0.20 and 16% in prose
(those stay in the ground-truth note); the price arithmetic is one helper; the README line is wrapped.

Left alone, as judgement calls: the `count_tokens`, `overhead_tokens` and similar override
parameters (the tests need them, and they are how a real tokenizer plugs in); `cost_usage` restating
the escalation rule `p_yes > cutoff` rather than calling the Evaluator (the end-to-end test checks the
two agree); a small type for the `(model, batch, figures)` rows; `_cost_section` at about 170 lines
(the same note as ticket 05 made about splitting `report.py`); the "Rule(s)" pluralising helper; and
dividing the runner's whole-loop seconds by calls made, which includes cache writes and hits.
