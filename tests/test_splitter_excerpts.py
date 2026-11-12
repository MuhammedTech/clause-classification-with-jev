"""Seam B, the Splitter, on short real excerpts: Parent Lines and the word ceiling (ticket 03).

The excerpts are copied from CUAD contexts, so each case is something a contract actually does. The
`word_ceiling` argument lets a short excerpt stand in for a 600-word block; the corpus-wide tests in
`test_partition.py` run the real ceiling.
"""

from jev_cascade.splitter import WORD_CEILING, split_document

EUROMEDIA_OPENING = (
    "Exhibit 10.B.01 EXECUTION COPY\n\nVIDEO-ON-DEMAND CONTENT LICENSE AGREEMENT between Rogers "
    'Cable Communications Inc. ("Rogers") and EuroMedia Holdings Corp. ("Licensor") offering '
    'EurocinemaSM Video-on-Demand service made as of July 11 , 2006 (the "Effective Date") '
    '(the "Agreement")\n\n  1. RIGHTS GRANTED   Licensor grants to Rogers the non-exclusive right.\n'
)

IDEANOMICS_DEFINITIONS = (
    '1. Definitions.\n\n(a) "Additional Title" shall have the meaning specified in Section 5.\n\n'
    '(b) "Advertising" shall have the meaning specified in Section 9.\n\n'
)

COHERUS_LEAD_IN = "1.74 Interpretation. In this Agreement, unless the context otherwise requires:"
COHERUS_ITEM_A = (
    "(a) headings do not affect the interpretation of this Agreement; the singular shall include "
    "the plural and vice versa; and references to one gender include all genders;\n\n"
)
COHERUS_INTERPRETATION = (
    COHERUS_LEAD_IN
    + "\n\n"
    + COHERUS_ITEM_A
    + "(b) references to EUR or € are references to the lawful currency from time to time in "
    "the Eurozone;\n\n"
)

IDEANOMICS_FOOTER = (
    '(i) "Mobile Sites" shall mean any and all versions of the Licensee Sites optimized for '
    "delivery and/or distribution via a wireless network.\n\n1\n\n"
    "Source: IDEANOMICS, INC., 10-K, 3/30/2016\n\n\n\n\n\n"
)


def test_opening_text_stays_its_own_clause_and_has_no_parent_line():
    clauses = split_document("E", EUROMEDIA_OPENING)
    assert len(clauses) == 2
    assert clauses[0].text.startswith("Exhibit 10.B.01 EXECUTION COPY")
    assert clauses[1].text.lstrip().startswith("1. RIGHTS GRANTED")
    assert clauses[0].parent_line == ""
    # Nothing sits above the first item but the opening, which is not a Parent Line.
    assert clauses[1].parent_line == ""


def test_a_real_heading_over_lettered_items_hands_its_words_to_the_first_item():
    clauses = split_document("I", IDEANOMICS_DEFINITIONS)
    assert len(clauses) == 2
    assert clauses[0].text.startswith("1. Definitions.")
    assert '(a) "Additional Title"' in clauses[0].text
    assert clauses[1].text.startswith('(b) "Advertising"')
    # The heading is the Parent Line for the rest of its section, but the first item already
    # carries the heading's words and has nothing above it.
    assert clauses[0].parent_line == ""
    assert clauses[1].parent_line == "1. Definitions."


def test_a_lettered_list_sits_under_its_lead_in_not_under_its_sibling():
    clauses = split_document("C", COHERUS_INTERPRETATION)
    assert len(clauses) == 3
    assert clauses[0].text.strip() == COHERUS_LEAD_IN
    assert clauses[1].parent_line == COHERUS_LEAD_IN
    assert clauses[2].parent_line == COHERUS_LEAD_IN


