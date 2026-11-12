"""The Corpus: the License Agreement Set and its Highlights.

The 53 documents are the CSV rows whose `Document Name` contains "licen". The JSON has no
`Document Name` field, so each row is joined to the annotation JSON by comparing the CSV `Filename`
to the JSON `title` on **alphanumerics only, lowercased**, with the `.pdf` / `.txt` extension
stripped first. With that normalisation all 53 resolve; without it Pacira fails, whose filename says
`A&R` where the title says `A_R`.

Two other filters give different counts and are not the set we use: CSV `Filename` containing
"licen" gives 44, and JSON `title` containing "licen" gives 44.

Document text comes from the JSON `context`, the same record the Highlight offsets are measured
against. The `full_contract_txt/` files can differ in whitespace, which would silently shift every
overlap.

Ticket 02 deepens this module with the Rulebook gate and the measured assertions from
`docs/cuad-ground-truth.md`.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

from . import config
from .domain import Highlight
from .rulebook import RULEBOOK, Rule

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]")
_EXTENSION = re.compile(r"\.(pdf|txt)$", re.IGNORECASE)


def join_key(name: str) -> str:
    """Normalise a filename or title for the join: extension off, alphanumerics only, lowercased.

    The extension is stripped as an explicit `.pdf` / `.txt` suffix rather than with
    `os.path.splitext`, which would cut a title like `..._EX-10.B(01)_Content License Agreement`
    at its last dot and truncate most of the name away.
    """
    return _NON_ALPHANUMERIC.sub("", _EXTENSION.sub("", name.strip()).lower())


@dataclass(frozen=True)
class Document:
    """One contract, its text, and the Highlights lawyers marked on it."""

    doc_id: str
    document_name: str
    filename: str
    text: str
    highlights: tuple[Highlight, ...]
    certified_negative_rules: frozenset[str]

    def highlights_for(self, rule_id: str) -> tuple[Highlight, ...]:
        return tuple(h for h in self.highlights if h.rule_id == rule_id)

    def is_certified_negative(self, rule_id: str) -> bool:
        """Whether CUAD flags this document as having no such clause anywhere."""
        return rule_id in self.certified_negative_rules

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@lru_cache(maxsize=2)
def _load_json(path: str) -> dict[str, dict]:
    """The annotation JSON, indexed by normalised title. Cached: the file is 38 MB."""
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {join_key(record["title"]): record for record in payload["data"]}


def _license_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if "licen" in row["Document Name"].lower()]


def filter_counts(directory: Path | None = None) -> dict[str, int]:
    """The three filters that give three different counts, kept so the difference stays documented."""
    directory = directory or config.cuad_dir()
    with config.master_clauses_csv(directory).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    records = _load_json(str(config.cuad_json(directory)))
    return {
        "csv_document_name": sum(1 for r in rows if "licen" in r["Document Name"].lower()),
        "csv_filename": sum(1 for r in rows if "licen" in r["Filename"].lower()),
        "json_title": sum(1 for r in records.values() if "licen" in r["title"].lower()),
    }


def load_corpus(
    rules: Sequence[Rule] | None = None,
    doc_ids: Iterable[str] | None = None,
    directory: Path | None = None,
) -> tuple[Document, ...]:
    """Load the License Agreement Set, with the Highlights for `rules`.

    `doc_ids` selects a subset by JSON title, which is what the tracer run uses.
    """
    rules = list(rules if rules is not None else RULEBOOK)
    directory = directory or config.cuad_dir()
    wanted = {join_key(d) for d in doc_ids} if doc_ids is not None else None

    records = _load_json(str(config.cuad_json(directory)))
    documents: list[Document] = []
    missing: list[str] = []

    for row in _license_rows(config.master_clauses_csv(directory)):
        key = join_key(row["Filename"])
        record = records.get(key)
        if record is None:
            missing.append(row["Filename"])
            continue
        if wanted is not None and key not in wanted:
            continue

        paragraph = record["paragraphs"][0]
        text = paragraph["context"]
        doc_id = record["title"]

        by_category = {
            qa["id"].split("__", 1)[1]: qa for qa in paragraph["qas"] if "__" in qa["id"]
        }

        highlights: list[Highlight] = []
        certified: set[str] = set()
        for rule in rules:
            qa = by_category.get(rule.cuad_category)
            if qa is None:
                continue
            if qa.get("is_impossible"):
                certified.add(rule.id)
                continue
            for answer in qa["answers"]:
                start = answer["answer_start"]
                highlights.append(
                    Highlight(
                        doc_id=doc_id,
                        rule_id=rule.id,
                        start=start,
                        end=start + len(answer["text"]),
                        text=answer["text"],
                    )
                )

        documents.append(
            Document(
                doc_id=doc_id,
                document_name=row["Document Name"],
                filename=row["Filename"],
                text=text,
                highlights=tuple(highlights),
                certified_negative_rules=frozenset(certified),
            )
        )

    if missing:
        raise RuntimeError(
            f"{len(missing)} license documents did not join to the annotation JSON: "
            f"{missing[:3]}. All 53 resolve when the join compares alphanumerics only."
        )
    if wanted is not None:
        found = {join_key(d.doc_id) for d in documents}
        unknown = wanted - found
        if unknown:
            raise RuntimeError(f"No License Agreement Set document matches {sorted(unknown)}")

    return tuple(documents)
