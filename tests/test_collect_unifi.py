"""Synthetic-only tests for task-selected UniFi Skill Collector. No live device calls."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect_unifi as collector
import run_unifi_skill as agent
from check_diagnostic_evidence import validate


class MockNetworkApi:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail
    def paged(self, path, cap=150):
        self.calls.append(("GET list", path, cap))
        if self.fail == path:
            raise collector.ReadError("synthetic query failed")
        if path == "/sites":
            return [{"id": "PRIVATE_SITE"}]
        if path == "/sites/PRIVATE_SITE/devices":
            return [{"id": "SECRET_AP"}, {"id": "SECRET_SWITCH"}]
        if path == "/sites/PRIVATE_SITE/networks":
            return [{"id": "PRIVATE_LAN_1"}, {"id": "PRIVATE_LAN_2"}]
        if path == "/sites/PRIVATE_SITE/clients":
            return [{"mac": "aa:bb:cc:dd:ee:ff"}]
        raise AssertionError("Unapproved API listing requested: " + path)
    def get(self, path):
        self.calls.append(("GET", path))
        if self.fail == path:
            raise collector.ReadError("synthetic query failed")
        if path == "/sites/PRIVATE_SITE/devices/SECRET_AP":
            return {"name": "HOME SSID", "model": "SYNTHETIC_AP",
                    "interfaces": {"ports": [{"idx": 0, "state": "UP", "speedMbps": 2500}]}}
        if path == "/sites/PRIVATE_SITE/devices/SECRET_SWITCH":
            return {"name": "PRIVATE_SWITCH",
                    "interfaces": {"ports": [
                        {"idx": 1, "state": "UP", "speedMbps": 1000},
                        {"idx": 2, "state": "DOWN", "speedMbps": 0}]}}
        raise AssertionError("Unapproved API request: " + path)


class NetworkCollectorTests(unittest.TestCase):
    def test_supported_all_get_is_bounded_and_aggregated(self):
        api = MockNetworkApi()
        result = collector.measure("all", client=api)
        observed = {o["metric"]: o["value"] for o in result["observations"]
                    if o["state"] == "OBSERVED"}
        self.assertEqual(observed, {
            "site_count": 1, "adopted_device_count": 2, "network_count": 2,
            "connected_client_count": 1, "device_port_count": 3,
            "device_up_port_count": 2,
        })
        self.assertEqual(result["collector_status"]["protect"], "NOT_IMPLEMENTED_VERSION_GATED")
        self.assertEqual(result["collector_status"]["gateway"], "NOT_IMPLEMENTED_VERSION_GATED")
        serial = json.dumps(result)
        for private in ("PRIVATE_SITE", "SECRET_AP", "SECRET_SWITCH",
                        "HOME SSID", "PRIVATE_SWITCH", "aa:bb:cc", "PRIVATE_LAN"):
            self.assertNotIn(private, serial)
        self.assertTrue(all("/actions" not in str(x) for x in api.calls))
        self.assertFalse(any(x[0] not in ("GET", "GET list") for x in api.calls))

    def test_network_combines_documented_get_families(self):
        api = MockNetworkApi()
        result = collector.measure("network", client=api)
        self.assertEqual(result["collector_status"]["network"], "OBSERVED")
        self.assertEqual(set(result["required_metrics"]), {
            "site_count", "adopted_device_count", "network_count",
            "connected_client_count", "device_port_count", "device_up_port_count",
        })
        self.assertTrue(all(o["state"] == "OBSERVED" for o in result["observations"]))

    def test_network_partial_failure_does_not_invent_missing_count(self):
        api = MockNetworkApi(fail="/sites/PRIVATE_SITE/clients")
        result = collector.measure("network", client=api)
        self.assertEqual(result["collector_status"]["network"],
                         "NETWORK_AGGREGATE_INCOMPLETE")
        self.assertIn("connected_client_count",
                      result["missing_evidence_reasons"])

    def test_does_not_fetch_unrelated_profiles(self):
        api = MockNetworkApi()
        result = collector.measure("networks", client=api)
        self.assertEqual(result["required_metrics"], ["network_count"])
        self.assertFalse(any("/devices" in x[1] or "/clients" in x[1] for x in api.calls))

    def test_partial_network_query_does_not_claim_zero(self):
        api = MockNetworkApi(fail="/sites/PRIVATE_SITE/networks")
        result = collector.measure("networks", client=api)
        self.assertEqual(result["observations"][0]["state"], "NOT_OBSERVED")
        self.assertEqual(result["missing_evidence_reasons"]["network_count"],
                         "NETWORK_LIST_QUERY_FAILED")

    def test_port_status_missing_or_duplicate_is_fail_closed(self):
        api = MockNetworkApi()
        original = api.get
        def incomplete(path):
            data = original(path)
            if path.endswith("SECRET_SWITCH"):
                data["interfaces"]["ports"][1]["idx"] = 1
            return data
        api.get = incomplete
        result = collector.measure("ports", client=api)
        self.assertTrue(all(o["state"] == "NOT_OBSERVED" for o in result["observations"]))

    def test_no_ports_documented_is_not_observed(self):
        api = MockNetworkApi()
        api.get = lambda path: {"interfaces": {}}
        result = collector.measure("ports", client=api)
        self.assertEqual(result["collector_status"]["ports"], "NO_VERIFIED_PORT_ARRAYS")

    def test_unsupported_api_family_is_never_called(self):
        for profile in ("firewall", "vpn", "protect", "access", "backup", "gateway"):
            with self.subTest(profile=profile):
                result = collector.measure(profile, client=None)
                self.assertEqual(result["collector_status"][profile],
                                 "NOT_IMPLEMENTED_VERSION_GATED")
                self.assertTrue(all(o["state"] == "NOT_OBSERVED"
                                    for o in result["observations"]))

    def test_mock_cannot_launder_synthetic_observed_metrics(self):
        for profile in ("all", "inventory", "networks", "clients", "ports"):
            result = collector.measure(profile, mock=True)
            self.assertTrue(all(o["state"] == "NOT_OBSERVED" for o in result["observations"]))
            self.assertTrue(all(v == "MOCK_NO_DEVICE_ACCESS"
                                for k, v in result["collector_status"].items()
                                if k in collector.CAPABILITIES))

    def test_reject_unknown_profile(self):
        with self.assertRaises(ValueError):
            collector.measure("raw-api-admin")


class GenericAgentTests(unittest.TestCase):
    def args(self, directory, **extras):
        obj = {
            "collect": "inventory", "mock": True, "local": None,
            "out": directory / "private.json", "collector_dir": None, "ca_cert": None,
        }
        obj.update(extras)
        return SimpleNamespace(**obj)

    def test_offline_inventory_json_gate_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.args(Path(tmp))
            self.assertEqual(agent.execute(args), 0)
            report = json.loads(args.out.read_text(encoding="utf8"))
            self.assertEqual(validate(report, ROOT), [])
            self.assertEqual(report["device_access"], "NONE")
            self.assertEqual(report["collector_profile"], "inventory")
            self.assertEqual(report["verification_status"], "INCOMPLETE")
            self.assertIn("adopted_device_count", report["missing_metrics"])
            files = {v["path"] for v in report["skill"]["loaded_files"]}
            self.assertIn("scripts/collect_unifi.py", files)
            self.assertIn("modules/M06-protect.md", files)
            self.assertIn("docs/api-capabilities.json", files)

    def test_all_includes_wifi_and_unsupported_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            stream = io.StringIO()
            args = self.args(Path(tmp), collect="all", out=Path("-"))
            with contextlib.redirect_stdout(stream):
                self.assertEqual(agent.execute(args), 0)
            report = json.loads(stream.getvalue())
            self.assertEqual(validate(report, ROOT), [])
            self.assertIn("client_band", report["missing_metrics"])
            self.assertIn("access_validated_status", report["missing_metrics"])
            self.assertIn("network_count", report["missing_metrics"])
            self.assertIn("modules/M07-access.md", report["modules"])
            self.assertEqual(report["verification_status"], "INCOMPLETE")
            self.assertEqual(report["device_access"], "NONE")

    def test_compatibility_wifi_default_uses_existing_runner(self):
        with patch.object(agent.legacy, "execute", return_value=0) as old:
            with tempfile.TemporaryDirectory() as tmp:
                args = self.args(Path(tmp), collect="wifi")
                self.assertEqual(agent.execute(args), 0)
                old.assert_called_once_with(args)

    def test_capabilities_offline_without_creds_or_controller(self):
        text = io.StringIO()
        with contextlib.redirect_stdout(text):
            self.assertEqual(agent.main(["--capabilities"]), 0)
        data = json.loads(text.getvalue())
        self.assertIn("wifi", data["implemented_profiles"])
        self.assertIn("protect", data["unimplemented_profiles"])
        self.assertTrue(data["no_persistent_service"])


if __name__ == "__main__":
    unittest.main()
