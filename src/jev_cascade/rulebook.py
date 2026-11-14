"""The Rulebook: six Rules, one positively phrased Detection Question each (ADR-0005, ADR-0008).

The numbering keeps the gaps at R4 and R6 so these ids stay comparable with the earlier notes and
with the real run's cache, which still holds R6's answers (they are ignored, never deleted).

Two Rules were dropped, for different reasons, and neither is the gate:

- **R4, Uncapped Liability**, because it is not independent of R1: it appears in these contracts as a
  carve-out from a cap, so the two Rules mark overlapping text. ADR-0005 said it was the only Rule to
  fail the gate, at 16 documents and 23 Highlights, but that was measured before Pacira joined the
  corpus. On all 53 documents it measures **17 documents and 26 Highlights** and passes the gate by
  one. See the correction note in ADR-0005.
- **R6, Minimum Commitment**, after the real run, because Jev could not separate it and its
  Highlights could not be checked (ADR-0008). **This was decided after seeing how it performed**, so
  every figure over six Rules is more favourable than one chosen blind, and the seven-Rule figures
  are kept in ADR-0008 beside them.

(CUAD's own files call a Highlight a span; `GLOSSARY.md` does not.)

R5 and R8 changed meaning from the original notes — Exclusivity replaced Non-Compete and
Anti-Assignment replaced Volume Restriction — so their results must not be compared to the old
rules. Ticket 05 puts that statement in the report; ticket 01's report covers one Rule only.

The wording below was approved by the user on 2026-11-13 (ticket 08), exactly as ADR-0005 drafted it.
"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Rule:
    """One of the Rulebook's six detection questions, mapped to one CUAD category."""

    id: str
    cuad_category: str
    detection_question: str


RULEBOOK: tuple[Rule, ...] = (
    Rule("R1", "Cap On Liability", "Does this clause cap or limit a party's liability?"),
    Rule(
        "R2",
        "Post-Termination Services",
        "Does this clause require help or obligations after termination?",
    ),
    Rule(
        "R3",
        "Termination For Convenience",
        "Does this clause let a party terminate without cause?",
    ),
    Rule("R5", "Exclusivity", "Does this clause grant or require exclusivity?"),
    Rule(
        "R7",
        "Change Of Control",
        "Does this clause give a right or trigger on a change of control?",
    ),
    Rule(
        "R8",
        "Anti-Assignment",
        "Does this clause restrict assigning or transferring the agreement?",
    ),
)

#: The Rules that were considered and dropped, kept here so the report can print their measured
#: counts rather than a remembered reason. They are never asked: they are not in `RULEBOOK`.
#: R4 carries no Detection Question, because ADR-0005 drafts wording only for Rules that are asked.
#: R6 keeps the question it was asked with in the real run, for the record, since its answers are
#: still in that run's cache.
DROPPED_RULES: tuple[Rule, ...] = (
    Rule("R4", "Uncapped Liability", ""),
    Rule(
        "R6",
        "Minimum Commitment",
        "Does this clause commit a party to a minimum purchase, payment or volume?",
    ),
)

#: Why each dropped Rule is out, for the report. R4 is out for independence, not the gate (see the
#: module docstring and the correction note in ADR-0005). R6 is out for performance and unverifiable
#: labels, and was dropped after its results were seen (ADR-0008).
DROPPED_REASONS: dict[str, str] = {
    "R4": (
        "It is not independent of R1 — uncapped liability appears in these contracts as a "
        "carve-out from a cap, so the two Rules mark overlapping text and cannot be read "
        "separately."
    ),
    "R6": (
        "Jev could not separate it: at the 0.5 Cutoff it lost 18 of its 51 Highlights, more than any "
        "other Rule, and some of the Highlights it missed read as technical performance "
        "requirements rather than purchase commitments, so the labels look inconsistent. With no "
        "lawyer to check them and no more data, it was removed after the "
        "real run, knowing how it performed (ADR-0008). Figures over the remaining Rules are "
        "therefore more favourable than a Rule set fixed in advance would give."
    ),
}


@dataclass(frozen=True)
class SupersededCounts:
    """A gate count ADR-0005 recorded that a later measurement corrected.

    Kept as data so the report can print the old figure beside the new one without the renderer
    carrying a number of its own, and so correcting it again means editing one place.
    """

    documents: int
    highlights: int
    why_it_changed: str


#: What ADR-0005 recorded for each dropped Rule, and why that measurement no longer stands.
SUPERSEDED_GATE_COUNTS: dict[str, SupersededCounts] = {
    "R4": SupersededCounts(
        documents=16,
        highlights=23,
        why_it_changed=(
            "measured before Pacira, which carries 3 Uncapped Liability Highlights by itself, "
            "joined the corpus"
        ),
    ),
}

#: R5 and R8 replaced thinner Rules and so must not be compared to the earlier notes' results.
REPLACED_RULES: dict[str, str] = {
    "R5": "Non-Compete",
    "R8": "Volume Restriction",
}

_BY_ID = {rule.id: rule for rule in RULEBOOK}


def rule(rule_id: str) -> Rule:
    """Look up one Rule by id."""
    try:
        return _BY_ID[rule_id]
    except KeyError:
        if rule_id in DROPPED_REASONS:
            raise KeyError(
                f"{rule_id} was dropped (ADR-0005, ADR-0008): {DROPPED_REASONS[rule_id]} See the "
                "counts the report prints"
            ) from None
        raise KeyError(f"Unknown rule {rule_id}; the Rulebook holds {sorted(_BY_ID)}") from None