def test_a_dotted_item_after_a_numbering_gap_takes_no_parent_line():
    # Measured on the corpus: 301 of 666 dotted items beneath a numbered ancestor would be given a
    # section whose number is not theirs, `7.2` under `6. Term and Termination.`. A wrong section
    # label is worse than an empty one, and ticket 08 measures what the heading does.
    text = (
        "6. Term and Termination.\n6.1 Term. Five years.\n6.2 Renewal. Automatic.\n"
        "7.2 Fees are due.\n"
    )
    clauses = split_document("D", text)
    assert len(clauses) == 3
    assert clauses[1].text.startswith("6.2")
    assert clauses[1].parent_line == "6. Term and Termination."
    assert clauses[2].text.startswith("7.2")
    assert clauses[2].parent_line == ""


def test_siblings_across_a_whole_section_share_the_heading_as_their_parent_line():
    text = "5. Fees\n5.1 Licensee shall pay.\n5.2 Interest accrues.\n5.3 Taxes are extra.\n"
    clauses = split_document("D", text)
    assert [c.parent_line for c in clauses] == ["", "5. Fees", "5. Fees"]


def test_the_word_ceiling_is_600():
    assert WORD_CEILING == 600


def test_an_oversized_clause_is_split_at_a_paragraph_break():
    clauses = split_document("I", IDEANOMICS_FOOTER, word_ceiling=22)
    assert "".join(c.text for c in clauses) == IDEANOMICS_FOOTER
    assert len(clauses) == 2
    assert clauses[0].text.endswith("wireless network.\n\n")
    assert clauses[1].text.startswith("1\n\nSource:")
    assert all(c.word_count <= 22 for c in clauses)


def test_a_clause_at_the_ceiling_is_not_split():
    assert len(split_document("I", IDEANOMICS_FOOTER, word_ceiling=28)) == 1


def test_an_oversized_clause_with_no_paragraph_break_falls_back_to_sentences():
    clauses = split_document("C", COHERUS_ITEM_A.rstrip("\n"), word_ceiling=15)
    assert all(c.word_count <= 15 for c in clauses)
    assert len(clauses) == 3
    assert clauses[0].text.endswith("this Agreement; ")


def test_the_pieces_of_a_split_clause_share_the_parent_line_of_the_clause():
    # A continuation piece is not a new item, so it sits under the same line the whole Clause did.
    clauses = split_document("C", COHERUS_INTERPRETATION, word_ceiling=15)
    under_lead_in = [c for c in clauses if c.parent_line]
    assert len(under_lead_in) >= 4
    assert {c.parent_line for c in under_lead_in} == {COHERUS_LEAD_IN}


def test_a_page_that_is_one_line_is_split_with_no_newline_or_punctuation_to_use():
    # Hertz-style: a whole contract on one line.
    text = "ARTICLE 1 " + " ".join(f"word{i}" for i in range(98))
    clauses = split_document("H", text, word_ceiling=10)
    assert "".join(c.text for c in clauses) == text
    assert all(0 < c.word_count <= 10 for c in clauses)
    assert len(clauses) == 10


def test_no_piece_of_a_split_is_empty_or_blank():
    text = "   \n\n" + " ".join(f"w{i}" for i in range(40)) + "\n\n   \n\n"
    clauses = split_document("D", text, word_ceiling=7)
    assert "".join(c.text for c in clauses) == text
    assert all(c.text.strip() for c in clauses)
    assert all(c.word_count <= 7 for c in clauses)


def test_the_default_ceiling_bounds_a_long_unmarked_document():
    text = " ".join(f"w{i}" for i in range(1700))
    clauses = split_document("D", text)
    assert "".join(c.text for c in clauses) == text
    assert max(c.word_count for c in clauses) <= WORD_CEILING
    assert [c.index for c in clauses] == list(range(len(clauses)))


def test_a_clause_enlarged_by_a_merged_heading_is_measured_against_the_ceiling():
    body = " ".join(f"w{i}" for i in range(9))
    text = f"1. Fees\n1.1 {body}\n"
    clauses = split_document("D", text, word_ceiling=10)
    assert "".join(c.text for c in clauses) == text
    assert all(c.word_count <= 10 for c in clauses)
    assert len(clauses) == 2
