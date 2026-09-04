# Changelog

Every version of Sidecar answers one question before anything else:
**could this change what my loop does with my money?**

---

## The convention (binding — a release that ignores it does not ship)

**Every entry states, in ONE line, whether it can change a trading decision.** That line
comes first and starts with exactly one of three markers:

| marker | meaning |
|---|---|
| `DECISION: no` | cannot change any gate, cap, size, route, clock or REQUIRED ACTION |
| `DECISION: YES` | can — say **which** decision, and what changes |
| `DECISION: unknown` | you have not established it. **Not shippable.** Establish it, or ship it as MAJOR. |

Rules that make the marker mean something:

1. **"Refactor" is not an acceptable entry** for a money-moving system. If you cannot say
   what a change does to a decision, you do not know what you changed.
2. **`DECISION: YES` forces a MAJOR bump**, whatever the size of the code change. A
   one-character constant that moves a cap is MAJOR. A thousand-line rewrite that provably
   cannot move one is not.
3. **The version numbers carry trading semantics, not engineering ones:**
   - **PATCH** `1.8.1` — bug fix, no decision change. Rides the update rail.
   - **MINOR** `1.9.0` — new capability, additive, existing decisions unchanged. Rides the rail.
   - **MAJOR** `2.0.0` — would change a trading decision. **Explicit opt-in**, and never
     installed before a behaviour diff has been shown.
4. **A change to `LOOP_PROMPT.md` is a decision change unless you can argue otherwise.**
   The mandate is the model's input; rewording a rule can change behaviour even when no
   code moved. Say which way. In practice the rail never touches a filled-in mandate, so
   this applies to what a *new* clone starts with.
5. **A MAJOR is held; the diff is yours to run.** Since 1.9.0 the update rail refuses to
   hand you a MAJOR as a routine, ready-to-merge PR: it opens a draft, drops the "changes
   nothing" line, and tells you to run `bot/cli/behaviour_diff.py` against your own clone
   first. Closing that PR is a legitimate outcome — declining a behaviour change is not
   falling behind.
   **The rail deliberately does not run the diff for you.** It runs on a fresh checkout,
   where `bot/raw/` is gitignored and therefore absent; the engine then degrades and most of
   the decision surface never executes, so the diff would print "no decision changes" having
   tested almost nothing. A false all-clear on the one release most likely to move money is
   worse than no check. The diff is only meaningful where your data is.

History before 1.8.0 predates this convention and is not reconstructed here; those releases
are in `git log`. Retrofitting decision markers onto them would mean asserting, after the
fact, something nobody established at the time — which is exactly what marker 3 forbids.

---

## [2.0.0] — 2026-09-04 · the engine becomes binding

**DECISION: YES — from this release a new clone's cycle can be BLOCKED by a gate.**

Every release since 1.8.0 shipped the engine and said, truthfully, that nothing ran it. This
one wires `bot/precheck.py` and `bot/postcheck.py` into the template's own `LOOP_PROMPT.md`,
at cycle states 3 through 8. A clone created from this version runs the deterministic layer
from its first cycle, and the numbers in `bot/state.json` stop being documentation.

### Which decisions change — named, because "it adds checks" is not good enough

New findings a cycle must resolve or justify in writing before it may proceed:

- `BLOC_SOFT_CAP` · `BLOC_HARD_CAP` · `BLOC_RISK_HARD` — concentration, in dollars and in
  ATR-denominated daily risk. Inert on a book with no bloc members declared.
- `BAND_BREACH` · `BAND_HARD` — per-name weight against its band. **Advisory until the book
  holds `policy.bands.min_positions_to_bind` (4) positions** — see below.
- `LIVE_TIER_MISSING` · `NO_REVIEW_TRIGGER` — a held position with no conviction tier or no
  review trigger recorded.
- `PRECOMMIT_EXPIRED` — a pre-commitment that has failed its observation count.
- `CARRIED_UNADDRESSED` — a prior REQUIRED ACTION the entry does not mention. Findings do not
  age out; that is the point of the ledger.

`postcheck.py` additionally **fails a cycle** that placed an order with no declared TIER, or
whose fill landed outside its declared tier's band, or that omitted the weekly benchmark line,
or whose entry has no status line.

Sizing becomes tiered — a conviction tier as a percentage of the total account — replacing
whatever flat starter size a mandate had drifted into. Adds become explicit routes with a
per-name weekly cooldown on the macro-weakness route.

