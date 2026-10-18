import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class ProtectAccessSafetyContracts(unittest.TestCase):
 def test_public_module_contract(self):
  for file in ["M06-protect.md","M07-access.md"]:
   t=(ROOT/"modules"/file).read_text(encoding="utf8")
   for h in ["## 核心概念","## 官方建議做法","## UI 操作路徑",
             "## CLI / API 替代方法","## 風險與注意事項",
             "## 驗證方式","## 故障排除流程","## 官方文件連結"]:
    self.assertIn(h,t,file)
   self.assertIn("DOC_REVIEWED",t,file)
   self.assertIn("https://help.ui.com/hc/en-us/articles/",t,file)

 def test_irreversible_retention_and_privacy(self):
  t=(ROOT/"modules/M06-protect.md").read_text(encoding="utf8")
  for word in ["5.1+","5.2.42+","Off-Site","Enhanced Retention","不可逆","本地","個資"]:
   self.assertIn(word,t)
  self.assertNotIn("UNIFI_API_KEY=",t)

 def test_access_emergency_block_and_fire_panel(self):
  t=(ROOT/"modules/M07-access.md").read_text(encoding="utf8")
  for word in ["Fail-safe","Fail-secure","Emergency Evacuation","Fire Panel",
               "不可","人身安全","消防"]:
   self.assertIn(word,t)
  self.assertNotIn("curl -X POST",t)

 def test_structured_support_matrix_fails_closed(self):
  d=json.loads((ROOT/"docs/protect-access-safety-matrix.json").read_text())
  self.assertFalse(d["auto_apply"])
  self.assertFalse(d["requires_private_media"])
  self.assertEqual(len(d["protect"]),4)
  self.assertEqual(len(d["access"]),4)
  p={e["capability"]:e for e in d["protect"]}
  a={e["capability"]:e for e in d["access"]}
  self.assertEqual(p["enhanced_retention"]["min_protect"],"5.1")
  self.assertEqual(p["stream_encryption"]["min_protect"],"5.2.42")
  self.assertFalse(p["cloud_archiving"]["default_on"])
  self.assertFalse(a["emergency_mode"]["automation_allowed"])
  self.assertFalse(a["fire_panel_emergency"]["app_override_allowed"])
  for x in d["protect"]+d["access"]:
   self.assertTrue(x["source"].startswith("https://help.ui.com/hc/en-us/articles/"))
if __name__=="__main__":unittest.main()
