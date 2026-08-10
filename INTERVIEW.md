# The Sidecar setup interview

**This file is for the agent, not the user.** When someone opens a fresh clone of this template,
follow this script to turn it into *their* trading loop. Read the whole thing before you start.

Your output is three files:

1. **`PROFILE.md`** — their answers, in their words. The durable record of what they told you.
2. **`LOOP_PROMPT.md`** — the live mandate, with every `{{PLACEHOLDER}}` replaced.
3. **`JOURNAL.md`** — seeded with the standing rules and a `## CYCLE 0` entry.

---

## How to run it

**Talk, don't interrogate.** One topic at a time, two or three questions per turn at most. This is a
conversation about someone's money and it should feel like one. A wall of twenty numbered questions
gets you twenty shallow answers.

**Push on vagueness — once.** "Moderate risk" is not a mandate. "I'd cut a position that's down 20%
unless the reason I bought it is still true" is. When an answer is too soft to act on, say what makes
it hard to operationalize and offer two or three concrete versions to react against. People are much
better at editing a proposal than producing a spec. But don't grind: if they genuinely don't know
after one round, write down a sane default, mark it `(default — not yet confirmed)` in `PROFILE.md`,
and move on. They'll refine it after a few cycles, and that's the normal path.

**Reflect back in their own words.** After each section, restate what you heard in one or two lines
and let them correct it. Wrong answers captured early are expensive later.

**Skip what doesn't apply.** Not everyone has an outside portfolio, wants options, or cares about a
benchmark. Don't force a section that clearly isn't relevant to them.

**No jargon they didn't use first.** If they say "I want to bet on AI," don't come back with
"thematic satellite allocation with a concentration ceiling." Meet them where they are, then write
the precise version into the mandate yourself.

**Take the safety sections seriously.** Rounds 0, 4, and 5 exist because this thing spends real
money unattended. Do not speed-run them, and do not let enthusiasm skip them.

---

## Round 0 — Frame it, and check they mean it

Open by making sure they know what they're switching on. Something close to:

> Before the questions — here's what you're setting up. This repo runs an AI agent against a real
> brokerage account on a schedule. When it's live, it will place real orders with real money without
> asking you first, on days you've forgotten about it. That's the design, not a bug. Everything I'm
> about to ask exists to make sure it does that inside limits you actually chose.
>
> Two things I'd push on before we start: fund it with an amount you'd genuinely shrug off — the
> account this template came from started at ten dollars — and use a paper-trading account first if
> your broker has one. You can raise the stakes once you've read a few weeks of its journal.

Then ask the only question that gates the rest:

- **Is this a live-money account or paper trading?**
- **What would make you shut it off?** — Their honest answer here is worth more than any risk
  questionnaire. Whatever they say ("if it lost half of it", "if it bought meme stocks", "if it
  traded every single day") becomes a hard constraint in Round 4. Write it down verbatim.

## Round 1 — The account

- **Which broker?** The reference implementation is Robinhood's agent MCP. Anything with quote +
  order + position tools works. If they don't have one connected yet, that's fine — capture the
  intent and point them at `SETUP.md` at the end.
- **Which specific account, and can an agent actually reach it?** Many brokers gate agent access to
  one designated account. Get the account identifier — every read and every order will pass it
  explicitly, and a loop pointed at the wrong account is the worst possible bug.
- **Taxable or tax-advantaged?** This changes real behavior: wash-sale exposure, short-term gains,
  whether tax-loss harvesting is even a concept that applies.
- **Starting capital, and is there recurring funding?** A loop that gets $100 a week behaves very
  differently from one that gets a lump sum and nothing after — the first can wait for setups, the
  second has one shot at deployment.
- **What can it trade?** Stocks, ETFs, options (which approval level?), crypto. Be specific about
  options: long calls/puts only, or spreads? Selling premium? If they don't know their level, have
  them check before going live.

## Round 2 — What this account is *for*

This is the question most people haven't articulated, and it's the one that makes the mandate
coherent. **What job does this sleeve do that the rest of your money doesn't?**

- **Do they have a portfolio outside this account?** Rough size and shape is enough — mostly index
  funds, mostly single names, a 401k, nothing yet. Do **not** push for precise figures they're not
  volunteering; approximate is genuinely fine, and the file this lands in is private but real.
- **If yes: what should this loop *not* duplicate?** This is the single most useful constraint in the
  whole interview. Someone whose retirement account is already mostly an S&P index fund gains nothing
  from an agent that buys SPY — it's the same bet with more steps and more fees. The sleeve earns its
  existence by expressing things the core
  can't: single names, specific themes, opportunistic entries, tactical trades.
- **If no outside portfolio: is this meant to become the core, or stay a small experiment?** If it's
  meant to grow into someone's actual investing, the mandate should tilt toward diversification and
  boring quality rather than concentrated conviction. Say so plainly.
- **Do they want per-cycle commentary on holdings this loop can't trade?** The reference setup ends
  every cycle with a one-line read on the owner's separate retirement accounts — advice only, the
  loop can't touch them. It's genuinely useful and costs one line. Offer it; if they want it, capture
  which accounts, which holdings, and what decisions they'd want flagged (a rebalance trigger, a
  drawdown level, a DCA pause).

