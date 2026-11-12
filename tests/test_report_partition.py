"""Seam C: the report's partition section covers the whole corpus, not just the documents scored.

The tracer documents were chosen because they split cleanly, so a section limited to them would show
nothing. ADR-0004 keeps the documents the splitter handles badly on the condition that they show up
here. The share of Highlights inside one Clause is **reported, not asserted**: it is what the data
gives and not a build gate.
"""

import pytest

from jev_cascade import config
from jev_cascade.corpus import load_corpus
from jev_cascade.jev import StubJevClient
from jev_cascade.pipeline import run

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)


def _section(markdown: str, heading: str) -> str:
    start = markdown.index(heading)
    end = markdown.find("\n## ", start + len(heading))
    return markdown[start : end if end != -1 else len(markdown)]


@pytest.fixture(scope="module")
def markdown(tmp_path_factory):
    out = tmp_path_factory.mktemp("report")
    return run(client=StubJevClient(), out_dir=out).markdown


def test_the_report_has_a_partition_section(markdown):
    assert "## Partition" in markdown


def test_the_partition_section_states_the_ceiling_and_that_none_exceed_it(markdown):
    section = _section(markdown, "## Partition")
    assert "600 words" in section
    assert "| Clauses over the Word Ceiling | 0 |" in section


def test_the_partition_section_covers_all_53_documents_not_only_the_tracer_three(markdown):
    section = _section(markdown, "## Partition")
    for document in load_corpus():
        assert document.doc_id in section, document.doc_id


def test_the_partition_section_reports_the_highlight_share_as_counts_beside_a_share(markdown):
    section = _section(markdown, "## Partition")
    assert "Highlights inside exactly one Clause" in section
    assert "build gate" in section


def test_the_partition_section_states_the_unit_of_context_growth(markdown):
    section = _section(markdown, "## Partition")
    assert "Parent Line" in section
    # No tokenizer here; tokens are ticket 06's.
    assert "more words" in section
    assert "no tokenizer" in section
