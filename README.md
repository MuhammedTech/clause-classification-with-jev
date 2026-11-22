# Clause classification with Jev

Measures how much CUAD license-agreement text Jev, a cheap decision model (TypeSafe calls it a System
One model), can **Bin** — discard before an expensive model ever reads it — and what that costs in
provisions nobody would look at, judged against lawyer highlights.

## Results

**Read this first: [the Operating Point tables](docs/operating-point.md)** — the full numbers, in this
repository, with the caveats beside them. The one picture is
[the Cutoff trade-off](docs/cutoff-tradeoff.png): how much Jev skips against how much it loses, with
the Operating Point and the fixed 0.5 Cutoff marked, drawn from the real run's stored answers. For a plain-language walkthrough of the real run with a worked
example, see the [Jev Cascade Results page](https://claude.ai/artifact/3Cg59wmFZPDAt4cSS8P5xX). The same
numbers are in the report that `--from-cache` rebuilds (see Running).

The real run was all 53 license agreements against seven Rules (3,246 Clauses, `jev-1.14.0`). **Minimum
Commitment was then dropped after its results were seen**: there is no lawyer to check its labels and no
more data. That departs from the Rule set agreed with the reviewer and makes the figures below, which are
over the six Rules left, more favourable than a Rule set fixed in advance. The seven-Rule figures are kept
beside them in ADR-0008. The question is how much Jev can skip, and the answer depends on how many
lawyer-marked provisions you will let it lose:

- **At a loss a legal reader would accept (aimed for 1% of marked provisions, got 1.1%): Jev skips about 1
  Clause in 3 (31.5%)** and loses 4 of 378 provisions. The Cutoff was chosen on one half of the documents
  and read on the other, both ways round: `docs/operating-point.md`. For the agreed seven Rules the same
  procedure at a 2% budget skipped 20.5% and lost 7 of 429 (1.6%).
- **The 2% budget did not hold over six Rules:** 64.6% skipped, but 4.2% lost (6.4% on the worse half).
  Do not quote that 64.6% without the loss beside it.
- **Cost, per 1,000 Clauses against sending everything to Claude Sonnet 5.5:** about $4.68 saved of $7.11
  at the 1% budget (an estimate: the expensive model was never run, and that figure rests on an assumed
  answer length; counting only the reading, the saving is about $0.28, or 25%). The baseline is lower than
  the seven-Rule $8.15 only because Claude is asked six questions; that is not a saving.
- **At a fixed Cutoff of 0.5, Jev skips 78.5% of Clauses but loses 26 of 378 provisions (6.9%).** That is
  the other end of the same curve, and too much loss for a legal team. Never quote the 78% without the 7%.
- **The answer is unstable.** Which half chooses the Cutoff moves the skip from 14.6% to 51.0% at the 1%
  budget, and the losses sit in few documents (2 of the 4 are in one). That is the main limitation.
- Five Rules catch 92 to 94% of lawyer-marked Clauses at 0.5; Change Of Control catches 75%.

Start with `GLOSSARY.md` for the vocabulary, `.scratch/jev-cascade/spec.md` for the method, and
`docs/cuad-ground-truth.md` for what has already been measured about the data.

## License

The code is MIT (see `LICENSE`). The CUAD dataset is not included and is downloaded separately (see
below), but a few tests quote short excerpts from CUAD contracts so each case is something a contract
actually does. CUAD is curated and maintained by The Atticus Project, Inc. and published under
CC BY 4.0; credit it wherever it is used (https://github.com/TheAtticusProject/cuad).

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
into the shell first: `set -a; . ./.env; set +a`. `--from-cache` needs no key.

**The real run (ticket 09)** is every document against every Rule, 3,246 calls: one per Clause, with all
seven Rules' questions in it (22,722 Pairs, still one cache row each). At most about $0.27 at the
published price; the command prints the input tokens Jev's replies reported, to check that against the
invoice. Each call is stamped with when it arrived, so the report
rebuilds from the cache with the real run's date and Jev time:

```
uv run jev-cascade --jev real --full --out out/real               # asks Jev; resumes if interrupted
uv run jev-cascade --jev real --full --out out/real --from-cache  # the final report; no key, no calls
```

The report is reproducible from the cache, not from scratch: real Jev moved by up to 0.04 between runs
on the same Pair (measured on one question a call, before the fan-out). `--full` cannot be combined with `--doc` or `--rule`. `--workers N` sets how many
calls are in flight (32 for the real client, 1 for the stub); it changes the speed, never the answers.

## Where things are

| Module | What it owns |
| --- | --- |
| `config.py` | The CUAD path, the output directory, prices and cost assumptions, each with its source and date |
| `corpus.py` | The 53-document License Agreement Set, the join, the Highlights, and the gate |
| `splitter.py` | Partitioning a document into Clauses |
| `rulebook.py` | The six Rules and their Detection Questions (ADR-0005; R6 dropped, ADR-0008) |
| `jev.py` | The Jev client interface and the deterministic seeded stub |
| `typesafe.py`, `clients.py` | The real Jev client (retries, rate spacing, pinned model) and the choice between it and the stub |
| `runner.py` | Asking every Pair once, and the JSONL P(yes) cache |
| `evaluator.py` | The pure metrics at one Cutoff, the Cutoff Curve and the free saving (ADR-0003) |
| `cost.py` | What the expensive model would be asked and cost, Jev's cost and time, per 1,000 Clauses (pure; no model is called) |
| `report.py` | Rendering the Markdown report |
| `operating_point.py`, `operating_point_report.py`, `operating_point_cli.py` | The Operating Point: a Cutoff chosen on one half of the documents and reported on the other, with its cost (ADR-0007). Nothing that grades a run imports these |
| `charts.py` | The per-Rule curve PNG and the curve CSV |
| `pipeline.py` | The stages wired together; the CLI is a thin wrapper |

The Operating Point (ticket 12) reads the real run's stored answers and writes `docs/operating-point.md`.
It needs no key and makes no calls, and rebuilds `out/real/report.md` from the cache as a side effect:

```
uv run jev-cascade-operating-point --out out/real
```

Ticket 08's sample (three question types, heading on against off, 1,357 real calls) is its own
command; it prints the plan before it asks anything and writes `docs/question-type-and-heading-sample.md`:

```
uv run jev-cascade-sample --jev real        # needs JEV_API_KEY
uv run jev-cascade-sample --jev real --from-cache   # rebuild the report, no key and no calls
```

## Status

Tickets 01 to 09, 11 and 12 are built. The real run is done: all 53 documents against all seven Rules
(Minimum Commitment dropped afterwards, ADR-0008), 22,722 Pairs in 3,246 fan-out calls, `jev-1.14.0`, 179 s, $0.085 as Jev reported it. The default
command still uses the signal-free stub (its figures carry no signal), so the real report is the one
built with `--jev real --full --out out/real`, and it is reproducible from the cache, not from scratch.
The report's Corpus and Rulebook sections are counted from CUAD over all 53 documents: the six
Rules with their document and span counts, and the gate, which all six pass.

Each ticket in `.scratch/jev-cascade/issues/` deepened one stage: 03 the Splitter, 04 and 05 the
metrics and the Cutoff Curve, 06 cost and time, 07 the real Jev client, 08 the question type and
heading, 09 the real run, and 12 the Operating Point.

One decision is waiting on the user: **Uncapped Liability (R4) passes the gate** over all 53
documents, at 17 documents and 26 spans. ADR-0005 dropped it partly for failing, measured before
Pacira joined the corpus. It stays out for not being independent of R1, which the new counts do not
change — see the correction note in ADR-0005.
