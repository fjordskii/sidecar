# Sidecar — Product Roadmap

_Decisions locked 2026-08-29 with the maintainer. This file is the plan of record for the
onboarding wizard, the versioning rail, and the internal architecture evolution. It is a
maintainer doc, not user documentation — it is not referenced by agents during cycles._

## Context

The template has 5–6 live users, all non-technical. Setup today is a 30-minute manual walk
through SETUP.md (git, CLI, OAuth, placeholders, scheduler config) with several quiet failure
modes. Target audience is "normies" — this product is their first aha moment with agentic
systems, and onboarding should sell that, not git.

## Decision log

| Decision | Choice | Rationale |
|---|---|---|
| Setup architecture | Hosted wizard with GitHub OAuth (Vercel, Next.js) | Automates repo creation + config commit; no DB, token lives only for the flow |
| Interview format | Guided form now; the user's own agent offers to refine the mandate on its first interactive run | Deterministic, no LLM backend cost; polish step reuses the product itself |
| Versioning | Staged: manifest + automated update PRs first; user/system file split as format v2 later | Rail works for current users today; v2 migrates through the rail |
| Existing users | Mixed cloud/local, exact split unknown | Migration path must auto-detect scheduler type |
| Internal architecture | Soft state machine (deterministic gates, probabilistic judgment) — NOT a full code runner | See analysis below |

## What a web wizard can and cannot automate

| Setup step (SETUP.md) | Automatable? |
|---|---|
| Create private repo from template | Yes — GitHub OAuth + template generation API |
| Interview → PROFILE.md / LOOP_PROMPT.md / JOURNAL.md / ops/ | Yes — guided form, committed to the repo via API |
| Robinhood OAuth + MCP connector | Partially — deep links + prefilled steps; the OAuth approval is inherently theirs |
| Create the Claude Routine | No public Routines API [verify before build] — best possible: prefilled copy block + per-field checklist + deep link |

Realistic ceiling: **3 clicks + 1 guided paste.** The wizard steers everyone to cloud
routines, which deletes the entire local-ops failure class (PATH, `which claude`, detached
HEAD) for normies. Local ops stay documented for power users.

## Core software analysis — the case for a soft state machine

The "core software" is ~500 lines of English prose interpreted non-deterministically, plus
~100 lines of bash that only does scheduling. Zero code in the trading path. Every
correctness invariant is prose read by a probabilistic reader, and the repo's own docs
catalog the production failures this caused:

- 4 days of read-only cycles, well-reasoned, every order silently blocked (no hard gate
  between auth and execution)
- commit succeeds / push fails / journal entry silently lost (no verified-persist step)
- wrong MCP tool prefix → runs that look successful and do nothing (no preflight)
- two order-capable schedulers racing one journal (human-detected only)
- journal rotation at 250KB left to agent discretion every cycle

The current fix pattern is more prose read by the same reader. The mechanical invariants
want code; the judgment wants prose.

A full code runner (public.com-style orchestration with the LLM invoked only for judgment
states) was considered and rejected for now:

1. **Portability is the product.** The template runs on claude.ai routines, Cursor, GH
   Actions, local cron. A code runner assumes a runtime the cloud-routine sandbox doesn't
   guarantee. Revisit if a dedicated runner (e.g. GitHub Actions as the primary scheduler)
   is adopted.
2. **The mandate is user-editable English** — amending your agent by arguing with it is the
   brand's core loop. Code walls it off.
3. **Normies can't debug code** but can read English and paste an error into Claude.

### Soft state machine — stages

- **v1.1 — named states in the mandate.** Restructure `THE CYCLE` in LOOP_PROMPT.md into
  `AUTHENTICATE → SYNC → SCAN → DECIDE → PREVIEW → EXECUTE → RECONCILE → JOURNAL → PERSIST
  → VERIFY`, each with explicit exit criteria, plus a machine-readable status line in every
  journal entry: `state: TRADED|HOLD|SKIPPED`, `order_path: OK|FAILED|UNVERIFIED`,
  `push: VERIFIED`. Makes the broken-pipe failure class detectable by the next cycle and by
  tooling.
