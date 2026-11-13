"""Seam C: the report's cost and time section. Estimated from token counts; nothing is called."""

import json

import pytest

from jev_cascade import config
from jev_cascade.jev import CacheOnlyJevClient, StubJevClient
from jev_cascade.pipeline import run

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run(client=StubJevClient(), out_dir=tmp_path_factory.mktemp("cost"))


def _section(markdown: str, heading: str) -> str:
    start = markdown.index(heading)
    end = markdown.find("\n## ", start + len(heading))
    return markdown[start : end if end != -1 else len(markdown)]


def _row(section: str, label: str) -> list[str]:
    line = next(l for l in section.splitlines() if l.startswith(f"| {label}"))
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def test_the_section_sits_between_fully_binned_and_reading_the_curve(result):
    markdown = result.markdown
    assert (
        markdown.index("\n## Fully Binned Clauses")
        < markdown.index("\n## Cost and time")
        < markdown.index("\n## Reading the curve")
    )


def test_the_cost_table_has_every_row_with_sonnet_and_opus_in_batch_and_not(result):
    section = _section(result.markdown, "## Cost and time")
    header = next(l for l in section.splitlines() if l.startswith("| Per 1,000 Clauses"))
    for column in ("Claude Sonnet 5.5", "Claude Sonnet 5.5 batch",
                   "Claude Opus 5.5", "Claude Opus 5.5 batch"):
        assert column in header, column
    for label in ("Expensive model alone", "Cascade: expensive part", "Cascade: Jev part",
                  "Net savings"):
        cells = _row(section, label)
        # The label plus one dollar figure for each of the four columns.
        assert len(cells) == 5, label
        assert all("$" in cell for cell in cells[1:]), label


def test_the_calls_and_tokens_behind_the_dollars_are_printed_counts_first(result):
    section = _section(result.markdown, "## Cost and time")
    assert "output tokens" in section.lower()
    cascade = _row(section, "Cascade expensive calls")
    usage = result.cost.usage
    assert cascade[1] == f"{usage.cascade.calls:,}"
    assert cascade[2] == f"{usage.cascade.input_tokens:,}"
    assert cascade[3] == f"{usage.cascade.output_tokens:,}"


def test_a_clause_is_charged_one_expensive_call_unless_it_is_fully_binned(result):
    # Two modules count this independently: the Evaluator's Fully Binned figure and the cost model.
    fully = result.fully_binned
    usage = result.cost.usage
    assert usage.cascade.calls == fully.clauses - fully.fully_binned_clauses
    assert usage.fully_binned_clauses == fully.fully_binned_clauses
    assert usage.alone.calls == fully.clauses


def test_every_price_and_assumption_is_printed_with_its_source_and_date(result):
    section = _section(result.markdown, "## Cost and time")
    for item in (config.JEV_INPUT_PRICE, config.BATCH_DISCOUNT, config.CHARS_PER_TOKEN,
                 config.EXPENSIVE_OVERHEAD_TOKENS, config.EXPENSIVE_OUTPUT_TOKENS_PER_QUESTION,
                 config.JEV_RATE_LIMIT_PER_MINUTE):
        assert item.source in section
        assert item.as_of in section
    for model in config.EXPENSIVE_MODELS:
        assert model.name in section
        assert model.input.source in section
    assert "unverified" in section


def test_tokens_are_called_an_estimate_and_the_expensive_model_is_never_run(result):
    section = _section(result.markdown, "## Cost and time")
    assert "estimate" in section.lower()
    assert "No expensive model is run" in section


def test_the_stub_labels_the_timing_and_the_scored_figures(result):
    section = _section(result.markdown, "## Cost and time")
    assert "stub timing" in section.lower()
    assert "Stub-derived" in section
    assert "per 1,000 Clauses" in section


def test_jev_time_is_given_measured_and_at_the_published_rate_limit(result):
    section = _section(result.markdown, "## Cost and time")
    measured = _row(section, "Jev wall clock, measured")
    assert measured[1].endswith("s (stub timing)")
    at_limit = _row(section, "Jev time at the published rate limit")
    # 1,000 Clauses is 1,000 calls (every Rule in one call) at 1,200 a minute.
    assert at_limit[1].startswith("0.83 minutes")


def test_a_rebuild_from_the_cache_reports_the_original_runs_timing(tmp_path):
    ticks = iter(float(n) * 0.25 for n in range(10_000))
    first = run(client=StubJevClient(), out_dir=tmp_path, now=lambda: next(ticks))
    again = run(client=CacheOnlyJevClient(StubJevClient()), out_dir=tmp_path)

    assert again.stats.calls_made == 0
    # A quarter of a second an answer, read back from the cache's timestamps, not the rebuild's clock.
    for result in (first, again):
        measured = _row(_section(result.markdown, "## Cost and time"), "Jev wall clock, measured")
        assert measured[1] == "250.0s (stub timing)"


def test_a_cache_with_no_timestamps_reports_no_measured_time(tmp_path):
    run(client=StubJevClient(), out_dir=tmp_path)
    cache = tmp_path / "pyes.jsonl"
    rows = [json.loads(line) for line in cache.read_text().splitlines()]
    cache.write_text(
        "".join(
            json.dumps({k: v for k, v in row.items() if k != "asked_at"}) + "\n" for row in rows
        )
    )

    again = run(client=CacheOnlyJevClient(StubJevClient()), out_dir=tmp_path)

    measured = _row(_section(again.markdown, "## Cost and time"), "Jev wall clock, measured")
    assert measured[1].startswith("n/a")


def test_the_full_run_is_sized_over_all_53_documents_not_remembered(result):
    section = _section(result.markdown, "## Cost and time")
    # docs/cuad-ground-truth.md: 3,246 Clauses on the final partition. One call a Clause, carrying
    # all 7 Rules' questions, so 3,246 calls and not 3,246 x 7.
    assert _row(section, "Clauses, all 53 documents")[1] == "3,246"
    assert _row(section, "Jev calls for the full run")[1] == "3,246"


def test_the_report_says_savings_track_the_fully_binned_share(result):
    section = _section(result.markdown, "## Cost and time")
    assert "track the Fully Binned Clause share, not per-Rule Binned Share" in section
