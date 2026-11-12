"""The Rulebook: seven Rules, one positively phrased Detection Question each (ADR-0005).

The numbering keeps the gap at R4 so these ids stay comparable with the earlier notes. Uncapped
Liability was R4 and is dropped: it is the only Rule failing the gate of at least 15 documents with
a span and at least 25 spans, and it is not independent of R1.

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

_BY_ID = {rule.id: rule for rule in RULEBOOK}


def rule(rule_id: str) -> Rule:
    """Look up one Rule by id."""
    try:
        return _BY_ID[rule_id]
    except KeyError:
        if rule_id == "R4":
            raise KeyError(
                "R4 was dropped in ADR-0005: it is the only Rule failing the gate, at 16 "
                "documents and 23 spans, and it is not independent of R1"
            ) from None
        raise KeyError(f"Unknown rule {rule_id}; the Rulebook holds {sorted(_BY_ID)}") from None
