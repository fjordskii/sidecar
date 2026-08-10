# ops/ — running it on a schedule

The loop is only a loop because something fires it. This directory holds the local-scheduler
path plus the prompt template every scheduler uses.

| File | What it's for |
|---|---|
| [`ROUTINE_PROMPT.md`](ROUTINE_PROMPT.md) | **The prompt you paste into any scheduler.** Start here regardless of which option you pick. |
| [`run.sh`](run.sh) | Headless cycle for a local `launchd`/`cron` job. |
| [`sidecar.plist.example`](sidecar.plist.example) | macOS `launchd` job definition. |
| `run.log` | Output from local runs. Gitignored — it contains balances and positions. |

## Which scheduler?

|  | Cloud routine | Local (`launchd`/`cron`) |
|---|---|---|
| Machine must be awake | No | **Yes** |
| Survives laptop sleep, travel, reboots | Yes | No |
| Setup | Paste a prompt into a web UI | Write a script, install a job, debug `PATH` |
| Broker auth | Connector on your account | OAuth token in your local session |
| Repo state | Fresh clone each run (**detached HEAD** — needs the explicit push refspec) | Persistent checkout on a branch |
| DST | Cron is usually fixed **UTC** — drifts an hour twice a year | Local time, follows DST automatically |
| Debugging | Read the routine's session log | `tail -f ops/run.log` |

**Recommendation: cloud.** The reference setup ran locally for a month, then migrated, and the
motivation was simple — no terminal and no laptop has to stay open for the loop to keep working. A
scheduler that only runs when you happen to be at your desk isn't really unattended, and the failure
is silent: you don't get an error, you just get no cycle.

The local path is still worth having. It's fully under your control, easy to inspect, needs no
external service, and is the natural fallback if a cloud routine breaks. Keep `run.sh` filled in even
if you don't install it.

> ⚠️ **Never run both at once.** Two order-capable runners share one journal with no lock: both wake
> on the same catalyst, both read the same buying power, both act. The "read live broker state first"
> rule is a read-then-act race, not a mutex. If you migrate, disable the old one in the same sitting.
> The reference setup ran both for a day and got two cycles competing for the same slot.

## Installing the local job (macOS)

```bash
# 1. Fill in every {{PLACEHOLDER}} in run.sh — repo path, account, model, MCP server,
#    autonomy line, and the PATH entries (`which claude`, `which node`).
chmod +x ops/run.sh

# 2. Test it by hand FIRST, at a time the market is open. This is a real cycle that can
#    place real orders — that's the point of the test.
bash ops/run.sh

# 3. Read what it did before automating it.
cat ops/run.log
tail -40 JOURNAL.md

# 4. Install the timer.
cp ops/sidecar.plist.example ~/Library/LaunchAgents/com.sidecar.loop.plist
#    edit the three /ABSOLUTE/PATH/TO/ placeholders inside, then:
launchctl load ~/Library/LaunchAgents/com.sidecar.loop.plist
launchctl list | grep sidecar     # `- 0 com.sidecar.loop` = registered, not yet run
```

To remove it: `launchctl unload ~/Library/LaunchAgents/com.sidecar.loop.plist`.

### Linux / cron

Same `run.sh`, different timer. `crontab -e`:

```cron
38 9,12 * * 1-5  /bin/bash /path/to/sidecar/ops/run.sh
33 15   * * 1-5  /bin/bash /path/to/sidecar/ops/run.sh
```

cron's environment is even more minimal than launchd's — the explicit `PATH` export in `run.sh` is
doing real work here, and a wrong one is the single most common reason a job "runs" and produces
nothing.

## Gotchas worth knowing before they bite

**`PATH` is the number one local failure.** launchd and cron do not source your shell profile. If
`claude` or `node` isn't findable, the job runs, fails instantly, and logs almost nothing. Hardcode
absolute paths from `which`.

**Check the allowlist tool names.** `--allowedTools` must match the MCP server's actual, exact tool
prefix. Get it wrong and the run proceeds cheerfully with no broker access — a cycle that looks
successful and did nothing.

**Verify a run actually fired.** `launchctl list | grep sidecar` shows the last exit status, and
`run.log` should open with a fresh `=== run <timestamp> ===` line. A cycle you assume ran is worth
nothing.

**Don't edit `run.sh` mid-run.** bash reads the script file as it executes; overwriting it during a
run is a genuine race, and the symptom is bizarre partial execution.

**Push failures are silent data loss.** The commit succeeds locally, the push fails, and the cycle
entry never leaves the machine. Check the remote SHA, not the local log — the journal *is* the
product here.

**Watch what a retry means.** `run.sh` retries a failed run up to 3 times, which is safe only because
each attempt re-reads live broker state and spends available buying power only. If you change the
mandate so a cycle acts on stale or cached state, revisit that loop before it double-trades.