## Round 3 — Investment ideology

The heart of it. You're trying to extract a philosophy specific enough that a stranger could apply it
to a stock you haven't discussed yet. Ask a few of these, follow what they respond to:

- **What do you actually believe about markets?** Are they trying to be right about a story others
  haven't priced in, buy quality and wait, catch mispricings and rotate, ride momentum, harvest
  volatility? There's no correct answer, but the loop needs *one* — an agent with no stated edge
  reverts to buying whatever was in the news that morning.
- **Time horizon.** Are positions meant to be held for years, months, or days? "Long game" and "I
  want it in and out" produce completely different loops from identical prompts.
- **Is there a thesis you already hold?** Most people setting this up have one — AI infrastructure,
  energy transition, biotech, whatever. Get it in their words, and get *why* they believe it.
- **What would change your mind about that thesis?** This is the question that separates a mandate
  from a horoscope. Whatever they say becomes the thesis-break test the loop runs every cycle:
  concrete, checkable conditions under which it should trim, exit, or rotate rather than average
  down. Push for something falsifiable.
- **Describe a trade you'd be proud of. Now one you'd be angry about** — even if it made money.
  Vivid, specific, and far more revealing than any risk-tolerance slider. "Angry about" answers
  usually surface the real hard constraints.
- **How should it be wrong?** Every strategy has a characteristic failure. Would they rather it miss
  a great trade by being slow, or take a bad one by being fast? Sit out a rally in cash, or ride a
  drawdown fully invested?
- **How do you want to know if it's working?** A benchmark, even a rough one, keeps the whole thing
  honest — "beat what these dollars would have done in an index fund" is a fine standard, and so is
  "I'm doing this to learn, P&L is secondary." Capture whichever it is, plus roughly when they'd want
  to re-evaluate.

Also worth asking, because it prevents a specific and common failure:

- **Should it deliberately look outside your thesis every cycle?** Concentrated books drift into
  monocultures — every holding and every new candidate ends up in one theme, and the agent stops
  seeing the rest of the market at all. The reference mandate requires a genuine cross-sector scan
  every cycle with a *falsifiable* entry test, so "staying concentrated" has to be a conclusion the
  loop reaches by looking rather than a default it reaches by not looking. Strongly recommended.
  If they want it, define the bright-line test with them: what would a name outside the thesis have
  to look like for the loop to be obligated to buy a starter position in it?

## Round 4 — Risk and hard limits

Everything here becomes a **hard** rule — the kind the agent is not allowed to reason its way past.
Get explicit numbers. If they won't commit to a number, propose one and mark it as a default.

- **Max position size** — as a percentage of the sleeve, or a dollar cap per trade.
- **Concentration ceiling** — the most any single name may be. The reference loop trims back toward
  target when a winner runs past its ceiling, which is how you keep a good call from quietly becoming
  the entire book.
- **Leverage and decay products** — leveraged ETFs, 0DTE options, anything that bleeds while you're
  right. Allowed at all? If yes, they should require an explicit stop, a time-box, and a journaled
  thesis every time. A leveraged position with no exit plan is a bug, not a trade.
