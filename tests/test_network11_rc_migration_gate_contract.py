"""Offline guards for a not-approved Network 11 RC migration review note."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "network11-rc-migration-gate.md"

class Network11RCMigrationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.note = GUIDE.read_text(encoding="utf8")

    def test_source_is_explicitly_rc_and_unreviewed(self):
        for token in (
            "SOURCE_TRIAGE_UNREVIEWED", "NO_PRODUCTION_APPROVAL", "Release Candidate",
            "CANDIDATE_UNREVIEWED", "UNKNOWN_NOT_VALIDATED_FROM_RSS",
            "https://community.ui.com/releases/UniFi-Network-Application-11-0-83/d6940379-cd5a-4e61-8596-7e22d647a4ea",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.note)

    def test_irreversible_and_compatibility_safety_gates(self):
        for token in (
            "UniFi OS 6.0 or newer", "UniFi OS 6.0.10 or newer",
            "PostgreSQL", "existing statistics history is cleared",
            "USG support is removed", "Network 10.6",
            "Network Application Server support is removed", "Zone-Based Firewall",
            "vendor-supported recovery", "stats_retention_disposition", "zbf_policy_parity",
            "**BLOCK**", "**NOT APPROVED**",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.note)

    def test_distinguishes_docs_and_read_only_from_approval(self):
        for path in ("modules/M01-platform.md", "modules/M03-firewall-vpn.md",
                     "modules/M09-backup-security.md", "modules/M10-api-n8n.md"):
            with self.subTest(module=path):
                self.assertIn(path, self.note)
        for token in ("28/28 SHA recheck", "not", "real human", "sync/reviewed.json",
                      "sync/pending.json", "production"):
            self.assertIn(token, self.note)

if __name__ == "__main__":
    unittest.main()
