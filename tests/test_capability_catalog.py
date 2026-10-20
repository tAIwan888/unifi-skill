"""Offline schema/source/version proof gates for UniFi capability catalogs."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_capability_catalog as catalog


class CatalogContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = json.loads((ROOT / "docs/product-capabilities.json").read_text(encoding="utf-8"))
        cls.apis = json.loads((ROOT / "docs/api-capabilities.json").read_text(encoding="utf-8"))

    def test_curated_real_official_catalog_and_sources_valid(self):
        self.assertEqual(catalog.validate(self.products, self.apis), [])
        self.assertGreaterEqual(len(self.products["products"]), 7)
        self.assertGreaterEqual(len(self.apis["endpoints"]), 13)
        self.assertEqual(catalog.load(ROOT)[0]["schema_version"], 1)

    def test_model_lookup_does_not_promote_model_hardware_to_runtime_evidence(self):
        obj = catalog.query_model("U7-Pro", ROOT)
        self.assertEqual(obj["model"], "U7-Pro")
        self.assertEqual(obj["source_url"], "https://techspecs.ui.com/unifi/wifi/u7-pro")
        self.assertIsNone(catalog.query_model("MODEL_NOT_IN_CATALOG", ROOT))
        feat = next(f for f in obj["features"] if f["name"] == "max_6ghz_channel_width_mhz")
        self.assertIn("not guaranteed", feat["constraint"])
        self.assertEqual(self.products["test_tier"], "DOC_REVIEWED")

    def test_api_lookup_exact_version_only_and_nonexecutable(self):
        item = catalog.query_endpoint("network", "10.6.106",
                                      "/v1/sites/{siteId}/firewall/policies", ROOT)
        self.assertEqual(item["method"], "GET")
        self.assertEqual(item["executable_template_approval"], "NOT_APPROVED_FOR_AUTOMATIC_EXECUTION")
        self.assertIsNone(catalog.query_endpoint("network", "10.5.0",
                                                 "/v1/sites/{siteId}/firewall/policies", ROOT))
        self.assertIsNone(catalog.query_endpoint("protect", "10.6.106",
                                                 "/v1/sites/{siteId}/firewall/policies", ROOT))

    def test_cross_app_endpoint_never_runnable_automatically(self):
        a = copy.deepcopy(self.apis)
        item = next(x for x in a["endpoints"] if x["api_family"] == "protect")
        item["executable_template_approval"] = "EXISTING_NETWORK_GET_COLLECTOR_ONLY"
        self.assertTrue(catalog.validate(self.products, a))

    def test_no_post_or_undocumented_endpoint_or_false_latest(self):
        a = copy.deepcopy(self.apis)
        a["endpoints"][0]["method"] = "POST"
        self.assertTrue(any("Unsafe" in x for x in catalog.validate(self.products, a)))
        a = copy.deepcopy(self.apis)
        a["endpoints"][0]["docs"] = "https://example.invalid/test"
        self.assertTrue(any("version-pinned" in x for x in catalog.validate(self.products, a)))
        a = copy.deepcopy(self.apis)
        a["latest_version_claim"] = "10.6.106"
        self.assertTrue(any("global latest" in x for x in catalog.validate(self.products, a)))

    def test_blocks_sneaking_unreviewed_firewall_into_runtime(self):
        a = copy.deepcopy(self.apis)
        x = next(i for i in a["endpoints"] if "/firewall/policies" in i["path"])
        x["executable_template_approval"] = "EXISTING_NETWORK_GET_COLLECTOR_ONLY"
        self.assertTrue(any("Unreviewed API promoted" in e for e in catalog.validate(self.products, a)))

    def test_blocks_unsupported_model_and_6ghz_regulatory_overclaim(self):
        p = copy.deepcopy(self.products)
        item = next(x for x in p["products"] if x["model"] == "U7-Pro")
        x = next(f for f in item["features"] if f["name"] == "radio_bands_ghz")
        x.pop("constraint")
        self.assertTrue(any("regulatory" in s for s in catalog.validate(p, self.apis)))
        p = copy.deepcopy(self.products)
        p["products"][0]["source_url"] = "http://techspecs.ui.com/unifi/wifi/u7-pro"
        self.assertTrue(any("Invalid official source" in s for s in catalog.validate(p, self.apis)))

    def test_duplicate_model_and_duplicate_version_endpoint_not_accepted(self):
        p = copy.deepcopy(self.products)
        p["products"].append(copy.deepcopy(p["products"][0]))
        self.assertTrue(any("Duplicate model" in s for s in catalog.validate(p, self.apis)))
        a = copy.deepcopy(self.apis)
        a["endpoints"].append(copy.deepcopy(a["endpoints"][0]))
        self.assertTrue(any("Duplicate API endpoint" in s for s in catalog.validate(self.products, a)))

    def test_onefile_agent_offline_lookup_and_unknown_results(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import run_unifi_skill
        for args, expected in [
            (["--catalog-model", "U7-Pro"], "U7-Pro"),
            (["--catalog-api", "/v1/sites/{siteId}/firewall/policies"], "GET"),
            (["--catalog-model", "UNKNOWN_MODEL"], "UNKNOWN_NOT_IN_DOCUMENTED_CATALOG"),
        ]:
            with self.subTest(args=args):
                out = StringIO()
                with redirect_stdout(out):
                    code = run_unifi_skill.main(args)
                self.assertEqual(code, 0)
                result = json.loads(out.getvalue())
                self.assertIn(expected, json.dumps(result))
        with self.assertRaises(SystemExit):
            run_unifi_skill.main(["--catalog-model", "U7-Pro", "--local",
                                  "https://unifi.local/proxy/network/integration/v1"])

    def test_catalog_does_not_require_private_device_or_network(self):
        from unittest.mock import patch
        with patch("socket.socket", side_effect=AssertionError("catalog must be offline")):
            model = catalog.query_model("USW-Pro-XG-8-PoE", ROOT)
            self.assertEqual(model["family"], "switch")


if __name__ == "__main__":
    unittest.main()
