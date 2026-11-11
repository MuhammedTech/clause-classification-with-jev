# 03: Real splitter with Lead-in context

**What to build:** the splitter cuts every document of the License Agreement Set into sensible Clauses. Each sub-item carries its parent's Lead-in as context for Jev. The Lead-in context is never used in grading.

The splitter must handle:
- numbering mid-line (Eton: `…defined below: 1.1 "Affiliates" means…`)
- spaced dotted numbering (Telkom: `2. 3. 1.`)
- numbers that are not item markers, such as prices, quantities, years and table rows (Glu Mobile pricing table: "5 MMS", "10 Wallpapers")
- short list items, which must survive ("(1) United Kingdom;")
- lettered and roman sub-items under a Lead-in

Clauses record their span, token count, parent Lead-in, and whether they are themselves a Lead-in.

**Blocked by:** 02.

**Status:** ready-for-agent

- [ ] Splitter tests (Seam B) use short excerpts from Telkom, Eton, Glu Mobile, the exclusivity territory list, and a Lead-in with lettered items, and pass.
- [ ] A corpus-wide test fails if any Clause exceeds 600 words.
- [ ] A corpus-wide test checks that about 97% or more of highlights sit inside exactly one Clause.
- [ ] Jev receives the Lead-in plus the Clause text. Grading uses only the Clause's own span. An Evaluator test shows a highlight in the parent does not make a sub-item touch it.
- [ ] The report shows: Clause count, word-length distribution, share of highlights inside one Clause, and token growth from added Lead-in context.
