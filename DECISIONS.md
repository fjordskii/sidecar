# Sidecar — Decisions (the loop's durable index)

`JOURNAL.md` is the narrative; a cycle only reads its tail, so anything older than a few days is
gone. **This file is what survives.** It is read *in full* every cycle, so it must stay small: rows,
not prose. One line each, newest at the bottom of its section.

If a decision needs to outlive this week — a trigger waiting to fire, why a position exists, a name
already ruled out — it belongs here. Everything else stays in the journal.

`ID` is `D-###`, monotonic, never reused. Cite it in the journal entry that opens or closes it.

## Baseline

Set once, at initialization. The fixed point every later cycle measures against.

- **Started:** {{DATE}} · **Capital:** _starting equity_ · **Benchmark:** _from the interview_
- **Opening positions:** _symbols and cost basis, or none_

## Open

Live commitments. **Nothing here ages out** — a row leaves only by being closed or cancelled, with
a reason. Read every row every cycle and honor it: it was set with more context than you have now.

`Kind`: ENTRY (why we own it) · TRIGGER (a condition to act on) · WATCH (a candidate and its entry
test) · AMEND (a mandate change, dated) · REPAIR (a known broken thing to fix).

| ID | Opened | Kind | Symbol | Decision | Fires when |
|---|---|---|---|---|---|
| D-000 | {{DATE}} | REPAIR | — | Prove the order path end to end before the first live cycle | first cycle runs |

## Closed

Keep the last ~20. Older rows move to `DECISIONS_ARCHIVE.md` — never delete them, the record of
what a trigger actually did is the only way to tell a good rule from a lucky one.

| ID | Opened | Closed | Symbol | Decision | Outcome |
|---|---|---|---|---|---|

## Ruled out

Names examined and passed on, so a later cycle doesn't re-litigate from scratch. Drop a row after
90 days — the reason goes stale and it deserves a fresh look.

| Date | Symbol | Why not |
|---|---|---|
