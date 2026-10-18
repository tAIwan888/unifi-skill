"""Offline guard for four AI-assisted official-source clarification patches.

These tests validate wording/safety boundaries, not current vendor freshness,
reviewer identity, repository approval or production hardware behavior.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Pr6SourceClarificationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m01 = (ROOT / 'modules/M01-platform.md').read_text(encoding='utf-8')
        cls.m04 = (ROOT / 'modules/M04-wifi.md').read_text(encoding='utf-8')
        cls.m09 = (ROOT / 'modules/M09-backup-security.md').read_text(encoding='utf-8')

    def test_help_center_403_is_historical_not_current(self):
        self.assertIn('舊版 HTML 讀取曾受 HTTP 403 限制', self.m01)
        self.assertIn('官方公開 Help Center Article API', self.m01)
        self.assertNotIn('排程自動爬取仍受 403 限制', self.m01)
        self.assertIn('指紋成功不代表 PR #6 已完成人工來源簽核', self.m01)

    def test_official_hosting_scope_is_narrow(self):
        self.assertIn('UniFi Network', self.m01)
        self.assertIn('UniFi Talk Relay（第三方 PBX 用途）', self.m01)
        self.assertIn('Protect、Access 等其他 App 必須搭配', self.m01)
        self.assertIn('不得把跨主機的 Site Manager 統一管理誤稱為由 Hosting 代管所有 Apps', self.m01)

    def test_6ghz_requires_owe_or_wpa3_even_with_transition_ui(self):
        self.assertIn('6 GHz 無線連線本身只能使用 WPA3 或 OWE', self.m04)
        self.assertIn('不能使用 WPA2', self.m04)
        self.assertIn('6 GHz 可用 WPA2 或無 PMF', self.m04)
        self.assertIn('PPSK', self.m04)

    def test_same_vlan_and_layer3_adoption_distinguished(self):
        self.assertIn('Same-VLAN', self.m09)
        self.assertIn('Layer 3', self.m09)
        self.assertIn('TCP **8080**', self.m09)
        self.assertIn('UDP **10001**', self.m09)
        self.assertIn('不是要求在 WAN、全部 VLAN 或全部裝置全面開放連接埠', self.m09)
        self.assertIn('不可把同 VLAN 的 UDP 10001 發現條件直接視為跨 VLAN 的萬用開埠建議', self.m09)
        self.assertIn('Factory Reset 只能當作', self.m09)

    def test_provenance_citation_is_not_approval(self):
        self.assertIn('不代表 PR #6 的該來源已獲獨立真人批准', self.m09)
        self.assertIn('https://help.ui.com/hc/en-us/articles/360012622613-UniFi-Device-Adoption', self.m09)
        self.assertIn('https://help.ui.com/hc/en-us/articles/32065480092951-UniFi-WiFi-SSID-and-AP-Settings-Overview', self.m04)
        self.assertIn('https://help.ui.com/hc/en-us/articles/4415364143511-Getting-Started-with-Official-UniFi-Hosting', self.m01)


if __name__ == '__main__':
    unittest.main()
