#!/usr/bin/env python3
"""
behaviour_diff.py — ⭐ run the OLD and the NEW engine against the user's REAL current
state and show, before anything is installed, whether the new one would decide
differently today.

This is the feature that makes multi-user upgrades safe.
**Nobody upgrades a system that moves money blind.**

How it works, and why each choice is the way it is:

  * **Two subprocesses, not two imports.** Old and new engines are different code with the
    same module names; importing both into one process would silently run whichever won
    the import race. Each side runs as its own `python3 bot/precheck.py`.
  * **Two sandboxes, never the live instance.** `precheck.py` appends to
    `failures.jsonl`, and a dry run must not leave a trace in the real ledger — a
    phantom carried finding would show up as a REQUIRED ACTION in the next real cycle.
    Each side gets its own copy of state.json / raw / journal / ledger.
  * **A structured DECISION FINGERPRINT, not just a text diff.** Text diffs are noisy
    (timestamps, wording) and, worse, they bury the one changed number in a wall of
    unchanged prose. The fingerprint pulls out exactly the things that can change what
    the loop does with money: gate results, REQUIRED ACTIONS, caps, sizing bands, the
    clock, cooldowns, pre-commitment gates. Everything else is reported as COSMETIC.
  * **A failure to produce a brief is itself a decision difference.** If the new engine
    crashes or refuses on this state, that is the single most important thing the diff
    can tell you, and it is reported as a decision change, not as an error.
"""

from __future__ import annotations
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile

# What gets copied into each sandbox, as (path relative to the clone root). Everything a
# clone needs in order to produce a brief — and nothing else, so a sandbox can never be
# mistaken for a real clone or push anything anywhere.
SANDBOX_ITEMS = ("bot/state.json", "bot/failures.jsonl", "bot/raw",
                 "JOURNAL.md", "JOURNAL_ARCHIVE.md", "LOOP_PROMPT.md")

# `precheck.py` finds state.json, failures.jsonl and raw/ relative to its OWN file, and
# takes no --instance flag. So a sandbox is only isolated if the ENGINE goes in the box
# too: each side gets a copy of its candidate's bot/*.py beside a copy of the data. Point
# an engine at a sandbox any other way and it reads — and appends to — the live ledger.
ENGINE_FILES = ("precheck.py", "postcheck.py", "schema_check.py")

# Normalise the TIMESTAMP ONLY, not the line it sits on. Blanking the whole line would
# hide any wording change that shares it — a diff tool that hides changes is worse than
# no diff tool.
_TS_TOKEN = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")


class DiffError(Exception):
    pass


# ------------------------------------------------------------------ running

def _sandbox(clone_root: str, dest: str) -> str:
    os.makedirs(os.path.join(dest, "bot"), exist_ok=True)
    for item in SANDBOX_ITEMS:
        src = os.path.join(clone_root, item)
        if not os.path.exists(src):
            continue
        dst = os.path.join(dest, item)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    # Deliberately no synthesised policy, no seeded state: the diff has to run on what
    # the user actually has, or it is answering a question nobody asked.
    return dest


def run_engine(core_dir: str, instance_dir: str, timeout: int = 120) -> tuple[str, int, str]:
    """-> (brief text, exit code, stderr). Never raises on a failing engine."""
    src_bot = os.path.join(core_dir, "bot")
    if not os.path.exists(os.path.join(src_bot, "precheck.py")):
        raise DiffError(f"no engine at {os.path.join(src_bot, 'precheck.py')}")
    # Copy this candidate's engine into its own sandbox — see ENGINE_FILES above.
    for fn in ENGINE_FILES:
        f = os.path.join(src_bot, fn)
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(instance_dir, "bot", fn))
    schema_src = os.path.join(src_bot, "schema")
    if os.path.isdir(schema_src):
        shutil.copytree(schema_src, os.path.join(instance_dir, "bot", "schema"),
                        dirs_exist_ok=True)
    script = os.path.join(instance_dir, "bot", "precheck.py")
    brief = os.path.join(instance_dir, "brief.md")
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        p = subprocess.run([sys.executable, script, "--brief", brief],
                           capture_output=True, text=True, timeout=timeout, env=env,
                           cwd=instance_dir)
    except subprocess.TimeoutExpired:
        return ("", 124, f"engine at {core_dir} timed out after {timeout}s")
    text = ""
    if os.path.exists(brief):
        with open(brief) as f:
            text = f.read()
    if not text:
        text = p.stdout
    return (text, p.returncode, p.stderr)


# ------------------------------------------------------------------ fingerprint

