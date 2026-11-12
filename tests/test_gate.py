"""The gate's arithmetic, on hand-built counts.

These need no dataset, so they run everywhere and they fail on a wrong threshold. The corpus tests
assert what CUAD actually gives; these assert what the rule means. ADR-0005 sets the gate at at
least 15 documents carrying a Highlight and at least 25 Highlights.
"""

from jev_cascade.corpus import RuleCounts


def counts(documents: int, highlights: int) -> RuleCounts:
    return RuleCounts(
        rule_id="RX",
        cuad_category="Made Up",
        documents_with_highlights=documents,
        highlights=highlights,
        certified_negative_doc_ids=(),
    )


def test_a_rule_exactly_on_both_minimums_passes():
    assert counts(15, 25).passes_gate


def test_one_document_short_fails_however_many_highlights():
    assert not counts(14, 400).passes_gate


def test_one_highlight_short_fails_however_many_documents():
    assert not counts(50, 24).passes_gate


def test_the_margin_counts_highlights_above_the_minimum():
    assert counts(17, 26).highlight_margin == 1
    assert counts(15, 25).highlight_margin == 0
    # Negative when the Rule fails on that count, which is what makes it safe to print.
    assert counts(15, 23).highlight_margin == -2


def test_certified_negative_documents_are_counted_from_the_ids():
    assert counts(15, 25).certified_negative_documents == 0
    with_ids = RuleCounts(
        rule_id="RX",
        cuad_category="Made Up",
        documents_with_highlights=2,
        highlights=3,
        certified_negative_doc_ids=("alpha", "beta", "gamma"),
    )
    assert with_ids.certified_negative_documents == 3
