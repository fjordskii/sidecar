"""The manifest, and the two files that must agree with it.

Invariant 3 in BACKPORT.md: `sidecar-manifest.json`, `.github/workflows/sidecar-update.yml`
and `.claude/commands/sidecar-upgrade.md` all encode the same ownership rules in three
different languages — JSON, bash, and English read by an agent. They did not agree before
v1.7.1, and the disagreement was a data-loss bug.

The sharpest test here is coverage: every tracked file must be in a class or on an explicit
exclusion list. That is what catches the mistake nobody makes deliberately — a new file
added upstream that quietly ends up owned by nobody, or by everybody.
"""

import json
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIL = os.path.join(ROOT, ".github", "workflows", "sidecar-update.yml")
UPGRADE = os.path.join(ROOT, ".claude", "commands", "sidecar-upgrade.md")

# Files that are deliberately in NO class: the template repo's own CI. See the manifest's
# `notes.not_delivered` — secret_scan.py would fail a build on the real account number that
# legitimately lives in a private clone's mandate.
NOT_DELIVERED = ("tools/", "tests/", ".github/workflows/ci.yml", ".gitignore",
                 ".github/workflows/sidecar-update.yml",
                 # A maintainer planning doc; its own header says it is not read by agents.
                 "docs/ROADMAP.md")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def manifest():
    return json.loads(read(os.path.join(ROOT, "sidecar-manifest.json")))


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout
    return [p for p in out.splitlines() if p]


class TestManifestShape(unittest.TestCase):

    def test_every_tracked_file_is_owned_or_explicitly_excluded(self):
        """The one that catches a file nobody thought about."""
        m = manifest()["files"]
        owned = {p for paths in m.values() for p in paths}
        orphans = [f for f in tracked_files()
                   if f not in owned and not f.startswith(NOT_DELIVERED)]
        self.assertEqual(orphans, [],
                         "these files are in no manifest class and on no exclusion list — "
                         "decide who owns them:\n  " + "\n  ".join(orphans))

    def test_every_listed_path_exists(self):
        """A class naming a file that isn't here makes the rail 404 on every update."""
        m = manifest()["files"]
        # `user` names files a clone creates for itself; they need not exist upstream.
        for cls in ("system", "system_setup", "system_if_uninitialized", "system_if_absent"):
            for path in m[cls]:
                self.assertTrue(os.path.exists(os.path.join(ROOT, path)),
                                f"{cls} lists {path}, which does not exist in the template")

    def test_every_class_has_a_note(self):
        notes = manifest()["notes"]
        for cls in manifest()["files"]:
            self.assertIn(cls, notes, f"class {cls} ships with no explanation")

    def test_readme_is_the_users(self):
        """It was in `system` and replaced unconditionally — a live bug until this release."""
        m = manifest()["files"]
        self.assertIn("README.md", m["user"])
        self.assertNotIn("README.md", m["system"])
        self.assertNotIn("README.md", m["system_setup"])


class TestAccumulatingFilesAreNeverTokenGated(unittest.TestCase):
    """Invariant 1. This was a real data-loss bug, fixed in v1.7.1."""

    ACCUMULATES = ("JOURNAL.md", "DECISIONS.md", "bot/state.json", "bot/failures.jsonl")

    def test_they_are_existence_gated_not_token_gated(self):
        m = manifest()["files"]
        for f in self.ACCUMULATES:
            with self.subTest(file=f):
                self.assertIn(f, m["system_if_absent"], f"{f} must be existence-gated")
                self.assertNotIn(f, m["system_if_uninitialized"],
                                 f"{f} accumulates — token-gating it is a data-loss bug")
                self.assertNotIn(f, m["system"], f"{f} must never be replaced wholesale")

    def test_they_are_also_declared_the_users(self):
        m = manifest()["files"]
        for f in self.ACCUMULATES:
            self.assertIn(f, m["user"], f"{f} is the user's once it exists")