### Fixed — a gate that could not be satisfied

Per-name bands are now **advisory until the book holds four positions**
(`policy.bands.min_positions_to_bind`, and an instance may set it to 0).

This is arithmetic, not tuning. With two positions the smaller is at least 50% of equity; with
three, at least 33.3%. The shipped 35% hard ceiling is therefore **unreachable below three
names** and needs four to hold with any realistic spread. Binding it from cycle one meant a
new user's first brief opened with high-severity findings ordering them to trim positions they
had just bought, to meet a limit no allocation of their book could have met. A band enforces
diversification *within* a built book; it is not a rule you can obey while building one. The
weights are still printed either way — the user sees exactly where they stand.

### Existing repos are NOT switched on

Your `LOOP_PROMPT.md` is yours. The update rail has never touched it once setup filled it in,
and `AGENTS.md` — the one file replaced wholesale in an initialized repo — names no part of
`bot/`, which CI asserts on every commit. So this release changes nothing about a running loop
unless its owner asks.

To ask: **`/sidecar-activate`**. It reads the policy numbers out in plain language, runs
`precheck.py` once so you can see exactly which findings fire on your actual book *before*
anything binds, requires an explicit yes, and then edits your mandate as a PR you can close.
It refuses to run `postcheck.py --commit` or to place an order.

### Upgrading

This is the first MAJOR, and the rail holds it: you will get a **draft** PR titled
`⚠ MAJOR … (behaviour diff required)` rather than the usual routine one. Read `CHANGELOG.md`,
run `bot/cli/behaviour_diff.py` against your clone, and close the PR if you do not want this.
Declining is not falling behind.

---

## [1.10.0] — 2026-09-04 · a way in for people without a broker

**DECISION: no — onboarding copy only. No gate, cap, size, route, clock or REQUIRED ACTION
moves, and nothing here is read during a cycle.**

Setup assumed you already had a brokerage account. Everyone who didn't hit step 1 of
`SETUP.md` with nowhere to go, and the interview's broker question had no answer for "I'm
not on Robinhood yet" — a dead end at the exact moment someone is most willing to act.

### Added

- **A Robinhood signup link at the four places the question actually comes up**: the README
  (setup section and *Works with*), `SETUP.md` §3 before the Robinhood steps, `INTERVIEW.md`
  round 1 as an aside the agent offers once, and `setup-schema.json` round 1 (intro and the
  Robinhood option), which is what the wizard renders as a form.
- The interview's version is **bounded on purpose**: offered once, never repeated, never
  pressed, and skipped outright for anyone who already has an account or picked another
  broker. An agent conducting an interview about someone's money does not get to sell to
  them; it mentions the link because approval and the first ACH take a day or two and
  flagging that early is genuinely useful, then drops it.

### Disclosed

It is a **referral link** and every instance of it says so in the same breath, including
what each side gets. A template that quietly monetises its own setup flow would be a worse
template. Nothing about the loop's behaviour, broker support, or defaults changes: Alpaca
and "other" are untouched, and Robinhood remains a choice rather than a requirement.

---

## [1.9.0] — 2026-09-04 · the rail learns to hold a MAJOR

**DECISION: no — this changes the update path, not any gate, cap, size, route or clock.**

Until now the convention promised something the rail did not do. Rule 3 said a MAJOR is
opt-in and is not installed before a behaviour diff has been shown; the rail compared two
version strings and opened the same cheerful pull request either way, carrying the line
*"merging this changes nothing about your strategy"* — which for a MAJOR would be false.
A non-technical user merging on that promise is the whole risk this template exists to
manage.

### Added

- **A MAJOR-hold in `.github/workflows/sidecar-update.yml`.** When upstream's MAJOR is ahead
  of yours the update PR is opened as a **draft**, retitled `⚠ MAJOR … (behaviour diff
  required)`, and its body leads with the changelog's decision line and a copy-pasteable
  recipe for running `bot/cli/behaviour_diff.py` against your own clone. The reassurance
  line is dropped. Closing the PR is named as a legitimate outcome. Drafts are unavailable
  on some private-repo plans, so it falls back to a normal PR with the warning intact rather
  than failing.
- The same rule in `/sidecar-upgrade`, so both upgrade paths agree (invariant 3).

### Why the rail does not run the diff for you

