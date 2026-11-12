# 10: The P(yes) cache key ignores the Parent Line, so a changed prompt is served a stale answer

**What to build:** a cache key that identifies everything the Jev client was actually shown.

`runner.py` keys a cached answer on `(doc_id, clause_start, clause_end, rule_id, question_type,
model_version)`. Jev is shown **Parent Line plus Clause text**, and the Parent Line is in none of
that. So two different prompts share one key, and the second is answered from the cache with the
first's P(yes).

- Add a fingerprint of what the client was shown — a hash of the Parent Line and the Clause text —
  to the key and to the JSONL row.
- The span stays in the key: it is what the Evaluator grades on, and it keeps the row readable.
- A cache written before the fingerprint existed has no such field, so treat a row without one as a
  miss and ask the Pair again rather than guessing.

**Why it matters now.** Three ways it bites, in the order they arrive:

- **Ticket 03** changes Parent Lines while leaving spans untouched. `(b)` keeps its span and its
  Parent Line changes from its sibling `(a)` to the item they both sit under, so an existing
  `out/pyes.jsonl` serves `(b)` the P(yes) computed from the sibling's prompt.
- **Ticket 08** compares the section heading included as Parent Line against excluded, on the same
  documents. Those two runs collide in the cache, which is the measurement the ticket exists to make.
- **Ticket 07** makes this cost money rather than just being wrong, since the real client is billed
  per call and a stale hit is silent.

The Clause text is strictly implied by the document and the span, so hashing it adds nothing on its
own; it is in the fingerprint so that a changed text source — a re-extracted `context`, a different
whitespace normalisation — cannot quietly reuse answers either.

**Blocked by:** None. Ticket 03 fixes it in passing, because 03 cannot be correct while it stands.

**Status:** resolved

- [x] A runner test shows two Clauses with the same document, span, Rule, question type and model
      version but **different Parent Lines** get two client calls and two different P(yes) values.
- [x] A runner test shows a cache row written without the fingerprint is treated as a miss, not as a
      hit, and the Pair is asked again.
- [x] The existing guarantees still hold: a second run makes zero client calls, and a run interrupted
      midway resumes from the cache.
- [x] The cache docstring states what the key identifies and why the Parent Line is part of it.

## Comments

**2026-11-12, from ticket 03.** Found by reading `runner.py:41` while planning ticket 03's Parent
Line work, not by a failing test: every existing cache test varies the span, so nothing in the suite
holds the span fixed while changing the Parent Line.

No measured result is contaminated. Everything so far has run on the stub, whose P(yes) is a hash of
its inputs and carries no signal, and `out/` is gitignored and rebuildable. The defect is in ticket
01's runner and predates ticket 03; it was harmless only because ticket 01's Parent Line rule made
the line a function of the span.

**2026-11-12, resolved.** `runner.py` now keys each answer on a `prompt_fingerprint`: a sha256 of the
Parent Line and the Clause text joined with `\x1f`, truncated to 16 hex characters, stored on every
row. A row without one is a miss. The different-Parent-Line test is two sequential runs on one cache
file, because the P(yes) table is keyed by (document, span) and cannot hold two answers for one span.
An existing `out/pyes.jsonl` is therefore ignored and rebuilt, which costs nothing on the stub.
