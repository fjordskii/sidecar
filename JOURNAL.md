# Sidecar — Journal (the loop's memory)

This file is the loop's memory. Every cycle appends a `## CYCLE` entry: portfolio snapshot,
news and analysis, the thesis, and any orders placed. **The most recent CYCLE entry is the current
thesis.** Do not delete history — rotate it into `JOURNAL_ARCHIVE.md` when this file passes ~250KB.

Entries are written for a stranger: the next cycle is a fresh session with no memory of the reasoning
that produced this one.

Every entry opens with a **status line**: `state: TRADED|HOLD|SKIPPED · order_path: OK|FAILED|NOT_TESTED
· push: VERIFIED|FAILED`. It's the loop's health check — a cycle reads the previous entry's status
line before anything else, and `order_path: FAILED` or `push: FAILED` becomes that cycle's first
repair job. Definitions live in LOOP_PROMPT.md, state 7.

## Standing rules

_Filled in during setup — a compact summary of the hard limits in `LOOP_PROMPT.md`, which remains the
authority if the two ever disagree._

- Account: **{{ACCOUNT_ID}}** at **{{BROKER}}** — the only account this loop may touch.
- Mode: **{{LIVE_OR_PAPER}}** · **{{AUTONOMY}}**
- Instruments: **{{INSTRUMENTS}}**
- Sizing: available buying power only. **Never deposit, transfer, or self-fund.**
- Max position **{{MAX_POSITION}}** · concentration ceiling **{{CONCENTRATION_CEILING}}**
- Never: **{{NEVER_ALLOWED}}**
- Do not duplicate the core: **{{DO_NOT_DUPLICATE}}**
- Broker state outranks this file. Always re-read live positions and buying power.

## Portfolio baseline

_Set at initialization. The starting point every later cycle measures against._

---

## CYCLE 0 — initialized {{DATE}}

**Portfolio:** _starting capital, positions (or none)_
**Thesis:** _the opening thesis from the setup interview — what this sleeve is for and what it
intends to own_
**Orders:** none — loop initialized, not yet scheduled
**Notes/next:** _what the first live cycle should do: verify the broker connection end to end
(including a review/preview call to prove the order path works), then act on the opening thesis_