def fingerprint(brief: str) -> dict:
    """The decision-relevant content of a brief, as comparable fields."""
    fp: dict = {}

    for marker, status in (("STATE UNREADABLE", "STATE_UNREADABLE"),
                           ("PRECHECK CRASHED", "PRECHECK_CRASHED")):
        if marker in brief:
            fp["status"] = status
            break
    else:
        fp["status"] = "OK" if brief.strip() else "EMPTY"

    def one(pattern, name, group=1, flags=0):
        m = re.search(pattern, brief, flags)
        if m:
            fp[name] = m.group(group).strip()

    one(r"\*\*Buying power \(authoritative\): ([^*]+)\*\*", "cash.buying_power")
    one(r"\*\*cash = ([\d.]+)% of account\*\*", "cash.pct_of_account")
    one(r"^## Positions \((\d+)\)", "positions.count", flags=re.M)
    one(r"cost \$[\d,.]+ → value \$[\d,.]+ = \*\*([+-][\d.]+%)\*\*", "positions.total_return")

    # per-position weight + review-trigger presence: a band breach is a decision
    for m in re.finditer(r"^\| ([A-Z.]{1,6}) \| ([\d.]+) \| ([^|]+) \| ([^|]+) \| [^|]* \| ([^|]*)\|$",
                         brief, re.M):
        sym, wt, val, pl, review = m.groups()
        fp[f"position.{sym}.weight_pct"] = wt
        fp[f"position.{sym}.value"] = val.strip()
        fp[f"position.{sym}.review_missing"] = "MISSING" in review

    # The bloc label is configurable, so match whatever label the brief printed.
    one(r"\*\*([A-Z0-9 /&+._-]{2,30} BLOC [^*]+)\*\*", "concentration.bloc_equity")
    one(r"\(soft (\d+(?:\.\d+)?)% / hard (\d+(?:\.\d+)?)%\)", "concentration.caps_equity", 0)
    one(r"bloc = ([\d.]+)% of DAILY RISK\*\*", "concentration.bloc_risk_pct")
    one(r"book risk ≈ ([^/]+)/day", "concentration.book_risk")
    one(r"top risk contributors: (.+)$", "concentration.top_risk", flags=re.M)

    for m in re.finditer(r"^- \*\*(TIER[123])\*\* ([\d.]+)–([\d.]+)% of account = \*\*(.+?)\*\*$",
                         brief, re.M):
        fp[f"sizing.{m.group(1)}.pct"] = f"{m.group(2)}-{m.group(3)}"
        fp[f"sizing.{m.group(1)}.dollars"] = m.group(4)
    one(r"^- positions \*\*(\d+/\d+)\*\*", "sizing.position_count_vs_cap", flags=re.M)
    fp["sizing.at_soft_cap"] = "AT SOFT CAP" in brief
    one(r"minimum new position [\d.]+% of account = \*\*([^*]+)\*\*", "sizing.min_new_position")

    one(r"^- session \*\*(\d+/\d+)\*\* · cash ([\d.]+)% vs target ≤(\d+)%", "clock.session",
        group=0, flags=re.M)
    fp["clock.inactive"] = bool(re.search(r"^- \*\*INACTIVE\*\*", brief, re.M))
    fp["clock.target_met"] = "✅ target met" in brief
    one(r"\*\*deployable now: ([^*]+)\*\*", "clock.deployable")
    one(r"cash floor (\$[\d,.]+)", "clock.cash_floor")

    # add channel
    one(r"^- eligible now: (.+)$", "adds.eligible", flags=re.M)
    one(r"^- blocked \(do-not-add[^)]*\): \*\*([^*]+)\*\*", "adds.blocked", flags=re.M)
    m = re.search(r"ROUTE 3 ON COOLDOWN[^\n]*", brief)
    fp["adds.route3_cooldown"] = m.group(0) if m else (
        "clear" if "R3 cooldown: clear" in brief else None)

    # pre-commitments: a gate flipping is the sharpest possible decision change
    for m in re.finditer(r"^- 🔔 \*\*([A-Z.]{1,6}) GATE MET", brief, re.M):
        fp[f"precommit.{m.group(1)}"] = "GATE MET"
    for m in re.finditer(r"^- ([A-Z.]{1,6}) \$[\d,.]+ vs gate \$[\d,.]+ — \*\*fails by ([+-][\d.]+%)\*\*, (\d+)",
                         brief, re.M):
        fp[f"precommit.{m.group(1)}"] = f"fails by {m.group(2)} ({m.group(3)} obs)"

    # required actions — the top of the brief, the things the cycle must resolve
    codes = {}
    for m in re.finditer(r"^- \*\*\[([A-Z0-9_]+)\](?: \(carried[^)]*\))?\*\* (.+)$", brief, re.M):
        codes[m.group(1)] = m.group(2).strip()
    fp["required_actions"] = codes
    fp["required_actions.codes"] = sorted(codes)
    fp["no_blocking_findings"] = "✅ No blocking findings" in brief

    # roll-off + pass-list clocks
    fp["rolloff.warned"] = bool(re.search(r"52-wk-high roll-off within 7 days", brief))
    one(r"^## PASS-list re-adjudication due — (.+)$", "pass_list.due", flags=re.M)

    return fp


