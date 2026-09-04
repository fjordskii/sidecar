"""The engine's contract with a stranger's clone.

sidecar ships `bot/` INERT: nothing in the template calls precheck or postcheck, and
`AGENTS.md` names neither, so the engine activates only when a user adds it to their own
LOOP_PROMPT.md. That makes these tests the only thing standing between a bad harvest and
five people's real money, because no cycle will exercise the code before they do.

Two rules govern how this file works:

  * **Never run the engine against this repo.** `precheck.py` appends to
    `bot/failures.jsonl` and `postcheck.py` rewrites `bot/state.json` and can rotate a
    journal. Every test below builds a throwaway clone in a temp dir and deletes it.
  * **Fixtures are invented, never captured.** See `tests/fixtures/.secret-scan-allow-fixtures`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT = os.path.join(ROOT, "bot")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
if BOT not in sys.path:
    sys.path.insert(0, BOT)

import schema_check  # noqa: E402

JOURNAL_ENTRY = """# Journal

## """ + """CYCLE 2026-09-04 09:30 (local, open)
state: HOLD · order_path: NOT_TESTED · push: VERIFIED
**Portfolio:** equity $800.00, buying_power $1,000.00, cash = 55.6% of account
{bloc_line}
**Orders:** none — hold
**Notes/next:** nothing.
"""


def build_clone(dest: str, state: dict | None = None, journal: str | None = None) -> str:
    """A throwaway clone: the engine, a state file, synthetic broker feeds, a journal."""
    os.makedirs(os.path.join(dest, "bot"), exist_ok=True)
    for fn in ("precheck.py", "postcheck.py", "schema_check.py"):
        shutil.copy2(os.path.join(BOT, fn), os.path.join(dest, "bot", fn))
    shutil.copytree(os.path.join(BOT, "schema"), os.path.join(dest, "bot", "schema"),
                    dirs_exist_ok=True)
    shutil.copytree(os.path.join(FIXTURES, "raw"), os.path.join(dest, "bot", "raw"),
                    dirs_exist_ok=True)
    with open(os.path.join(dest, "bot", "state.json"), "w") as f:
        json.dump(state if state is not None else shipped_state(), f, indent=2)
    open(os.path.join(dest, "bot", "failures.jsonl"), "w").close()
    with open(os.path.join(dest, "JOURNAL.md"), "w") as f:
        f.write(journal if journal is not None else
                JOURNAL_ENTRY.format(bloc_line="**BLOC 0.0% of equity**"))
    return dest


def read(*parts) -> str:
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def read_json(*parts):
    return json.loads(read(*parts))


def shipped_state() -> dict:
    return read_json(BOT, "state.json")


def run(script: str, clone: str, *args) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, os.path.join(clone, "bot", script), *args],
                          capture_output=True, text=True, cwd=clone, env=env, timeout=120)


class TempCloneCase(unittest.TestCase):
    def clone(self, **kw) -> str:
        d = tempfile.mkdtemp(prefix="sidecar-engine-test-")
        self.addCleanup(shutil.rmtree, d, True)
        return build_clone(d, **kw)


class TestShippedTemplate(unittest.TestCase):
    """What actually leaves this repo — the riskiest file in the backport."""

    def test_state_ships_empty(self):
        st = shipped_state()
        self.assertEqual(st["positions"], {})
        self.assertEqual(st["bench"], {})
        self.assertEqual(st["holdings_highs"], {})
        self.assertEqual(st["precommitments"], {})
        self.assertEqual(st["benchmark_history"], [])
        self.assertIsNone(st["last_cycle"])

    def test_state_carries_no_identity(self):
        """Owner decision 1: the NUMBERS ship, the identity does not."""
        st = shipped_state()
        self.assertEqual(st["account_number"], "", "the account id must ship empty")
        bloc = st["policy"]["ai_bloc"]
        self.assertEqual(bloc["members"], [], "shipped bloc names somebody's holdings")
        self.assertEqual(bloc["label"], "", "shipped bloc carries somebody's theme")
        self.assertEqual(st["policy"]["bands"]["levered_names"], [])

    def test_state_carries_the_policy_defaults(self):
        """The other half of decision 1: the engine must be usable on arrival."""
        pol = shipped_state()["policy"]
        self.assertEqual(pol["ai_bloc"]["soft_cap_pct_equity"], 68.0)
        self.assertEqual(pol["ai_bloc"]["hard_cap_pct_equity"], 75.0)
        self.assertEqual(pol["bands"]["hard_pct"], 35.0)
        self.assertEqual(pol["positions_soft_cap"], 12)
        self.assertEqual(pol["sizing_tiers_pct_account"]["TIER1"], [10.0, 12.0])

    def test_no_dated_prose_survived_the_harvest(self):
        """Dated directives are one instance's history, not a stranger's config."""
        blob = json.dumps(shipped_state())
        for gone in ("clock_retired", "route3_suspended", "gate4_differentiation",
                     "owner directive"):
            self.assertNotIn(gone, blob, f"{gone} is this repo's history, not a default")

    def test_state_validates_against_the_schema(self):
        schema = read_json(BOT, "schema", "state.schema.json")
        self.assertEqual(schema_check.validate(shipped_state(), schema), [])

    def test_schema_is_not_vacuous(self):
        """A validator that accepts everything is worse than none — it reassures."""
        schema = read_json(BOT, "schema", "state.schema.json")
        self.assertTrue(schema_check.validate({}, schema))
        self.assertTrue(schema_check.validate(
            {"schema_version": 1, "policy": {"sizing_basis": "vibes"}}, schema))

    def test_ledger_ships_empty(self):
        self.assertEqual(read(BOT, "failures.jsonl"), "",
                         "the failure ledger ships with somebody's findings")


class TestEngineRuns(TempCloneCase):
    """The engine, exercised on synthetic feeds. Never against this repo."""

    def test_precheck_produces_a_brief(self):
        c = self.clone()
        p = run("precheck.py", c)
        self.assertEqual(p.returncode, 0, p.stderr)
        brief = read(c, "bot", "brief.md")
        self.assertIn("PRECHECK BRIEF", brief)
        self.assertIn("## Positions (4)", brief)
        self.assertIn("## Sizing", brief)

    def test_the_shipped_policy_defaults_reach_the_brief(self):
        """Defaults nobody can see are defaults nobody can correct."""
        c = self.clone()
        run("precheck.py", c)
        brief = read(c, "bot", "brief.md")
        self.assertIn("(soft 68.0% / hard 75.0%)", brief)
        self.assertIn("**TIER1** 10–12% of account", brief)
        self.assertIn("positions **4/12**", brief)

    def test_precheck_degrades_loudly_on_unreadable_state(self):
        """A silent empty brief is the single worst failure: it reads as a clean cycle."""
        c = self.clone()
        with open(os.path.join(c, "bot", "state.json"), "w") as f:
            f.write("{ not json")
        p = run("precheck.py", c)
        self.assertEqual(p.returncode, 2)
        brief = read(c, "bot", "brief.md")
        self.assertIn("STATE UNREADABLE", brief)
        self.assertIn("MANUALLY", brief)

    def test_postcheck_runs_without_commit(self):
        c = self.clone()
        p = run("postcheck.py", c, "--cycle", "2026-09-04 09:30")
        self.assertIn("POSTCHECK", p.stdout + p.stderr)
        self.assertEqual(read_json(c, "bot", "state.json")["last_cycle"], "2026-09-04 09:30")


class TestBlocLabelIsConfiguration(TempCloneCase):
    """The bloc's printed name was hard-coded to one instance's theme.

    That is not cosmetic: postcheck's BLOC_LINE_MISSING keyed on the same literal, so a
    template shipping it would have obliged every user to write somebody else's noun into
    their journal every cycle to clear a finding.
    """

    def brief_for(self, label):
        st = shipped_state()
        st["policy"]["ai_bloc"]["label"] = label
        st["policy"]["ai_bloc"]["members"] = ["AAA", "BBB"]
        c = self.clone(state=st)
        run("precheck.py", c)
        return read(c, "bot", "brief.md")

    def test_unset_label_prints_no_theme(self):
        brief = self.brief_for("")
        self.assertIn("**BLOC ", brief)
        self.assertNotIn("AI-INFRA", brief)

    def test_a_configured_label_is_used(self):
        self.assertIn("**AI-INFRA BLOC ", self.brief_for("AI-INFRA"))

    def _bloc_finding(self, bloc_line):
        c = self.clone(journal=JOURNAL_ENTRY.format(bloc_line=bloc_line))
        p = run("postcheck.py", c, "--cycle", "2026-09-04 09:30")
        return "BLOC_LINE_MISSING" in (p.stdout + p.stderr)

    def test_the_bloc_line_check_fires_when_the_line_is_absent(self):
        self.assertTrue(self._bloc_finding("**Thesis:** nothing."))

    def test_the_bloc_line_check_accepts_an_unthemed_line(self):
        self.assertFalse(self._bloc_finding("**BLOC 0.0% of equity**"))

    def test_the_bloc_line_check_still_accepts_a_themed_line(self):
        """Existing instances write a themed line; the loosening must not break them."""
        self.assertFalse(self._bloc_finding("⭐ **AI-INFRA BLOC 60.0% of equity**"))


class TestBehaviourDiff(TempCloneCase):
    """The tool that makes an engine update safe to install."""

    def setUp(self):
        sys.path.insert(0, os.path.join(BOT, "cli"))
        self.addCleanup(sys.path.remove, os.path.join(BOT, "cli"))

    def cores(self):
        """Two candidate checkouts: identical, then one with a changed printed band."""
        base = tempfile.mkdtemp(prefix="sidecar-cores-")
        self.addCleanup(shutil.rmtree, base, True)
        a, b = os.path.join(base, "a"), os.path.join(base, "b")
        for d in (a, b):
            os.makedirs(os.path.join(d, "bot"))
            for fn in ("precheck.py", "postcheck.py", "schema_check.py"):
                shutil.copy2(os.path.join(BOT, fn), os.path.join(d, "bot", fn))
            shutil.copytree(os.path.join(BOT, "schema"), os.path.join(d, "bot", "schema"))
        src = os.path.join(b, "bot", "precheck.py")
        text = read(src)
        anchor = ('        add(f"- **{tname}** {lo:g}–{hi:g}% of account = '
                  '**{money(total*lo/100.0)}–{money(total*hi/100.0)}**")')
        assert text.count(anchor) == 1, "the sizing print moved; this test needs updating"
        with open(src, "w", encoding="utf-8") as f:
            f.write(text.replace(anchor, "        lo, hi = lo*2, hi*2\n" + anchor))
        return a, b

    def test_identical_engines_show_no_decision_change(self):
        import behaviour_diff as bd
        a, _ = self.cores()
        res = bd.behaviour_diff(self.clone(), a, a)
        self.assertEqual(res["decision_changes"], [])
        self.assertFalse(res["engine_broke"])

    def test_a_changed_band_is_reported_as_decision_affecting(self):
        import behaviour_diff as bd
        a, b = self.cores()
        res = bd.behaviour_diff(self.clone(), a, b)
        fields = {c["field"] for c in res["decision_changes"]}
        self.assertIn("sizing.TIER1.pct", fields)
        self.assertIn("sizing.TIER1.dollars", fields)

    def test_it_never_touches_the_clone(self):
        """precheck appends to the ledger. A dry run that leaves a trace is not dry."""
        import behaviour_diff as bd
        c = self.clone()
        ledger = os.path.join(c, "bot", "failures.jsonl")
        state = os.path.join(c, "bot", "state.json")
        before = (read(ledger), read(state))
        a, b = self.cores()
        bd.behaviour_diff(c, a, b)
        self.assertEqual((read(ledger), read(state)), before)


class TestNoThirdPartyImports(unittest.TestCase):
    def test_the_engine_imports_only_the_standard_library(self):
        """A clone must run from a bare checkout, inside a 09:30 cycle nobody watches."""
        import re
        bad = re.compile(r"^\s*(?:import|from)\s+"
                         r"(yaml|jsonschema|requests|pydantic|numpy|pandas)\b", re.M)
        for dirpath, _, filenames in os.walk(BOT):
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                src = read(dirpath, fn)
                for m in bad.finditer(src):
                    line = src[:m.start()].count("\n") + 1
                    # schema_check defers to jsonschema only if it is already installed.
                    self.assertIn("try:", src[max(0, m.start() - 200):m.start()],
                                  f"{fn}:{line} imports {m.group(1)} unguarded")


if __name__ == "__main__":
    unittest.main()
