"""The Corpus loader, against the real CUAD files.

Facts measured in `docs/cuad-ground-truth.md` become assertions here rather than scripts. Ticket 02
adds the rest of them; ticket 01 asserts the join, which is what the tracer run depends on.
"""

import pytest

from jev_cascade import config
from jev_cascade.corpus import filter_counts, join_key, load_corpus
from jev_cascade.rulebook import rule

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)

R1 = rule("R1")


def test_the_join_key_strips_only_a_real_extension():
    # `os.path.splitext` would cut this title at its last dot and throw most of the name away.
    title = "EuromediaHoldingsCorp_20070215_10SB12G_EX-10.B(01)_525118_EX-10.B(01)_Content License Agreement"
    assert join_key(title + ".pdf") == join_key(title)
    assert join_key(title).endswith("contentlicenseagreement")


def test_the_join_key_matches_pacira_across_its_ampersand():
    # The CSV filename says A&R where the JSON title says A_R.
    assert join_key("PACIRA PHARMACEUTICALS, INC. - A&R STRATEGIC LICENSING.PDF") == join_key(
        "PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC LICENSING"
    )


def test_the_three_filters_give_three_different_counts():
    # Kept as an assertion so the difference between the 53, the 44 and the 44 stays documented.
    assert filter_counts() == {
        "csv_document_name": 53,
        "csv_filename": 44,
        "json_title": 44,
    }


def test_the_corpus_loads_exactly_53_documents_including_pacira():
    documents = load_corpus(rules=[R1])
    assert len(documents) == 53
    assert any("PACIRA" in d.filename.upper() for d in documents)


def test_every_r1_highlight_offset_lands_exactly_on_its_answer_text():
    documents = load_corpus(rules=[R1])
    checked = 0
    for document in documents:
        for highlight in document.highlights_for("R1"):
            assert document.text[highlight.start : highlight.end] == highlight.text
            assert "<omitted>" not in highlight.text
            checked += 1
    # The ground-truth table counts 78 R1 spans excluding Pacira, so it is a floor.
    assert checked >= 78


def test_certified_negative_documents_carry_no_highlights_for_that_rule():
    documents = load_corpus(rules=[R1])
    certified = [d for d in documents if d.is_certified_negative("R1")]
    # The ground-truth table counts 19 certified-negative documents for R1, excluding Pacira.
    assert len(certified) >= 19
    for document in certified:
        assert document.highlights_for("R1") == ()


def test_the_tracer_documents_give_non_empty_recall_denominators():
    from jev_cascade.pipeline import TRACER_DOC_IDS

    documents = load_corpus(rules=[R1], doc_ids=TRACER_DOC_IDS)
    assert len(documents) == 3
    with_highlights = [d for d in documents if d.highlights_for("R1")]
    certified = [d for d in documents if d.is_certified_negative("R1")]
    assert len(with_highlights) == 2
    assert len(certified) == 1


def test_an_unknown_document_id_is_refused():
    with pytest.raises(RuntimeError, match="No License Agreement Set document matches"):
        load_corpus(rules=[R1], doc_ids=["not a real contract"])
