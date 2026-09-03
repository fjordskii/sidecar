# Sidecar — instructions for agents

This repo is an agentic trading loop. Read this first.

## Is it initialized?

```bash
test -f PROFILE.md && ! grep -qE '\{\{(ACCOUNT_ID|BROKER|STRATEGY|AUTONOMY)\}\}' LOOP_PROMPT.md && echo INITIALIZED || echo NOT_INITIALIZED
```

(The grep targets real setup tokens, not a blanket `{{`: the template header mentions
`{{PLACEHOLDER}}` in prose, which is not an unfilled token.)

**NOT_INITIALIZED** means a fresh clone with nothing configured. Do not trade, do not run a cycle, do not guess
at a strategy. Which init path depends on what you are:

- **Interactive session** (a human is talking to you): greet them, explain in two sentences what this
  repo is, and offer to run the setup interview. If they agree (or opened the repo asking to set it
  up), follow **[INTERVIEW.md](INTERVIEW.md)** exactly. It's a conversation, not a form. Touch nothing
  else during init.
- **Non-interactive runner** (a scheduled routine with nobody to talk to): run **auto-init**, below,
  then stop. Never attempt the interview; there is no one to answer.

### Auto-init (non-interactive runner, NOT_INITIALIZED)

Mechanical setup only; zero judgment calls. Do all of it, then stop:

1. **Verify broker auth** — call the accounts endpoint (Robinhood: `get_accounts`). On failure,
   append a `SKIPPED — not authenticated` entry and stop cleanly.
2. **Account ID** — find the account designated for agent trading in that response. That identifier
   fills every account field below. If several or none are designated, stop and say so in the entry.
3. **Live capital**: pull the portfolio for that account; current equity is the starting capital.
4. **Write the setup files from `setup-schema.json` defaults**, never from invention. Three tokens
   have no schema default; use exactly these sources:
   - `ACCOUNT_ID` — step 2.
   - `STRATEGY` — "Hold what exists and open nothing new until the owner personalizes this mandate."
   - `KILL_SWITCH` (lands in the never-allowed list) — "any order the owner did not expect: halt and
     ask before trading again."
   Live values beat defaults: starting capital from step 3, not the schema's "unspecified" string.
   Files:
   - `PROFILE.md` — every value, each marked `(default — not yet confirmed)` except the two live
     fetches (account ID, starting capital), which are confirmed by the API itself.
   - `LOOP_PROMPT.md` — placeholders filled from schema defaults; broker Robinhood, account ID from
     step 2, LIVE mode, **PROPOSE-ONLY autonomy**. Never auto-init to full autonomy; that upgrade is
     a human decision made in an interactive session. If a value has no schema default and no live
     source, delete its section or line outright rather than writing a stub; a cold agent will try
     to satisfy a stub. (Auto-init keeps the cross-sector scan default and the not-to-duplicate
     list, and drops the optional outside-account check.)
   - `JOURNAL.md` — standing rules from the hard limits, plus a CYCLE 0 entry noting this was an
     automated init.
5. **Completion gate** — grep the three files for `{{`: no `{{TOKEN}}` may survive. (Exempt: the
   word PLACEHOLDER in `run.sh` prose and its local-only `{{CLI_PATH}}`/`{{NODE_PATH}}`/`{{REPO_PATH}}`,
   which only a local scheduler fills.)
6. **Prove the order path** with one review/preview call. No order is placed; autonomy is
   propose-only regardless.
7. **Commit and push everything** (detached-HEAD refspec if applicable), verify the remote SHA.
8. **End the entry with a note to the owner**: open this repo in an interactive session and say
   "initialize" to personalize the mandate. The loop proposes but never trades until then.

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
- **`DECISIONS.md` is the memory that doesn't age out.** A cycle reads only the journal's tail, so
  anything a future cycle must honor — a trigger, why a position exists, a name already ruled out —
  gets a row there in the same breath as the journal entry. Read it in full at SYNC, update it at
  JOURNAL, keep it terse.
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
