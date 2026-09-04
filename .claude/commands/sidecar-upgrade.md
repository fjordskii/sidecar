---
description: Bring this Sidecar copy up to the latest template version, safely
---

Upgrade this repo to the current Sidecar template. The user is likely non-technical: do the work,
don't hand them instructions.

Upstream raw base is `.upstream.raw_base` in `sidecar-manifest.json`, or
`https://raw.githubusercontent.com/fjordskii/sidecar/main` if the manifest doesn't exist yet.

## Rules — these are not negotiable

Ownership is declared in the upstream `sidecar-manifest.json`. Fetch it first and follow it:

- **`files.system`** — replace with the upstream copy. This now includes the engine under `bot/`
  (`precheck.py`, `postcheck.py`, the schema, the behaviour diff). Delivering it changes nothing
  about a cycle: **the engine is inert** — nothing in the template calls it and `AGENTS.md` names
  no part of it, so it runs only if the user's own `LOOP_PROMPT.md` tells a cycle to run it.
- **`files.system_setup`** (`INTERVIEW.md`, `SETUP.md`, `setup-schema.json`,
  `ops/ROUTINE_PROMPT.md`, `ops/sidecar.plist.example`, `.claude/commands/sidecar-init.md`) —
  onboarding material. Replace **only while this repo is still uninitialized**, and ask that
  question of **`LOOP_PROMPT.md`** with the token grep below — never of the setup files themselves.
  Three of them carry no tokens at all, and `SETUP.md` and `ops/ROUTINE_PROMPT.md` carry them only
  as printed examples that are never filled in, so testing them would answer "uninitialized"
  forever. A missing `LOOP_PROMPT.md` counts as uninitialized. Once the mandate is filled in, skip
  these and name them in the PR body: an interview the user already answered is finished business,
  and declining it must never mean declining engine or rail fixes.
- **`files.system_if_uninitialized`** (`LOOP_PROMPT.md`, `ops/run.sh`) — replace
  **only** while the file still contains a real setup token. Test with exactly this grep, the same
  one the rail uses:
  `grep -qE '\{\{(ACCOUNT_ID|BROKER|MCP_SERVER|STRATEGY|REPO_PATH|CLI_PATH|NODE_PATH|DATE|SLOTS|AUTONOMY|AUTONOMY_LINE)\}\}'`
  No match means setup filled it in and it is the user's file — skip it and name it in the PR body.
  Never a blanket `{{` check: these templates mention `{{PLACEHOLDER}}` in prose and a loose match
  would clobber a live mandate.
- **`files.system_if_absent`** (`JOURNAL.md`, `DECISIONS.md`, `bot/state.json`,
  `bot/failures.jsonl`) — write it **only if the file does not exist**. The test is `test -f`, never the token grep. These files accumulate: a user appends to
  them for months, so "does it still contain a placeholder" answers *yes* for as long as one token
  in the header is unfilled, however many real entries sit below. ⛔ **Never run the token grep
  against a journal.** If the file exists, skip it and name it in the PR body — no exceptions, no
  matter what it contains. `bot/state.json` is the same shape of thing as a journal: it is the
  engine's live record of positions, entry dates and clocks, and a fresh clone needs the empty
  template exactly once.
- **`files.user`** (`PROFILE.md`, `README.md`, `JOURNAL.md` once initialized, `JOURNAL_ARCHIVE.md`,
  `bot/state.json` and `bot/failures.jsonl` once they exist, logs) — never read, never touch.
  **`README.md` moved here in this release**: it was listed under `system` and so was replaced
  unconditionally, which silently destroyed the README of any instance that had written its own.
- **Never** run a trading cycle, place an order, or edit strategy as part of an upgrade.
- ⛔ **A MAJOR bump is held.** If upstream's MAJOR is ahead of the local one — `2.x` when they
  are on `1.x` — the template is saying, by its own `CHANGELOG.md` convention, that this release
  **can change what their loop does with their money**. Do not present it as routine:
  - open it as a **draft** PR (fall back to a normal PR if drafts are unavailable on their plan,
    but keep the warning in the title and body);
  - drop the "changes nothing about your strategy" line — for a MAJOR it is false;
  - lead the body with the newest `CHANGELOG.md` entry's decision line, and with how to run
    `bot/cli/behaviour_diff.py --old <current> --new <candidate> --instance .` in their clone;
  - say that closing the PR is a legitimate outcome: declining a behaviour change is not
    falling behind.
  **Do not run the behaviour diff for them from CI or from a bare checkout.** `bot/raw/` is
  gitignored, so it is absent there, and the diff degrades to exercising almost none of the
  decision surface while still printing "no decision changes" — a false all-clear on exactly
  the release that warrants the check. It has to run where their data is. If you are in their
  clone with `bot/raw/` populated, running it and pasting the output IS the right thing to do.
  A repo with **no `VERSION`** is at `0.0.0` and is *adopting* the rail, not crossing a major —
  never hold that one.

## Steps

1. **Read the local state.** `VERSION` (absent = `0.0.0`), whether `sidecar-manifest.json` and
   `.github/workflows/sidecar-update.yml` exist.
2. **Read upstream** `VERSION` and `sidecar-manifest.json`.
3. **Install or repair the rail.** If `.github/workflows/sidecar-update.yml` is missing, or differs
   from upstream, write the upstream copy. This is the one file the rail can never update itself —
   doing it here is the point of this command.
4. **Apply the update** if upstream is strictly newer (semver): fetch every `files.system` path,
   fetch `files.system_setup` paths only if `LOOP_PROMPT.md` still holds setup tokens, fetch
   `files.system_if_uninitialized` paths that still pass the token grep, fetch
   `files.system_if_absent` paths that do not exist locally, and copy upstream `VERSION`. If local
   and upstream versions match, say so and stop after step 3.
   ⛔ `tools/` and `tests/` are in **no** class and are never fetched: they are the template repo's
   own CI, and `tools/secret_scan.py` would fail a build on the real account number that belongs in
   a private clone's mandate.
5. **Ship it as a PR**, branch `sidecar-update/v<upstream>` — a draft one if the MAJOR-hold
   above applies. Use whatever GitHub tooling this
   session has (the `gh` CLI, GitHub MCP tools). If you can't open a PR, push the branch and give
   them the compare URL. Never push template changes straight to `main`.

   PR body: version before → after, the files updated, the files skipped as already theirs, and one
   line stating their journal, profile, and mandate were not touched.

6. **Report in chat, in two or three sentences:** old version → new version, what changed for them
   in plain language, and whether anything needs a human. Then tell them future updates arrive on
   their own as a weekly PR — this command is only needed if the rail itself falls behind.

## If the repo is pre-rail (no `VERSION`, no manifest)

That's the normal migration case, and steps 1–6 already handle it: treat local as `0.0.0`, install
the rail, backfill `VERSION` and `sidecar-manifest.json`, skip everything setup personalized. Say
plainly that nothing about their loop changed — they just gained automatic updates.

## Uninitialized repo

If `PROFILE.md` doesn't exist and `LOOP_PROMPT.md` still has its setup tokens, this is a fresh copy
that was never set up. Upgrading is harmless, but say so and offer `/sidecar-init` instead.
