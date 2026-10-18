import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("knowledge_audit",ROOT/"scripts/validate_knowledge.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class KnowledgeAuditTests(unittest.TestCase):
    def test_public_repository_current_contract(self):
        self.assertEqual(audit.validate(ROOT),[])

    def test_reject_unapproved_or_spoofed_official_domains(self):
        for url in ("https://ui.com.evil.test/help", "http://help.ui.com/docs",
                    "https://user:secret@help.ui.com/docs",
                    "https://developer.ui.com:8080/network"):
            with self.subTest(url=url):
                catalog={"trusted_hosts":["help.ui.com"],"sources":[
                    {"id":"network", "url":url,"modules":["M01"]}
                ]}
                self.assertTrue(audit.validate_sources(catalog,{"M01"},1))

    def test_duplicate_sources_or_missing_module_mapping(self):
        good="https://help.ui.com/hc/en-us/articles/example"
        catalog={"trusted_hosts":["help.ui.com"],"sources":[
            {"id":"docs","url":good,"modules":["M01"]},
            {"id":"docs","url":good,"modules":["M01"]}
        ]}
        errors=audit.validate_sources(catalog,{"M01","M02"},2)
        self.assertTrue(any("duplicate source id" in x for x in errors))
        self.assertTrue(any("M02 has no official source mapping" in x for x in errors))

    def test_missing_required_module_heading_rejected(self):
        data=("DOC_REVIEWED https://help.ui.com/\n"
              "## 核心概念\n## 官方建議做法\n")
        errors=audit.validate_module(data,"M01")
        self.assertTrue(any("## 驗證方式" in x for x in errors))

    def test_manifest_is_honest_about_historical_degraded_sync(self):
        manifest=json.loads((ROOT/"manifest.json").read_text())
        self.assertFalse(manifest["operational_snapshot"]["is_live_status"])
        self.assertEqual(manifest["operational_snapshot"]["official_sync"]["last_observed_health"],"DEGRADED")
        self.assertEqual(manifest["operational_snapshot"]["official_sync"]["valid_public_content_sources_observed"],0)
        self.assertFalse(manifest["live_private_controller_connections_by_default"])
        self.assertFalse(manifest["requires_personal_device_data"])

if __name__=="__main__":
    unittest.main()
