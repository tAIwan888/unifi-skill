"""Synthetic-only tests for integrated UniFi GET collector. No private or live traffic."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect_wifi_lan_local as collector


class FakeReadClient:
    def __init__(self):
        self.paths = []

    def paged(self, path, cap=150):
        self.paths.append(path)
        if path == "/sites":
            return [{"id": "synthetic_site"}]
        if path == "/sites/synthetic_site/devices":
            return [{"id": "ap01"}, {"id": "sw01"}]
        raise AssertionError("Unexpected paged endpoint")

    def get(self, path):
        self.paths.append(path)
        if path == "/info":
            return {"applicationVersion": "10.6.106"}
        if path.endswith("/devices/ap01"):
            return {"id": "ap01", "name": "SECRET_AP_NAME", "macAddress": "AABBCCDDEEFF",
                    "ipAddress": "192.0.2.9", "model": "U7 Pro", "firmwareVersion": "8.7.11",
                    "state": "ONLINE", "uplink": {"deviceId": "sw01"},
                    "interfaces": {"radios": [
                        {"frequencyGHz": 5, "channel": 44, "channelWidthMHz": 80},
                        {"frequencyGHz": 6, "channel": 85, "channelWidthMHz": 160}],
                        "ports": []}}
        if path.endswith("/devices/sw01"):
            return {"id": "sw01", "name": "PRIVATE_SWITCH", "model": "USW Pro XG 8 PoE",
                    "state": "ONLINE", "interfaces": {"ports": [
                        {"idx": 1, "state": "UP", "speedMbps": 2500},
                        {"idx": 2, "state": "UP", "speedMbps": 5000}]}}
        if path.endswith("/devices/ap01/statistics/latest"):
            return {"interfaces": {"radios": [
                {"frequencyGHz": 5, "txRetriesPct": 10.5},
                {"frequencyGHz": 6, "txRetriesPct": 0.0}]}}
        if path.endswith("/devices/sw01/statistics/latest"):
            return {"cpuUtilizationPct": 10}
        raise AssertionError("Unexpected GET endpoint: " + path)


class CollectionTests(unittest.TestCase):
    def test_read_only_site_evidence_redacts_private_identifiers(self):
        fake = FakeReadClient()
        sites = collector.site_snapshot(fake)
        self.assertEqual(len(sites), 1)
        ap = sites[0]["access_points"][0]
        self.assertTrue(ap["uplink_parent_in_device_inventory"])
        self.assertIsNone(ap["uplink_negotiated_speed_mbps"])
        self.assertEqual(ap["uplink_mapping_evidence"], "PARENT_DEVICE_ONLY_NO_PORT_MAPPING")
        self.assertEqual(ap["stats"]["radio_samples"][0]["tx_retries_percent"], 10.5)
        self.assertEqual(sites[0]["other_unifi_devices"][0]["ports"][0]["negotiated_speed_mbps"], 2500)
        output = json.dumps(sites)
        for secret in ("synthetic_site", "ap01", "sw01", "SECRET_AP_NAME",
                       "AABBCCDDEEFF", "192.0.2.9", "PRIVATE_SWITCH"):
            self.assertNotIn(secret, output)
        self.assertTrue(all("/actions" not in path for path in fake.paths))

    def test_no_false_uplink_port_even_if_parent_has_single_port(self):
        fake = FakeReadClient()
        original = fake.get
        def one_port(path):
            val = original(path)
            if path.endswith("/devices/sw01"):
                val["interfaces"]["ports"] = [{"idx": 1, "state": "UP", "speedMbps": 2500}]
            return val
        fake.get = one_port
        ap = collector.site_snapshot(fake)[0]["access_points"][0]
        self.assertIsNone(ap["uplink_negotiated_speed_mbps"])

    def test_auto_collect_ap_side_speed_from_unique_up_port(self):
        fake = FakeReadClient()
        raw = fake.get
        def ap_port(path):
            d = raw(path)
            if path.endswith("/devices/ap01"):
                d["interfaces"]["ports"] = [{
                    "idx": 0, "state": "UP", "speedMbps": 2500,
                    "maxSpeedMbps": 2500,
                }]
            return d
        fake.get = ap_port
        ap = collector.site_snapshot(fake)[0]["access_points"][0]
        self.assertEqual(ap["uplink_negotiated_speed_mbps"], 2500)
        self.assertEqual(ap["uplink_speed_evidence"], "AP_SIDE_SINGLE_UP_PORT_PARENT_VERIFIED")
        self.assertEqual(ap["uplink_mapping_evidence"], "PARENT_DEVICE_ONLY_NO_PORT_MAPPING")
        self.assertFalse(any("SECRET" in str(x) for x in ap.values()))

    def test_multi_up_ports_is_ambiguous(self):
        fake = FakeReadClient()
        raw = fake.get
        def with_ports(path):
            d = raw(path)
            if path.endswith("/devices/ap01"):
                d["interfaces"]["ports"] = [
                    {"idx": 0, "state": "UP", "speedMbps": 2500},
                    {"idx": 1, "state": "UP", "speedMbps": 5000},
                ]
            return d
        fake.get = with_ports
        ap = collector.site_snapshot(fake)[0]["access_points"][0]
        self.assertIsNone(ap["uplink_negotiated_speed_mbps"])
        self.assertEqual(ap["uplink_speed_evidence"], "AP_UP_PORT_COUNT_NOT_UNIQUE")

    def test_duplicate_ap_port_index_and_max_speed_ambiguity(self):
        cases = [
            ([{"idx": 0, "state": "UP", "speedMbps": 2500},
              {"idx": 0, "state": "DOWN", "speedMbps": 0}],
             "AP_LOCAL_PORT_INDEX_AMBIGUOUS"),
            ([{"idx": 0, "state": "UP", "maxSpeedMbps": 2500}],
             "AP_UP_PORT_NEGOTIATED_SPEED_UNAVAILABLE"),
            ([{"idx": 0, "state": "UP", "speedMbps": 5000, "maxSpeedMbps": 2500}],
             "AP_PORT_SPEED_EXCEEDS_DECLARED_MAXIMUM"),
        ]
        for raw_ports, reason in cases:
            with self.subTest(reason=reason):
                fake = FakeReadClient()
                original = fake.get
                def with_ports(path):
                    d = original(path)
                    if path.endswith("/devices/ap01"):
                        d["interfaces"]["ports"] = raw_ports
                    return d
                fake.get = with_ports
                ap = collector.site_snapshot(fake)[0]["access_points"][0]
                self.assertIsNone(ap["uplink_negotiated_speed_mbps"])
                self.assertEqual(ap["uplink_speed_evidence"], reason)

    def test_parent_not_verified_cannot_claim_ap_uplink(self):
        fake = FakeReadClient()
        raw = fake.get
        def no_parent(path):
            d = raw(path)
            if path.endswith("/devices/ap01"):
                d["uplink"] = {"deviceId": "unknown"}
                d["interfaces"]["ports"] = [{"idx": 0, "state": "UP", "speedMbps": 2500}]
            return d
        fake.get = no_parent
        ap = collector.site_snapshot(fake)[0]["access_points"][0]
        self.assertIsNone(ap["uplink_negotiated_speed_mbps"])

    def test_local_url_rfc1918_and_no_public_endpoints(self):
        for url in ("https://unifi.local/proxy/network/integration/v1",
                    "https://192.168.1.1/proxy/network/integration/v1",
                    "https://10.1.1.1/integration/v1"):
            with self.subTest(url=url):
                self.assertEqual(collector.local_api_url(url), url)
        for url in ("https://api.ui.com/proxy/network/integration/v1",
                    "http://192.168.1.1/proxy/network/integration/v1",
                    "https://192.0.2.1/proxy/network/integration/v1",
                    "https://user:key@unifi.local/proxy/network/integration/v1",
                    "https://unifi.local/proxy/network/integration/v1?q=token"):
            with self.subTest(url=url):
                with self.assertRaises(collector.ReadError):
                    collector.local_api_url(url)

    def test_pagination_fails_closed_for_missing_records(self):
        item = object.__new__(collector.ReadOnlyClient)
        with patch.object(item, "get", side_effect=[
            {"offset": 0, "count": 1, "totalCount": 3, "data": [{"id": "s"}]},
            {"offset": 1, "count": 0, "totalCount": 3, "data": []},
        ]):
            with self.assertRaisesRegex(collector.ReadError, "Incomplete"):
                item.paged("/sites")

    def test_stats_missing_is_unknown_not_zero(self):
        stat = collector.stats_view({"interfaces": {"radios": [{"frequencyGHz": 5}]}})
        self.assertIsNone(stat["radio_samples"][0]["tx_retries_percent"])
        self.assertEqual(stat["observed_measurements"], 0)

    def test_mock_fixture_never_calls_local_network(self):
        with patch.object(collector, "ReadOnlyClient") as fake:
            mock = collector.mock_fixture()
            fake.assert_not_called()
        self.assertEqual(mock["collection_mode"], "mock")
        self.assertEqual(mock["windows_native_wifi"]["status"], "MOCK")
        self.assertEqual(mock["lan_tcp_throughput_test"]["status"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
