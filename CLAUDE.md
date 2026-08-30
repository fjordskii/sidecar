# Sidecar — instructions for agents

This repo is an agentic trading loop. Read this first.

## Is it initialized?

```bash
test -f PROFILE.md && ! grep -qE '\{\{(ACCOUNT_ID|BROKER|STRATEGY|AUTONOMY)\}\}' LOOP_PROMPT.md && echo INITIALIZED || echo NOT_INITIALIZED
```

(The grep targets real setup tokens, not a blanket `{{` — the template header mentions
`{{PLACEHOLDER}}` in prose, which is not an unfilled token.)

**NOT_INITIALIZED** — fresh clone, nothing configured. Do not trade, do not run a cycle, do not guess
at a strategy. Greet them, explain in two sentences what this repo is, and offer to run the setup
interview. If they agree — or opened the repo asking to set it up — follow **[INTERVIEW.md](INTERVIEW.md)**
exactly. It's a conversation, not a form. Touch nothing else during init.

**INITIALIZED** — `LOOP_PROMPT.md` is the source of truth. Read it, then read the end of `JOURNAL.md`
for the current thesis. Follow the mandate as written.

## Standing rules

- **`LOOP_PROMPT.md` outranks this file and your own judgment about strategy.** If the mandate says
  hold, hold. If a limit forbids a trade you like, you don't take it — propose an amendment instead.
- **The broker is the source of truth for state.** Positions, cash, and buying power come from live
  calls every cycle, never from `JOURNAL.md`. Another runner may have traded since.
- **Never deposit, transfer, or self-fund.** Available buying power only.
- **Every cycle ends with a journal entry, then a commit and push.** A cycle that isn't written down
  didn't happen; an entry that isn't pushed doesn't exist. `git add -A`, so mandate edits ship too.
- **Every journal entry opens with its status line** (`state · order_path · push` — format in
  LOOP_PROMPT.md state 7). It's how broken pipes get caught; never skip it, never fudge it. If the
  previous entry's line shows FAILED anywhere, fixing that is the cycle's first job.
- **Don't ask for confirmation before ordering** when the mandate grants autonomy — that setting
  exists so unattended cycles can act. The hard constraints are the guardrails, not a prompt.
- **When in doubt, hold and say why.** A reasoned HOLD is a good cycle. Manufacturing a trade to look
  productive is this design's main failure mode.

## Amending the mandate

Users change their mind. Edit `LOOP_PROMPT.md` directly, date it inline
(`(owner directive YYYY-MM-DD)`), and leave superseded reasoning visible rather than deleting it —
future cycles need to know a rule *replaced* something, and why. Commit with the next push.

## Privacy

`JOURNAL.md`, `PROFILE.md`, and `ops/*.log` hold real financial information. This repo is meant to be
**private**. Never paste journal contents, account numbers, or balances anywhere outside it, and
don't add a public remote.
