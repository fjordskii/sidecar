# Setting up Sidecar

End to end, roughly 30–45 minutes, most of it waiting on broker approvals.

The path below is the **reference implementation**: Robinhood + Claude Code + Claude Routines, which
is what this template was extracted from and what runs live. Substitutions are called out at each
step — nothing here is load-bearing except "a broker the agent can reach" and "something that fires
it on a timer."

---

## Step 1 — Make your own private copy

**Use this template → and set the visibility to Private.**

> Your `JOURNAL.md` will accumulate real balances, positions, cost bases, and P&L, cycle after cycle.
> `PROFILE.md` will contain what you told the interview about your finances. Neither belongs in a
> public repo, and neither is something you can meaningfully scrub later — git keeps the history.

```bash
git clone https://github.com/<you>/<your-private-repo>.git sidecar
cd sidecar
```

If you cloned this template directly instead of forking it, repoint the remote at your own private
repo before the loop ever pushes:

```bash
git remote set-url origin https://github.com/<you>/<your-private-repo>.git
```

## Step 2 — Run the setup interview

Open the folder in [Claude Code](https://claude.com/claude-code):

```bash
cd sidecar && claude
```

Say **"initialize"**, or just describe what you're trying to do. The agent reads `CLAUDE.md`, finds
the repo unconfigured, and runs the interview in `INTERVIEW.md` — about 10–15 minutes of conversation
about your goals, your existing portfolio, your risk limits, and how much autonomy you're handing
over.

It produces:

- **`PROFILE.md`** — your answers, in your words
- **`LOOP_PROMPT.md`** — the live mandate, placeholders filled
- **`JOURNAL.md`** — seeded with your standing rules and a `CYCLE 0` entry

**Read `LOOP_PROMPT.md` before going further.** It is the thing that will be spending your money at
7am on a Tuesday, and it is plain English — if a line doesn't say what you meant, edit it now. This
is the highest-leverage ten minutes in the whole setup.

> Using Cursor or another agent instead? Same flow — the agent needs to read `CLAUDE.md` and follow
> `INTERVIEW.md`. If it doesn't pick that up automatically, just say: *"Read CLAUDE.md and run the
> setup interview in INTERVIEW.md."*

## Step 3 — Connect the broker

### Robinhood (the reference path)

**3a. Get an agent-accessible account.** In the Robinhood app, enable agent trading. Robinhood
designates a *specific* account for agent access — other accounts will reject agent orders outright,
so note the account number of the enabled one. That identifier goes in `LOOP_PROMPT.md` and gets
passed on every single call.

**3b. Complete your investment profile.** Suitability gates block buys until it's filled in, and the
failure is confusing when you hit it mid-cycle. Do it now.

> One quirk worth knowing: the suitability flag returned by the accounts endpoint *lags*. It can
> still read `false` after you've completed the profile. The order endpoint is authoritative — if
> you think you're cleared, place a small test order rather than trusting the flag.

**3c. Options approval,** if your mandate allows options. Level 2 (long calls/puts, covered calls,
cash-secured puts — no spreads) is what the reference setup runs. Approval takes a day or two.

**3d. Fund it.** Small. Genuinely small. ACH transfers take several days to settle, and until they
do, buying power may be zero or the funds may be unsettled — the loop will correctly log HOLD cycles
in the meantime rather than trading with money it doesn't have.

**3e. Connect the MCP server.**

For **local / Claude Code** sessions:

```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
```

This runs an OAuth device flow — approve it in the browser. Verify with `/mcp` inside Claude Code;
you're looking for tools like `get_portfolio`, `get_equity_positions`, `place_equity_order`. Note the
tool names are **unprefixed** (`get_portfolio`, not `robinhood_get_portfolio`) — an easy thing to get
wrong in an allowlist, and a wrong allowlist fails silently as a run that can't trade.

For **cloud routines**, add the same server as a connector in your claude.ai settings so the
scheduled session inherits it. A cloud session can't see MCP servers you added locally — this is the
most common reason a routine authenticates fine on your laptop and fails on schedule.

### Another broker

Any MCP server or API exposing quotes, positions, and order placement works. Point `{{MCP_SERVER}}`
in `LOOP_PROMPT.md` at it and adjust the tool names in the cycle steps to match. Alpaca has both
paper and live endpoints and is a good place to start. Record anything the broker *can't* do in the
**Capability gaps** section of `LOOP_PROMPT.md` the day you find it — e.g. the Robinhood agent server
has no crypto tools and no news/movers endpoints, so crypto is unavailable in practice and market
data comes from web search. Undocumented gaps get rediscovered by every future cycle.

## Step 4 — Verify the connection, and prove the order path

Two separate things, and the second is the one people skip.

**Read path** — in an interactive session:

> "Call get_accounts, then get_portfolio for account &lt;your account&gt;. Just show me the results,
> don't trade."

You should see your account, your buying power, your (probably empty) positions.

**Order path** — this is the important one:

> "Run a review/preview for a $1 market buy of a liquid ETF in that account. Don't place it — I want
> to confirm the order endpoint responds."

A clean preview with no rejections means the pipe is open.

> **Why this matters.** In the setup this template came from, the loop ran **read-only for four
> days** — pulling data, reasoning well, journaling beautifully, and having every order silently
> blocked by a safety classifier in the session it happened to be running in. Nobody noticed until a
> real trigger fired and the order was refused. A string of HOLD cycles looks exactly like a
> considered strategy right up until you learn it was a broken pipe. Prove the order path before you
> schedule anything, and have every cycle note whether it still works.

## Step 5 — Run one cycle by hand

Before any schedule exists:

> "Run one full cycle now, exactly as LOOP_PROMPT.md describes."

Then **read the journal entry it wrote.** This is your real acceptance test, and it's a judgment
call, not a checklist — does the reasoning sound like something you'd endorse? Did it respect your
limits? Did the cross-sector scan actually look, or did it hand-wave? Would you have made this trade?

If the answer is no, the fix is almost always in `LOOP_PROMPT.md`, not in the agent. Edit the
mandate, run another cycle, repeat. Two or three rounds here is normal and is time extremely well
spent — you are debugging in English, before there's a schedule and before there's real size.

## Step 6 — Schedule it

The prompt you paste into any scheduler is templated in **[`ops/ROUTINE_PROMPT.md`](ops/ROUTINE_PROMPT.md)**
— fill its placeholders and use it verbatim.

### Option A — Cloud routine (recommended)

Nothing runs on your machine. Your laptop can be shut. This is what the reference setup migrated to
and it removed an entire category of problems.

1. Go to **[claude.ai/code/routines](https://claude.ai/code/routines)** and create a routine.
2. Point it at your private repo — it clones fresh each run.
3. Paste your filled-in routine prompt.
4. Set the schedule. Reference cadence is 3× per weekday, near the open, midday, and before the
   close. Once daily is fine. More than 3× mostly buys churn.
5. Confirm the broker connector is enabled for cloud sessions (Step 3e).
6. **Trigger it once manually** and read the resulting journal entry and commit.

> ⚠️ **DST drift.** Cloud cron is usually fixed **UTC** while market hours are **ET**. A cron set
> during EDT (UTC−4) fires an hour early once EST begins — and the spring/fall shift can move your
> first slot to *before the market opens*, which turns your best cycle of the day into a no-op.
> Set a calendar reminder for the changeover to shift the hours. Example: `30 13,16,19 * * 1-5`
> (9:30/12:30/15:30 EDT) becomes `30 14,17,20 * * 1-5` under EST.

### Option B — Local scheduler

`ops/` ships a working `launchd` setup: [`run.sh`](ops/run.sh) and a plist example. See
[`ops/README.md`](ops/README.md) for the install steps, the `cron` equivalent, and the trade-offs.

Short version: it works, it's fully under your control, and it stops the moment your laptop sleeps.

### Option C — Anything else

Cursor background agents, GitHub Actions on a `schedule` trigger, any hosted agent platform with a
timer. Same prompt; only the trigger changes. For CI, remember the checkout is detached — keep the
explicit push refspec.

> ⚠️ **Run exactly one order-capable scheduler.** Two runners sharing one journal will both wake on
> the same catalyst and both spend the same buying power. There's no lock. If you migrate from local
> to cloud, *disable the local job in the same sitting* — this bit the reference setup and it's the
> kind of bug that shows up as a mysterious duplicate position.

## Step 7 — Living with it

**Read the journal.** Not every entry, but regularly, and especially after a losing week. It's the
whole point: you have a dated record of what your agent believed and why, which is more than most
people have about their own trading.

**Amend the mandate when you disagree.** Tell the agent in a session — *"stop buying anything within
two weeks of an earnings print"* — and have it edit `LOOP_PROMPT.md` and commit. Dated amendments,
superseded reasoning left visible. This is the intended way to steer the loop; arguing with a single
cycle isn't, because the next cycle won't remember it.

**Watch for these failure modes.** They're the ones that actually show up:

| Symptom | Usually means |
|---|---|
| Every cycle is HOLD | Broken order path, or a mandate so tight nothing can clear it. Check the preview call first. |
| Every candidate is in one theme | The cross-sector scan has become a ritual. Tighten the entry test into something that can actually fire. |
| It trades every cycle | The mandate rewards activity. Add an explicit "no quota, holding is success" line, or reduce the cadence. |
| Journal entries stop appearing | Push failures. Check the remote SHA, not the local log. |
| Duplicate positions | Two schedulers. Kill one. |

**Rotate the journal** when it passes ~250KB — the agent will do it if you ask, or on its own per the
mandate.

**Re-evaluate on your benchmark.** You set one in the interview. Actually check it. The honest
question is whether this sleeve beats what the same dollars would have done sitting in an index fund
— and if it doesn't over a few months, shrink it or shut it off. Being able to answer that is worth
more than the sleeve.
