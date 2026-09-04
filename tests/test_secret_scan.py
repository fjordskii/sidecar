"""The CI gate that keeps this template publishable.

sidecar is a PUBLIC repo that five people clone and point at real brokerage accounts.
`tools/secret_scan.py` is the machine that stops one of their account numbers — or one of
their positions — from arriving back here in a pull request. These tests are what make the
gate trustworthy: a scanner nobody has proved catches a leak is a comment, not a control.

⚠ The account number below is INVENTED. The upstream copy of this file (in the private
robinhood-loop repo) tests against the real pre-1.0 account number, assembled from string
fragments so the digits never sit contiguously in the source. That trick is safe in a
private repo and is NOT safe here: fragments in a public file are still the number. So this
copy uses a synthetic stand-in of the same shape, which is all the scanner reasons about.
Never replace it with a real one.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import secret_scan  # noqa: E402

# Invented. Nine digits, no repeated-digit filler, not in ALLOWED_NUMBERS — i.e. exactly
# the shape the scanner must refuse, and tied to no account anywhere.
# The marker is what keeps this file from tripping its own scanner — the one
# documented use for it: a line where the pattern IS the subject matter.
FAKE_ACCOUNT = "738451902"  # secret-scan: allow


class TestSecretScan(unittest.TestCase):

    def test_catches_an_account_number(self):
        text = f'ACCOUNT: trade ONLY the account, account_number "{FAKE_ACCOUNT}".'
        found = secret_scan.scan_text(text, "LOOP_PROMPT.md")
        self.assertTrue(found, "the scanner missed a real-shaped account number")
        self.assertEqual(found[0]["rule"], "ACCOUNT_NUMBER")
        self.assertEqual(found[0]["match"], FAKE_ACCOUNT)

    def test_catches_it_in_json_and_in_prose(self):
        for text in (f'{{"account_number": "{FAKE_ACCOUNT}"}}',
                     f"pass account_number={FAKE_ACCOUNT} on every read",
                     f"get_portfolio(account_number='{FAKE_ACCOUNT}')"):
            with self.subTest(text=text):
                self.assertTrue(any(f["rule"] == "ACCOUNT_NUMBER"
                                    for f in secret_scan.scan_text(text, "x.md")))

    def test_does_not_flag_versions_dates_or_budgets(self):
        clean = ("template version 1.7.1 · rotated 2026-08-28 at 09:30 ET · "
                 "journal_rotate_bytes: 250000 · entry ceiling 9000b · cron 30 13,16,19 * * 1-5")
        self.assertEqual(secret_scan.scan_text(clean, "x.md"), [])

    def test_catches_a_cost_basis_field(self):
        """The other half of the mandate: a position's cost basis is as personal as an id."""
        text = '"average_buy_price": "184.22",'                  # secret-scan: allow
        self.assertEqual([f["rule"] for f in secret_scan.scan_text(text, "bot/state.json")],
                         ["STATE_FIELD"])

    def test_catches_journal_and_state_artefacts(self):
        # Each sample carries the allow marker so this file does not trip its own
        # scanner — which is itself the marker mechanism under test.
        samples = [
            '## ' + 'CYCLE 2026-08-28 12:40',            # secret-scan: allow
            '"spy_at_entry": 751.28',                    # secret-scan: allow
            '"entry_date": "2026-07-06"',                # secret-scan: allow
            '/Users/someone/dev/loop',                   # secret-scan: allow
            'routine trig_01QscxHFQsdMb7gzQYAk',         # secret-scan: allow
        ]
        rules = {f["rule"] for f in secret_scan.scan_text("\n".join(samples), "x.md")}
        self.assertIn("JOURNAL_CYCLE_BLOCK", rules)
        self.assertIn("STATE_FIELD", rules)
        self.assertIn("PERSONAL_PATH", rules)
        self.assertIn("ROUTINE_ID", rules)

    def test_schema_keys_alone_are_not_a_leak(self):
        """A schema has to name the fields it validates; that is not personal data."""
        self.assertEqual(secret_scan.scan_text(
            '"spy_at_entry": {"type": ["number", "null"]},', "bot/schema/state.schema.json"), [])
        self.assertEqual(secret_scan.scan_text('"benchmark_history": [],', "bot/precheck.py"), [])

    def test_the_allow_marker_is_the_only_line_level_waiver(self):
        leak = f'account_number "{FAKE_ACCOUNT}"'
        self.assertTrue(secret_scan.scan_text(leak, "x.md"))
        self.assertEqual(
            secret_scan.scan_text(leak + "  # " + secret_scan.ALLOW_MARKER, "x.md"), [])

    def test_the_fixture_exemption_never_waives_the_account_rule(self):
        """A fixtures directory may hold state-shaped data — never an account number."""
        text = f'{{"account_number": "{FAKE_ACCOUNT}", "spy_at_entry": 751.28}}'  # secret-scan: allow
        found = secret_scan.scan_text(text, "tests/fixtures/x.json", fixtures_dir=True)
        self.assertEqual([f["rule"] for f in found], ["ACCOUNT_NUMBER"])

    def test_the_template_itself_is_clean(self):
        """The build gate, run against the real tree. If this fails, do not publish."""
        findings = secret_scan.scan(ROOT)
        self.assertEqual(
            findings, [],
            "the sidecar template contains personal data:\n" +
            "\n".join(f"  {f['file']}:{f['line']} [{f['rule']}] {f['match']}" for f in findings))


if __name__ == "__main__":
    unittest.main()