It runs on a fresh checkout, and `bot/raw/` — the verbatim broker data the engine reads — is
gitignored and therefore absent there. `behaviour_diff.py` against a repo with no `raw/`
degrades: bands, bloc caps, risk caps, sizing and the add channel never execute, so it would
report **"no decision changes"** having exercised almost none of the decision surface. A
false all-clear on the release most likely to move money is worse than no check at all. The
diff is only meaningful where your data is, which is your clone, after a cycle has fetched.

### Not held, deliberately

A repo with **no `VERSION`** is at `0.0.0` and is *adopting* the rail, not crossing a major.
Without that carve-out every pre-rail user would meet this hold on the one pull request that
is supposed to be easy.

---

## [1.8.0] — 2026-09-04 · the deterministic layer arrives, inert

**DECISION: no — nothing in this release can change what a cycle does.**

That claim rests on one specific, checkable property rather than on the code being
harmless: **nothing in the template invokes the engine.** `AGENTS.md` — the file the rail
replaces wholesale on every update, and therefore the one file that could switch it on for
everybody at once — names no part of `bot/`. CI asserts that on every commit. The cycle
procedure that would call `precheck.py` lives in your own `LOOP_PROMPT.md`, which the rail
never touches once setup has filled it in.

So this release lands as files nothing runs. It becomes binding only when you choose to add
the steps to your own mandate, and **that** release — for whoever makes it, in their own
repo — is the MAJOR one. It is opt-in by construction, because only you can edit your
mandate.

### Added — the engine (`bot/`)

Harvested from three weeks of live use in the reference instance and scrubbed of every
personal artefact: no account number, no positions, no journal, no bench, no theme.

- `bot/precheck.py` — computes the brief: cash and cash-as-%-of-account, weights on both
  bases, per-name bands, bloc concentration in **dollars and in daily risk (ATR-based)**,
  pre-commitment gates and their failure counters, 52-week-high roll-off, PASS-list expiry,
  the deployment clock, tier sizing bands, the add channel with its cooldown, order
  reconciliation, and carried REQUIRED ACTIONS.
- `bot/postcheck.py` — validates the cycle, auto-fixes what is mechanical, carries what is
  not into the next brief, and escalates anything recurring 3+ cycles as *"the rule is
  wrong, not the run."*
- `bot/state.json`, `bot/failures.jsonl` — shipped empty. The `policy` block carries
  starting defaults; **they are one person's numbers and were not chosen for your account.**
  Read them before you switch anything on.
- `bot/schema/state.schema.json` + `bot/schema_check.py` — what a valid state file looks
  like, validated with the standard library alone.
- `bot/cli/behaviour_diff.py` — runs two engine versions against a **copy** of your state
  and reports whether the new one would decide differently. See convention rule 5.

### Added — the template's own safety net

- `tools/secret_scan.py` + `.github/workflows/ci.yml` — fails the build on anything shaped
  like a real account number, a populated state field, a journal entry, a personal path or
  an email. Sidecar is public and is cloned by people who point it at real money; the leak
  this prevents had already happened once. Not delivered to clones: your mandate
  legitimately contains the number this refuses.

### Fixed

- **`README.md` was `system`, so the rail replaced it unconditionally.** Any instance that
  had written its own README lost it on every update, under a PR body promising their files
  were untouched. It is now `user`. If this happened to you, your README is in your git
  history. `DECISION: no`.
- **`bot/raw/` and `bot/brief.md` are gitignored.** The engine's first run writes verbatim
  broker JSON — your real positions, balances and order ids — into `bot/raw/`.

### Changed

- New manifest class **`system_setup`** (`INTERVIEW.md`, `SETUP.md`, `setup-schema.json`,
  `ops/ROUTINE_PROMPT.md`, `ops/sidecar.plist.example`, `/sidecar-init`): onboarding
  material, delivered only while a repo is still uninitialized. Once your mandate is filled
  in, an interview you already answered stops arriving as churn — **without** that meaning
  you decline engine or rail fixes. `DECISION: no`.
- `docs/ROADMAP.md` item 6 (`loop/` shell gates) struck: superseded by this backport.

### Not in this release, deliberately

- **No activation.** See the decision line. Guiding users through amending their mandates
  would mean editing an input they wrote about their own account.
- **No policy interview.** The defaults ship as defaults. Nothing asks you to adopt them,
  and nothing enforces them until you say so.
