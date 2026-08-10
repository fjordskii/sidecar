# The routine prompt

This is the text you paste into your scheduler — the thing that actually fires on a timer and wakes
the agent up. Everything else in this repo is read *by* the session this prompt starts.

Keep it short. It is a **pointer, not a strategy.** Its whole job is: identify the account, name the
two files that are the source of truth, and hand off. Strategy lives in `LOOP_PROMPT.md`, where it
can be amended by any cycle and version-controlled. A routine prompt that duplicates strategy will
drift out of sync with the mandate within a week, and then you have two mandates that disagree and no
way to tell which one a given cycle followed.

---

## Template — copy, fill the `{{PLACEHOLDERS}}`, paste into your scheduler

```text
Scheduled cycle of the {{BROKER}} account {{ACCOUNT_ID}}. You are ONE run of a shared,
continuous trading loop — not a standalone bot with its own mandate. Everything you need is
in the repo {{REPO_URL}}.

Source of truth — read both, in this order:
  1. Mandate/spec: LOOP_PROMPT.md
  2. Memory/journal: JOURNAL.md — tail it (~15KB), do not read the whole file. The most
     recent CYCLE entry is the current thesis and carries standing triggers left for you by
     the previous cycle. Honor them.

Then execute the cycle EXACTLY as LOOP_PROMPT.md describes: verify session, pull live
portfolio/positions/open orders, gather news and run the cross-sector scan, form a thesis,
and act within the mandate's hard limits. Trust the live broker API over anything in the
files — another runner may have traded since the last entry. Preview orders before placing
when sizing is unclear. Spend available buying power only; never deposit or self-fund. If
the market is closed, or buying power is ~$0 with nothing to manage, log a brief HOLD cycle
and stop cleanly.

{{AUTONOMY_LINE}}

Finish by APPENDING a new dated ## CYCLE entry to JOURNAL.md in the exact format given in
LOOP_PROMPT.md, then commit and push. You are in a fresh clone and likely on a DETACHED
HEAD, so push with an explicit refspec — `git push origin HEAD:refs/heads/main` — and
verify with `git ls-remote --heads origin` that the remote SHA matches `git rev-parse HEAD`.
A commit that fails to push is a silent data-loss bug, not a cosmetic warning.

End with a one-paragraph summary of what you did and why.
```

## Filling it in

| Placeholder | What goes there |
|---|---|
| `{{BROKER}}` | `Robinhood`, `Alpaca`, etc. |
| `{{ACCOUNT_ID}}` | The exact account identifier every order must carry. |
| `{{REPO_URL}}` | Your **private** repo URL. The routine clones this fresh each run. |
| `{{AUTONOMY_LINE}}` | One sentence, from the table below. |

**`{{AUTONOMY_LINE}}` — pick one, matching what the interview set in `LOOP_PROMPT.md`:**

- *Full autonomy:*
  `FULL AUTONOMY — place orders without asking for confirmation. There is no human in this session to approve anything; a cycle that stops to ask has failed to run.`
- *Propose-only:*
  `PROPOSE-ONLY — do NOT place any order. Analyze fully, state the exact order you would place (symbol, side, size, order type), journal it, and leave it for the owner to execute manually.`
- *Mixed:*
  `Place orders up to {{THRESHOLD}} without confirmation. Above that, do NOT place — journal the proposed order in full and leave it for the owner.`

That autonomy line is the single most consequential sentence in the prompt. In an unattended cloud
session there is nobody to answer a confirmation request, so an agent that pauses to ask simply
stalls and the cycle produces nothing. Say explicitly which mode you're in.

## Notes for specific schedulers

**Claude Routines** (`claude.ai/code/routines` — the reference setup)
Paste the filled template as the routine's prompt and point it at your repo; it clones fresh, runs in
an isolated cloud session, and pushes its own commit. Nothing runs on your machine and no terminal
stays open. Set the cron in **UTC** and see the DST warning in [README.md](README.md) — a fixed-UTC
cron drifts an hour against market hours twice a year, and the spring shift can move your first slot
to *before the open*.

**Headless CLI on a local timer** (`launchd`, `cron`)
The same text becomes the `PROMPT` variable in [`run.sh`](run.sh) — it's already there, with the same
placeholders. Since a local run works in a persistent checkout rather than a fresh clone, it's on a
normal branch and a plain `git push` works; the detached-HEAD paragraph is harmless but unnecessary,
and `run.sh` handles the push itself.

**GitHub Actions / other CI**
Same prompt, passed to an agent CLI in the workflow. The checkout is detached there too, so keep the
explicit refspec. The job needs write permissions on the repo and your broker credentials in secrets.

**Anything else with a timer**
Any platform that can run an agent on a schedule with tool access works. The prompt doesn't change —
only the mechanism that fires it.

## Testing it

Before trusting a schedule, run the exact prompt once by hand — in an interactive session, or by
triggering the routine manually. You are checking four things, in order:

1. It authenticates to the broker.
2. It reads the journal and picks up the current thesis.
3. It can place an order — verify with a *review*/preview call even on a HOLD cycle, so a plumbing
   failure can never masquerade as a thesis decision.
4. **The push lands.** Check the remote, not just the local log.

Point 3 is not paranoia. In the setup this template came from, the loop ran read-only for four days —
analyzing and journaling perfectly while every order was silently blocked — and nobody noticed until
a real trigger fired and the order was refused. Every cycle should note in its journal whether the
order path actually worked, rather than letting a string of HOLD entries look like a strategy when
it's a broken pipe.
