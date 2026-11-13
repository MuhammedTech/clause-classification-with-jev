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


# --------------------------------------------------------------------------------------------------
# How Jev is asked. Both settings are set from ticket 08's sample runs and printed in the report.
# --------------------------------------------------------------------------------------------------

#: The question type Jev is asked with, one for every Rule. It is part of the P(yes) cache key
#: because the same question asked as a different type gives different probabilities. `binary` is
#: Jev's yes/no type (sent as `noul`); `score2` and `choice2` are the other two ticket 08 compared.
#: Set from ticket 08's sample on 2026-11-13 (`docs/question-type-and-heading-sample.md`): mean
#: separation over the seven Rules was 0.980 for `binary`, 0.973 for `score2` and 0.973 for
#: `choice2`, so neither beat `binary` by the 0.02 margin fixed in advance and `binary` stands.
QUESTION_TYPE = "binary"

#: Whether Jev is shown a section heading as the Parent Line. A Parent Line that introduces a list,
#: such as "Licensee shall:", is always shown; only a standalone heading is taken out when this is
#: off (ticket 08). That is 459 of the 1,269 Clauses that have a Parent Line: 433 introduce a list
#: and 377 are longer lines with body text on them, which stay in both settings.
#: Set from the same sample: taking the heading out changed mean separation by +0.000 (95%
#: interval -0.002 to +0.002), well under the 0.02 it needed to come out, so it stays on. The sample
#: is near its ceiling and holds only 40 near misses, so this is "no difference detectable", which
#: is weaker than "no difference".
HEADING_CONTEXT = True


# --------------------------------------------------------------------------------------------------
# Prices and cost assumptions. Every number the cost model uses lives here, with where it came from
# and when, so correcting one is an edit to one place and the report can print its source.
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Sourced:
    """A number with its unit, where it came from and the date it was read.

    `source` says plainly when a figure is an assumption or unverified, because the report prints it.
    """

    value: float | str
    unit: str
    source: str
    as_of: str


@dataclass(frozen=True)
class ExpensiveModel:
    """One expensive model's list price, per million tokens, in and out."""

    name: str
    input: Sourced
    output: Sourced


_CLAUDE_LIST_PRICES_SOURCE = (
    "Anthropic list price as cached in the claude-api skill's model table, not read from the "
    "pricing page; confirm against it"
)
_CLAUDE_LIST_PRICES_AS_OF = "2026-11-03"
_USD_PER_MTOK = "USD per million tokens"


def _claude_price(value: float) -> Sourced:
    return Sourced(value, _USD_PER_MTOK, _CLAUDE_LIST_PRICES_SOURCE, _CLAUDE_LIST_PRICES_AS_OF)


#: The two expensive models the cascade is priced against. Sonnet first: it is the headline row.
EXPENSIVE_MODELS: tuple[ExpensiveModel, ...] = (
    ExpensiveModel("Claude Sonnet 5.5", input=_claude_price(2.00), output=_claude_price(10.00)),
    ExpensiveModel("Claude Opus 5.5", input=_claude_price(4.00), output=_claude_price(20.00)),
)

#: The Message Batches discount on the expensive model. It does not apply to Jev.
BATCH_DISCOUNT = Sourced(
    0.5,
    "multiplier on the expensive model's price",
    "Anthropic Message Batches run asynchronously at 50% of list price, per the claude-api skill; "
    "confirm against the pricing page",
    _CLAUDE_LIST_PRICES_AS_OF,
)

#: The Jev model the real client asks, **pinned to a version, never `jev-latest`**. The runner reads
#: the model version before the first call and puts it in every cache key, so it must be known
#: without a network call, and an alias that moved would serve old answers under a new model.
JEV_MODEL = Sourced(
    "jev-1.14.0",
    "model id sent in the request's `model` field",
    "https://docs.typesafe.ai/models.md: `jev-latest` points to jev-1.14.0 (released 2026-10-14); "
    "the page advises sending the version id, not the alias, when results must stay stable",
    "2026-11-12",
)

#: The System One endpoint: POST, `Authorization: Bearer <key>`, JSON body `{model, state, questions}`.
JEV_ENDPOINT = Sourced(
    "https://api.typesafe.ai/v1/systemone",
    "URL",
    "https://docs.typesafe.ai/introduction/quickstart.md (official quick start)",
    "2026-11-12",
)

#: What Jev charges, on input tokens only: its answer is one probability, so output is taken as free.
JEV_INPUT_PRICE = Sourced(
    0.042,
    _USD_PER_MTOK,
    "https://docs.typesafe.ai/models.md: $42 per billion tokens for Jev 1.14 and 1.13, input "
    "tokens billed, output tokens free (vendor's official models page; no separate pricing page "
    "exists in its docs index)",
    "2026-11-12",
)

#: Jev's published request limit, which sets how fast the full run can go.
JEV_RATE_LIMIT_PER_MINUTE = Sourced(
    1200,
    "requests per minute",
    "unverified: several third-party blogs agree on 1,200 requests a minute and 250,000 input "
    "tokens a second, but the vendor's models page says only that limits are set per organization, "
    "in tokens and requests per second, and shown in the developer console. Check the console",
    "2026-11-12",
)

#: How much text one Jev call can take. A Clause plus its Parent Line must fit under both.
JEV_CONTEXT_PER_REQUEST_TOKENS = Sourced(
    64_000,
    "tokens per request: the state plus all questions",
    "https://docs.typesafe.ai/models.md (default context window); 262,000 with the "
    "`TypeSafe-Danger-Zone-Long-Context: true` header, which this client does not send",
    "2026-11-12",
)

JEV_CONTEXT_PER_QUESTION_TOKENS = Sourced(
    32_000,
    "tokens per question: the state plus that one question",
    "https://docs.typesafe.ai/models.md (default context window). With every Rule's question in "
    "one call the request limit also applies, but neither is near the largest Clause. Over it the "
    "API answers HTTP 400 `max_tokens_exceeded` (https://docs.typesafe.ai/api/errors.md)",
    "2026-11-12",
)

# The three numbers below are ASSUMPTIONS, not prices, and the report says so. They size the
# expensive model's call, which never runs.

#: There is no tokenizer in the code and the report rebuilds with no network, so tokens are counted
#: as characters over this. A Claude count would differ, and Jev's tokenizer is a third one.
CHARS_PER_TOKEN = Sourced(
    4.0,
    "characters per token",
    "assumption: the usual rule of thumb for English prose, not measured on CUAD; legal text with "
    "numbers and cross-references probably tokenises denser. Replace it with a `count_tokens` run "
    "to firm it up",
    "2026-11-12",
)

#: The fixed instruction each expensive call carries around the Parent Line, Clause and questions.
EXPENSIVE_OVERHEAD_TOKENS = Sourced(
    200,
    "tokens per expensive call",
    "assumption: a short instruction asking the model to find and quote any provision answering "
    "the listed questions; no real prompt exists yet",
    "2026-11-12",
)

#: What the expensive model writes back per question it is asked: a yes/no and a quoted span.
EXPENSIVE_OUTPUT_TOKENS_PER_QUESTION = Sourced(
    100,
    "output tokens per question asked",
    "assumption: a yes/no plus a short quotation of the provision, about 60 words. Reasoning "
    "tokens are NOT included, and both models think by default, so every expensive-model figure "
    "is probably an underestimate. This is the softest number in the cost table",
    "2026-11-12",
)
