"""Seam C: the finished report. One command writes every section, the curve and a chart per Rule."""

import re

import pytest

from jev_cascade import config
from jev_cascade.cli import main
from jev_cascade.jev import StubJevClient
from jev_cascade.pipeline import run

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

SECTIONS = (
    "## Summary",
    "## Run",
    "## How this is measured",
    "## Corpus",
    "## Rulebook and the gate",
    "## Partition",
    "## Documents scored in this run",
    "## R1 — ",
    "## Fully Binned Clauses",
    "## Reading the curve",
    "## What this does not measure",
    "## Vendor caveats",
)


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run(client=StubJevClient(), out_dir=tmp_path_factory.mktemp("finished"))


def _section(markdown: str, heading: str) -> str:
    start = markdown.index(heading)
    end = markdown.find("\n## ", start + len(heading))
    return markdown[start : end if end != -1 else len(markdown)]


def test_every_section_heading_is_present(result):
    for heading in SECTIONS:
        assert f"\n{heading}" in result.markdown, heading


def test_the_report_opens_with_the_per_rule_summary(result):
    first_heading = next(l for l in result.markdown.splitlines() if l.startswith("## "))
    assert first_heading == "## Summary"


def test_the_summary_leads_with_counts_and_the_lowest_held_score(result):
    summary = _section(result.markdown, "## Summary")
    (curve,) = result.curves
    saving = curve.saving
    assert saving is not None
    row = next(l for l in summary.splitlines() if l.startswith("| R1 "))
    assert f"{saving.metrics.holding_clauses}/{saving.clauses}" in row
    assert f"{saving.lowest_held_p_yes:g}" in row
    assert f"{saving.binned_words}/{saving.total_words} words" in row


def test_the_summary_shows_the_fully_binned_share_apart_from_the_per_rule_figures(result):
    summary = _section(result.markdown, "## Summary")
    fully = result.fully_binned
    assert f"{fully.fully_binned_clauses}/{fully.clauses} Clauses" in summary
    assert "does not combine" in summary


def test_the_curve_csv_has_one_row_per_distinct_observed_p_yes(result):
    (curve,) = result.curves
    distinct = {p for p in result.p_yes["R1"].values()}
    assert len(curve.rows) == len(distinct)
    csv_lines = (result.report_path.parent / curve.csv).read_text(encoding="utf-8").splitlines()
    assert len(csv_lines) == len(distinct) + 1  # plus the header
    assert csv_lines[0].startswith("cutoff,")


def test_a_per_rule_chart_is_written_as_a_png_and_referenced(result):
    (curve,) = result.curves
    chart = result.report_path.parent / curve.chart
    assert chart.read_bytes().startswith(PNG_MAGIC)
    assert f"]({curve.chart})" in result.markdown


def test_every_scored_table_is_labelled_stub(result):
    # Summary, the fixed-Cutoff table, the curve excerpt and the Fully Binned table.
    assert result.markdown.count("Stub-derived") >= 4


def test_accuracy_and_roc_auc_are_explained_but_never_reported(result):
    assert "Accuracy and ROC AUC are deliberately absent" in result.markdown
    for line in result.markdown.splitlines():
        if line.startswith("|"):
            assert "accuracy" not in line.lower() and "roc auc" not in line.lower(), line


def test_no_retired_term_appears(result):
    retired = (
        "Kept", "Keep Share", "Lower Cutoff", "Upper Cutoff", "Found Highlight",
        "Pending Highlight", "False Alarm", "Fold", "Miss Rate", "Fully Cleared",
        "Touch", "Lead-in", "Sub-question",
    )
    found = [t for t in retired if re.search(rf"\b{re.escape(t)}\b", result.markdown, re.I)]
    assert found == []


def test_the_two_readings_of_the_curve_are_named(result):
    section = _section(result.markdown, "## Reading the curve")
    assert "classifier reading" in section
    assert "cascade reading" in section
    assert "wrong" in section and "Jev's accuracy" in section


def test_how_this_is_measured_states_the_ground_truth_and_the_overlap_rule(result):
    section = _section(result.markdown, "## How this is measured")
    for phrase in (
        "only ground truth", "one character", "Clause Recall", "Provision Recall",
        "Certified Negative", "Inferred Negative",
    ):
        assert phrase in section, phrase


def test_the_corpus_section_relates_53_to_the_44(result):
    section = _section(result.markdown, "## Corpus")
    assert "53" in section and "44" in section and "PACIRA" in section.upper()


def test_the_report_states_the_vendor_caveats_and_the_optimism(result):
    caveats = _section(result.markdown, "## Vendor caveats")
    assert "self-run" in caveats
    assert "prompt-injection" in caveats
    assert "optimistically" in result.markdown


def test_the_three_unmeasured_things_are_stated(result):
    section = _section(result.markdown, "## What this does not measure")
    assert "confident yes" in section
    assert "expensive model" in section
    assert "lawyers highlighted everything" in section


def test_the_command_rebuilds_the_report_from_the_cache_without_asking_jev(tmp_path, capsys):
    assert main(["--out", str(tmp_path)]) == 0
    first = (tmp_path / "report.md").read_text(encoding="utf-8")
    (tmp_path / "report.md").unlink()

    assert main(["--out", str(tmp_path), "--from-cache"]) == 0
    assert "0 Jev calls" in capsys.readouterr().out
    rebuilt = (tmp_path / "report.md").read_text(encoding="utf-8")
    for heading in SECTIONS:
        assert f"\n{heading}" in rebuilt
    # Wall clock and call counts differ between runs; the figures do not.
    assert _section(rebuilt, "## Summary") == _section(first, "## Summary")


def test_from_cache_refuses_rather_than_asking_jev_when_the_cache_is_empty(tmp_path):
    with pytest.raises(SystemExit):
        main(["--out", str(tmp_path), "--from-cache"])