class TestTheThreeCopiesAgree(unittest.TestCase):
    """Invariant 3, checked rather than trusted."""

    def test_the_rail_and_the_command_handle_every_class(self):
        rail, upgrade = read(RAIL), read(UPGRADE)
        for cls in manifest()["files"]:
            if cls == "user":
                continue          # the rule for `user` is to do nothing; nothing to read
            with self.subTest(cls=cls):
                self.assertIn(cls, rail, f"{cls} is in the manifest but not in the rail")
                self.assertIn(cls, upgrade, f"{cls} is in the manifest but not in the command")

    def test_the_token_grep_is_identical_in_both(self):
        """A drifting grep means the two paths disagree about who owns a mandate."""
        pattern = re.compile(
            r"\\?\{\\?\{\(ACCOUNT_ID\|BROKER\|MCP_SERVER\|STRATEGY\|REPO_PATH\|CLI_PATH"
            r"\|NODE_PATH\|DATE\|SLOTS\|AUTONOMY\|AUTONOMY_LINE\)\\?\}\\?\}")
        self.assertTrue(pattern.search(read(RAIL)), "the rail's setup-token grep changed shape")
        self.assertTrue(pattern.search(read(UPGRADE)), "the command's setup-token grep changed shape")

    def test_the_rail_defines_the_grep_once(self):
        """It was inlined twice; two copies of a security-relevant test drift."""
        rail = read(RAIL)
        self.assertIn("has_setup_tokens()", rail)
        self.assertEqual(rail.count("ACCOUNT_ID|BROKER|MCP_SERVER"), 1,
                         "the token list appears more than once in the rail — define it once")


class TestSetupClassIsAnsweredByTheMandate(unittest.TestCase):
    """system_setup asks LOOP_PROMPT.md whether onboarding is done, not its own files.

    Three of the setup files carry no tokens at all, and two carry them only as printed
    examples that are never filled in — so a file testing itself would answer
    "still onboarding" forever and the class would never skip anything.
    """

    TOKENS = re.compile(r"\{\{(ACCOUNT_ID|BROKER|MCP_SERVER|STRATEGY|REPO_PATH|CLI_PATH"
                        r"|NODE_PATH|DATE|SLOTS|AUTONOMY|AUTONOMY_LINE)\}\}")

    def test_the_setup_files_cannot_answer_for_themselves(self):
        unanswerable = [f for f in manifest()["files"]["system_setup"]
                        if not self.TOKENS.search(read(os.path.join(ROOT, f)))]
        self.assertTrue(unanswerable,
                        "if every setup file carried real tokens, self-testing would work "
                        "and this class's design note would be wrong")

    def test_the_mandate_can(self):
        self.assertTrue(self.TOKENS.search(read(os.path.join(ROOT, "LOOP_PROMPT.md"))),
                        "LOOP_PROMPT.md ships tokenized; it is the onboarding signal")

    def test_the_rail_reads_the_mandate_for_this(self):
        rail = read(RAIL)
        self.assertRegex(rail, r"has_setup_tokens LOOP_PROMPT\.md",
                         "the rail must ask LOOP_PROMPT.md, not the setup files")


class TestEngineDelivery(unittest.TestCase):

    def test_the_engine_rides_the_rail(self):
        system = manifest()["files"]["system"]
        for f in ("bot/precheck.py", "bot/postcheck.py", "bot/README.md",
                  "bot/schema_check.py", "bot/schema/state.schema.json",
                  "bot/cli/behaviour_diff.py"):
            self.assertIn(f, system, f"{f} would never reach a user")

    def test_maintainer_ci_does_not(self):
        owned = {p for paths in manifest()["files"].values() for p in paths}
        for f in ("tools/secret_scan.py", "tests/test_engine.py", ".github/workflows/ci.yml"):
            self.assertNotIn(f, owned,
                             f"{f} is template CI and must not be delivered to clones")


if __name__ == "__main__":
    unittest.main()
