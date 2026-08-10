# Sidecar

**An agentic trading loop that rides alongside your real portfolio.**

An AI agent wakes on a schedule, reads the market, trades a small account inside rules you set, and
writes down why. A *sidecar* is the finance term for a small vehicle that invests alongside a main
fund — that's the design. Not your whole portfolio. The small, opinionated sleeve next to it.

> ⚠️ **Places real trades with real money, unattended.** See [Before you start](#before-you-start).

## How it works

Three parts:

- **`LOOP_PROMPT.md`** — the mandate. Strategy, risk limits, cycle steps. Read every run.
- **`JOURNAL.md`** — the memory. One entry per cycle. Latest entry = current thesis.
- **A scheduler** — fires a fresh agent session on a timer.

That's the whole idea: **mandate + journal + cron.**

The journal is the part people underestimate. Without it, every run is a stock picker with amnesia —
re-deriving a thesis from scratch and quietly contradicting yesterday. With it, the agent carries a
thesis across weeks, leaves triggers for its own future self ("trim above 25%"), and gets held to
them on the record.

Each cycle: read the mandate → tail the journal → pull live account state → scan news and sectors →
form a thesis → trade inside the limits → append an entry → push. Market closed or no buying power?
Log a HOLD and stop. Doing nothing is a valid, journaled outcome.

## Setup

1. **Use this template → make your copy private.** Your journal fills with real balances and positions.
2. Clone it and open in [Claude Code](https://claude.com/claude-code) (or Cursor, or any coding agent).
3. Say **"initialize"** (or `/sidecar-init`). A ~10-minute interview about your goals, risk limits,
   and how much autonomy you're handing over. It writes `PROFILE.md`, fills in `LOOP_PROMPT.md` and
   `ops/`, and hands you your scheduler prompt ready to paste.
4. **You** connect the broker — enabling agent trading, funding, and OAuth all need a human.
5. Prove the order path works, run one cycle by hand, read what it wrote, then schedule it.

Steps 4–5 in detail: **[SETUP.md](SETUP.md)** · The scheduler prompt: **[ops/ROUTINE_PROMPT.md](ops/ROUTINE_PROMPT.md)**

## Works with

The reference setup — the live loop this was extracted from — is **Robinhood's agent MCP +
[Claude Routines](https://claude.ai/code/routines)**, cloud-scheduled, nothing running locally.

Nothing here is specific to either. You need two things:

- **A broker the agent can reach** — any MCP server or API with quotes, positions, and orders. Paper
  endpoints work, and are the right place to start.
- **Something that runs an agent on a timer** — Claude Routines, `cron`/`launchd` ([`ops/`](ops/)
  ships a working one), Cursor background agents, GitHub Actions on a schedule.

## Before you start

- **It trades without asking.** That's the design — and it's a setting. The interview asks you.
- **Start tiny.** The reference account started at **$10**. You're buying evidence about how the
  thing behaves, and evidence is cheaper at small size.
- **Paper trade first** if your broker offers it. Same loop, same journal, no money.
- **Not investment advice.** No backtest, no risk engine. Models are non-deterministic — one that
  reasoned well yesterday can be confidently wrong today.
- **Losses are yours,** including from orders you never saw coming. Read the journal.
- **Know your broker's rules** — settlement, good-faith violations, PDT thresholds, options levels.
  The loop respects the limits you write down, not the ones you assume.
- **Taxes are real.** A busy loop in a taxable account makes short-term gains and wash-sale risk.

## Layout

```
LOOP_PROMPT.md   the mandate               SETUP.md       broker + scheduling
JOURNAL.md       the memory                INTERVIEW.md   the setup interview
PROFILE.md       your answers (on init)    CLAUDE.md      how agents behave here
ops/             schedulers + the routine prompt
```

MIT — see [LICENSE](LICENSE). No warranty, expressly including fitness for trading.
