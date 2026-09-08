# Upgrading an older Sidecar copy

For repos made before the update rail existed. One time, two minutes, and your loop keeps running
throughout. Nothing here touches your journal, your mandate, or your profile.

Not sure whether you need this? If your repo has no `VERSION` file at its root, you do.

## Step 1 — give your repo the upgrade command (once, two clicks)

Your copy predates `/sidecar-upgrade`, so the command doesn't exist yet and typing it does
nothing. Adding it is two clicks and no typing:

1. Open this link, replacing `<you>/<your-repo>` with your repo:

   `https://github.com/<you>/<your-repo>/new/main?filename=.claude%2Fcommands%2Fsidecar-upgrade.md&value=---%0Adescription%3A%20Bring%20this%20Sidecar%20copy%20up%20to%20date%0A---%0A%0AFetch%20https%3A%2F%2Fraw.githubusercontent.com%2Ffjordskii%2Fsidecar%2Fmain%2F.claude%2Fcommands%2Fsidecar-upgrade.md%0Aand%20follow%20it%20exactly.%20It%20replaces%20this%20file%20during%20the%20upgrade%2C%20so%20this%20stub%20is%20needed%20once.%0A`

   It opens GitHub's editor with the file path **and its contents already filled in.**

2. Click **Commit changes** (straight to `main` is fine).

That's the whole of step 1. The stub is six lines; the real command replaces it during the
upgrade, so you never do this again.

> Prefer to paste? Create `.claude/commands/sidecar-upgrade.md` with:
>
> ```markdown
> ---
> description: Bring this Sidecar copy up to date
> ---
>
> Fetch https://raw.githubusercontent.com/fjordskii/sidecar/main/.claude/commands/sidecar-upgrade.md
> and follow it exactly. It replaces this file during the upgrade, so this stub is needed once.
> ```

## Step 2 — run it

Open your repo in Claude — the same session you use for the loop — and type:

```
/sidecar-upgrade
```

That is the only command you need, now or ever. It installs the update rail, backfills the
version files, skips everything setup personalized, offers to switch the deterministic layer on
if you want it, and opens **one** pull request for you to merge.

After that, updates arrive on their own as a weekly pull request. Merging it is the whole job.

## Fallback — no Claude session at all

Steps 1–2 are the supported path. This one gets the rail in without Claude, but it cannot offer
you the deterministic layer, so run `/sidecar-upgrade` afterwards if you want that.

1. Open this link, replacing `<you>/<your-repo>` — it opens GitHub's editor with the path already
   filled in:
   `https://github.com/<you>/<your-repo>/new/main?filename=.github/workflows/sidecar-update.yml`
2. Paste the entire contents of
   [`sidecar-update.yml`](https://raw.githubusercontent.com/fjordskii/sidecar/main/.github/workflows/sidecar-update.yml).
3. **Commit changes** — straight to `main` is fine.
4. **Actions** tab → enable workflows if GitHub asks → **Sidecar update** → **Run workflow**.
5. Merge the pull request it opens.

## What the upgrade actually brings you

Your loop keeps running exactly as it does today. Specifically:

- **Your mandate, journal, profile and `ops/run.sh` are not touched.** Verified against a real
  copy of the 2026-08-10 template with everything filled in.
- **Your `README.md` is not touched either — and that is a fix.** Until v1.8.0 the template
  claimed ownership of `README.md` and replaced it on every update, so if you had written your
  own and lost it, that was this bug. Your text is still in your repo's git history.
- **Onboarding files stop arriving.** `INTERVIEW.md`, `SETUP.md` and friends are skipped once
  your mandate is filled in. You already answered the interview; you should not get a pull
  request about it every release.

**New: a `bot/` folder with an engine in it — that does nothing.**

It is roughly 76KB of tested Python that computes the mechanical parts of a cycle: cash as a
percentage of the account, position weights on both bases, per-name bands, concentration in
dollars *and* in daily risk, tier sizing, add-route cooldowns, and a ledger that carries an
unresolved finding into the next cycle and escalates anything recurring three times.

**Nothing runs it.** Not the template, not `AGENTS.md`, not your routine. It arrives as files
that sit there. It runs only if *you* add the steps to your own `LOOP_PROMPT.md`, which is the
one file the update rail never touches once you have filled it in. Leaving it switched off
forever is a perfectly good choice and costs you nothing.

⚠ **If you do decide to switch it on, read `bot/state.json` first.** The numbers under `policy`
— bloc caps, per-name bands, tier sizes, the position cap — are *starting defaults carried over
from the loop this engine was built for*. They are one person's risk limits. They were not
chosen for your account, and nothing has checked whether they suit it.

## Afterwards

Updates arrive on their own: at most one pull request a week, titled `Sidecar update: vX → vY`.
Merging it is the whole upgrade. Two exceptions, both handled by re-running `/sidecar-upgrade`:
the rail file itself (GitHub forbids a workflow from editing workflow files, so the PR body says
so when it changes), and a **MAJOR** release, which arrives as a draft PR titled
`⚠ MAJOR … (behaviour diff required)` because it can change what your loop does with money.

You never need a second command. `/sidecar-upgrade` also offers the deterministic layer if it is
present and switched off. `/sidecar-activate` exists only for someone who said no and came back
later — you should never have to reach for it.

---

## Maintainer notes

- The rail treats a repo with no `VERSION` as `0.0.0` and backfills by PR.
- Initialized `LOOP_PROMPT.md` / `ops/run.sh` are detected by the specific-token grep and skipped —
  nothing personalized changes. `/sidecar-upgrade` uses the same token list; keep the two in sync if
  it ever changes.
- `system_setup` (added v1.8.0) is onboarding material — `INTERVIEW.md`, `SETUP.md`,
  `setup-schema.json`, `ops/ROUTINE_PROMPT.md`, `ops/sidecar.plist.example`, `/sidecar-init`. It
  is delivered only while the repo is still uninitialized, and that question is asked of
  **`LOOP_PROMPT.md`**, never of the setup files themselves: three of them carry no setup tokens
  at all, and `SETUP.md` and `ops/ROUTINE_PROMPT.md` carry them only as printed examples that are
  never filled in, so a file testing itself would answer "still onboarding" forever.
- `bot/state.json` and `bot/failures.jsonl` are existence-gated like the journal: seeded once for
  a clone that has none, never written again. A running engine's positions and entry dates live
  in that file.
- `JOURNAL.md` and `DECISIONS.md` are **never** token-tested. They are written only when absent and
  skipped whenever they exist, because they accumulate — the token grep would answer "still
  uninitialized" for a journal of any length whose header had one unfilled placeholder. Do not move
  an accumulating file back into the token-gated class.
- If a user's loop is paused and their repo goes 60 days without commits, GitHub disables the
  scheduled run. A manual dispatch (step 4) or `/sidecar-upgrade` revives it.
- With push access to a user's repo, just commit the workflow file yourself — then they only merge.
- **Verified end-to-end**, against a real `cb67bb2` (2026-08-10) checkout personalised
  the way a live user's is — mandate and `ops/run.sh` filled, own README, real journal. Result:
  all four kept byte-identical; `VERSION`, the manifest, `AGENTS.md`, a seeded `DECISIONS.md` and
  the inert engine delivered; all six onboarding files skipped. Re-run that simulation before any
  release that changes a manifest class.
- Ready-to-send version of the above: point them at this file's first two sections.
