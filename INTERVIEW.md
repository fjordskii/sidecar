# The setup interview

**For the agent, not the user.** When someone opens a fresh clone, follow this to turn it into *their*
trading loop. Read it all before starting.

Output: **`PROFILE.md`** (their answers, their words), **`LOOP_PROMPT.md`** (every `{{PLACEHOLDER}}`
filled), **`JOURNAL.md`** (standing rules + a `CYCLE 0` entry).

## How to run it

- **Talk, don't interrogate.** Two or three questions per turn. It's a conversation about someone's
  money; twenty numbered questions gets you twenty shallow answers.
- **Push on vagueness — once.** "Moderate risk" isn't a mandate. "I'd cut a position down 20% unless
  the reason I bought it is still true" is. Offer two or three concrete versions to react against —
  people edit better than they specify. If they still don't know, write a sane default, mark it
  `(default — not yet confirmed)`, move on. They'll refine it after a few cycles.
- **Reflect back** in their words after each section. Wrong answers captured early get expensive.
- **Skip what doesn't apply.** Not everyone has an outside portfolio or wants options.
- **No jargon they didn't use first.** They say "I want to bet on AI"; you write the precise version
  into the mandate yourself.
- **Don't speed-run rounds 0, 4, and 5.** Those are the ones that spend money unattended.

---

## 0 — Frame it

Make sure they know what they're switching on:

> This runs an AI agent against a real brokerage account on a schedule. Once live, it places real
> orders without asking you first, on days you've forgotten about it. That's the design. Everything
> I'm about to ask makes sure it does that inside limits you actually chose.
>
> Two things first: fund it with an amount you'd genuinely shrug off — the account this came from
> started at ten dollars — and use paper trading first if your broker has it.

- **Live money or paper?**
- **What would make you shut it off?** Worth more than any risk questionnaire. Whatever they say
  ("if it lost half", "if it bought meme stocks", "if it traded every day") becomes a hard constraint
  in round 4. Verbatim.

## 1 — The account

- **Which broker**, and **which specific account** — many brokers gate agent access to one. Get the
  identifier; every read and order passes it explicitly, and a loop pointed at the wrong account is
  the worst possible bug.
- **Taxable or tax-advantaged?** Changes wash-sale exposure, short-term gains, whether harvesting is
  even a concept here.
- **Starting capital, and recurring funding?** A loop fed weekly can wait for setups; one with a lump
  sum and nothing after has one shot at deployment.
- **What can it trade?** Stocks, ETFs, options (which level? spreads? selling premium?), crypto.

## 2 — What this account is *for*

The question most people haven't articulated, and the one that makes the mandate coherent.

- **Is there a portfolio outside this account?** Rough shape is enough — mostly index funds, a 401k,
  nothing yet. Don't push for figures they aren't volunteering.
- **If yes: what should this loop NOT duplicate?** The most useful constraint in the interview.
  Someone whose retirement account is already an S&P index fund gains nothing from an agent that buys
  SPY — same bet, more steps, more fees. The sleeve earns its existence by expressing what the core
  can't: single names, themes, opportunistic entries, tactical trades.
- **If no outside portfolio: is this meant to become the core?** If so, tilt the mandate toward
  diversification and boring quality rather than concentration, and say so plainly.
- **Want per-cycle commentary on accounts this loop can't trade?** The reference setup ends every
  cycle with a one-line read on separate retirement accounts — advice only. Costs one line, genuinely
  useful. If yes: which accounts, which holdings, what decisions they'd want flagged.

## 3 — Investment ideology

The heart. You want a philosophy specific enough that a stranger could apply it to a stock you never
discussed. Ask a few, follow what they respond to:

- **What do you actually believe about markets?** Being right about a story others haven't priced?
  Buy quality and wait? Catch mispricings and rotate? Ride momentum? No correct answer, but the loop
  needs *one* — an agent with no stated edge reverts to buying whatever was in the news that morning.
- **Time horizon.** "Long game" and "in and out" produce completely different loops from identical
  prompts.
- **A thesis they already hold?** Most people setting this up have one. Get it in their words, and
  get *why*.
- **What would change your mind about it?** The question that separates a mandate from a horoscope.
  Becomes the thesis-break test the loop runs every cycle. Push for something falsifiable.
- **Describe a trade you'd be proud of. Now one you'd be angry about** — even if it made money. The
  second usually surfaces the real hard constraints.
- **How should it be wrong?** Miss a great trade by being slow, or take a bad one by being fast? Sit
  out a rally in cash, or ride a drawdown fully invested?
- **How will you know it's working?** A rough benchmark keeps it honest — "beat what these dollars
  would've done in an index fund" is fine, and so is "I'm doing this to learn." Capture which, and
  when they'd re-evaluate.

Then, because it prevents a specific and common failure:

- **Should it deliberately look outside your thesis every cycle?** Concentrated books drift into
  monocultures — every holding and every new candidate lands in one theme and the agent stops seeing
  the market. Strongly recommended. If yes, define the bright-line test: what would a name outside
  the thesis have to look like for the loop to be *obligated* to take a starter position?

## 4 — Risk and hard limits

All of this becomes rules the agent can't reason past. Get numbers; propose one if they won't.

- **Max position size** — % of sleeve or dollar cap per trade.
- **Concentration ceiling** — most any single name may be. Trimming back past it is how a good call
  is kept from quietly becoming the whole book.
