"""The Rulebook: seven Rules, one positively phrased Detection Question each (ADR-0005).

The numbering keeps the gap at R4 so these ids stay comparable with the earlier notes. Uncapped
Liability was R4 and is dropped **because it is not independent of R1** — it appears in these
contracts as a carve-out from a cap, so the two Rules mark overlapping text — and because it was one
of the compound Rules.

It is *not* dropped for failing the gate. ADR-0005 said it was the only Rule to fail, at 16
documents and 23 spans, but that was measured before Pacira joined the corpus. On all 53 documents
it measures **17 documents and 26 spans** and passes the gate by one span. See the correction note
in ADR-0005.

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
#: counts rather than a remembered reason. They are never asked: they are not in `RULEBOOK`.
DROPPED_RULES: tuple[Rule, ...] = (
    Rule("R4", "Uncapped Liability", "Does this clause leave a party's liability uncapped?"),
)

#: Why each dropped Rule is out, for the report. Independence, not the gate — see the module
#: docstring and the correction note in ADR-0005.
DROPPED_REASONS: dict[str, str] = {
    "R4": (
        "It is not independent of R1 — uncapped liability appears in these contracts as a "
        "carve-out from a cap, so the two Rules mark overlapping text and cannot be read "
        "separately. It was also one of the compound Rules, whose sub-questions ADR-0005 drops."
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
                f"{rule_id} was dropped in ADR-0005: {DROPPED_REASONS[rule_id]} It passes the "
                "gate on the full 53 documents, at 17 documents and 26 spans"
            ) from None
        raise KeyError(f"Unknown rule {rule_id}; the Rulebook holds {sorted(_BY_ID)}") from None
