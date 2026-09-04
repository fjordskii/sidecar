# bot/ — the deterministic layer

> ## ⚠ WHETHER THIS RUNS IS DECIDED BY YOUR MANDATE, AND ONLY BY YOUR MANDATE
>
> Since v2.0.0 the **template's** `LOOP_PROMPT.md` calls `precheck.py` and `postcheck.py`
> in cycle states 3–8, so a **new clone runs the engine from its first cycle.**
>
> An **existing** repo does not, and cannot be switched on behind your back. Your mandate is
> yours: the update rail never touches `LOOP_PROMPT.md` once setup has filled it in, and
> `AGENTS.md` — the one file that IS replaced wholesale on every update — names no part of
> `bot/` and never will. One line there would switch the engine on in every user's next
> cycle without anyone choosing it. CI asserts it stays absent.
>
> **To switch an existing repo on:** run `/sidecar-activate`. It reads you the policy numbers
> first, shows you exactly which findings would fire on your book today, and only then edits
> your mandate — as a PR you can close. **To leave it off:** do nothing.
>
> ⚠ Either way, read `state.json`'s `policy` block line by line before the engine binds.
> Those numbers are STARTING DEFAULTS carried over from the instance this engine was built
> for. They are not advice, they were never chosen for your account, and from v2.0.0 they
> can block a trade.

**Why this exists:** the loop is a model reading a prose spec, so prose rules fail silently — a
rule went unrun for ~40 cycles, a capability was never discovered, arithmetic drifted unnoticed.
Anything mechanical belongs here. The model's job is judgment, not bookkeeping.

## Cycle procedure

**Step 1 — FETCH.** `mkdir -p bot/raw` first (it is gitignored, so it does not exist in a fresh
clone). MCP tools are callable only by the model, not by scripts, so the model fetches
and dumps raw JSON. Write the tool's **entire response** verbatim; `precheck.py` unwraps the
envelope itself. Batch the array-taking calls — one call, not one per symbol.

| file | call |
|---|---|
| `bot/raw/portfolio.json` | `get_portfolio(account_number)` |
| `bot/raw/accounts.json` | `get_accounts()` |
| `bot/raw/positions.json` | `get_equity_positions(account_number)` |
| `bot/raw/quotes.json` | `get_equity_quotes([...holdings, ...bench])` ← **one batched call**; `bench` carries your benchmark symbol |
| `bot/raw/orders.json` | `get_equity_orders(account_number, created_at_gte=<last cycle>)` |
| `bot/raw/atr_<SYM>.json` | `get_equity_technical_indicators(SYM, type="atr", interval="day", start_time=<~60d ago>, output="latest")` — one per holding; **without these the risk caps are NOT evaluated** |
| `bot/raw/news_<SYM>.json` | `get_equity_news(SYM)` — holdings under adjudication + live candidates. **Primary news source; dated and attributed.** Not needed for every holding every cycle |
| `bot/raw/realized_pnl.json` | `get_realized_pnl(account_number, span="all")` — Friday benchmark only; replaces the hand-computed realized tally |

**Step 2 — PRECHECK.** `python3 bot/precheck.py` → writes `bot/brief.md` and prints it.

**Step 3 — DECIDE.** Read `brief.md`, **not** the raw JSON and **not** the whole journal. Every
mechanical gate is already evaluated. Spend the cycle on what only a model can do:
**gate ③ — is this drawdown a fundamental crack or a positioning flush?** — plus gate ④ theme
overlap, thesis falsification, and conviction tiering. **Resolve or explicitly justify every item
under 🚨 REQUIRED ACTIONS.**

**Step 4 — ACT & WRITE.** Place orders (declare **TIER + reason before** ordering). Append a
journal entry ≤6KB: what changed, what you decided, why. Do not restate unchanged lists — those
live in `state.json`.

⛔ **Step 4a — RE-DUMP `bot/raw/orders.json` AND `bot/raw/positions.json` AFTER placing, BEFORE
postcheck.** The step-1 fetch
happens *before* any order exists, so a fill placed this cycle is never in that file. Without the
re-dump, `ORDER_ID_NOT_JOURNALED` fires on every cycle that trades — i.e. exactly the cycles the
check exists for — and the tier/route recorder falls back to prose instead of the broker. Re-fetch
`get_equity_orders(account_number, created_at_gte=<last cycle>)` and overwrite the file. Found
2026-08-27. **`positions.json` added 2026-08-31 for the same reason on the SELL side:
`record_exits` marks a sold name closed by diffing state against the broker's live positions,
so against a pre-trade dump a position sold this cycle still looks held and the exit is never
recorded. Re-dump both, or neither leg of a swap lands in state.**