DECISION_PREFIXES = ("status", "cash.", "positions.", "position.", "concentration.",
                     "sizing.", "clock.", "adds.", "precommit.", "required_actions",
                     "no_blocking_findings", "rolloff.", "pass_list.")


def compare(old_fp: dict, new_fp: dict) -> list[dict]:
    out = []
    for key in sorted(set(old_fp) | set(new_fp)):
        if key == "required_actions":
            continue  # compared through required_actions.codes + per-code details
        a, b = old_fp.get(key), new_fp.get(key)
        if a != b:
            out.append({"field": key, "old": a, "new": b,
                        "decision": key.startswith(DECISION_PREFIXES)})
    oa = old_fp.get("required_actions") or {}
    nb = new_fp.get("required_actions") or {}
    for code in sorted(set(oa) | set(nb)):
        if oa.get(code) != nb.get(code):
            out.append({"field": f"required_action.{code}", "old": oa.get(code),
                        "new": nb.get(code), "decision": True})
    return out


def normalise(brief: str) -> str:
    """Strip what legitimately differs between two runs a second apart."""
    return _TS_TOKEN.sub("<generated-at normalised>", brief)


# ------------------------------------------------------------------ top level

def behaviour_diff(clone_root: str, old_core: str, new_core: str,
                   keep_sandbox: bool = False) -> dict:
    """Run both engines against the clone's real state. Never touches the clone."""
    clone_root = os.path.abspath(clone_root)
    tmp = tempfile.mkdtemp(prefix="sidecar-behaviour-diff-")
    try:
        old_dir = _sandbox(clone_root, os.path.join(tmp, "old"))
        new_dir = _sandbox(clone_root, os.path.join(tmp, "new"))
        old_brief, old_rc, old_err = run_engine(old_core, old_dir)
        new_brief, new_rc, new_err = run_engine(new_core, new_dir)

        old_fp, new_fp = fingerprint(old_brief), fingerprint(new_brief)
        changes = compare(old_fp, new_fp)

        text_diff = list(difflib.unified_diff(
            normalise(old_brief).splitlines(), normalise(new_brief).splitlines(),
            fromfile="brief (current engine)", tofile="brief (candidate engine)",
            lineterm="", n=2))

        decision_changes = [c for c in changes if c["decision"]]

        # ⚠ How much of the engine did this diff actually exercise? `raw/` is gitignored,
        # so a fresh clone has none of it — and with no positions, quotes or ATR the
        # brief degrades and most of the decision surface (bands, bloc caps, risk caps,
        # sizing, add channel) never executes. A diff run in that state can print "no
        # decision changes" while having tested almost nothing. Say so, loudly.
        missing = sorted({m.group(1) for m in re.finditer(
            r"\[RAW_MISSING\]\*\* \S*?([a-z_]+)\.json", old_brief + new_brief)})
        no_atr = "risk-denominated caps NOT evaluated" in old_brief
        # An engine that cannot produce a brief on this state is the loudest possible
        # signal, so it is promoted regardless of what the fingerprints say.
        engine_broke = (new_rc != 0 and old_rc == 0) or new_fp.get("status") not in ("OK", old_fp.get("status"))
        return {
            "old": {"core": old_core, "rc": old_rc, "stderr": old_err[-2000:],
                    "brief": old_brief, "fingerprint": old_fp},
            "new": {"core": new_core, "rc": new_rc, "stderr": new_err[-2000:],
                    "brief": new_brief, "fingerprint": new_fp},
            "changes": changes,
            "decision_changes": decision_changes,
            "cosmetic_changes": [c for c in changes if not c["decision"]],
            "engine_broke": bool(engine_broke),
            "text_diff": text_diff,
            "coverage": {"raw_missing": missing, "atr_missing": no_atr,
                         "underpowered": bool(missing or no_atr)},
            "sandbox": tmp if keep_sandbox else None,
        }
    finally:
        if not keep_sandbox:
            shutil.rmtree(tmp, ignore_errors=True)