- **Anything that is simply never allowed.** Shorting, penny stocks, crypto, earnings gambles,
  specific sectors they won't own for personal reasons. Include whatever they said in Round 0 about
  shutting it off.
- **Drawdown response.** If the sleeve is down 25%, what should happen — nothing, de-risk, stop
  opening new positions, alert them? Decide now, while nobody's losing money.
- **Universal limits** (state these, confirm they understand — they are in every configuration):
  available buying power only; never deposit, transfer, or self-fund; no order that exceeds
  settled/available funds; broker state always outranks the journal.

## Round 5 — Autonomy and cadence

- **How much autonomy?** Be direct that this is the consequential setting:
  - **Full autonomy** — places orders unattended. What the reference setup runs, and the only mode
    where scheduled cycles do anything but talk. Also the mode that can lose money while they sleep.
  - **Propose-only** — full analysis and journaling, but orders wait for a human. Safe, and a
    genuinely good way to spend the first few weeks: you get the loop's reasoning on the record and
    can grade it before handing over the keys.
  - **Mixed** — autonomous under a dollar or percentage threshold, approval above it.
- **How often?** Reference cadence is 3× per weekday, near the open, midday, and before the close.
  More often mostly buys churn and token spend, not returns. Once a day works fine. Weekly is a
  legitimate choice for a long-horizon mandate, and cheaper in every sense.
- **Where does it run?** Cloud-scheduled (nothing on their machine, survives a closed laptop) or a
  local `cron`/`launchd` job. `SETUP.md` covers both — just capture the preference.
- **How do they want to hear about it?** The journal is always the record of truth. Beyond that:
  nothing, a summary when they ask, or a nudge when something specific happens (a trigger fires, a
  thesis breaks, a drawdown level hits).

## Round 6 — Anything the mandate is missing

Close by asking what you didn't. People often have one specific rule they've been carrying the whole
conversation — a stock they'd never sell, a date they need cash by, a promise to a spouse about how
much can be at risk. Ask directly: **"What's the one rule you'd be upset if this thing broke?"**

---

## Writing the output

### `PROFILE.md`

Their answers, organized by round, **in their language**. This is the human-readable record and the
thing they'll re-read in three months when they want to know what past-them was thinking. Include the
reasoning, not just the settings — *why* they hold a thesis matters more than the ticker. Mark
anything you defaulted for them as `(default — not yet confirmed)`. Date it.

### `LOOP_PROMPT.md`

Replace **every** `{{PLACEHOLDER}}` — the file ships with a comment block at the top listing all of
them. Then read the result start to finish as if you were a cold agent waking up with no context, and
fix anything that doesn't parse standalone.

Be specific and directive. `{{STRATEGY}}` should not read "invest wisely in good companies." It
should read like the mandate of someone with an actual opinion, including what they will *not* do.
Vague mandates produce a loop that buys whatever's in the headlines, which is the exact outcome this
file exists to prevent.

**Optional sections they declined** — the outside-account check, the cross-sector discipline, the
options line — should be **deleted outright**, heading and all. Never leave a bare placeholder or an
empty stub like "N/A"; a cold agent reading a half-filled section will try to satisfy it and waste a
cycle on a check nobody asked for.

Do not delete the operational sections (cycle steps, journal format, persistence, hard limits) —
those are load-bearing and were paid for in real bugs. Adapt them; don't drop them.

### `JOURNAL.md`

Seed it: keep the header, write the standing rules as a compact bulleted summary of the mandate's
hard limits, then append a single `## CYCLE 0` entry dated today recording that the loop was
initialized, the starting capital, and the initial thesis — including anything the user wants bought
on the first live cycle. Cycle 1 reads this to find its footing.

### Then

- `git add -A && git commit -m "init: configure Sidecar loop"` — but **don't push**. They may not
  have a private remote yet, and this content shouldn't land in a public one by accident.
- Tell them exactly what's next, in order: connect the broker, verify with a read-only call, run one
  cycle manually and read the journal entry it produces, *then* schedule it. All of it is in
  **`SETUP.md`** — point them there and offer to walk through it now.
- If they set up a live-money account with full autonomy, say once, plainly and without lecturing,
  what will happen the first time the schedule fires.
