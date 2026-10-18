import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
    "M01-platform.md":["platform_intro","unifi_updates"],
    "M02-networks.md":["network_application_release_rss"],
    "M03-firewall-vpn.md":["isolation"],
    "M05-switch.md":["l3_routing","vlan"],
    "M06-protect.md":["protect_api"],
    "M09-backup-security.md":["adoption","unifi_updates"],
    "M10-api-n8n.md":["network_api","site_manager_api","protect_api","network_application_release_rss"],
}

class PublicCitationGaps(unittest.TestCase):
    def test_every_target_source_has_exact_url_and_explicit_unreviewed_status(self):
        catalog=json.loads((ROOT/"sync/sources.json").read_text(encoding="utf8"))
        by_id={s["id"]:s for s in catalog["sources"]}
        self.assertEqual(sum(map(len,EXPECTED.values())),13)
        for file,ids in EXPECTED.items():
            md=(ROOT/"modules"/file).read_text(encoding="utf8")
            with self.subTest(module=file):
                self.assertIn("SOURCE_OBSERVED_UNREVIEWED",md)
                self.assertIn("尚待人工內容覆核",md)
                for sid in ids:
                    self.assertIn(by_id[sid]["url"],md)
    def test_release_and_developer_scope_not_overstated(self):
        m2=(ROOT/"modules/M02-networks.md").read_text()
        m10=(ROOT/"modules/M10-api-n8n.md").read_text()
        self.assertIn("Official／RC／EA 尚未核實",m2)
        self.assertIn("不是最新 API 或相容性保證",m10)
        self.assertIn("Official／RC／EA 尚未核實",m10)
    def test_no_private_network_info_in_source_index(self):
        for file in EXPECTED:
            md=(ROOT/"modules"/file).read_text()
            appendix=md.split("### 已觀測官方來源補充索引",1)[1]
            self.assertNotIn("X-API-Key:",appendix)
            self.assertNotIn("Authorization: Bearer",appendix)
if __name__=="__main__":unittest.main()