def render(result: dict, show_text_diff: bool = True) -> str:
    L = []
    a, b = result["old"], result["new"]
    L.append("=" * 78)
    L.append("BEHAVIOUR DIFF — both engines run against your REAL current state")
    L.append("=" * 78)
    L.append(f"  current engine : {a['core']}  (exit {a['rc']}, status {a['fingerprint'].get('status')})")
    L.append(f"  candidate      : {b['core']}  (exit {b['rc']}, status {b['fingerprint'].get('status')})")
    L.append("")

    if result["engine_broke"]:
        L.append("🚨 THE CANDIDATE ENGINE DID NOT PRODUCE A CLEAN BRIEF ON YOUR STATE.")
        L.append("   That is a decision change of the worst kind: the cycle would HOLD.")
        if b["stderr"].strip():
            L.append("   stderr (tail):")
            for line in b["stderr"].strip().splitlines()[-8:]:
                L.append(f"     {line}")
        L.append("")

    cov = result.get("coverage") or {}
    if cov.get("underpowered"):
        L.append("⚠ THIS DIFF IS UNDER-POWERED — it did not exercise the whole engine.")
        if cov.get("raw_missing"):
            L.append("   missing broker dumps: " + ", ".join(
                f"raw/{n}.json" for n in cov["raw_missing"]))
            L.append("   Without them there are no positions, weights or quotes, so the")
            L.append("   per-name bands, bloc caps, sizing and add channel never ran.")
        if cov.get("atr_missing"):
            L.append("   no ATR coverage: the risk-denominated caps were not evaluated on")
            L.append("   either side, so a change to them would be invisible here.")
        L.append("   ⛔ Re-run this diff straight after a normal cycle's FETCH step, when")
        L.append("      raw/ is populated. 'No decision changes' means much less than it")
        L.append("      looks like right now.")
        L.append("")

    dc = result["decision_changes"]
    if dc:
        L.append(f"⚠ {len(dc)} DECISION-AFFECTING CHANGE(S) — this upgrade would change what the")
        L.append("  loop does with money TODAY, on the state you have right now:")
        L.append("")
        for c in dc:
            L.append(f"  • {c['field']}")
            L.append(f"      now      : {c['old']!r}")
            L.append(f"      after    : {c['new']!r}")
        L.append("")
    else:
        L.append("✅ NO decision-affecting differences on today's state.")
        L.append("   Gate results, REQUIRED ACTIONS, caps, sizing bands, the deployment clock,")
        L.append("   pre-commitment gates and add-route cooldowns are all identical.")
        L.append("   ⚠ This is evidence about TODAY's state, not a proof about every state.")
        L.append("")

    cc = result["cosmetic_changes"]
    if cc:
        L.append(f"  ({len(cc)} non-decision difference(s): "
                 + ", ".join(sorted({c['field'] for c in cc})[:8]) + ")")
        L.append("")

    if show_text_diff and result["text_diff"]:
        L.append("-" * 78)
        L.append("FULL BRIEF DIFF (timestamps normalised)")
        L.append("-" * 78)
        L += result["text_diff"]
        L.append("")
    elif show_text_diff:
        L.append("(the two briefs are textually identical once the timestamp is normalised)")
        L.append("")
    return "\n".join(L)


# ------------------------------------------------------------------ cli

def main(argv=None) -> int:
    """Stand-alone entry point.

    Upstream this was a subcommand of a `loop` CLI that is not part of sidecar, so the
    entry point lives here instead. `--old` and `--new` are two checkouts of THIS repo
    (e.g. two `git worktree` directories); the diff copies each one's `bot/` into its own
    sandbox and runs both against a throwaway copy of your real state.
    """
    import argparse
    ap = argparse.ArgumentParser(
        description="show whether a candidate engine would decide differently on YOUR state")
    ap.add_argument("--old", required=True, help="checkout containing the CURRENT bot/")
    ap.add_argument("--new", required=True, help="checkout containing the CANDIDATE bot/")
    ap.add_argument("--instance", default=".", help="your clone (default: cwd)")
    ap.add_argument("--text-diff", action="store_true", help="also print the full brief diff")
    ap.add_argument("--keep-sandbox", action="store_true")
    args = ap.parse_args(argv)

    try:
        result = behaviour_diff(args.instance, os.path.abspath(args.old),
                                os.path.abspath(args.new), keep_sandbox=args.keep_sandbox)
    except DiffError as e:
        print(f"⛔ {e}", file=sys.stderr)
        return 2
    print(render(result, show_text_diff=args.text_diff))
    # A decision change is not an error — it is the answer. Exit 1 so a script can gate
    # on it, and so an upgrade path can refuse to proceed unattended.
    return 1 if (result["decision_changes"] or result["engine_broke"]) else 0


if __name__ == "__main__":
    sys.exit(main())
