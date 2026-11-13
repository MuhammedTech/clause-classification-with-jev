# Clause classification with Jev

Measures how much CUAD license-agreement text Jev, a cheap decision model, can **Bin** — discard
before an expensive model ever reads it — and what that costs in provisions nobody would look at,
judged against lawyer highlights.

Start with `GLOSSARY.md` for the vocabulary, `.scratch/jev-cascade/spec.md` for the method, and
`docs/cuad-ground-truth.md` for what has already been measured about the data.

## The dataset is not in this repo

It lives at `~/personal_coding/playground/cuad/CUAD_v1/`. Point `CUAD_DIR` somewhere else if needed:

```sh
export CUAD_DIR=/path/to/CUAD_v1
```

## Running

```sh
uv sync --extra dev
uv run jev-cascade --out out      # writes out/report.md, out/charts/, out/curves/ and out/pyes.jsonl
uv run pytest
```

A second run answers every Pair from the cache and makes zero Jev calls. The tests that need CUAD
skip when it is absent.

```
uv run jev-cascade --rule R1 --cutoff 0.5 --out out
uv run jev-cascade --out out --from-cache   # rebuild the report from the cache; never asks Jev
```

The default is the signal-free stub. `--jev real` asks TypeSafe's Jev (pinned to `jev-1.14.0`) and
reads the key from `JEV_API_KEY` in the environment, never from the repo. Load a git-ignored `.env`
into the shell first: `set -a; . ./.env; set +a`. `--from-cache` needs no key. `--workers N` sets how many
calls are in flight (32 for the real client, 1 for the stub); it changes the speed, never the answers.

## Where things are

| Module | What it owns |
| --- | --- |
| `config.py` | The CUAD path, the output directory, prices and cost assumptions, each with its source and date |
| `corpus.py` | The 53-document License Agreement Set, the join, the Highlights, and the gate |
| `splitter.py` | Partitioning a document into Clauses |
| `rulebook.py` | The seven Rules and their Detection Questions (ADR-0005) |
| `jev.py` | The Jev client interface and the deterministic seeded stub |
| `typesafe.py`, `clients.py` | The real Jev client (retries, rate spacing, pinned model) and the choice between it and the stub |
| `runner.py` | Asking every Pair once, and the JSONL P(yes) cache |
| `evaluator.py` | The pure metrics at one Cutoff, the Cutoff Curve and the free saving (ADR-0003) |
| `cost.py` | What the expensive model would be asked and cost, Jev's cost and time, per 1,000 Clauses (pure; no model is called) |
| `report.py` | Rendering the Markdown report |
| `charts.py` | The per-Rule curve PNG and the curve CSV |
| `pipeline.py` | The stages wired together; the CLI is a thin wrapper |

Ticket 08's sample (three question types, heading on against off, 1,357 real calls) is its own
command; it prints the plan before it asks anything and writes `docs/question-type-and-heading-sample.md`:

```
uv run jev-cascade-sample --jev real        # needs JEV_API_KEY
uv run jev-cascade-sample --jev real --from-cache   # rebuild the report, no key and no calls
```

## Status

Tickets 01 to 08 and 11 are built. The run scores one Rule (R1) on three documents with the stub client at
one fixed Cutoff plus the whole Cutoff Curve, and **every figure it prints is stub-derived and
carries no signal** (the cost section's full-run Jev estimate is the exception: it needs no P(yes)).
The report's
Corpus and Rulebook sections, by contrast, are counted from CUAD over all 53 documents: the seven
Rules with their document and span counts, and the gate, which all seven pass.

The remaining tickets in `.scratch/jev-cascade/issues/` deepen each stage. Ticket 03 settles the
Splitter, 04 and 05 the metrics and the Cutoff Curve, 06 cost and time, 07 the real Jev client, and 09 runs it.

One decision is waiting on the user: **Uncapped Liability (R4) passes the gate** over all 53
documents, at 17 documents and 26 spans. ADR-0005 dropped it partly for failing, measured before
Pacira joined the corpus. It stays out for not being independent of R1, which the new counts do not
change — see the correction note in ADR-0005.
