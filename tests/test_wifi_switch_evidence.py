import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class WiFiSwitchPublicEvidence(unittest.TestCase):
    def test_module_structure_and_official_links(self):
        paths=[ROOT/"modules/M04-wifi.md",ROOT/"modules/M05-switch.md"]
        for path in paths:
            text=path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("DOC_REVIEWED",text)
                self.assertIn("https://help.ui.com/hc/en-us/articles/",text)
                for heading in ["## 核心概念","## 官方建議做法",
                                "## UI 操作路徑","## CLI / API 替代方法",
                                "## 風險與注意事項","## 驗證方式",
                                "## 故障排除流程","## 官方文件連結"]:
                    self.assertIn(heading,text)
    def test_region_and_roaming_constraints(self):
        w=(ROOT/"modules/M04-wifi.md").read_text(encoding="utf-8")
        for s in ["6 GHz","WPA2/3","PMF","AFC","802.11r","Band Steering",
                  "Client Isolation","Tagged VLAN","回滾"]:
            self.assertIn(s,w)
    def test_switch_safety_and_budget_contract(self):
        s=(ROOT/"modules/M05-switch.md").read_text(encoding="utf-8")
        for v in ["RSTP","BPDU Guarding","Loop Protection","Native VLAN",
                  "Tagged VLAN","PoE Budget","Tech Specs","帶外"]:
            self.assertIn(v,s)
    def test_machine_readable_matrix_is_public_and_version_aware(self):
        p=json.loads((ROOT/"docs/wifi-switch-capability-matrix.json").read_text())
        self.assertFalse(p["auto_apply"])
        self.assertFalse(p["requires_private_device_data"])
        self.assertEqual(len(p["wifi"]),4)
        self.assertEqual(len(p["switch"]),4)
        for rule in p["wifi"]+p["switch"]:
            self.assertTrue(rule["source"].startswith("https://help.ui.com/hc/en-us/articles/"))
            self.assertTrue(rule["requirements"])
            self.assertTrue(rule["notes"])
        self.assertIn("region_list",p["wifi"][0])
        self.assertIn("PoE",p["switch"][1]["requirements"][0])
if __name__=="__main__":
    unittest.main()
