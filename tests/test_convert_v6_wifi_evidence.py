"""Synthetic tests for the v6 -> Skill evidence conversion. No live UniFi access."""
import json
from pathlib import Path
import tempfile
import unittest

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import convert_v6_wifi_evidence as adapter
from check_diagnostic_evidence import validate


def fixture(mode="local"):
    return {
        "report_schema": "unifi-m04-wifi-evidence-lan-only-v6",
        "collection_mode": mode,
        "sites": [{"access_points": [{"model": "FAKE-U7", "uplink_mapping_evidence": "UNVERIFIED_PORT_ASSOCIATION",
            "active_port_speeds_mbps": [2500, 100], "stats": {"radio_samples": [
                {"band_ghz": 5, "tx_retries_percent": 10.5}, {"band_ghz": 6, "tx_retries_percent": 0.0}
            ]}}]}],
        "windows_station_link": {"status": "COLLECTED", "signal_percent": 60, "channel": 85,
                                 "rx_link_rate_mbps": 324, "tx_link_rate_mbps": 216},
        "lan_tcp_throughput_test": {"status": "NOT_RUN"},
        "private_do_not_copy": {"api_key": "NEVER_COPY_THIS_KEY",
                                "ip": "192.0.2.7", "ssid": "PRIVATE_SYNTHETIC_SSID"},
    }


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT

    def test_realistic_v6_is_incomplete_and_verified(self):
        item = adapter.convert(fixture(), self.root)
        self.assertEqual(item["verification_status"], "INCOMPLETE")
        self.assertEqual(validate(item, self.root), [])
        missing = set(item["missing_metrics"])
        self.assertIn("ap_uplink_negotiated_mbps", missing)
        self.assertIn("client_rssi_dbm", missing)
        self.assertIn("client_band", missing)
        self.assertIn("lan_throughput_mbps", missing)
        self.assertNotIn("ap_radio_retry_pct", missing)

    def test_does_not_guess_from_windows_phy_channel_and_signal(self):
        item = adapter.convert(fixture(), self.root)
        statuses = {o["metric"]: o["state"] for o in item["observations"]}
        for name in ("client_band", "client_rssi_dbm", "ap_uplink_port_mapping", "ap_uplink_negotiated_mbps"):
            self.assertEqual(statuses[name], "NOT_OBSERVED")

    def test_private_values_are_never_copied(self):
        result = json.dumps(adapter.convert(fixture(), self.root))
        self.assertNotIn("NEVER_COPY_THIS_KEY", result)
        self.assertNotIn("192.0.2.7", result)
        self.assertNotIn("PRIVATE_SYNTHETIC_SSID", result)
        self.assertNotIn("FAKE-U7", result)

    def test_mock_cannot_claim_radio_retry_measurement(self):
        item = adapter.convert(fixture("mock"), self.root)
        self.assertEqual(item["device_access"], "NONE")
        self.assertEqual(item["test_tier"], "MOCK_TESTED")
        self.assertIn("ap_radio_retry_pct", item["missing_metrics"])

    def test_not_proof_of_uplink_even_if_one_speed_listed(self):
        src = fixture()
        src["sites"][0]["access_points"][0]["active_port_speeds_mbps"] = [2500]
        item = adapter.convert(src, self.root)
        self.assertIn("ap_uplink_negotiated_mbps", item["missing_metrics"])

    def test_windows_native_observation_marks_band_and_rssi(self):
        src = fixture()
        src["windows_native_wifi"] = {
            "status": "OBSERVED", "source": "WINDOWS_WLAN_API_ASSOCIATED_BSS",
            "band_ghz": 5.0, "rssi_dbm": -73,
            "rx_phy_mbps": 324, "tx_phy_mbps": 216, "not_throughput": True,
        }
        item = adapter.convert(src, self.root)
        self.assertEqual(adapter.convert(src, self.root)["verification_status"], "INCOMPLETE")
        measured = {o["metric"]: o for o in item["observations"]}
        self.assertEqual(measured["client_band"]["value"], 5.0)
        self.assertEqual(measured["client_rssi_dbm"]["value"], -73)
        self.assertNotIn("client_band", item["missing_metrics"])
        self.assertNotIn("client_rssi_dbm", item["missing_metrics"])
        self.assertIn("lan_throughput_mbps", item["missing_metrics"])
        self.assertIn("ap_uplink_negotiated_mbps", item["missing_metrics"])

    def test_mock_does_not_launder_synthetic_windows_evidence(self):
        src = fixture("mock")
        src["windows_native_wifi"] = {
            "status": "OBSERVED", "source": "WINDOWS_WLAN_API_ASSOCIATED_BSS",
            "band_ghz": 6, "rssi_dbm": -51,
        }
        self.assertIn("client_band", adapter.convert(src, self.root)["missing_metrics"])
        self.assertIn("client_rssi_dbm", adapter.convert(src, self.root)["missing_metrics"])

    def test_lan_peer_measurement_is_not_automatically_complete(self):
        src = fixture()
        src["lan_tcp_throughput_test"] = {
            "status": "MEASURED",
            "scope": "THIS_WINDOWS_PC_TO_EXPLICIT_PRIVATE_LAN_SERVER_ONLY",
            "wifi_to_wired_mbps": 742.5, "wired_to_wifi_mbps": 638.4,
        }
        item = adapter.convert(src, self.root)
        self.assertNotIn("lan_throughput_mbps", item["missing_metrics"])
        self.assertIn("client_rssi_dbm", item["missing_metrics"])
        self.assertEqual(item["verification_status"], "INCOMPLETE")

    def test_lan_fake_scope_rejected(self):
        src = fixture()
        src["lan_tcp_throughput_test"] = {"status": "MEASURED", "scope": "WAN",
                                         "wifi_to_wired_mbps": 1000, "wired_to_wifi_mbps": 1000}
        self.assertIn("lan_throughput_mbps", adapter.convert(src, self.root)["missing_metrics"])

    def test_api_not_available_does_not_claim_retries(self):
        src = fixture()
        src["sites"][0]["access_points"][0]["stats"] = None
        self.assertIn("ap_radio_retry_pct", adapter.convert(src, self.root)["missing_metrics"])

    def test_multi_ap_does_not_confuse_radio_client_identity(self):
        src = fixture()
        src["sites"][0]["access_points"] *= 2
        self.assertIn("ap_radio_retry_pct", adapter.convert(src, self.root)["missing_metrics"])

    def test_nan_and_invalid_values_are_not_evidence(self):
        src = fixture()
        src["sites"][0]["access_points"][0]["stats"]["radio_samples"] = [{"band_ghz": 5, "tx_retries_percent": float("nan")}]
        self.assertIn("ap_radio_retry_pct", adapter.convert(src, self.root)["missing_metrics"])

    def test_reject_wrong_schema(self):
        src = fixture()
        src["report_schema"] = "unknown"
        with self.assertRaises(ValueError):
            adapter.convert(src, self.root)

    def test_reject_empty_sites(self):
        src = fixture()
        src["sites"] = []
        with self.assertRaises(ValueError):
            adapter.convert(src, self.root)


if __name__ == "__main__":
    unittest.main()
