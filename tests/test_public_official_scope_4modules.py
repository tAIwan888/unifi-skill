from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PublicOfficialScopeTests(unittest.TestCase):
 def read(self,mid):
  names={"M02":"M02-networks.md","M04":"M04-wifi.md",
         "M05":"M05-switch.md","M09":"M09-backup-security.md"}
  return (ROOT/"modules"/names[mid]).read_text(encoding="utf8")
 def test_third_party_gateway_and_vlan_magic_limitations(self):
  s=self.read("M02")
  for term in ("Third-party Gateway","USW Flex Mini","ECS Aggregation",
               "不支援","https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs"):
   self.assertIn(term,s)
 def test_wifi_ppsk_and_6ghz_are_not_misrepresented(self):
  s=self.read("M04")
  for term in ("PPSK","WPA2","WPA3","OWE","6 GHz","MLO",
               "https://help.ui.com/hc/en-us/articles/32065480092951-UniFi-WiFi-SSID-and-AP-Settings-Overview"):
   self.assertIn(term,s)
 def test_switch_multicast_per_firmware_not_assumed(self):
  s=self.read("M05")
  for term in ("IGMP Snooping","mDNS","7.2+","224.0.0.0/24",
               "https://help.ui.com/hc/en-us/articles/33402927617047-UniFi-Switch-Settings"):
   self.assertIn(term,s)
 def test_backup_settings_not_equivalent_to_recordings(self):
  s=self.read("M09")
  for term in ("System Config Backup","Network-only Backup","UniFi OS 3.1",
               "既有 Protect Recordings 不能直接","永久刪除",
               "https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi"):
   self.assertIn(term,s)
 def test_every_section_remains_unreviewed_by_source_gate(self):
  for mid in ("M02","M04","M05","M09"):
   s=self.read(mid)
   self.assertIn("正式審核待 PR #6",s)
   self.assertNotIn("LAB_VERIFIED",s)
if __name__=="__main__":unittest.main()
