"""Offline, synthetic-only tests for diagnostic evidence acceptance."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("diagnostic_evidence", ROOT / "scripts/check_diagnostic_evidence.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

SYNTHETIC_PATHS = [
    "SKILL.md", "docs/evidence-and-acceptance.md",
    "modules/M04-wifi.md", "modules/M05-switch.md", "modules/M10-api-n8n.md",
    "runbooks/RB03-link-poe-inventory.md", "runbooks/RB04-wifi6-ssid-staging.md",
]


def make_report(root):
    required = sorted(checker.WIFI_LAN_METRICS)
    return {
        "schema_version": 1,
        "skill": {"repository": checker.REPO_NAME, "version": "v0.7.0-public-draft", "loaded_files": [
            {"path": p, "blob_sha": checker.git_blob_sha((root / p).read_bytes())} for p in SYNTHETIC_PATHS
        ]},
        "modules": ["modules/M04-wifi.md", "modules/M05-switch.md", "modules/M10-api-n8n.md"],
        "runbooks": ["runbooks/RB03-link-poe-inventory.md", "runbooks/RB04-wifi6-ssid-staging.md"],
        "scope": "wifi-lan-performance", "device_access": "AUTHORIZED_READ_ONLY",
        "test_tier": "MOCK_TESTED", "verification_status": "INCOMPLETE",
        "observations": [
            {"metric": metric, "state": "NOT_OBSERVED", "source": "synthetic-only"} for metric in required
        ],
        "missing_metrics": required, "configuration_change_proposals": [],
    }


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for p in SYNTHETIC_PATHS:
            file = self.root / p
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("synthetic fixture for " + p + "\n", encoding="utf-8")
        self.data = make_report(self.root)

    def validate(self):
        return checker.validate(self.data, self.root)

    def make_ready(self):
        self.data["verification_status"] = "EVIDENCE_READY"
        examples = {
            "ap_uplink_port_mapping": {"switch_port_number": 1, "method": "LLDP_VERIFIED"},
            "ap_uplink_negotiated_mbps": 2500,
            "client_band": 6,
            "client_rssi_dbm": -50,
            "ap_radio_retry_pct": [{"band_ghz": 6, "retry_pct": 1.2}],
            "lan_throughput_mbps": {"wifi_to_wired_mbps": 700, "wired_to_wifi_mbps": 710},
        }
        for item in self.data["observations"]:
            item.update(state="OBSERVED", source="synthetic fixture", value=examples[item["metric"]])
        self.data["missing_metrics"] = []

    def test_incomplete_report_passes_only_as_incomplete(self):
        self.assertEqual(self.validate(), [])

    def test_complete_report_can_be_marked_evidence_ready(self):
        self.make_ready()
        self.assertEqual(self.validate(), [])

    def test_fails_closed_when_missing_metric_is_claimed_ready(self):
        self.data["verification_status"] = "EVIDENCE_READY"
        self.assertTrue(any("forbidden" in e for e in self.validate()))

    def test_rejects_fake_string_throughput(self):
        self.make_ready()
        record = next(x for x in self.data["observations"] if x["metric"] == "lan_throughput_mbps")
        record["value"] = "1000 Mbps from Windows PHY link"
        self.assertTrue(any("invalid WiFi LAN measurement" in x for x in self.validate()))

    def test_rejects_unphysical_rssi(self):
        self.make_ready()
        record = next(x for x in self.data["observations"] if x["metric"] == "client_rssi_dbm")
        record["value"] = 75
        self.assertTrue(any("invalid WiFi LAN measurement" in x for x in self.validate()))

    def test_rejects_forged_git_blob_sha(self):
        self.data["skill"]["loaded_files"][0]["blob_sha"] = "0" * 40
        self.assertTrue(any("SHA mismatch" in e for e in self.validate()))

    def test_rejects_module_not_loaded(self):
        self.data["modules"].append("modules/M03-firewall-vpn.md")
        self.assertTrue(any("modules" in e for e in self.validate()))

    def test_forbids_unjustified_change(self):
        self.data["configuration_change_proposals"] = [{"basis":"guess"}]
        self.assertTrue(any("forbidden" in e for e in self.validate()))

    def test_forbids_secrets_or_private_addresses_as_named_fields(self):
        for field in ("api_key", "mac_address", "ssid", "ip_address", "token"):
            with self.subTest(field=field):
                self.data[field] = "sensitive"
                self.assertTrue(any("sensitive" in e for e in self.validate()))
                del self.data[field]

    def test_rejects_incorrect_missing_metrics(self):
        self.data["missing_metrics"] = []
        self.assertTrue(any("missing_metrics" in e for e in self.validate()))

    def test_rejects_executed_change(self):
        self.make_ready()
        self.data["configuration_change_proposals"] = [{
            "basis": "synthetic", "baseline": "synthetic", "validation_plan": "synthetic",
            "rollback_plan": "synthetic", "execution_status": "EXECUTED"
        }]
        self.assertTrue(any("cannot be marked executed" in e for e in self.validate()))

    def test_rejects_missing_provenance(self):
        self.data["skill"]["loaded_files"] = []
        self.assertTrue(any("must both be loaded" in e for e in self.validate()))


if __name__ == "__main__":
    unittest.main()
