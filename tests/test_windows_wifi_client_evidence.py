"""Synthetic-only Windows station evidence tests: no Windows/UniFi access."""
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import windows_wlan_native as native
import windows_netsh_localized as netsh
from convert_v6_wifi_evidence import extract_windows_current_connection

ZH_TW = """\
系統上有 1 個介面:
    狀態                    : 已連線
    SSID                    : SYNTHETIC_SECRET_WIFI
    AP BSSID                : aa:bb:cc:dd:ee:ff
    共置的 AP: 3
        BSSID: aa:bb:cc:dd:ee:01 , 頻帶: 6 GHz , 通道: 85
    頻帶                    : 5 GHz
    通道                    : 44
    接收速率 (Mbps)         : 324
    傳輸速率 (Mbps)         : 216
    訊號                    : 60%
    Rssi                    : -73
"""
EN = """\
    State : connected
    SSID : SYNTHETIC_SECRET_WIFI
    BSSID : aa:bb:cc:dd:ee:ff
    Band : 6 GHz
    Channel : 85
    Receive rate (Mbps) : 1201
    Transmit rate (Mbps) : 1000
    Signal : 82%
    Rssi : -51
"""


class NativeWlanTests(unittest.TestCase):
    def test_frequency_maps_to_correct_band(self):
        self.assertEqual(native.band_from_frequency_mhz(2437), 2.4)
        self.assertEqual(native.band_from_frequency_mhz(5220), 5.0)
        self.assertEqual(native.band_from_frequency_mhz(6375), 6.0)
        self.assertIsNone(native.band_from_frequency_mhz(8000))

    def test_native_sample_preserves_phy_vs_throughput(self):
        result = native.sanitized_sample(6375000, -51, 82, 1201000, 960000)
        self.assertEqual(result["band_ghz"], 6.0)
        self.assertEqual(result["rssi_dbm"], -51)
        self.assertEqual(result["rx_phy_mbps"], 1201)
        self.assertTrue(result["not_throughput"])

    def test_native_rejects_invalid_rssi_and_frequency(self):
        self.assertIsNone(native.sanitized_sample(6375000, 70, 50, 1000, 1000))
        self.assertIsNone(native.sanitized_sample(1000000, -50, 50, 1000, 1000))
        self.assertIsNone(native.sanitized_sample(6375000, -50, 110, 1000, 1000))

    @unittest.skipUnless(sys.platform == "win32", "Windows-only Native WLAN ABI smoke")
    def test_windows_native_abi_and_safe_status(self):
        import ctypes
        self.assertEqual(ctypes.sizeof(native.WLAN_ASSOCIATION_ATTRIBUTES), 68)
        self.assertEqual(native.WLAN_CONNECTION_ATTRIBUTES.association.offset, 520)
        self.assertEqual(native.WLAN_BSS_LIST.items.offset, 8)
        # Hosted GitHub runner has no physical WiFi adapter; safe unavailable is OK.
        sample = native.sample()
        self.assertIn(sample["status"], native.STATUS)

    def test_native_does_not_include_sensitive_fields(self):
        obj = native.sanitized_sample(5220000, -73, 60, 324000, 216000)
        text = json.dumps(obj)
        for banned in ["ssid", "bssid", "mac", "password", "ip_address"]:
            self.assertNotIn('"' + banned + '"', text.casefold())


class LocalizedNetshTests(unittest.TestCase):
    def test_co_located_6ghz_does_not_override_actual_5ghz(self):
        sample = netsh.parse(ZH_TW)
        self.assertEqual(sample["status"], "OBSERVED")
        self.assertEqual(sample["band_ghz"], 5)
        self.assertEqual(sample["rssi_dbm"], -73)
        self.assertEqual(sample["channel"], 44)
        self.assertEqual(sample["rx_phy_mbps"], 324)
        self.assertNotIn("SYNTHETIC_SECRET_WIFI", json.dumps(sample))
        self.assertNotIn("aa:bb:cc", json.dumps(sample))

    def test_real_connected_6ghz_en(self):
        sample = netsh.parse(EN)
        self.assertEqual(sample["band_ghz"], 6)
        self.assertEqual(sample["rssi_dbm"], -51)

    def test_multiple_connected_interfaces_rejected_not_first_result(self):
        text = ("State : connected\nBand : 5 GHz\nRssi : -60\n"
                "State : connected\nBand : 6 GHz\nRssi : -40\n")
        self.assertEqual(netsh.parse(text)["status"], "AMBIGUOUS_MULTIPLE_CONNECTIONS")

    def test_does_not_infer_rssi_from_signal_percent(self):
        sample = netsh.parse("State : connected\nBand : 5 GHz\nSignal : 40%\n")
        self.assertIsNone(sample["rssi_dbm"])

    def test_no_band_from_channel_only(self):
        sample = netsh.parse("State : connected\nChannel : 85\nSignal : 60%\n")
        self.assertEqual(sample["status"], "NO_SUPPORTED_WIFI_FIELDS")

    def test_disconnect_not_observed(self):
        sample = netsh.parse("State : disconnected\nBand : 6 GHz\nRssi : -50")
        self.assertEqual(sample["status"], "NOT_CONNECTED")

    def test_rejects_invalid_band(self):
        self.assertEqual(netsh.parse("State : connected\nBand : 7 GHz\nRSSI : 50")["status"], "NO_SUPPORTED_WIFI_FIELDS")

    def test_extraction_accepts_known_observations_only(self):
        self.assertEqual(extract_windows_current_connection({
            "windows_native_wifi": netsh.parse(ZH_TW),
        })["rssi"], -73)
        self.assertEqual(extract_windows_current_connection({
            "windows_native_wifi": native.sanitized_sample(6375000, -54, 65, 1201000, 960000),
        })["band"], 6.0)

    def test_extraction_rejects_fake_source_and_out_of_range(self):
        self.assertIsNone(extract_windows_current_connection({
            "windows_native_wifi": {"status": "OBSERVED", "source": "UNVERIFIED_CLAIM",
                                    "rssi_dbm": -44, "band_ghz": 6},
        }))
        obj = extract_windows_current_connection({
            "windows_native_wifi": {"status": "OBSERVED", "source": "WINDOWS_NETSH_EXPLICIT_CURRENT_INTERFACE",
                                    "rssi_dbm": 50, "band_ghz": 5}
        })
        self.assertIsNone(obj["rssi"])


if __name__ == "__main__":
    unittest.main()
