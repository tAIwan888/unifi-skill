import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class NetworkSecurityDocs(unittest.TestCase):
    def test_module_format_and_official_evidence(self):
        for name in ['M02-networks.md','M03-firewall-vpn.md']:
            text=(ROOT/'modules'/name).read_text(encoding='utf-8')
            for header in ['## 核心概念','## 官方建議做法','## UI 操作路徑',
                           '## CLI / API 替代方法','## 風險與注意事項',
                           '## 驗證方式','## 故障排除流程','## 官方文件連結']:
                self.assertIn(header,text,name)
            self.assertIn('DOC_REVIEWED',text,name)
            self.assertIn('https://help.ui.com/hc/en-us/articles/',text,name)
    def test_safety_and_version_conditions_not_lost(self):
        m2=(ROOT/'modules/M02-networks.md').read_text(encoding='utf-8')
        m3=(ROOT/'modules/M03-firewall-vpn.md').read_text(encoding='utf-8')
        self.assertIn('Third-Party Gateway',m2)
        self.assertIn('Traffic Identification',m2)
        self.assertIn('4040',m2)
        self.assertIn('9.0+',m3)
        self.assertIn('4.1+',m3)
        self.assertIn('LAN_LOCAL',m3)
        self.assertIn('Teleport',m3)
        self.assertIn('24 小時',m3)
    def test_capability_matrix_does_not_promise_unsupported(self):
        d=json.loads((ROOT/'docs/network-security-compatibility.json').read_text(encoding='utf-8'))
        self.assertFalse(d['auto_apply'])
        byid={r['feature']:r for r in d['rules']}
        self.assertEqual(byid['zone_based_firewall']['network_min'],'9.0')
        self.assertEqual(byid['zone_based_firewall']['gateway_firmware_min'],'4.1')
        self.assertIn('hardware',byid['zone_based_firewall']['notes'])
        self.assertIn('Traffic Identification',byid['unifi_l3_switch_routing']['limitations'][0])
        self.assertEqual(byid['teleport']['invitation_expiry_hours'],24)
        for r in d['rules']:
            self.assertTrue(r['source'].startswith('https://help.ui.com/'))
if __name__=='__main__':
    unittest.main()
