"""Heading context: taking a section heading out of what Jev is shown, and nothing else.

Seam: `without_heading` on Clauses, and `pipeline.run` with the setting on and off.
"""

import pytest

from jev_cascade import config
from jev_cascade.domain import Clause, without_heading
from jev_cascade.jev import CountingJevClient, StubJevClient
from jev_cascade.pipeline import run


def test_a_heading_parent_line_is_blanked_and_everything_else_is_kept():
    heading = Clause("D", 0, 0, 10, "capped", "9. Liability", parent_is_heading=True)
    lead_in = Clause("D", 1, 10, 20, "pay fees", "10.1 Licensee shall:", parent_is_heading=False)
    bare = Clause("D", 2, 20, 30, "notices")

    out = without_heading([heading, lead_in, bare])

    # Spans and text are what grading uses, so they must not move.
    assert [(c.doc_id, c.start, c.end, c.text) for c in out] == [
        (c.doc_id, c.start, c.end, c.text) for c in (heading, lead_in, bare)
    ]
    assert out[0].parent_line == ""
    assert out[1].parent_line == "10.1 Licensee shall:"
    assert out[2].parent_line == ""


pytestmark_cuad = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)


@pytestmark_cuad
def test_the_pipeline_asks_again_only_where_the_heading_was_taken_out(tmp_path):
    on = CountingJevClient(StubJevClient())
    first = run(client=on, out_dir=tmp_path, heading_context=True)
    assert on.calls == first.stats.pairs

    off = CountingJevClient(StubJevClient())
    second = run(client=off, out_dir=tmp_path, heading_context=False)

    # Clauses with no heading Parent Line are the same prompt in both runs: served from the cache.
    assert 0 < off.calls < second.stats.pairs
    assert "Heading context | off" in second.markdown
    assert "Heading context | on" in first.markdown
    # Grading does not move: the same Clauses, spans and Highlights.
    assert [(c.start, c.end) for c in first.clauses] == [(c.start, c.end) for c in second.clauses]


@pytestmark_cuad
def test_the_report_says_how_jev_was_asked_and_discloses_the_selection_leak(tmp_path):
    markdown = run(client=StubJevClient(), out_dir=tmp_path).markdown

    assert "## How Jev is asked" in markdown
    assert "selection leak" in markdown
    # The disclosure says the choices were made on Pairs the full run also scores.
    assert "later scored" in markdown
