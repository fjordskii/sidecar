#!/bin/bash
# Sidecar — headless trading cycle.
#
# The local-scheduler path: a non-interactive agent session fired by launchd (macOS) or cron
# (Linux). See ops/README.md to install, and SETUP.md Step 6 for how this compares to a cloud
# routine (which needs none of this file).
#
# Fill in every {{PLACEHOLDER}} before use.

set -uo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO="{{REPO_PATH}}"                   # absolute path to your private clone
LOG="$REPO/ops/run.log"
ACCOUNT="{{ACCOUNT_ID}}"
MODEL="{{MODEL}}"                      # e.g. opus
MCP_TOOLS="mcp__{{MCP_SERVER}}"        # broker MCP server name, mcp__-prefixed

# Weekday guard. Market holidays are a no-op decided inside the session — it checks the
# calendar and logs a short HOLD — but skipping weekends here saves two pointless runs.
[ "$(date +%u)" -ge 6 ] && exit 0

# launchd starts with a near-empty PATH, so the agent CLI and node must be spelled out.
# Verify yours with `which claude` and `which node`, and hardcode the results.
export PATH="{{CLI_PATH}}:{{NODE_PATH}}:/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$REPO" || exit 1

# ── The prompt ────────────────────────────────────────────────────────────────
# A pointer, not a strategy — see ops/ROUTINE_PROMPT.md. Strategy lives in LOOP_PROMPT.md so
# it stays version-controlled and amendable; duplicating it here creates two mandates that
# silently disagree.
PROMPT="Scheduled cycle of the {{BROKER}} account ${ACCOUNT}. You are ONE run of a shared,
continuous trading loop — not a standalone bot with its own mandate.

Source of truth — read both, in this order:
  1. Mandate/spec: ${REPO}/LOOP_PROMPT.md
  2. Memory/journal: ${REPO}/JOURNAL.md — tail it (~15KB), do not read the whole file. The
     most recent CYCLE entry is the current thesis and carries standing triggers left for you
     by the previous cycle. Honor them.

Then execute the cycle EXACTLY as LOOP_PROMPT.md describes: verify session, pull live
portfolio/positions/open orders, gather news and run the cross-sector scan, form a thesis,
and act within the mandate's hard limits. Trust the live broker API over anything in the
files — another runner may have traded since the last entry. Preview orders before placing
when sizing is unclear. Spend available buying power only; never deposit or self-fund. If the
market is closed, or buying power is ~\$0 with nothing to manage, log a brief HOLD cycle and
stop cleanly.

{{AUTONOMY_LINE}}

Identify yourself in the journal entry as a LOCAL cycle (distinct from any 'cloud routine' or
'interactive' entries already in the journal) and note which daily slot this is.

Finish by APPENDING a new dated ## CYCLE entry to ${REPO}/JOURNAL.md in the exact format
given in LOOP_PROMPT.md. End with a one-paragraph summary of what you did and why."

# ── Run ───────────────────────────────────────────────────────────────────────
echo "=== run $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

# Retry transient API/connection failures (exit != 0), which otherwise killed a meaningful
# share of runs. Safe to retry because the cycle is state-driven, not fire-and-forget: it
# re-reads live broker state on every attempt and only spends AVAILABLE buying power, so a
# retry after a partial fill sees the buying power already consumed and won't double-trade.
status=1
attempt=0
for attempt in 1 2 3; do
  claude -p "$PROMPT" \
    --model "$MODEL" \
    --allowedTools "$MCP_TOOLS,WebSearch,WebFetch,Read,Write,Edit,Glob,Grep"
  status=$?
  [ "$status" -eq 0 ] && break
  echo "=== attempt $attempt failed (exit $status); retry in 30s ==="
  sleep 30
done
echo "=== exit $status after $attempt attempt(s) ==="

# ── Persist ───────────────────────────────────────────────────────────────────
# The repo is the loop's durable state. `git add -A` sweeps up mandate edits too, so this
# doubles as a backstop for any spec change left uncommitted by an interactive session.
# Failure-tolerant by design: a git or network hiccup must never affect the trading run.
{
  cd "$REPO" && git add -A \
    && git commit -m "cycle: $(date '+%Y-%m-%d %H:%M %Z') (scheduled run, exit $status)" \
    && git push
} >> "$LOG" 2>&1 || echo "=== git sync failed (non-fatal) ==="

# Note: a persistent local checkout sits on a normal branch, so a plain `git push` works here.
# Cloud runners clone fresh and land in DETACHED HEAD, where it does not — see LOOP_PROMPT.md
# step 7 for the explicit-refspec fix.

# Don't edit this script while a run is in flight: bash reads the file as it executes, so a
# concurrent overwrite mid-run is a genuine race.
