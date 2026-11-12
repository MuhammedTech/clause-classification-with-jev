"""Seam A, the Evaluator: Certified and Inferred Negatives, and the false-alarm rate.

Two hand-made documents. "N" is a Certified Negative document for the Rule (CUAD flagged it
`is_impossible`): lawyers checked and it has no such clause. "D" has one Highlight.

    N0 [0,10) P(yes) 0.90   N1 [10,20) P(yes) 0.90   N2 [20,30) P(yes) 0.10
    D0 [0,10) P(yes) 0.90   D1 [10,20) P(yes) 0.90   D2 [20,30) P(yes) 0.10
    D's one Highlight [2,5) lies inside D0.
"""

import pytest

from jev_cascade.domain import Clause, Highlight
from jev_cascade.evaluator import evaluate_rule


def _case():
    clauses = [
        Clause(doc_id=doc, index=i, start=10 * i, end=10 * i + 10, text="w")
        for doc in ("N", "D")
        for i in range(3)
    ]
    pyes = {(c.doc_id, c.span_key): (0.10 if c.index == 2 else 0.90) for c in clauses}
    highlights = [Highlight(doc_id="D", rule_id="R1", start=2, end=5)]
    return clauses, highlights, pyes


def test_negatives_are_split_into_certified_and_inferred():
    clauses, highlights, pyes = _case()
    m = evaluate_rule("R1", clauses, highlights, pyes, 0.50, certified_negative_docs={"N"})
    # All three N Clauses hold nothing in a certified document. D1 and D2 hold nothing in a
    # document that has a Highlight elsewhere. D0 holds one. 3 + 2 + 1 = 6 Clauses.
    assert m.certified_negative_clauses == 3
    assert m.inferred_negative_clauses == 2
    assert m.holding_clauses == 1


def test_false_alarm_rate_counts_escalated_clauses_inside_certified_negative_documents():
    clauses, highlights, pyes = _case()
    m = evaluate_rule("R1", clauses, highlights, pyes, 0.50, certified_negative_docs={"N"})
    # N0 and N1 are Escalated, N2 is Binned: 2 of 3. D's Clauses play no part.
    assert m.certified_negative_escalated == 2
    assert m.false_alarm_rate == pytest.approx(2 / 3)
    # Inferred Negatives are counted on their own: D1 Escalated, D2 Binned.
    assert m.inferred_negative_escalated == 1


def test_false_alarm_rate_is_kept_apart_from_precision():
    clauses, highlights, pyes = _case()
    m = evaluate_rule("R1", clauses, highlights, pyes, 0.50, certified_negative_docs={"N"})
    # Four Clauses are Escalated (N0, N1, D0, D1) and only D0 holds a Highlight: 1/4. The certified
    # figure, 2/3, is a different quantity on a different denominator.
    assert m.escalated_clauses == 4
    assert m.precision == pytest.approx(1 / 4)
    assert m.false_alarm_rate != pytest.approx(m.precision)


def test_without_a_certified_negative_document_the_false_alarm_rate_is_undefined():
    clauses, highlights, pyes = _case()
    m = evaluate_rule("R1", clauses, highlights, pyes, 0.50)
    assert m.certified_negative_clauses == 0
    assert m.false_alarm_rate is None
    # N's Clauses are not silently promoted to Certified: with no certification they are Inferred.
    assert m.inferred_negative_clauses == 5
