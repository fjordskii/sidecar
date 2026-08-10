# Setup

~30 minutes, most of it waiting on broker approvals.

Reference path is Robinhood + Claude Code + Claude Routines. Substitutions are noted per step.

---

## 1. Private copy

**Use this template → set visibility to Private.** `JOURNAL.md` accumulates real balances and
positions; git history keeps them forever.

```bash
git clone https://github.com/<you>/<your-private-repo>.git sidecar && cd sidecar
```

Cloned this template directly instead? Repoint the remote before anything pushes:
`git remote set-url origin https://github.com/<you>/<your-private-repo>.git`

## 2. Interview

```bash
claude
```

Say **"initialize"**. The agent reads `CLAUDE.md`, finds the repo unconfigured, and runs
`INTERVIEW.md` — 10–15 minutes on your goals, existing portfolio, risk limits, and autonomy. It
writes `PROFILE.md`, fills in `LOOP_PROMPT.md`, and seeds `JOURNAL.md`.

**Then read `LOOP_PROMPT.md`.** It's plain English and it's what will be spending your money at 7am
on a Tuesday. If a line doesn't say what you meant, edit it. Highest-leverage ten minutes here.

> Other agents: say *"Read CLAUDE.md and run the setup interview in INTERVIEW.md."*

## 3. Broker

**Robinhood:**

No paper environment on this path — every order from step 4 onward is real money.

1. Enable agent trading in the app. Robinhood designates **one specific account** for it — others
   reject agent orders. Note that account number.
2. Complete your investment profile. Suitability gates block buys until you do.
   *(The flag on the accounts endpoint lags and can still read `false` afterward — the order endpoint
   is authoritative. Test with a small order rather than trusting the flag.)*
3. Options approval if your mandate uses them. Level 2 = long calls/puts, covered calls, CSPs. Takes
   a day or two.
4. Fund it. ACH takes days to settle; until then the loop correctly logs HOLD cycles.
5. Connect the MCP server:
   ```bash
   claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
   ```
   OAuth device flow — approve in browser. Verify with `/mcp`. Tool names are **unprefixed**
   (`get_portfolio`, not `robinhood_get_portfolio`); a wrong allowlist fails silently.
6. **For cloud routines, add the same server as a connector on claude.ai.** A cloud session cannot
   see MCP servers you added locally.

**Other brokers:** any MCP server or API with quotes, positions, and orders. Point `{{MCP_SERVER}}`
at it and adjust tool names in `LOOP_PROMPT.md`. Alpaca has paper + live endpoints. Record anything
the broker *can't* do under **Capability gaps** in `LOOP_PROMPT.md` — e.g. Robinhood's agent server
has no crypto tools and no news/movers endpoints, so crypto is unavailable in practice and market
data comes from web search.

## 4. Verify — both paths

**Read:** *"Call get_accounts, then get_portfolio for &lt;account&gt;. Don't trade."*

**Order:** *"Run a review/preview for a $1 market buy of a liquid ETF. Don't place it."*

A clean preview means the pipe is open.

> **Why bother:** the loop this came from ran read-only for four days — reasoning well, journaling
> beautifully, every order silently blocked — until a real trigger fired and got refused. HOLD cycles
> look exactly like a considered strategy until you learn it was a broken pipe.

## 5. One cycle by hand

*"Run one full cycle now, exactly as LOOP_PROMPT.md describes."*

Then **read the entry it wrote.** Does the reasoning sound like something you'd endorse? Did it
respect your limits? Did the cross-sector scan actually look, or hand-wave?

If no, fix `LOOP_PROMPT.md`, not the agent. Two or three rounds is normal — you're debugging in
English before there's a schedule or real size.

## 6. Schedule

Prompt + full config: **[`ops/ROUTINE_PROMPT.md`](ops/ROUTINE_PROMPT.md)**.

**Cloud routine (recommended).** Nothing on your machine; your laptop can be shut.
[claude.ai/code/routines](https://claude.ai/code/routines) → new routine → point it at your private
repo → paste the filled prompt → set tools, connector, and cron per `ops/ROUTINE_PROMPT.md` →
**trigger once manually** and read the resulting entry and commit.

**Local.** `ops/` ships a `launchd` setup — see [`ops/README.md`](ops/README.md). Works, fully under
your control, stops when your laptop sleeps.

**Anything else.** Cursor background agents, GitHub Actions on a `schedule`. Same prompt.

Cadence: 3×/weekday (open, midday, pre-close) is the reference. Once daily is fine. More mostly buys
churn.

> ⚠️ **Exactly one order-capable scheduler.** Two runners share one journal with no lock. Migrating
> from local to cloud? Disable the local job the same day.

## 7. Living with it

**Read the journal** — regularly, especially after a bad week. You have a dated record of what your
agent believed and why, which is more than most people have about their own trading.

**Amend the mandate** when you disagree: *"stop buying within two weeks of an earnings print"* →
agent edits `LOOP_PROMPT.md` and commits. Arguing with a single cycle doesn't work; the next one
won't remember.

| Symptom | Usually means |
|---|---|
| Every cycle HOLDs | Broken order path, or limits nothing can clear. Check the preview call. |
| Every candidate is one theme | The cross-sector scan became a ritual. Tighten the entry test so it can actually fire. |
| It trades constantly | Mandate rewards activity. Add "no quota, holding is success", or cut the cadence. |
| Entries stop appearing | Push failures. Check the remote SHA, not the local log. |
| Duplicate positions | Two schedulers. Kill one. |

**Check your benchmark.** You set one in the interview — actually use it. If the sleeve can't beat
what the same dollars would've done in an index fund over a few months, shrink it or shut it off.
Being able to answer that is worth more than the sleeve.
