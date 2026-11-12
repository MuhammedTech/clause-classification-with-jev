"""Where the data and the run output live, and what things cost.

The CUAD dataset is **not in this repo**. Its location is configuration, not a constant: set
`CUAD_DIR` to override the default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: Default location of the unpacked CUAD v1 dataset.
DEFAULT_CUAD_DIR = "~/personal_coding/playground/cuad/CUAD_v1"

#: Default place for the P(yes) cache and the rendered report.
DEFAULT_OUT_DIR = "out"


def cuad_dir() -> Path:
    """The unpacked CUAD v1 directory, from `CUAD_DIR` or the default."""
    return Path(os.environ.get("CUAD_DIR") or DEFAULT_CUAD_DIR).expanduser()


def cuad_json(directory: Path | None = None) -> Path:
    return (directory or cuad_dir()) / "CUAD_v1.json"


def master_clauses_csv(directory: Path | None = None) -> Path:
    return (directory or cuad_dir()) / "master_clauses.csv"


def cuad_is_available(directory: Path | None = None) -> bool:
    """Whether the dataset is present. The tests that need it skip when it is not."""
    directory = directory or cuad_dir()
    return cuad_json(directory).exists() and master_clauses_csv(directory).exists()


@dataclass(frozen=True)
class Price:
    """A price with its source and the date it was taken, so a stale figure is visible."""

    usd_per_million_input_tokens: float
    source: str
    taken_on: str
    confirmed: bool


#: Jev's input price. Ticket 06 turns this into the savings estimate; it must be confirmed when the
#: key arrives, because it comes from a single unverified third-party blog.
JEV_INPUT_PRICE = Price(
    usd_per_million_input_tokens=0.042,
    source="unverified third-party blog; see docs/cuad-ground-truth.md",
    taken_on="2026-11-11",
    confirmed=False,
)
