"""Public-source product discovery tests; synthetic HTML only, no internet."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import discover_official_products as d


def fixtures():
    pages = {}
    for family, path in d.CATEGORIES.items():
        canonical = d.ORIGIN + path
        if family == "accessories":
            home = ('<a href="?subcategory=cables">Cables (4)</a>'
                    '<a href="?subcategory=mounts">Mounts (4)</a>')
            pages[canonical] = home
            for group in ("cables", "mounts"):
                url = canonical + "?subcategory=" + group
                pages[url] = "".join(
                    f'<a href="/unifi/accessories/test-{group}-{n}">Part {n} ACC-{group}-{n}</a>'
                    for n in range(4))
        else:
            product_group = "cloud-gateways" if family == "cloud-gateways" else family
            links = "".join(
                f'<a href="/unifi/{product_group}/test-{family}-{i}?subcategory=all-{family}">'
                f'Product {i} TEST-{family}-{i}</a>'
                for i in range(8))
            count = "" if family == "advanced-hosting" else (
                f'<a href="/unifi/{family}?subcategory=all-{family}">All (8)</a>')
            pages[canonical] = count + links
    return pages


def injected_fetch(pages):
    def get(url):
        html = pages[url]
        return html, hashlib.sha256(html.encode("utf-8")).hexdigest()
    return get


class OfficialDiscoveryTests(unittest.TestCase):
    def test_all_families_are_indexed_with_source_digests(self):
        pages = fixtures()
        c = d.discover(fetch=injected_fetch(pages), permitted=lambda _: True)
        self.assertEqual(c["snapshot_status"],
                         "ALL_CONFIGURED_LISTINGS_VERIFIED_NOT_ALL_VENDOR_HISTORY")
        self.assertEqual(c["unique_product_links"], 64)
        self.assertEqual(len(c["products"]), 64)
        self.assertEqual(len(c["sources"]), 8)
        self.assertEqual(len(c["source_sha256"]), 10)
        for row in c["products"]:
            self.assertEqual(row["identity_status"],
                             "OFFICIAL_LISTING_LINK_NOT_MODEL_SPEC_VERIFIED")
            self.assertEqual(len(row["categories"]), 1)
            self.assertNotIn("features", row)
        self.assertEqual(c["sources"]["advanced-hosting"]["coverage_status"],
                         "VISIBLE_LINKS_NO_OFFICIAL_TOTAL")

    def test_new_vendor_model_needs_no_code_or_allowlist_change(self):
        pages = fixtures()
        url = d.ORIGIN + "/unifi/wifi"
        pages[url] = pages[url].replace("All (8)", "All (9)") + (
            '<a href="/unifi/wifi/new-device-2027">New Device NEW-MODEL-2027</a>')
        c = d.discover(fetch=injected_fetch(pages), permitted=lambda _: True)
        self.assertEqual(c["unique_product_links"], 65)
        self.assertTrue(any(p["model_slug"] == "new-device-2027" for p in c["products"]))

    def test_short_page_or_unapproved_robots_aborts(self):
        pages = fixtures()
        pages[d.ORIGIN + "/unifi/wifi"] = pages[d.ORIGIN + "/unifi/wifi"].replace("All (8)", "All (46)")
        pages[d.ORIGIN + "/unifi/wifi?subcategory=all-wifi"] = pages[d.ORIGIN + "/unifi/wifi"]
        with self.assertRaisesRegex(d.DiscoveryError, "count"):
            d.discover(fetch=injected_fetch(pages), permitted=lambda _: True)
        pages = fixtures()
        with self.assertRaisesRegex(d.DiscoveryError, "Robots"):
            d.discover(fetch=injected_fetch(pages),
                       permitted=lambda url: "physical-security" not in url)

    def test_accessories_partial_leaf_aborts(self):
        pages = fixtures()
        url = d.ORIGIN + "/unifi/accessories?subcategory=mounts"
        pages[url] = '<a href="/unifi/accessories/one">One</a>'
        with self.assertRaisesRegex(d.DiscoveryError, "accessory"):
            d.discover(fetch=injected_fetch(pages), permitted=lambda _: True)

    def test_untrusted_links_and_query_strings_rejected(self):
        self.assertIsNone(d.canonical_url("https://evil.invalid/unifi/wifi/fake",
                                          d.ORIGIN + "/unifi/wifi"))
        self.assertIsNone(d.canonical_url("javascript:alert(1)",
                                          d.ORIGIN + "/unifi/wifi"))
        self.assertIsNone(d.canonical_url("?do=delete", d.ORIGIN + "/unifi/wifi"))
        self.assertIsNone(d.canonical_url("https://techspecs.ui.com:443/unifi/wifi/a",
                                          d.ORIGIN + "/unifi/wifi"))
        self.assertEqual(d.canonical_url("/unifi/wifi/new-ap?subcategory=all-wifi",
                                         d.ORIGIN + "/unifi/wifi"),
                         d.ORIGIN + "/unifi/wifi/new-ap")

    def test_no_partial_published_file_after_fetch_failure(self):
        pages = fixtures()
        existing = b'{"status":"LAST_KNOWN_GOOD"}\n'
        with tempfile.TemporaryDirectory() as t:
            target = Path(t) / "product-catalog.json"
            target.write_bytes(existing)
            def broken(url):
                if "switching" in url:
                    raise d.DiscoveryError("fail_closed")
                return injected_fetch(pages)(url)
            with patch.object(d, "_get", side_effect=broken), patch.object(
                     d, "_robots", return_value=lambda _: True):
                with self.assertRaises(d.DiscoveryError):
                    d.run(target)
            self.assertEqual(target.read_bytes(), existing)


if __name__ == "__main__":
    unittest.main()
