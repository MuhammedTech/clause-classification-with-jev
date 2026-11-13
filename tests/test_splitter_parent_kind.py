"""Seam: the Splitter says whether a Clause's Parent Line is a section heading or not.

Ticket 08 tests the heading in and out of Jev's context. That has to blank the heading and leave a
Parent Line that introduces a list, such as "Licensee shall:", alone, so the Splitter records
which one a Parent Line is.
"""

from jev_cascade.splitter import split_document

TEXT = (
    "9. Limitation of Liability\n"
    "9.1 Neither party is liable for indirect loss.\n"
    "9.2 Total liability is capped at the fees paid.\n"
    "10. Obligations\n"
    "10.1 Licensee shall:\n"
    "(a) pay the fees on time;\n"
    "(b) keep records.\n"
)


def by_text(clauses, fragment):
    (found,) = [c for c in clauses if fragment in c.text]
    return found


def test_a_short_numbered_heading_is_a_heading_parent_line():
    clause = by_text(split_document("D", TEXT), "capped at the fees")
    assert clause.parent_line == "9. Limitation of Liability"
    assert clause.parent_is_heading is True


def test_a_line_introducing_a_list_is_not_a_heading():
    clause = by_text(split_document("D", TEXT), "pay the fees")
    assert clause.parent_line == "10.1 Licensee shall:"
    assert clause.parent_is_heading is False


def test_no_parent_line_is_not_a_heading():
    clause = by_text(split_document("D", TEXT), "indirect loss")
    assert clause.parent_line == ""
    assert clause.parent_is_heading is False
