# Sidecar

**An agentic trading loop that rides alongside your real portfolio.**

An AI agent wakes on a schedule, reads the market, trades inside rules you set, and writes down why.
In finance, a *sidecar* is a small vehicle that invests alongside a main fund. That's the design:
not your whole portfolio, but a separate, opinionated sleeve next to it.

> ⚠️ **Places real trades with real money, unattended.** See [Before you start](#before-you-start).

## How it works

Three parts:

- **`LOOP_PROMPT.md`**: the mandate. Strategy, risk limits, cycle steps. Read every run.
- **`JOURNAL.md`**: the memory. One entry per cycle. The latest entry is the current thesis.
- **A scheduler**: fires a fresh agent session on a timer.

Mandate + journal + cron. That's the whole system.

The journal is the part people underestimate. Without it, every run is a stock picker with amnesia,
re-deriving a thesis from scratch and contradicting yesterday without noticing. With it, the agent
carries a thesis across weeks, leaves triggers for its future self ("trim above 25%"), and gets held
to them on the record.

Each cycle: read the mandate → tail the journal → pull live account state → scan news and sectors →
form a thesis → trade inside the limits → append an entry → push. Market closed or no buying power?
Log a HOLD and stop. Doing nothing is a valid, journaled outcome.

## Setup

**The easy way: the [setup wizard](https://sidecar-web-fjordskiis-projects.vercel.app)** — a guided
flow that creates your private repo and hands you the scheduler prompt. Three clicks plus one paste,
zero questions: the routine's first run initializes the repo itself (it fetches your Robinhood
account number and writes a safe mandate that proposes trades but places none). To personalize
later, open an interactive session and say **"initialize"**; it interviews you about goals, risk
limits, and autonomy. Prefer to write the rules up front? The wizard's customize path is a
10-minute form that writes them before launch.

The manual way:

1. **Use this template → make your copy private.** Your journal fills with real balances and positions.
2. Clone it and open in [Claude Code](https://claude.com/claude-code) (or Cursor, or any coding agent).
3. Say **"initialize"** (or `/sidecar-init`). A ~10-minute interview about your goals, risk limits,
   and how much autonomy you're handing over. It writes `PROFILE.md`, fills in `LOOP_PROMPT.md` and
   `ops/`, and hands you your scheduler prompt ready to paste.
4. **You** connect the broker: enabling agent trading, funding, and OAuth all need a human.
5. Prove the order path works, run one cycle by hand, read what it wrote, then schedule it.

Steps 4–5 in detail: **[SETUP.md](SETUP.md)** · The scheduler prompt: **[ops/ROUTINE_PROMPT.md](ops/ROUTINE_PROMPT.md)**

## Works with

The reference setup (the live loop this template was extracted from) is **Robinhood's agent MCP +
[Claude Routines](https://claude.ai/code/routines)**, cloud-scheduled, nothing running locally.

Nothing here depends on either. You need two things:

- **A broker the agent can reach**: any MCP server or API with quotes, positions, and orders, live
  or paper.
- **Something that runs an agent on a timer**: Claude Routines, `cron`/`launchd` ([`ops/`](ops/)
  ships a working one), Cursor background agents, GitHub Actions on a schedule.

## Updating

Your copy is yours forever, but the template keeps improving, so each repo carries an
update rail: [`.github/workflows/sidecar-update.yml`](.github/workflows/sidecar-update.yml)
checks weekly and opens a PR when the template ships something new. Merge with one click.
Your journal, profile, and filled-in mandate are never touched: ownership is declared in
[`sidecar-manifest.json`](sidecar-manifest.json), and files the interview personalized are
skipped by rule. Older copy without the rail? Say `/sidecar-upgrade` in Claude and it migrates
itself — or do it by hand from [docs/MIGRATION.md](docs/MIGRATION.md).

## Before you start

- **It trades without asking.** That's deliberate, and it's a setting: the interview asks you.
- **Works at any account size.** The loop reads buying power from the broker live, every cycle. It
  has no minimum and no opinion on how much you fund it with.
- **Real orders by default.** If your broker exposes a paper-trading endpoint, the loop runs against
  it the same way: same mandate, same journal. Whether you use it is your call. (Robinhood, the
  reference broker here, doesn't have one, so every order is real money from the first trade.)
- **Not investment advice.** No backtest, no risk engine. Models are non-deterministic; one that
  reasoned well yesterday can be confidently wrong today.
- **Losses are yours,** including from orders you never saw coming. Read the journal.
- **Know your broker's rules**: settlement, good-faith violations, PDT thresholds, options levels.
  The loop respects the limits you write down, not the ones you assume.
- **Taxes are real.** A busy loop in a taxable account makes short-term gains and wash-sale risk.

## Layout

```
LOOP_PROMPT.md   the mandate               SETUP.md       broker + scheduling
JOURNAL.md       the memory (narrative)    INTERVIEW.md   the setup interview
DECISIONS.md     the memory (durable)      AGENTS.md      how agents behave here (CLAUDE.md shims it)
PROFILE.md       your answers (on init)
ops/             schedulers + the routine prompt
VERSION + sidecar-manifest.json            template version + the update rail's file ownership
```

MIT — see [LICENSE](LICENSE). No warranty, expressly including fitness for trading.
