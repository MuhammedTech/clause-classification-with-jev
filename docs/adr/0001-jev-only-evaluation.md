# Jev-only evaluation, no strong-LLM run

The original plan ran a strong LLM on a sample of clauses to build a cascade and an LLM-alone baseline. We dropped it: the question is how much work Jev takes off the expensive model and how accurate Jev is against the lawyer labels, so only Jev is run. Escalated pairs are never scored for accuracy, the headline is keep share plus precision/recall on kept pairs, an "expensive model gets every escalated pair right" line is shown only as a labelled upper bound, and savings are estimated from token counts at list prices (Claude Sonnet 5.5, with Opus 5.5 as a second row) rather than measured.

## Consequences

The cutoff cannot be tuned against LLM-alone recall; it is tuned against a fixed miss budget instead (see ADR-0002). Adding an LLM later is possible but changes the headline, so do it as a separate comparison, not a silent replacement.
