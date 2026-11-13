"""Seam C: the report of a run on the real Jev, which says what it is and carries no stub label.

The real client is stood in for by the stub answering as `jev-1.14.0` with `is_stub` false, so the
report is rendered exactly as a real run would render it without a network call.
"""

from datetime import datetime, timezone

import pytest

from jev_cascade import config
from jev_cascade.jev import CacheOnlyJevClient, FanOutAnswers, StubJevClient
from jev_cascade.pipeline import run

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)

#: 2026-11-13 12:00:00 UTC, and the next answer a quarter of a second later, and so on.
RUN_START = datetime(2026, 11, 13, 12, 0, 0, tzinfo=timezone.utc).timestamp()


#: What each fake call reports having been billed.
TOKENS_PER_CALL = 1_000


class RealLikeClient(StubJevClient):
    def p_yes_many(self, clause_text, parent_line, questions, question_type):
        return FanOutAnswers(
            super().p_yes_many(clause_text, parent_line, questions, question_type),
            input_tokens=TOKENS_PER_CALL,
        )

    @property
    def model_version(self) -> str:
        return "jev-1.14.0"

    @property
    def is_stub(self) -> bool:
        return False


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("real")
    ticks = iter(RUN_START + 0.25 * n for n in range(100_000))
    run(client=RealLikeClient(), out_dir=out, now=lambda: next(ticks))
    # The report is rebuilt from the cache alone, as the final report is.
    return run(client=CacheOnlyJevClient(RealLikeClient()), out_dir=out)


def _run_table_row(markdown: str, label: str) -> str:
    line = next(l for l in markdown.splitlines() if l.startswith(f"| {label} |"))
    return line.strip().strip("|").split("|")[1].strip()


def test_the_run_table_gives_the_model_version_question_type_heading_and_date(result):
    markdown = result.markdown
    assert _run_table_row(markdown, "Model version") == "jev-1.14.0"
    assert _run_table_row(markdown, "Question type") == config.QUESTION_TYPE
    assert _run_table_row(markdown, "Heading context") == "on"
    # The date the answers were asked, read from the cache, not the day the report was rebuilt.
    assert _run_table_row(markdown, "Run date") == "2026-11-13"


def test_the_report_states_the_switch_from_stub_to_real(result):
    markdown = result.markdown
    assert "## From the stub to the real Jev" in markdown
    section = markdown[markdown.index("## From the stub to the real Jev") :]
    section = section[: section.find("\n## ", 5)]
    assert "jev-1.14.0" in section
    assert "2026-11-13" in section


def test_no_figure_is_labelled_as_stub(result):
    # The switch statement is the one place the stub is named, because it says what changed.
    mentions = [l for l in result.markdown.splitlines() if "stub" in l.lower()]
    switch = result.markdown.index("## From the stub to the real Jev")
    first_after = result.markdown.index("\n## ", switch + 5)
    allowed = result.markdown[switch:first_after].splitlines()
    assert [l for l in mentions if l not in allowed] == []


def test_the_report_says_it_is_reproducible_from_the_cache_not_from_scratch(result):
    markdown = result.markdown
    assert "reproducible from the cache, not from scratch" in markdown.lower()
    assert "0.04" in markdown


def test_the_summary_puts_net_savings_beside_the_fully_binned_share(result):
    markdown = result.markdown
    summary = markdown[markdown.index("## Summary") : markdown.index("## Run")]
    assert "Fully Binned Clauses" in summary
    assert "Net savings" in summary
    assert "Claude Sonnet 5.5" in summary


def test_the_measured_jev_time_is_the_run_s_own_and_not_called_stub(result):
    markdown = result.markdown
    line = next(l for l in markdown.splitlines() if l.startswith("| Jev wall clock, measured |"))
    assert "stub" not in line
    # A quarter of a second an answer, per 1,000 Clauses of one Rule.
    assert "250.0s" in line


def test_the_report_says_every_rule_is_asked_in_one_call_and_what_that_changes(result):
    markdown = result.markdown
    asked = markdown[markdown.index("## How Jev is asked") : markdown.index("## How this is measured")]
    assert "one call" in asked.lower()
    # Ticket 08 settled the wording on one question a call, so the full run is not that experiment.
    assert "ticket 08" in asked and "one question a call" in asked

    cost = markdown[markdown.index("## Cost and time") : markdown.index("## Reading the curve")]
    assert "one call per Clause" in cost
    # The token figure is the cautious one until the replies' own usage is known.
    assert "cautious" in cost


def test_the_cost_section_puts_what_jev_billed_beside_the_estimate(result):
    markdown = result.markdown
    cost = markdown[markdown.index("### What Jev billed") : markdown.index("### The full run")]
    calls = result.cost.usage.jev.calls  # one call a Clause
    measured = calls * TOKENS_PER_CALL

    def row(label):
        line = next(l for l in cost.splitlines() if l.startswith(f"| {label}"))
        return line.strip().strip("|").split("|")[1].strip()

    assert row("Input tokens Jev reported") == f"{measured:,}"
    estimated = result.cost.usage.jev.input_tokens
    assert row("Estimated for the same run") == f"{estimated:,}"
    # Reported over estimated tells whether Jev bills the Clause once a call or once a question.
    assert row("Reported against estimated") == f"{measured / estimated:.1%}"
    assert row("Cost at the published price, from the reported tokens") == (
        f"${measured * config.JEV_INPUT_PRICE.value / 1_000_000:.4f}"
    )


def test_a_cache_with_no_usage_says_the_bill_is_not_recorded(tmp_path):
    out = tmp_path
    # The plain stub does not report usage, so no row carries it.
    run(client=StubJevClient(), out_dir=out)
    again = run(client=CacheOnlyJevClient(StubJevClient()), out_dir=out)
    cost = again.markdown[again.markdown.index("### What Jev billed") :]
    assert "not recorded" in cost[: cost.index("### The full run")].lower()
