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
5. **The marker is a claim, and the rail does not yet check it.** `bot/cli/behaviour_diff.py`
   is the tool that can: it runs the installed engine and a candidate against a copy of your
   real state and reports whether the new one would decide differently. **Nothing calls it
   automatically.** The update rail opens a PR; it has no MAJOR-hold and no
   version-contract gate. That gap is survivable only for as long as the engine stays
   inert — see the note under 1.8.0 — and the release that makes the engine binding is the
   one that has to close it.

History before 1.8.0 predates this convention and is not reconstructed here; those releases
are in `git log`. Retrofitting decision markers onto them would mean asserting, after the
fact, something nobody established at the time — which is exactly what marker 3 forbids.

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
