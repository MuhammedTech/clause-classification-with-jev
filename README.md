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
uv run jev-cascade --out out      # writes out/report.md and out/pyes.jsonl
uv run pytest
```

A second run answers every Pair from the cache and makes zero Jev calls. The tests that need CUAD
skip when it is absent.

```
uv run jev-cascade --rule R1 --cutoff 0.5 --out out
```

## Where things are

| Module | What it owns |
| --- | --- |
| `config.py` | The CUAD path, the output directory, prices with their source and date |
| `corpus.py` | The 53-document License Agreement Set, the join, and the Highlights |
| `splitter.py` | Partitioning a document into Clauses |
| `rulebook.py` | The seven Rules and their Detection Questions (ADR-0005) |
| `jev.py` | The Jev client interface and the deterministic seeded stub |
| `runner.py` | Asking every Pair once, and the JSONL P(yes) cache |
| `evaluator.py` | The pure metrics at one Cutoff (ADR-0003) |
| `report.py` | Rendering the Markdown report |
| `pipeline.py` | The stages wired together; the CLI is a thin wrapper |

## Status

Ticket 01, the tracer bullet, is built: one Rule (R1) on three documents with the stub client, at one
fixed Cutoff. **Every figure it prints is stub-derived and carries no signal.** The remaining tickets
in `.scratch/jev-cascade/issues/` deepen each stage.
