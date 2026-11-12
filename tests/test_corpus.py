"""The Corpus loader, against the real CUAD files.

Facts measured in `docs/cuad-ground-truth.md` become assertions here rather than scripts. Ticket 01
asserted the join, which the tracer run depends on; ticket 02 adds the rest of them and the gate.
"""

import json

import pytest

from jev_cascade import config
from jev_cascade.corpus import (
    GATE_MIN_DOCUMENTS,
    GATE_MIN_HIGHLIGHTS,
    corpus_facts,
    filter_counts,
    gate_counts,
    join_key,
    load_corpus,
)
from jev_cascade.rulebook import RULEBOOK, SUPERSEDED_GATE_COUNTS, Rule, rule

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
    # Asserted so the difference between the 53, the 44 and the 44 stays documented.
    counts = filter_counts()
    assert (counts.csv_document_name, counts.csv_filename, counts.json_title) == (53, 44, 44)


def test_the_corpus_loads_exactly_53_documents_including_pacira():
    documents = load_corpus(rules=[R1])
    assert len(documents) == 53
    assert any("PACIRA" in d.filename.upper() for d in documents)


def test_every_highlight_offset_lands_exactly_on_its_answer_text():
    # All 429 spans across the seven Rules, so character-range overlap is a sound label (ADR-0004).
    documents = load_corpus()
    checked = 0
    for document in documents:
        for highlight in document.highlights:
            assert document.text[highlight.start : highlight.end] == highlight.text
            assert "<omitted>" not in highlight.text
            checked += 1
    assert checked == 429


def test_certified_negative_documents_carry_no_highlights_for_that_rule():
    documents = load_corpus(rules=[R1])
    certified = [d for d in documents if d.is_certified_negative("R1")]
    assert len(certified) == 19
    for document in certified:
        assert document.highlights_for("R1") == ()


def test_an_impossible_document_category_carries_zero_answers_in_cuad_itself():
    # Asserted on the raw records, not through the loader: the loader returns on `is_impossible`
    # before it reads `answers`, so going through it would prove only its own control flow. This is
    # the fact that makes every Clause of such a document a verified negative for that Rule.
    with config.cuad_json().open(encoding="utf-8") as handle:
        payload = json.load(handle)

    pairs = 0
    impossible = 0
    for record in payload["data"]:
        for qa in record["paragraphs"][0]["qas"]:
            pairs += 1
            if qa.get("is_impossible"):
                impossible += 1
                assert qa["answers"] == [], (record["title"], qa["id"])
    # The corpus-wide figures from `docs/cuad-ground-truth.md`: 510 documents x 41 categories.
    assert (pairs, impossible) == (20910, 14208)


def test_the_loader_exposes_the_same_certified_negative_documents_cuad_flags():
    # Checked against the raw records rather than against the loader's own view of them: the
    # expected set is read straight out of `is_impossible` in the JSON, so a loader that dropped
    # or invented one would disagree. Going through `is_certified_negative` instead would only
    # re-run the filter that built the list.
    with config.cuad_json().open(encoding="utf-8") as handle:
        payload = json.load(handle)

    license_titles = {d.doc_id for d in load_corpus()}
    expected: dict[str, set[str]] = {rule_.id: set() for rule_ in RULEBOOK}
    category_to_rule = {rule_.cuad_category: rule_.id for rule_ in RULEBOOK}
    for record in payload["data"]:
        if record["title"] not in license_titles:
            continue
        for qa in record["paragraphs"][0]["qas"]:
            category = qa["id"].split("__", 1)[-1]
            rule_id = category_to_rule.get(category)
            if rule_id is not None and qa.get("is_impossible"):
                expected[rule_id].add(record["title"])

    exposed = {c.rule_id: set(c.certified_negative_doc_ids) for c in gate_counts()}
    assert exposed == expected
    # And the lists are lists, not accidentally deduplicated views.
    for count in gate_counts():
        assert len(count.certified_negative_doc_ids) == len(set(count.certified_negative_doc_ids))


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


