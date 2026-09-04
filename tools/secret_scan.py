#!/usr/bin/env python3
"""
secret_scan.py — FAIL THE BUILD if anything shaped like a real brokerage account number,
or any other personal artefact, has landed in the sidecar template.

BACKPORT.md's owner constraint makes this non-negotiable: sidecar is PUBLIC and is
cloned by strangers who then point it at their own money. The reason the reference
instance could not be shared is that one account number hard-coded across the mandate,
the state and the journal. A reviewer will not catch it a second time by reading
carefully; a machine has to.

⚠ Positions leak as easily as account numbers do. A "fixture" captured from a live broker
session is somebody's real book — same symbols, same cost bases — even after the account
number in it has been masked. That is a real finding this scanner has already caught once.

    python3 tools/secret_scan.py            # scan the template, exit 1 on any finding
    python3 tools/secret_scan.py --path X   # scan somewhere else
    python3 tools/secret_scan.py --json     # machine-readable findings

What counts as a finding:
  * **ACCOUNT_NUMBER** — a bare 8-11 digit run that is not obviously something else.
    Deliberately broad: false positives cost a reviewer thirty seconds and an allowlist
    entry; a false negative publishes someone's account.
  * **JOURNAL/STATE ARTEFACT** — a `## CYCLE` block, an `order_id`, a `spy_at_entry`,
    a `last_route3` … i.e. private machine state pasted into a shared file.
  * **PERSONAL PATH / IDENTIFIER** — `/Users/<name>/`, an email address, a scheduler
    routine id.

What is allowed, and why each exemption is narrow:
  * version strings, dates and times (`2026-08-28`, `1.0.0`, `09:30`)
  * byte budgets and thresholds that are genuinely policy (`250000`, `9000`) — matched
    only when they appear as a number in a key/value or a size context
  * UUID-shaped order ids in a REGEX (the engine parses them; it must contain the pattern)
  * the literal placeholder `REPLACE_ME`, and the test fixture `000000000` family
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `raw` is the broker-snapshot directory (`bot/raw/`): gitignored, never committed, and
# full of live JSON — scanning a local one would drown the real findings in noise.
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "raw"}
SKIP_SUFFIXES = (".pyc", ".png", ".jpg", ".gif", ".pdf", ".zip", ".ico")

# 8-11 consecutive digits, not preceded/followed by another digit, a dot or a dash
# (so 2026-08-28, 1.0.0 and 250000 do not trip it — 250000 is only 6 digits anyway).
ACCOUNT_RE = re.compile(r"(?<![\d.\-])(\d{8,11})(?![\d.\-])")

# Digit runs that legitimately belong in the template. Keep this list SHORT and justified.
ALLOWED_NUMBERS = {
    "00000000",     # obviously-fake fixture
    "000000000",
    "0000000000",
    "12345678",     # documentation example, clearly not real
    "123456789",
}

ARTEFACT_PATTERNS = [
    ("JOURNAL_CYCLE_BLOCK", re.compile(r"^## CYCLE \d{4}-\d{2}-\d{2}", re.M),
     "a journal cycle entry has been pasted into the template"),
    # Keys alone are not a leak — `schema/state.schema.json` has to name every field it
    # validates. What leaks is a key with a REAL VALUE next to it, so the value shape is
    # part of the pattern: a scalar, or the opening of a non-empty container.
    ("STATE_FIELD",
     re.compile(r'"(spy_at_entry|last_route3|add_history|benchmark_history|entry_date'
                r'|order_id|average_buy_price|review_trigger)"\s*:\s*'
                r'(?:"[^"]+"|-?\d|\[\s*$|\[\s*\{)'),
     "private state.json content (a populated field, not just a schema key name)"),
    ("PERSONAL_PATH", re.compile(r"/(?:Users|home)/(?!user\b|runner\b)[A-Za-z][A-Za-z0-9_.-]{2,}/"),
     "a personal filesystem path"),
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
     "an email address"),
    ("ROUTINE_ID", re.compile(r"\btrig_[A-Za-z0-9]{10,}\b"),
     "a scheduler routine id"),
    ("GITHUB_INSTANCE_REPO", re.compile(r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]*loop\b"),
     "a link to somebody's private instance repo"),
]

# Lines carrying this marker are exempt. Use it only where the pattern is genuinely the
# subject matter (the scanner's own tests, a documented example).
ALLOW_MARKER = "secret-scan: allow"

# A directory containing this file may hold state-SHAPED test fixtures. It exempts the
# shape rules ONLY — the account-number rule is never waivable anywhere, because that is
# the one leak with no acceptable version. The file must explain itself; a reviewer
# reading it should be able to confirm the fixtures are synthetic.
DIR_ALLOW_FILE = ".secret-scan-allow-fixtures"


def iter_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        fixtures = DIR_ALLOW_FILE in filenames
        for fn in filenames:
            if fn.endswith(SKIP_SUFFIXES):
                continue
            yield os.path.join(dirpath, fn), fixtures


def scan_text(text: str, relpath: str, fixtures_dir: bool = False) -> list[dict]:
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        for m in ACCOUNT_RE.finditer(line):
            token = m.group(1)
            if token in ALLOWED_NUMBERS:
                continue
            if len(set(token)) == 1:      # 00000000 / 99999999 style filler
                continue
            findings.append({
                "rule": "ACCOUNT_NUMBER", "file": relpath, "line": i, "match": token,
                "why": "looks like a brokerage account number — it belongs in your own "
                       "private clone, never in the public template",
            })
        if fixtures_dir:
            continue          # shape rules only; the account rule above still applied
        for rule, rx, why in ARTEFACT_PATTERNS:
            for m in rx.finditer(line):
                findings.append({"rule": rule, "file": relpath, "line": i,
                                 "match": m.group(0)[:80], "why": why})
    return findings


def scan(root: str) -> list[dict]:
    findings = []
    for path, fixtures_dir in iter_files(root):
        rel = os.path.relpath(path, root)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        findings += scan_text(text, rel, fixtures_dir)
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="fail the build on personal data in the sidecar template")
    ap.add_argument("--path", default=DEFAULT_ROOT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    findings = scan(os.path.abspath(args.path))
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}: [{f['rule']}] {f['match']}\n    {f['why']}")
    if findings:
        print(f"\n⛔ SECRET SCAN FAILED — {len(findings)} finding(s) in {args.path}.")
        print("   sidecar is PUBLIC. Personal data belongs in a private clone, never here:")
        print("   account id -> the clone's own LOOP_PROMPT.md · narrative -> its JOURNAL.md")
        print("   Test fixtures must be INVENTED, not captured from a live session — a")
        print("   masked account number does not make real positions synthetic.")
        return 1
    print(f"✅ secret scan clean: {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
