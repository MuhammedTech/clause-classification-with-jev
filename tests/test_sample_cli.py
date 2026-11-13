"""Ticket 08's command, end to end on real documents with the stub: no real Jev call is made."""

import pytest

from jev_cascade import config
from jev_cascade.jev import CountingJevClient, StubJevClient
from jev_cascade.sample_cli import main, run_study

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)


def test_the_study_asks_four_arms_and_a_rerun_asks_nothing(tmp_path):
    first = CountingJevClient(StubJevClient())
    inputs = run_study(first, tmp_path, held=3, not_held=6)

    pairs = inputs.sample.pairs
    # Three types with the heading shown, plus the chosen type with it taken out. The last arm
    # re-asks only the Clauses that had a heading, so the total is under four full arms.
    assert 3 * pairs < first.calls < 4 * pairs
    assert inputs.answers == first.calls
    assert inputs.chosen_type in ("binary", "score2", "choice2")

    second = CountingJevClient(StubJevClient())
    run_study(second, tmp_path, held=3, not_held=6)
    assert second.calls == 0


def test_the_command_prints_the_plan_before_asking_and_writes_the_report(tmp_path, capsys):
    report = tmp_path / "report.md"
    code = main(
        ["--out", str(tmp_path / "cache"), "--report", str(report), "--held", "3", "--not-held", "6"]
    )

    assert code == 0
    printed = capsys.readouterr().out
    assert "Pairs per arm" in printed
    assert printed.index("Pairs per arm") < printed.index("Wrote")
    text = report.read_text(encoding="utf-8")
    assert "Chosen question type" in text
    assert "no signal" in text  # the stub is labelled