**Step 5 — POSTCHECK.** `python3 bot/postcheck.py --cycle "YYYY-MM-DD HH:MM" --commit`, then
commit and push everything (`git push origin HEAD:refs/heads/main` — detached HEAD in the cloud
container).

⛔ **Step 5a — WHILE TRIMMING FOR `ENTRY_OVERSIZE`, RUN POSTCHECK **WITHOUT** `--commit`.** That
carry is designed to force re-runs, and `--commit` on each one writes another near-identical
`postcheck: auto-fix` commit: the 2026-08-27 12:42 cycle produced **seven** of them and, because
`git commit` then exits non-zero on a clean tree, the `&&`-chained `cycle:` commit and push never
ran at all. Iterate with the bare script, pass `--commit` only on the final clean run, and make
the `cycle:` commit as its own command — never chained behind a commit that may legitimately
find nothing to do. Found 2026-08-27.

## The feedback loop

`postcheck.py` validates the cycle it just ran and responds in three tiers:

- **AUTO-FIX** — mechanical drift is repaired immediately (e.g. journal over 250KB is rotated,
  preserving the header and every `## NOTE`).
- **CARRY** — behavioural misses are appended to `failures.jsonl` and surfaced by the next
  `precheck.py` under **🚨 REQUIRED ACTIONS**, at the top of the brief, where they cannot be
  skipped. They stay open until an entry addresses them — **but only while they still reproduce.**
  ⛔ **A carried row is a CLAIM; the live broker fetch is the FACT.** A code the current fetch does
  not reproduce is demoted to **ℹ️ Stale carried findings** — not an action item, never a reason to
  trade — and postcheck closes it at `--commit`. It keeps carrying as 🚨 **UNVERIFIED** only when
  the inputs it depends on were NOT read cleanly (`RAW_MISSING` etc.), since non-reproduction proves
  nothing there. Fixed 2026-09-01 15:30: `prior` was by construction the *non-reproducing* set and
  every member of it was printed as a REQUIRED ACTION — one demanded a sale on a weight the live
  book contradicted by 5.4pts.
- **ESCALATE** — a failure recurring **3+ cycles** prints a loud banner: *the rule is wrong, not
  the run.* Rewrite or retire it in `LOOP_PROMPT.md` — and record WHY in `DECISIONS.md` —
  rather than repeating the same miss. ⚠ **It fires only on a finding that REPRODUCED this cycle**
  (`FAIL`, counted as prior occurrences + 1). Before the same 2026-09-01 fix it was attached
  exclusively to the non-reproducing list, so it could never fire on a genuinely recurring failure
  and fired forever on ones already fixed.

Checks: entry present · entry ≤6KB · TIER declared when an order was placed · Friday close carries
a `**Benchmark:**` line · a `BLOC` line present · live buying power actually read · prior
REQUIRED ACTIONS addressed · journal size.

## Files

| file | owner | notes |
|---|---|---|
| `../LOOP_PROMPT.md` | the HOT spec | your operating rules, read every cycle. **The engine runs only if this file tells a cycle to run it.** |
| `../DECISIONS.md` | the COLD spec | rationale, evidence, superseded rules — read ONLY when questioning a rule. **A rule change edits both; if they disagree, LOOP_PROMPT governs.** |
| `state.json` | postcheck writes, precheck reads | positions/entry dates, bench + 52-wk highs, PASS list with expiry, pre-commitment counters, deployment clock, policy thresholds. **Never hand-edit prose into it.** |
| `precheck.py` | — | computes everything mechanical → `brief.md` |
| `postcheck.py` | — | validates, auto-fixes, carries, escalates |
| `failures.jsonl` | append-only | the feedback ledger; a `resolved:true` row closes a code |
| `brief.md` | regenerated each cycle | the model's actual input |
| `raw/` | model writes | verbatim MCP responses; safe to delete between cycles. Gitignore it — it is your live book |
| `schema/state.schema.json` | — | what a valid `state.json` looks like; `schema_check.py` enforces it |
| `cli/behaviour_diff.py` | — | runs two engine versions against a COPY of your state and reports whether the new one would decide differently **before** you install it |

## Failure behaviour

Both scripts are built so a bug in them cannot silently disable the checks:

- `state.json` unreadable → brief says **STATE UNREADABLE**, run manually, do not trade blind.
- `precheck.py` raises → brief says **PRECHECK CRASHED — checks did NOT run**, and says plainly
  not to assume gates passed.
- a missing `raw/` file → logged as `RAW_MISSING`, that section degrades, the rest still runs.
- no ATR files → risk caps explicitly reported as **not evaluated** rather than quietly skipped.

A cycle that cannot read the broker **HOLDS and says so.**
