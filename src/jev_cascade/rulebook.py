"""The Rulebook: seven Rules, one positively phrased Detection Question each (ADR-0005).

The numbering keeps the gap at R4 so these ids stay comparable with the earlier notes. Uncapped
Liability was R4 and is dropped **because it is not independent of R1**: it appears in these
contracts as a carve-out from a cap, so the two Rules mark overlapping text. That is the only
argument that distinguishes it — R2 and R6 were compound Rules too and both survive.

It is *not* dropped for failing the gate. ADR-0005 said it was the only Rule to fail, at 16
documents and 23 Highlights, but that was measured before Pacira joined the corpus. On all 53
documents it measures **17 documents and 26 Highlights** and passes the gate by one. See the
correction note in ADR-0005. (CUAD's own files call a Highlight a span; `GLOSSARY.md` does not.)

R5 and R8 changed meaning from the original notes — Exclusivity replaced Non-Compete and
Anti-Assignment replaced Volume Restriction — so their results must not be compared to the old
rules. Ticket 05 puts that statement in the report; ticket 01's report covers one Rule only.

The wording below is drafted and awaits the user's review in ticket 08.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The question type Jev is asked with. It is part of the P(yes) cache key because the same
#: question asked as a different type gives very different probabilities.
QUESTION_TYPE = "binary"


@dataclass(frozen=True)
class Rule:
    """One of the Rulebook's seven detection questions, mapped to one CUAD category."""

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
        "R6",
        "Minimum Commitment",
        "Does this clause commit a party to a minimum purchase, payment or volume?",
    ),
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
#: counts rather than a remembered reason. They are never asked: they are not in `RULEBOOK`, and
#: they carry no Detection Question, because ADR-0005 drafts wording only for Rules that are asked
#: and all wording needs the user's review in ticket 08.
DROPPED_RULES: tuple[Rule, ...] = (Rule("R4", "Uncapped Liability", ""),)

#: Why each dropped Rule is out, for the report. Independence, not the gate — see the module
#: docstring and the correction note in ADR-0005.
#:
#: Being compound is deliberately absent: R2 and R6 were also to be asked as sub-questions and both
#: survive, so it does not distinguish R4 from the Rules that stayed. Independence is the only
#: argument that does.
DROPPED_REASONS: dict[str, str] = {
    "R4": (
        "It is not independent of R1 — uncapped liability appears in these contracts as a "
        "carve-out from a cap, so the two Rules mark overlapping text and cannot be read "
        "separately."
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
                f"{rule_id} was dropped in ADR-0005: {DROPPED_REASONS[rule_id]} It is not out for "
                "failing the gate, which it passes on the full corpus; see the correction note in "
                "ADR-0005 and the counts the report prints"
            ) from None
        raise KeyError(f"Unknown rule {rule_id}; the Rulebook holds {sorted(_BY_ID)}") from None
