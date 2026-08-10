# Sidecar

**An agentic trading loop that rides alongside your real portfolio.**

Sidecar is a template for running a small, autonomous, journal-keeping AI trading agent against a
real brokerage account on a fixed schedule. You define the mandate once, through an interview. From
then on the agent wakes up on its own, reads the market, reasons about your positions, places real
orders inside your rules, and writes down what it did and why — whether or not you are watching.

The name is the finance term: a *sidecar* is a small vehicle that invests alongside a main fund.
That is the design. Sidecar is not meant to be your whole portfolio. It is the small, opinionated,
high-conviction sleeve that rides next to whatever core you already have.

> ⚠️ **This places real trades with real money, unsupervised, by default.** Read
> [Before you start](#before-you-start) before you connect a funded account.

---

## The idea

Three things do all the work:

| | |
|---|---|
| **`LOOP_PROMPT.md`** | The standing mandate — strategy, risk limits, hard constraints, the cycle steps, the journal format. Read first, every single run. |
| **`JOURNAL.md`** | The loop's memory. Every cycle appends an entry. **The most recent entry is the current thesis.** |
| **A scheduler** | Fires a fresh, isolated agent session on a cadence (e.g. 3× per weekday). |

That's it: **mandate + persistent journal + cron.** Everything else in this repo is scaffolding
around those three.

The journal is the part people underestimate. A language model with no memory is a stock picker with
amnesia — it will re-derive a thesis from scratch every run and quietly contradict itself. The
journal gives it continuity: it can carry a thesis across weeks, leave *falsifiable* triggers for its
own future self ("trim if this position exceeds 25% of the sleeve"), and get held to them on the
record. The mandate stops it from drifting. The schedule means it actually happens.

## What a cycle looks like

Every run, the agent:

1. Reads the mandate, then tails the journal for the current thesis
2. Pulls live account state from the broker — never trusts the file for positions or cash
3. Gathers news on its holdings, plus a genuine cross-sector scan for new setups
4. Forms a thesis for *this* cycle and states it plainly
5. Places orders inside the hard limits — or explains why holding beats trading
6. Appends a dated `## CYCLE` entry: portfolio, analysis, thesis, orders, what to watch next
7. Commits and pushes, so the journal survives the session

If the market is closed, or buying power is zero, or the data is thin, it logs a short HOLD and
stops. Doing nothing is a valid, journaled outcome — a loop that must trade to justify itself is a
loop that will churn your account.

## Quickstart

1. **Use this template → make your copy PRIVATE.** Your journal will fill up with real balances,
   positions, and P&L. Do not put it in a public repo.
2. Clone it and open the folder in [Claude Code](https://claude.com/claude-code) (or Cursor, or any
   coding agent that reads repo instruction files).
3. Say **"initialize"** — or just describe what you want. The agent finds the repo uninitialized and
   interviews you about your goals, risk tolerance, and constraints. About 10–15 minutes.
4. It writes `PROFILE.md` (your answers) and fills in `LOOP_PROMPT.md` (the live mandate).
5. Connect your broker and schedule it — **[SETUP.md](SETUP.md)** walks through both, end to end.

Full detail: **[SETUP.md](SETUP.md)** · The interview itself: **[INTERVIEW.md](INTERVIEW.md)**

## Works with

The reference setup — the one this template was extracted from, running live — is
**Robinhood's agent MCP + Anthropic's Claude Routines** (cloud-scheduled, nothing running locally).

But nothing about the design is specific to either. The loop needs exactly two capabilities:

- **A broker the agent can reach** — any MCP server or API with quote + order + position tools.
  Robinhood's is the turnkey option today; a thin wrapper over any brokerage API works the same way.
  Paper-trading endpoints work too, and are the right place to start.
- **Something that runs an agent on a schedule** — Claude Routines, a local `cron` or `launchd` job
  calling a headless agent CLI, Cursor's background agents, a GitHub Actions workflow on a `schedule`
  trigger, or any hosted agent platform with a timer.

`ops/` ships a working local scheduler as the fallback path, and
[ops/README.md](ops/README.md) covers the trade-offs between each option.

## Before you start

Read this part.

- **It trades real money without asking.** Full autonomy is the default because a loop that stops to
  ask permission isn't a loop — but it is a real setting, and you can turn it down. The interview
  asks. Choose deliberately.
- **Start impossibly small.** Fund it with an amount you would shrug off entirely. The reference
  account started at **$10**. You are buying evidence about how the thing behaves, and evidence is
  cheaper at small size.
- **Paper trade first if your broker offers it.** Same loop, same journal, no money.
- **This is not investment advice, and it is not a product.** It is a prompt, a text file, and a
  timer. There is no backtest, no risk engine, and no guarantee the agent won't be confidently wrong.
  Model outputs are non-deterministic; an agent that reasoned well yesterday can reason badly today.
- **Losses are yours.** You are responsible for every order placed under your credentials, including
  the ones you didn't see coming. Check the journal.
- **Know your broker's rules** — settlement timing, good-faith violations, pattern-day-trader
  thresholds, options approval levels. The loop respects the limits you write into the mandate; it
  does not know the ones you leave out.
- **Taxes are real.** A busy loop in a taxable account generates short-term gains and wash-sale
  risk. Tell the interview what kind of account it is.

## Repo layout

```
LOOP_PROMPT.md      the standing mandate (filled in by the interview)
JOURNAL.md          the loop's memory — one entry per cycle
PROFILE.md          your answers to the interview (created on init)
INTERVIEW.md        the interview script the agent runs
SETUP.md            broker connection + scheduling, step by step
CLAUDE.md           repo instructions — how an agent should behave here
ops/                local scheduler (run.sh, plist example) + notes on alternatives
```

## License

MIT. See [LICENSE](LICENSE). No warranty, expressly including fitness for trading.
