# Sidecar — repo instructions for agents

This repo is an agentic trading loop. Read this before doing anything else here.

## First: is this repo initialized?

Check whether `PROFILE.md` exists **and** `LOOP_PROMPT.md` contains no `{{PLACEHOLDER}}` tokens:

```bash
test -f PROFILE.md && ! grep -q '{{' LOOP_PROMPT.md && echo INITIALIZED || echo NOT_INITIALIZED
```

**If NOT_INITIALIZED** — the user has just cloned the template and nothing is configured yet. Do not
start trading, do not run a cycle, and do not guess at a strategy. Instead:

> Greet them, explain in two sentences what this repo is, and offer to run the setup interview.
> If they agree (or if they opened the repo asking to set it up, initialize it, or get started),
> follow **[INTERVIEW.md](INTERVIEW.md)** exactly.

The interview is a conversation, not a form. Its output is `PROFILE.md` plus a fully filled-in
`LOOP_PROMPT.md` and a seeded `JOURNAL.md`. Nothing else in the repo should be touched during init.

**If INITIALIZED** — `LOOP_PROMPT.md` is the source of truth for everything the loop does. Read it,
then read the end of `JOURNAL.md` for the current thesis. Follow the mandate as written.

## Standing rules once initialized

- **`LOOP_PROMPT.md` outranks this file and outranks your own judgment about strategy.** If the
  mandate says hold, hold. If the user's stated risk limit forbids a trade you like, you don't take
  it. Propose an amendment to the mandate instead — that's the legitimate path.
- **The broker is the source of truth for state.** Positions, cash, and buying power come from live
  API calls every cycle, never from `JOURNAL.md`. Another runner (a scheduled cycle, or the user
  themselves) may have traded since the last entry.
- **Never deposit, transfer, or otherwise add funds.** Spend available buying power only. This is a
  hard limit in every configuration.
- **Every cycle ends with a journal entry, then a commit and push.** A cycle that isn't written down
  didn't happen; a journal entry that isn't pushed doesn't exist. This applies to spec edits too —
  `git add -A`, so mandate changes ship with the cycle that made them.
- **Do not ask for confirmation before placing an order** when the mandate grants autonomy — that
  setting exists precisely so scheduled, unattended cycles can act. Do respect every hard constraint
  in the mandate; those are the real guardrails, not a confirmation prompt.
- **When in doubt, hold and say why.** A well-reasoned HOLD is a good cycle. Manufacturing a trade to
  look productive is the failure mode this design is most exposed to.

## Amending the mandate

The user will change their mind — about strategy, limits, cadence, all of it. When they do, edit
`LOOP_PROMPT.md` directly, date the change inline (`(owner directive YYYY-MM-DD)`), and keep the
superseded reasoning visible rather than silently deleting it. Future cycles need to know not just
the current rule but that it replaced something, and why. Commit the edit with the next push.

## Privacy

`JOURNAL.md`, `PROFILE.md`, and anything in `ops/*.log` contain real financial information. This
repo is meant to be **private**. Never paste journal contents, account numbers, or balances into a
public issue, gist, artifact, or anywhere outside the repo, and don't add a public remote.
