"""Where the data and the run output live, and what things cost.

The CUAD dataset is **not in this repo**. Its location is configuration, not a constant: set
`CUAD_DIR` to override the default.
"""

from __future__ import annotations

import os
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
