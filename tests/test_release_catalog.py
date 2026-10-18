import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_catalog_v06",ROOT/"scripts/release_catalog.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ReleaseCandidateTests(unittest.TestCase):
    def test_known_unifi_app_versions_dedupe_and_channel_unknown(self):
        text=("UniFi Network Application 10.6.106 for macOS Sep 15 2026. "
              "UniFi Network Application 10.6.106 for Windows. "
              "UniFi OS - Cloud Key Gen2 Plus 6.0.11 Oct 8 2026. "
              "UniFi OS Server 5.1.42 for Linux.")
        found=mod.extract(text,"https://www.ui.com/download/unifi")
        pairs={(r["product_label"],r["version"]) for r in found}
        self.assertIn(("UniFi Network Application","10.6.106"),pairs)
        self.assertIn(("UniFi OS - Cloud Key Gen2 Plus","6.0.11"),pairs)
        self.assertIn(("UniFi OS Server","5.1.42"),pairs)
        self.assertEqual(len(found),len(pairs))
        self.assertTrue(all(r["release_channel"]=="UNKNOWN_NOT_VALIDATED" for r in found))

    def test_no_assumed_latest_no_order_inferred(self):
        data=mod.extract("UniFi Network Application 10.5.67 and UniFi Network Application 10.6.106",
                         "https://www.ui.com/download/unifi")
        self.assertEqual([r["version"] for r in data],["10.5.67","10.6.106"])
        self.assertFalse(any("Official" in r.get("release_channel","") for r in data))

    def test_nav_without_versions_rejected(self):
        self.assertEqual(mod.extract("UniFi Network Release Notes Download More From UI",
                                     "https://www.ui.com/download/unifi"),[])
if __name__=="__main__":unittest.main()
