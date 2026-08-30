# The routine prompt

What you paste into your scheduler. Everything else in the repo is read *by* the session it starts.

Keep it a **pointer, not a strategy.** Strategy lives in `LOOP_PROMPT.md` where it's version-controlled
and any cycle can amend it. Duplicate it here and within a week you have two mandates that disagree
and no way to tell which one a cycle followed.

---

## The prompt

This block is ready to paste as-is for the Robinhood quick start: the account identifier is
not in it, because the agent fetches it from the broker itself on first run.

```text
Scheduled CLOUD routine cycle of the Robinhood agent-trading account configured in this repo.
You are ONE run of a shared, continuous trading loop — not a separate bot with its own
mandate. You share repo state with any interactive session that may also touch this account.

FIRST RUN CHECK: if the repo has no PROFILE.md, it is NOT_INITIALIZED. Do not trade. Run the
auto-init procedure in AGENTS.md instead: fetch the account identifier from the broker
yourself via the accounts endpoint (get_accounts), write the setup files from
setup-schema.json defaults with PROPOSE-ONLY autonomy, prove the order path with one
review/preview call, commit and push, and stop.

Otherwise, source of truth (read both, in order, from the repo root):
  1. Spec/mandate: LOOP_PROMPT.md
  2. Memory/journal: JOURNAL.md — tail it (do not read the whole file); the most recent
     CYCLE entry is the current thesis + standing rules. Honor any triggers it left you.

Then execute the loop EXACTLY as LOOP_PROMPT.md describes: check session / portfolio /
positions / open orders via the robinhood-trading MCP server, gather news + cross-sector
movers via WebSearch, form a thesis, and act under the mandate. Trust the live broker API
over the journal file for positions and cash — another runner may have traded since the
journal was last written. Preview orders (review_* tools) before placing. Only spend SETTLED
buying power; never deposit or self-fund. If the market is closed (weekend or holiday) or
buying power is ~$0 with nothing to manage, log a brief HOLD cycle and stop — do not error
out.

Identify yourself in the journal entry as a CLOUD-ROUTINE cycle (distinct from any 'local' or
'interactive' entries already in the journal) and note which daily slot this is.

Finish by APPENDING a new dated ## CYCLE entry to JOURNAL.md (format in LOOP_PROMPT.md), then
commit and push — a change that isn't pushed doesn't exist. You are in a FRESH CLONE and
therefore on a DETACHED HEAD, where a plain `git push` fails *after* the commit succeeds, so
push with an explicit refspec and verify:
  git add -A && git commit -m "cycle: <date/time> (cloud routine, <slot>)"
  git push origin HEAD:refs/heads/main
  git ls-remote --heads origin   # SHA must match `git rev-parse HEAD`

End with a one-paragraph summary of what you did and why.
```

**Customizing (other broker, different cadence)?** The wizard's customize path renders a
filled variant of this prompt from your answers. If you're doing it by hand: swap the broker
name and MCP server name, name your slots explicitly, and keep the autonomy line identical to
what `LOOP_PROMPT.md` grants:

- **Full** — `FULL AUTONOMY — no user confirmation needed for any trade.`
- **Propose-only** — `PROPOSE-ONLY — place NO orders. State the exact order you would place, journal it, leave it for the owner.`
- **Mixed** — `Place orders up to <threshold> without confirmation; above that, journal the proposed order and leave it.`

There's nobody in a scheduled session to answer a confirmation prompt, so an agent that pauses to ask
just stalls and the cycle produces nothing. Be explicit.

## The rest of the config

The prompt is half of it. These fields decide whether the run can actually *do* anything:

| Field | Value | Why |
|---|---|---|
| **Repo source** | your private repo URL | Cloned fresh each run — this is how it gets the mandate and journal. |
| **Allowed tools** | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebSearch`, `WebFetch`, `mcp__{{MCP_SERVER}}` | **`Bash` is required** — without it there's no `git push`, so the cycle runs, trades, and loses its journal entry. `WebSearch` is required if your broker has no news/movers endpoint. |
| **MCP connector** | your broker server, attached to the routine | A cloud session cannot see MCP servers you added locally. This is the #1 reason a routine works on your laptop and fails on schedule. |
| **Model** | a frontier model | This is judgment work on real money. |
| **Cron** | `30 13,16,19 * * 1-5` = 9:30/12:30/15:30 ET **during EDT** | See DST below. |
| **Persist session** | off | Every cycle should start cold from the repo. State lives in the journal, not in a session. |

> ⚠️ **DST drift.** Cloud cron is fixed **UTC**; market hours are **ET**. A cron set during EDT fires
> an hour early once EST starts — which can move your first slot to *before the open*. Under EST the
> example becomes `30 14,17,20 * * 1-5`. Set a calendar reminder for the changeover.

## Other schedulers

Same prompt, different trigger.

- **Local `launchd`/`cron`** — it's already in [`run.sh`](run.sh). A persistent checkout sits on a
  real branch, so a plain `git push` works and the detached-HEAD refspec is unnecessary.
- **GitHub Actions** — checkout is detached, so keep the refspec. Needs write permission and broker
  credentials in secrets.

> ⚠️ **Exactly one order-capable scheduler.** Two runners share one journal with no lock — both wake
> on the same catalyst and spend the same buying power. Migrating? Disable the old one the same day.

## Test it before you trust it

Trigger the routine manually once and check, in order:

1. It authenticates to the broker.
2. It reads the journal and picks up the thesis.
3. **The order path works** — verify via a review/preview call even on a HOLD cycle.
4. **The push landed** — check the remote SHA, not the local log.

Point 3 isn't paranoia. The loop this came from ran **read-only for four days** — reasoning well,
journaling beautifully, every order silently blocked — and nobody noticed until a real trigger fired
and got refused. A run of HOLD entries looks exactly like a considered strategy until you learn it was
a broken pipe. Have every cycle state whether the order path worked.
