# Upgrading an older Sidecar copy

For repos made before the update rail existed. One time, two minutes, and your loop keeps running
throughout. Nothing here touches your journal, your mandate, or your profile.

Not sure whether you need this? If your repo has no `VERSION` file at its root, you do.

## Easiest: ask Claude

Open your repo in Claude — the same session you use for the loop — and run:

```
/sidecar-upgrade
```

It installs the update rail, backfills the version files, skips everything setup personalized, and
opens a pull request for you to merge. Older copy with no `.claude/commands/` folder? Paste this
instead:

> Upgrade this repo to the latest Sidecar template from
> https://github.com/fjordskii/sidecar — install `.github/workflows/sidecar-update.yml`, backfill
> `VERSION` and `sidecar-manifest.json`, and apply the template-owned files listed in the upstream
> manifest. Do not touch `PROFILE.md`, `JOURNAL.md`, or my filled-in `LOOP_PROMPT.md`. Open it as a
> pull request.

## By hand, on github.com

No terminal needed.

1. Open this link, replacing `<you>/<your-repo>` — it opens GitHub's editor with the path already
   filled in:
   `https://github.com/<you>/<your-repo>/new/main?filename=.github/workflows/sidecar-update.yml`
2. Paste the entire contents of
   [`sidecar-update.yml`](https://raw.githubusercontent.com/fjordskii/sidecar/main/.github/workflows/sidecar-update.yml).
3. **Commit changes** — straight to `main` is fine.
4. **Actions** tab → enable workflows if GitHub asks → **Sidecar update** → **Run workflow**.
5. Merge the pull request it opens.

## After either path

Updates arrive on their own: at most one pull request a week, titled `Sidecar update: vX → vY`.
Merging it is the whole upgrade. The one exception is the rail file itself — GitHub forbids a
workflow from editing workflow files, so when that changes the PR body says so. Run
`/sidecar-upgrade` and it handles that copy for you.

---

## Maintainer notes

- The rail treats a repo with no `VERSION` as `0.0.0` and backfills by PR.
- Initialized `LOOP_PROMPT.md` / `ops/run.sh` are detected by the specific-token grep and skipped —
  nothing personalized changes. `/sidecar-upgrade` uses the same token list; keep the two in sync if
  it ever changes.
- `JOURNAL.md` and `DECISIONS.md` are **never** token-tested. They are written only when absent and
  skipped whenever they exist, because they accumulate — the token grep would answer "still
  uninitialized" for a journal of any length whose header had one unfilled placeholder. Do not move
  an accumulating file back into the token-gated class.
- If a user's loop is paused and their repo goes 60 days without commits, GitHub disables the
  scheduled run. A manual dispatch (step 4) or `/sidecar-upgrade` revives it.
- With push access to a user's repo, just commit the workflow file yourself — then they only merge.
- Ready-to-send version of the above: point them at this file's first two sections.
