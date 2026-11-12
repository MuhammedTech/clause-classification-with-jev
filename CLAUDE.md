## Orientation

Four things that cost time to rediscover:

- **The CUAD dataset is not in this repo.** It is at `~/personal_coding/playground/cuad/CUAD_v1/`
  (`CUAD_v1.json`, `master_clauses.csv`, `full_contract_txt/`). Treat the path as configuration.
- **Facts about the data are already measured** in `docs/cuad-ground-truth.md`: the 53-document join,
  span-offset integrity, per-rule counts, base rates, clause volume and run size. Read it rather than
  re-deriving, and correct it if a run disagrees.
- **ADR-0002 is superseded by ADR-0003.** Do not implement grading from ADR-0002; it also contradicts
  itself on the miss budget units.
- **Some glossary terms inverted.** "Kept" and "Keep Share" used to mean the text Jev discards. The
  current terms are **Binned** (discarded) and **Escalated** (sent to the expensive model). See the
  retired-terms table at the bottom of `GLOSSARY.md` before reading any older note.

## Agent skills

### Issue tracker

Issues and specs are local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
