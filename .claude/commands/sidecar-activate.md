---
description: Switch on the deterministic layer (bot/) for this loop, after showing what it would change
---

Wire `bot/precheck.py` and `bot/postcheck.py` into this repo's own `LOOP_PROMPT.md`, so the
engine actually runs each cycle instead of sitting there inert.

**This edits the user's mandate.** That file is theirs — the update rail never touches it, and
nothing else in Sidecar will ever write to it. Running this command IS the consent. So the job
is to show them what changes *before* changing it, and to leave them able to undo it.

The user is likely non-technical. Do the work; don't hand them a checklist.

## Refuse to proceed if

- `bot/precheck.py` is missing → they are on a pre-2.0 copy. Tell them to run `/sidecar-upgrade`
  first, then come back.
- `LOOP_PROMPT.md` still contains `{{ACCOUNT_ID}}` → setup never finished. Send them to
  `/sidecar-init`; there is no mandate to activate yet.
- The mandate already calls `precheck.py` → say so and stop. Do not add it twice.

## Steps

1. **Read `bot/state.json`'s `policy` block aloud to them, in plain language, before anything
   else.** Bloc caps, per-name bands, tier sizes, position cap, cash floor. These arrived as
   template defaults from somebody else's book and are about to start **blocking their trades**.
   Ask whether the numbers suit their account. Edit `bot/state.json` with any they want changed.
   ⚠ Do not skip this because they said "just do it" — a gate they did not choose is the whole
   risk of this command. One pass, plainly stated, then move on.

2. **Show them what would fire today.** Run one cycle's FETCH by hand into `bot/raw/`, then:

   ```bash
   python3 bot/precheck.py
   ```

   Nothing is committed and no order is placed — precheck only reads the broker and writes
   `bot/brief.md`. Walk them through every 🚨 REQUIRED ACTION it produces. **These are what the
   engine will demand from the next cycle onward.** If the list is long or surprising, that is a
   reason to fix the policy numbers in step 1, not a reason to push on.

   Note honestly: findings like `LIVE_TIER_MISSING` and `NO_REVIEW_TRIGGER` fire on positions
   they already hold, because those were bought before the engine existed and have no tier or
   review trigger recorded. Those clear as they score each position — they are a backlog, not a
   fault. Per-name bands stay advisory until the book holds
   `policy.bands.min_positions_to_bind` positions, because a hard ceiling is not reachable on a
   book too small to satisfy it.

3. **Get an explicit yes.** Not "should I continue" buried in a paragraph — state that the next
   step edits their mandate and that from the following cycle the loop can be blocked by these
   gates. If they hesitate, stop; nothing has changed yet and the engine stays inert.

4. **Edit `LOOP_PROMPT.md`, minimally.** Take the engine steps from the current template
   (upstream `LOOP_PROMPT.md`, the `THE DETERMINISTIC LAYER` section and the engine additions
   to cycle states 3, 4, 5, 6 and 8) and merge them into **their** file, matching their state
   names and numbering. ⛔ Change nothing else: not their strategy, not their risk limits, not
   their autonomy setting, not their account. If their mandate has diverged enough that the
   merge is unclear, show them a diff and let them choose — never guess at a mandate.

   Append a dated amendment line recording the change, per this repo's amendment discipline.

5. **Ship it as a PR**, branch `sidecar-activate`. Never push a mandate edit straight to `main`.
   The PR body says: what was added, that the policy numbers are now binding, which findings
   fired in step 2, and that closing the PR leaves the engine inert with nothing lost.

## Afterwards

Tell them the first cycle with the engine on is worth watching, and that
`bot/cli/behaviour_diff.py` exists if they ever want to see what a future engine change would
do to their book before installing it.

⛔ **Never run a trading cycle, place an order, or run `postcheck.py --commit` as part of this
command.** `postcheck.py` rewrites state and can rotate a journal; activation is a mandate edit
and nothing more.
