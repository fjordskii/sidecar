---
description: Bring this Sidecar copy up to the latest template version, safely
---

Upgrade this repo to the current Sidecar template. The user is likely non-technical: do the work,
don't hand them instructions.

Upstream raw base is `.upstream.raw_base` in `sidecar-manifest.json`, or
`https://raw.githubusercontent.com/fjordskii/sidecar/main` if the manifest doesn't exist yet.

## Rules — these are not negotiable

Ownership is declared in the upstream `sidecar-manifest.json`. Fetch it first and follow it:

- **`files.system`** — replace with the upstream copy.
- **`files.system_if_uninitialized`** (`LOOP_PROMPT.md`, `ops/run.sh`) — replace
  **only** while the file still contains a real setup token. Test with exactly this grep, the same
  one the rail uses:
  `grep -qE '\{\{(ACCOUNT_ID|BROKER|MCP_SERVER|STRATEGY|REPO_PATH|CLI_PATH|NODE_PATH|DATE|SLOTS|AUTONOMY|AUTONOMY_LINE)\}\}'`
  No match means setup filled it in and it is the user's file — skip it and name it in the PR body.
  Never a blanket `{{` check: these templates mention `{{PLACEHOLDER}}` in prose and a loose match
  would clobber a live mandate.
- **`files.system_if_absent`** (`JOURNAL.md`, `DECISIONS.md`) — write it **only if the file does not
  exist**. The test is `test -f`, never the token grep. These files accumulate: a user appends to
  them for months, so "does it still contain a placeholder" answers *yes* for as long as one token
  in the header is unfilled, however many real entries sit below. ⛔ **Never run the token grep
  against a journal.** If the file exists, skip it and name it in the PR body — no exceptions, no
  matter what it contains.
- **`files.user`** (`PROFILE.md`, `JOURNAL.md` once initialized, `JOURNAL_ARCHIVE.md`, logs) —
  never read, never touch.
- **Never** run a trading cycle, place an order, or edit strategy as part of an upgrade.

## Steps

1. **Read the local state.** `VERSION` (absent = `0.0.0`), whether `sidecar-manifest.json` and
   `.github/workflows/sidecar-update.yml` exist.
2. **Read upstream** `VERSION` and `sidecar-manifest.json`.
3. **Install or repair the rail.** If `.github/workflows/sidecar-update.yml` is missing, or differs
   from upstream, write the upstream copy. This is the one file the rail can never update itself —
   doing it here is the point of this command.
4. **Apply the update** if upstream is strictly newer (semver): fetch every `files.system` path,
   fetch `files.system_if_uninitialized` paths that still pass the token grep, fetch
   `files.system_if_absent` paths that do not exist locally, and copy upstream `VERSION`. If local
   and upstream versions match, say so and stop after step 3.
5. **Ship it as a PR**, branch `sidecar-update/v<upstream>`. Use whatever GitHub tooling this
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
