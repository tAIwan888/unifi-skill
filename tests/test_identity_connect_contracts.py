import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class IdentityTalkConnect(unittest.TestCase):
 def test_public_module_contract(self):
  s=(ROOT/'modules/M08-identity-talk.md').read_text(encoding='utf8')
  for h in ['## 核心概念','## 官方建議做法','## UI 操作路徑',
            '## CLI / API 替代方法','## 風險與注意事項',
            '## 驗證方式','## 故障排除流程','## 官方文件連結']:
   self.assertIn(h,s)
  for keyword in ['DOC_REVIEWED','UniFi Fabrics','SAML','SCIM','UniFi Talk',
                  'UniFi Connect','EV','Single-Site Only','4.4+']:
   self.assertIn(keyword,s)
  self.assertIn('https://help.ui.com/hc/en-us/articles/',s)

 def test_machine_readable_scope(self):
  d=json.loads((ROOT/'docs/identity-talk-connect-capabilities.json').read_text())
  self.assertFalse(d['auto_apply'])
  self.assertFalse(d['personal_user_data_required'])
  items={v['name']:v for v in d['features']}
  self.assertEqual(items['fabrics']['min_unifi_os'],'4.4')
  self.assertEqual(items['talk_subscription']['regions'],['US','UK','CA'])
  self.assertFalse(items['ev_charging']['automation_allowed'])
  for entry in d['features']:
   self.assertTrue(entry['source'].startswith('https://help.ui.com/hc/en-us/articles/'))
   self.assertTrue(entry['notes'])
if __name__=='__main__':unittest.main()
