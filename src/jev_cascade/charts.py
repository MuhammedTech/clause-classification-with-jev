"""The per-Rule Cutoff Curve chart, written as a PNG, and the curve itself as a CSV.

One chart per Rule: the Cutoff along the bottom, and three shares on a single 0 to 100% axis (never
two axes). Provision Recall and Precision answer "what does Escalating cost the expensive model and
what does Binning lose", and Binned Share is the saving. A dotted line marks the lowest P(yes) any
holding Clause was given: left of it, Binning loses nothing.

Colours are slots 1 to 3 of the reference categorical palette, light mode, on a white surface.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # headless: the report is rebuilt without a display

import matplotlib.pyplot as plt  # noqa: E402

from .evaluator import FreeSaving, RuleMetrics  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e3e2de"

PROVISION_RECALL = "#2a78d6"
BINNED_SHARE = "#eb6834"
PRECISION = "#1baf7a"

CSV_COLUMNS = (
    "cutoff",
    "binned_clauses",
    "escalated_clauses",
    "clause_recall",
    "provision_recall",
    "precision",
    "lost_provisions",
    "binned_words",
    "total_words",
    "binned_share",
)


def _cell(value: float | None) -> str:
    return "" if value is None else repr(value)


def write_curve_csv(rows: Sequence[RuleMetrics], path: Path) -> None:
    """The complete Cutoff Curve: one line per distinct observed P(yes), counts beside shares."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    repr(row.cutoff),
                    row.binned_clauses,
                    row.escalated_clauses,
                    _cell(row.clause_recall),
                    _cell(row.provision_recall),
                    _cell(row.precision),
                    row.lost_provisions,
                    row.binned_words,
                    row.total_words,
                    _cell(row.binned_share),
                ]
            )


def write_curve_chart(
    rule_label: str,
    rows: Sequence[RuleMetrics],
    saving: FreeSaving | None,
    path: Path,
    is_stub: bool,
) -> None:
    """Draw one Rule's curve to `path` as a PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(figsize=(7.5, 4.2), dpi=130, facecolor=SURFACE)
    axes.set_facecolor(SURFACE)

    cutoffs = [row.cutoff for row in rows]

    def series(values: list[float | None]) -> tuple[list[float], list[float]]:
        points = [(x, v * 100) for x, v in zip(cutoffs, values) if v is not None]
        return [x for x, _ in points], [y for _, y in points]

    lines = (
        ("Provision Recall", PROVISION_RECALL, [r.provision_recall for r in rows]),
        ("Binned Share", BINNED_SHARE, [r.binned_share for r in rows]),
        ("Precision", PRECISION, [r.precision for r in rows]),
    )
    for label, colour, values in lines:
        xs, ys = series(values)
        # Steps, not slopes: nothing is measured between two P(yes) values Jev actually gave.
        axes.plot(xs, ys, color=colour, linewidth=2, label=label, drawstyle="steps-post")

    if saving is not None:
        axes.axvline(saving.lowest_held_p_yes, color=INK_SECONDARY, linewidth=1, linestyle=":")
        axes.annotate(
            f"lowest P(yes) of a holding Clause: {saving.lowest_held_p_yes:g}",
            xy=(saving.lowest_held_p_yes, 100),
            xytext=(4, -4),
            textcoords="offset points",
            fontsize=8,
            color=INK_SECONDARY,
            va="top",
        )

    axes.set_xlim(0, 1)
    axes.set_ylim(0, 102)
    axes.set_xlabel("Cutoff: P(yes) at or below it is Binned", color=INK_SECONDARY, fontsize=9)
    axes.set_ylabel("Share (%)", color=INK_SECONDARY, fontsize=9)
    axes.grid(color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        axes.spines[spine].set_color(GRID)
    axes.tick_params(colors=INK_SECONDARY, labelsize=8)

    stub_note = " (stub: no signal)" if is_stub else ""
    axes.set_title(f"{rule_label}: Cutoff Curve{stub_note}", loc="left", color=INK, fontsize=11)
    axes.legend(loc="center left", frameon=False, fontsize=8, labelcolor=INK_SECONDARY)

    figure.tight_layout()
    figure.savefig(path, facecolor=SURFACE)
    plt.close(figure)