- **v1.2 — `loop/` shell gates.** Tiny deterministic scripts the agent MUST call at state
  transitions: `preflight.sh` (auth, tool-prefix check, dual-scheduler detection via journal
  runner tags), `verify-push.sh` (remote SHA must equal HEAD, nonzero exit otherwise),
  `rotate-journal.sh`. `loop/` is system-owned in the manifest → upgradeable via the rail.
- **v2 — health surface.** The web app reads status lines from the user's repo and shows
  "loop healthy / broken pipe / stale". Normie-facing payoff; no log reading required.

## Versioning design (Stage 1 — built)

- `VERSION` — semver of the template the repo is on.
- `sidecar-manifest.json` — file ownership classes:
  - `system`: template-owned, always updated (CLAUDE.md, INTERVIEW.md, SETUP.md, ops docs,
    this rail itself, setup-schema.json)
  - `system_if_uninitialized`: updated only while still containing `{{PLACEHOLDER}}` markers
    (LOOP_PROMPT.md, JOURNAL.md, ops/run.sh) — once the interview fills them, they're the
    user's forever
  - `user`: never touched (PROFILE.md, JOURNAL.md after init, JOURNAL_ARCHIVE.md, logs)
- `.github/workflows/sidecar-update.yml` — weekly + manual. Diffs local VERSION against
  upstream, applies system files per the manifest, opens a PR. User merges with one click.
  The workflow cannot rewrite its own workflow file (GITHUB_TOKEN limitation), so a changed
  rail is flagged in the PR body as a manual copy step.
- **Existing users (pre-rail):** add the workflow file once (web UI paste, or a PR from the
  maintainer). First run treats missing VERSION as 0.0.0 and opens a PR that backfills
  VERSION + manifest without touching initialized files. Auto-detection of scheduler type
  reads journal runner tags and ops/run.sh fill state.

### Stage 2 (later) — format v2

Split user answers out of LOOP_PROMPT.md so the mandate template becomes system-owned and
upgradeable (answers live in PROFILE/config and render into the mandate). The Stage-1 rail
performs the migration when v2 lands — the payoff for shipping the rail first.

## Build order

1. ✅ Versioning rail: VERSION, sidecar-manifest.json, sidecar-update.yml
2. ✅ setup-schema.json — single source of truth for setup fields (drives the wizard form
   AND the agent interview, so they can't drift)
3. 🟡 Wizard app deployed: `fjordskii/sidecar-web` (private), live at
   https://sidecar-web-fjordskiis-projects.vercel.app (protection disabled, Git-connected
   auto-deploys, WIZARD_SECRET set). 18 render-engine tests green; production smoke-tested.
   Remaining: GitHub OAuth App creation (web UI only — can't be scripted), then set
   GITHUB_CLIENT_ID/SECRET env vars and redeploy, then a real end-to-end run.
4. ✅ Robinhood + routine handoff screens with verify-before-trust checklist (shipped in
   the wizard's launch step)
5. ⬜ Soft state machine v1.1 (named states + journal status lines)
6. ⬜ `loop/` shell gates (v1.2)
7. ⬜ Migration kit run for existing users
8. ⬜ Health surface in the web app (v2)

## Risks

- No public claude.ai Routines API → guided-paste handoff (planned).
- GitHub OAuth scope sizing: creating private repos needs `repo`; request the minimum and
  document why on the consent screen copy.
- Form-captured mandates are shallower than conversational ones → mitigated by the
  agent-refines-mandate step and by presets people can react against.
- Template repo must stay public for raw.githubusercontent fetches used by the update rail.
- GitHub disables scheduled workflows after 60 days of repo inactivity — harmless for live
  loops (cycles push constantly) but a dormant loop's rail goes quiet; note in SETUP.md.