def test_the_gate_counts_match_the_measured_per_rule_table():
    # The table in `docs/cuad-ground-truth.md`, measured over all 53 documents including Pacira.
    # Each row is (documents with a span, spans, documents certified as having none).
    expected = {
        "R1": (34, 82, 19),
        "R2": (26, 76, 27),
        "R3": (22, 33, 31),
        "R5": (24, 58, 29),
        "R6": (17, 51, 36),
        "R7": (20, 44, 33),
        "R8": (41, 85, 12),
    }
    counts = gate_counts()
    measured = {
        c.rule_id: (c.documents_with_highlights, c.highlights, c.certified_negative_documents)
        for c in counts
    }
    assert measured == expected
    assert sum(c.highlights for c in counts) == 429


def test_every_rule_accounts_for_all_53_documents():
    # Each document either holds a Highlight for a Rule or is certified as having none: no third
    # state. Without this, a category missing from a document's annotations would pass unnoticed.
    for count in gate_counts():
        assert (
            count.documents_with_highlights + count.certified_negative_documents == 53
        ), count.rule_id


def test_the_corpus_facts_match_the_measured_corpus_size():
    facts = corpus_facts()
    # From `docs/cuad-ground-truth.md`: the 53 contexts hold 2,990,822 characters, of which
    # Pacira is 145,168 — the 2,845,654 recorded before it joined.
    assert (facts.documents, facts.characters) == (53, 2990822)
    assert facts.highlights == 429
    assert facts.gate_passes


def test_the_dropped_rule_now_passes_the_gate_and_is_still_absent():
    # ADR-0005 dropped Uncapped Liability as the only Rule failing the gate, measured at 16
    # documents and 23 spans before Pacira joined. On all 53 it is 17 and 26, one span over the
    # gate, so the standing reason is independence from R1 and the counts must say so.
    (dropped,) = corpus_facts().dropped
    assert dropped.rule_id == "R4"
    assert (dropped.documents_with_highlights, dropped.highlights) == (17, 26)
    assert dropped.certified_negative_documents == 36
    assert dropped.passes_gate
    assert dropped.highlight_margin == 1
    # ADR-0005's superseded figures are kept as data so the report prints them without the
    # renderer holding a number of its own.
    assert (SUPERSEDED_GATE_COUNTS["R4"].documents, SUPERSEDED_GATE_COUNTS["R4"].highlights) == (
        16,
        23,
    )
    # The dropped Rule carries no Detection Question: wording is drafted only for Rules asked.
    assert dropped.cuad_category == "Uncapped Liability"
    # Dropped means never asked.
    assert "R4" not in [r.id for r in RULEBOOK]
    with pytest.raises(KeyError, match="dropped in ADR-0005"):
        rule("R4")


def test_the_backup_rules_counts_stay_recorded():
    # Neither backup is needed, but the counts are what proves that: the report says the gate was
    # settled without reaching for them.
    backups = (
        Rule("AR", "Audit Rights", ""),
        Rule("IP", "Ip Ownership Assignment", ""),
    )
    counts = {
        c.rule_id: (c.documents_with_highlights, c.highlights) for c in gate_counts(rules=backups)
    }
    assert counts == {"AR": (29, 92), "IP": (17, 52)}


def test_all_seven_rules_pass_the_gate():
    # The gate's thresholds are written out rather than imported, so a Rule that only passes
    # because someone lowered `GATE_MIN_*` fails here. ADR-0005: at least 15 documents with a
    # Highlight and at least 25 Highlights.
    counts = gate_counts()
    assert [c.rule_id for c in counts] == ["R1", "R2", "R3", "R5", "R6", "R7", "R8"]
    for count in counts:
        assert count.documents_with_highlights >= 15, count.rule_id
        assert count.highlights >= 25, count.rule_id
        assert count.passes_gate, count.rule_id


def test_the_gate_thresholds_are_the_ones_adr_0005_set():
    assert (GATE_MIN_DOCUMENTS, GATE_MIN_HIGHLIGHTS) == (15, 25)
