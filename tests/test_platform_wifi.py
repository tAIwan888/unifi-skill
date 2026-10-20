"""Mock-only multi-OS one-shot WiFi probe contract; no live WiFi/API calls."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import platform_wifi as adapter
from convert_v6_wifi_evidence import extract_windows_current_connection, convert
from check_diagnostic_evidence import validate

LINUX_LINK = """\
Connected to 00:11:22:33:44:55 (on wlan0)
        SSID: PRIVATE_SYNTHETIC
        freq: 6115
        RX: 100 bytes (1 packets)
        signal: -54 dBm
        tx bitrate: 1201.0 MBit/s MCS 11
"""

class LinuxLinkTests(unittest.TestCase):
    def test_linux_current_association_6ghz_without_privacy_leak(self):
        result = adapter.parse_iw_link(LINUX_LINK)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(result["band_ghz"], 6.0)
        self.assertEqual(result["rssi_dbm"], -54)
        self.assertEqual(result["bss_center_frequency_mhz"], 6115.0)
        self.assertTrue(result["not_throughput"])
        raw = json.dumps(result)
        for banned in ("PRIVATE_SYNTHETIC", "00:11:22", '"ssid"', '"bssid"'):
            self.assertNotIn(banned, raw)

    def test_iw_current_link_5ghz_and_disconnected(self):
        self.assertEqual(adapter.parse_iw_link(
            LINUX_LINK.replace("6115", "5220"))["band_ghz"], 5.0)
        self.assertEqual(adapter.parse_iw_link("Not connected.")["status"], "NOT_CONNECTED")

    def test_channel_without_freq_or_ssi_is_unknown(self):
        self.assertEqual(adapter.parse_iw_link(
            LINUX_LINK.replace("freq: 6115", "channel 5").replace(
                "signal: -54 dBm", "signal: 85%"))["status"], "NO_SUPPORTED_WIFI_FIELDS")

    def test_discover_one_client_and_no_shell_or_secret_leak(self):
        calls = []
        def fake(argv, **kwargs):
            self.assertIsInstance(argv, list)
            self.assertFalse(kwargs["check"])
            calls.append(argv)
            if argv == ["/usr/bin/iw", "dev"]:
                return SimpleNamespace(returncode=0, stdout="phy#0\n\tInterface wlan0\n")
            if argv == ["/usr/bin/iw", "dev", "wlan0", "link"]:
                return SimpleNamespace(returncode=0, stdout=LINUX_LINK)
            raise AssertionError("Unexpected command")
        obj = adapter.linux_link(runner=fake, which=lambda _: "/usr/bin/iw")
        self.assertEqual(obj["rssi_dbm"], -54)
        self.assertEqual(len(calls), 2)

    def test_linux_multiple_associations_fail_closed(self):
        def fake(argv, **kwargs):
            if argv[-1] == "dev":
                return SimpleNamespace(returncode=0, stdout="phy#0\n\tInterface wlan0\n\tInterface wlan1\n")
            return SimpleNamespace(returncode=0, stdout=LINUX_LINK)
        result = adapter.linux_link(fake, lambda _: "/usr/bin/iw")
        self.assertEqual(result["status"], "AMBIGUOUS_MULTIPLE_CONNECTIONS")

    def test_iw_missing_or_timeout(self):
        self.assertEqual(adapter.linux_link(which=lambda _: None)["status"], "NATIVE_API_UNAVAILABLE")
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("iw", 5)
        self.assertEqual(adapter.linux_link(timeout, lambda _: "/usr/bin/iw")["status"],
                         "NATIVE_API_UNAVAILABLE")

    def test_cannot_execute_interface_injection(self):
        self.assertEqual(adapter.linux_interface_names("  Interface wlan0;rm -rf /"), [])
        self.assertEqual(adapter.frequency_band(2462), 2.4)
        self.assertIsNone(adapter.frequency_band(7300))


class MacOSProbeTests(unittest.TestCase):
    def test_macos_corewlan_uses_current_channel_not_supported_scans(self):
        class CWChannel:
            def channelBand(self):
                return 3
        class Interface:
            def wlanChannel(self):
                return CWChannel()
            def serviceActive(self):
                return True
            def rssiValue(self):
                return -49
            def transmitRate(self):
                return 1201
            def supportedWLANChannels(self):
                raise AssertionError("Do not enumerate supported bands")
        client = SimpleNamespace(interfaces=lambda: [Interface()])
        mock = SimpleNamespace(kCWChannelBand2GHz=1,
                               kCWChannelBand5GHz=2,
                               kCWChannelBand6GHz=3,
                               CWWiFiClient=SimpleNamespace(sharedWiFiClient=lambda: client))
        with patch.dict(sys.modules, {"CoreWLAN": mock}):
            result = adapter.macos_link()
        self.assertEqual(result["band_ghz"], 6.0)
        self.assertEqual(result["rssi_dbm"], -49)
        self.assertTrue(result["not_throughput"])

    def test_multiple_macos_interfaces_fail_closed(self):
        class Interface:
            def wlanChannel(self):
                return object()
            def serviceActive(self):
                return True
        mock = SimpleNamespace(CWWiFiClient=SimpleNamespace(
            sharedWiFiClient=lambda: SimpleNamespace(interfaces=lambda: [Interface(), Interface()])))
        with patch.dict(sys.modules, {"CoreWLAN": mock}):
            result = adapter.macos_link()
        self.assertEqual(result["status"], "AMBIGUOUS_MULTIPLE_CONNECTIONS")

    def test_macos_permission_error_does_not_generate_fake_rssi(self):
        def denied():
            raise OSError("permission denied")
        mock = SimpleNamespace(CWWiFiClient=SimpleNamespace(
            sharedWiFiClient=lambda: SimpleNamespace(interfaces=denied)))
        with patch.dict(sys.modules, {"CoreWLAN": mock}):
            result = adapter.macos_link()
        self.assertEqual(result["status"], "NATIVE_API_UNAVAILABLE")
        self.assertNotIn("rssi_dbm", result)

    def test_missing_6ghz_constant_keeps_band_unknown(self):
        class Channel:
            def channelBand(self):
                return 3
        class Interface:
            def wlanChannel(self):
                return Channel()
            def serviceActive(self):
                return True
            def rssiValue(self):
                return -65
            def transmitRate(self):
                return 200
        mock = SimpleNamespace(kCWChannelBand2GHz=1, kCWChannelBand5GHz=2,
                               CWWiFiClient=SimpleNamespace(sharedWiFiClient=lambda:
                                   SimpleNamespace(interfaces=lambda: [Interface()])))
        with patch.dict(sys.modules, {"CoreWLAN": mock}):
            result = adapter.macos_link()
        self.assertIsNone(result["band_ghz"])
        self.assertEqual(result["rssi_dbm"], -65)


class SkillBridgeTests(unittest.TestCase):
    def test_cross_platform_sources_accepted_by_existing_gate(self):
        for src in ("MACOS_COREWLAN_CURRENT_INTERFACE", "LINUX_IW_CURRENT_LINK"):
            with self.subTest(src=src):
                payload = {"client_wifi_link": adapter.sanitized_link(src, 6.0, -54, 6115)}
                self.assertEqual(extract_windows_current_connection(payload)["band"], 6.0)
                self.assertEqual(extract_windows_current_connection(payload)["rssi"], -54)
                raw = {"report_schema": "unifi-m04-wifi-evidence-lan-only-v6",
                       "collection_mode": "local", "sites": [{"access_points": []}]}
                raw.update(payload)
                evidence = convert(raw, ROOT)
                self.assertEqual(validate(evidence, ROOT), [])
                self.assertNotIn("client_band", evidence["missing_metrics"])
                self.assertNotIn("client_rssi_dbm", evidence["missing_metrics"])
                self.assertIn("lan_throughput_mbps", evidence["missing_metrics"])

    def test_mock_never_promotes_client_probes(self):
        src = {"report_schema": "unifi-m04-wifi-evidence-lan-only-v6",
               "collection_mode": "mock", "sites": [{"access_points": []}],
               "client_wifi_link": adapter.sanitized_link("LINUX_IW_CURRENT_LINK", 6, -52)}
        report = convert(src, ROOT)
        self.assertIn("client_band", report["missing_metrics"])
        self.assertIn("client_rssi_dbm", report["missing_metrics"])

    def test_platform_dispatch(self):
        self.assertEqual(adapter.current_link("unsupported")["status"], "UNSUPPORTED_PLATFORM")
        with patch.object(adapter, "linux_link", return_value={"status": "NOT_CONNECTED"}):
            self.assertEqual(adapter.current_link("linux")["status"], "NOT_CONNECTED")


if __name__ == "__main__":
    unittest.main()
