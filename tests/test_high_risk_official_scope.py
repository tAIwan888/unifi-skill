from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class HighRiskOfficialScopeTests(unittest.TestCase):
    def read(self,name):return (ROOT/"modules"/name).read_text(encoding="utf-8")
    def test_access_reader_hub_l2_is_not_interchangeable_with_hub_console_l3(self):
        s=self.read("M07-access.md")
        self.assertIn("Reader ↔ Access Control Hub 是 Layer 2",s)
        self.assertIn("Hub ↔ UniFi Access Application 則透過 Layer 3",s)
        self.assertIn("必須位於相同 L2",s)
        self.assertIn("不能假設 Reader 能透過 VLAN Routing",s)
        self.assertIn("https://help.ui.com/hc/en-us/articles/17452334269975-Getting-Started-with-UniFi-Access",s)
    def test_protect_cloudkey_nvr_caveat_is_hardware_scoped(self):
        s=self.read("M06-protect.md")
        self.assertIn("若使用 CloudKey 或 NVR",s)
        self.assertIn("相同的 VLAN",s)
        self.assertIn("不得無條件延伸",s)
        self.assertIn("https://help.ui.com/hc/en-us/articles/27878858632599-Getting-Started-with-UniFi-Protect",s)
    def test_zbf_risky_delete_and_gateway_breakages_are_documented(self):
        s=self.read("M03-firewall-vpn.md")
        self.assertIn("刪除自訂 Zone 會一併刪除",s)
        self.assertIn("破壞 DHCP、DNS",s)
        self.assertIn("Network 9.4",s)
        self.assertIn("Network 9.3",s)
        self.assertIn("https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi",s)
    def test_public_document_review_is_not_equipment_or_source_approval(self):
        for name in ("M07-access.md","M06-protect.md","M03-firewall-vpn.md"):
            s=self.read(name)
            self.assertIn("正式審核仍待 PR #6",s)
            self.assertIn("未",s)
if __name__=="__main__":unittest.main()
