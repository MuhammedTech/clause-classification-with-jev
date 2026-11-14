# 12: A legal reader will not accept 10% of marked provisions lost

**What to build:** a reading of the cascade at a stated loss, chosen on one half of the documents and
reported on the other.

The reviewer's feedback on the real run: 10.3% of lawyer-marked Provisions lost at the 0.5 Cutoff is a
lot for a legal team. Pick the operating point a legal reader would accept (1 to 2% lost), lead with
how much Jev still skips there, choose it on one half of the agreements and report it on the other, and
add one line on cost per 1,000 Clauses against sending everything to the expensive model.

- `operating_point.py`: split by hash, `choose_cutoff` (highest shared Cutoff within the Loss Budget),
  `read_at`, `study` both ways round, pooled. Pure.
- `jev-cascade-operating-point --out out/real`: reads the stored answers, writes
  `docs/operating-point.md`. Never asks Jev.
- Cost per 1,000 Clauses against Claude Sonnet 5.5, from the token counts, with the reading-only
  saving beside it.
- ADR-0007 amends ADR-0003; glossary gains Operating Point, Loss Budget, Selection and Report Half.
- Does not touch the grading modules, and a test keeps it that way.

**Blocked by:** 09.

**Status:** resolved. Result: 20.5% skipped and 1.6% lost at the 2% budget, 7.7% skipped and 1.2% lost
at the 1% budget, and an unstable answer because one document's labels decide it.

**Superseded 2026-11-14 (ADR-0008).** The result above is for seven Rules, the Rule set agreed with the
reviewer, and stays here as the record. Minimum Commitment was then dropped after its results were seen.
Over six Rules, held out: 31.5% skipped and 1.1% lost at the 1% budget; at the 2% budget 64.6% skipped
but 4.2% lost, so that reading did not hold. Still unstable: which half chooses the Cutoff moves the skip
from 14.6% to 51.0% at the 1% budget.