- **Leverage / decay products** — leveraged ETFs, 0DTE. Allowed? If yes, require an explicit stop, a
  time-box, and a journaled thesis every time. A leveraged position with no exit plan is a bug.
- **Never allowed** — shorting, penny stocks, crypto, earnings gambles, sectors they won't own.
  Include whatever they said in round 0.
- **Drawdown response** — sleeve down 25%: nothing, de-risk, stop opening, alert them? Decide now,
  while nobody's losing money.
- **Universal** (state, confirm): available buying power only; never deposit or self-fund; broker
  state outranks the journal.

## 5 — Autonomy and cadence

- **How much autonomy?** The consequential setting:
  - **Full** — places orders unattended. The reference setup, and the only mode where a scheduled
    cycle does anything but talk. Also the one that loses money while they sleep.
  - **Propose-only** — full analysis and journaling, orders wait for a human. A genuinely good way to
    spend the first few weeks: you get the reasoning on record and can grade it first.
  - **Mixed** — autonomous under a threshold, approval above it.
- **How often?** 3×/weekday is the reference. Once daily is fine. Weekly is legitimate for a
  long-horizon mandate. More than 3× mostly buys churn.
- **Where does it run?** Cloud or local — just capture the preference; `SETUP.md` covers both.
- **How do they want to hear about it?** Journal always. Beyond that: nothing, a summary on request,
  or a nudge on specific events.

## 6 — What did I miss?

**"What's the one rule you'd be upset if this thing broke?"** People often carry one specific rule
through the whole conversation — a stock they'd never sell, a date they need cash by, a promise about
how much can be at risk.

---

## Writing the output

**`PROFILE.md`** — their answers by round, in their language, including the *reasoning*. Mark
defaults as `(default — not yet confirmed)`. Date it.

**`LOOP_PROMPT.md`** — replace every `{{PLACEHOLDER}}` (they're listed in the file's header comment),
then reread it as a cold agent with no context and fix anything that doesn't stand alone.

- Be directive. `{{STRATEGY}}` should not read "invest wisely in good companies" — it should read
  like someone with an actual opinion, including what they will *not* do. Vague mandates produce a
  loop that buys headlines, which is the exact thing this file prevents.
- **Sections they declined** (outside-account check, cross-sector discipline, options) get **deleted
  outright**, heading and all. Never leave a stub or "N/A" — a cold agent will try to satisfy it.
- **Don't delete the operational sections** (cycle steps, journal format, persistence, hard limits).
  They're load-bearing and were paid for in real bugs. Adapt, don't drop.

**`JOURNAL.md`** — keep the header, write standing rules as a compact summary of the hard limits,
then one `## CYCLE 0` entry dated today: initialization, starting capital, opening thesis, and
anything they want bought on the first live cycle.

**`ops/`** — you already collected every value these need, so fill them in rather than making the
user do it twice:

- **`ops/run.sh`** — fill `{{REPO_PATH}}`, `{{ACCOUNT_ID}}`, `{{BROKER}}`, `{{MCP_SERVER}}`,
  `{{MODEL}}`, `{{AUTONOMY_LINE}}`. For `{{CLI_PATH}}`/`{{NODE_PATH}}`, run `which claude` and
  `which node` and hardcode the real results — a guessed `PATH` is the single most common reason a
  local job fails silently. If they chose cloud-only, still fill it; it's their fallback.
- **`ops/sidecar.plist.example`** — only if they chose local. Substitute the absolute paths and
  match the hours to their cadence.

### Hand them the routine prompt, filled in

If they chose a cloud routine, do **not** just point at `ops/ROUTINE_PROMPT.md` and leave them to
substitute placeholders by hand. Take the template there, fill every value from this interview
(`{{BROKER}}`, `{{ACCOUNT_ID}}`, `{{MCP_SERVER}}`, `{{SLOTS}}`, and the `{{AUTONOMY_LINE}}` matching
what you wrote into `LOOP_PROMPT.md`), and print the finished prompt in the chat as one copy-pasteable
block. Alongside it, give them the rest of the routine config as a short checklist with their actual
values: repo URL, tools allowlist (**including `Bash`** — without it there's no `git push` and the
cycle loses its journal entry), the broker MCP connector, model, `persist_session: off`, and the cron
expression for their cadence and timezone — with the UTC/DST caveat if the cron is fixed-UTC.

This is the step users are most likely to get subtly wrong, and the failure modes are quiet: a
missing `Bash` tool or a locally-added-but-not-connected MCP server produces a routine that runs,
looks fine, and accomplishes nothing.

**Then:** `git add -A && git commit -m "init: configure Sidecar loop"` — but **don't push**; they may
not have a private remote yet.

Close with what's next, in order, and be explicit that the remaining steps need *them*, not you:

1. **Broker** — enable agent trading, complete the investment profile, options approval if needed,
   fund it. In the broker's app; you can't do any of it.
2. **Connect the MCP server** — you can run the command, they approve the OAuth flow in a browser.
   If they're going cloud, they must **also** add it as a connector on claude.ai; a cloud session
   cannot see servers added locally.
3. **Create their private repo** and push.
4. **Verify both paths** — a read call, then a review/preview call to prove orders aren't blocked.
5. **Run one cycle by hand** and read the entry it wrote.
6. **Then** schedule it, with the prompt and checklist you just handed them.

Point at `SETUP.md` for the detail, and offer to walk through it now. If they chose live money with
full autonomy, say once, plainly, what will happen the first time the schedule fires.
