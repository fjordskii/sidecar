# Migration kit — pre-rail Sidecar repos

_For the maintainer: the message below is ready to send to each existing user. Their repo
gets the update rail; from then on, template improvements arrive as one-click PRs._

---

**The message to send:**

> Sidecar now self-updates. One-time, two minutes, no terminal:
>
> 1. Open your repo on GitHub → **Add file → Create new file**.
> 2. Name it exactly: `.github/workflows/sidecar-update.yml` (GitHub makes the folders for
>    you as you type the slashes).
> 3. Paste the entire contents of this file:
>    https://raw.githubusercontent.com/fjordskii/sidecar/main/.github/workflows/sidecar-update.yml
> 4. **Commit changes** (straight to main is fine).
> 5. Go to the **Actions** tab → enable workflows if GitHub asks → **Sidecar update →
>    Run workflow**.
>
> It will open a pull request that adds the versioning files. Read it if you're curious,
> then merge — it does **not** touch your journal, your mandate, or your profile.
>
> From then on, when Sidecar improves you'll get a PR titled "Sidecar update: vX → vY"
> once a week at most. Merging it is the whole upgrade.

---

**Maintainer notes**

- Works because the rail treats a repo with no `VERSION` as `0.0.0` and backfills by PR.
- Their initialized `LOOP_PROMPT.md` / `JOURNAL.md` / `ops/run.sh` are detected by the
  specific-token check and skipped — nothing they've personalized changes.
- If a user's loop is paused and their repo goes 60 days without commits, GitHub disables
  the scheduled run; step 5 (manual dispatch) revives it.
- If you (the maintainer) have push access to a user's repo, skip the message and just
  commit the workflow file directly — one less step for them.
