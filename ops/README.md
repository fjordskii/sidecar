# ops/ — running it on a schedule

| File | |
|---|---|
| [`ROUTINE_PROMPT.md`](ROUTINE_PROMPT.md) | **The prompt + config for any scheduler. Start here.** |
| [`run.sh`](run.sh) | Headless cycle for local `launchd`/`cron`. |
| [`sidecar.plist.example`](sidecar.plist.example) | macOS `launchd` job. |
| `run.log` | Local run output. Gitignored — contains balances. |

## Cloud or local?

|  | Cloud routine | Local |
|---|---|---|
| Machine must be awake | No | **Yes** |
| Setup | Paste a prompt into a web UI | Script + job + debug `PATH` |
| Repo state | Fresh clone (**detached HEAD** — needs explicit refspec) | Persistent checkout on a branch |
| DST | Cron usually fixed **UTC** — drifts twice a year | Local time, follows DST |
| Debugging | Routine session log | `tail -f ops/run.log` |

**Recommendation: cloud.** The reference setup ran locally for a month then migrated, for one reason:
no laptop has to stay open. A scheduler that only runs when you're at your desk isn't unattended, and
the failure is silent — no error, just no cycle.

Keep `run.sh` filled in anyway. It's the fallback when a cloud routine breaks.

> ⚠️ **Never run both.** Two order-capable runners share one journal with no lock — both wake on the
> same catalyst and spend the same buying power. Migrating? Disable the old one the same day.

## Local install (macOS)

```bash
# 1. Fill every {{PLACEHOLDER}} in run.sh — repo path, account, model, MCP server, autonomy
#    line, and PATH (`which claude`, `which node`).
chmod +x ops/run.sh

# 2. Test by hand FIRST, while the market is open. This is a real cycle that can place real
#    orders — that's the point.
bash ops/run.sh

# 3. Read what it did before automating.
cat ops/run.log && tail -40 JOURNAL.md

# 4. Install the timer.
cp ops/sidecar.plist.example ~/Library/LaunchAgents/com.sidecar.loop.plist
#    edit the three /ABSOLUTE/PATH/TO/ placeholders, then:
launchctl load ~/Library/LaunchAgents/com.sidecar.loop.plist
launchctl list | grep sidecar     # `- 0 com.sidecar.loop` = registered, not yet run
```

Remove with `launchctl unload ~/Library/LaunchAgents/com.sidecar.loop.plist`.

**Linux/cron** — same `run.sh`:

```cron
38 9,12 * * 1-5  /bin/bash /path/to/sidecar/ops/run.sh
33 15   * * 1-5  /bin/bash /path/to/sidecar/ops/run.sh
```

## Gotchas

- **`PATH` is the #1 local failure.** launchd and cron don't source your profile. If `claude` or
  `node` isn't findable the job runs, dies instantly, and logs almost nothing. Hardcode absolutes.
- **Tool names in `--allowedTools` must match the MCP server exactly.** Wrong prefix → the run
  proceeds cheerfully with no broker access. Looks successful, did nothing.
- **Verify a run fired.** `launchctl list | grep sidecar` shows last exit status; `run.log` should
  open with a fresh `=== run <timestamp> ===`.
- **Don't edit `run.sh` mid-run.** bash reads the file as it executes; overwriting is a real race.
- **Push failures are silent data loss.** Commit succeeds, push fails, the entry never leaves the
  machine. Check the remote SHA.
- **`run.sh` retries 3×**, which is only safe because each attempt re-reads live broker state and
  spends available buying power. If you change that, revisit the retry before it double-trades.
