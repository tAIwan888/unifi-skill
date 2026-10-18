import importlib.util
import json
from xml.sax.saxutils import escape
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("multiproduct",ROOT/"scripts/check_official_updates.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
LINK="https://community.ui.com/releases/Official-Product-7-3-70/7853e377-dc73-4c41-9278-8174f252e3d2"
CASES={
 "protect_application_release_rss":("UniFi Protect Application 7.3.70","unifi-protect","UNIFI_PROTECT_APPLICATION_ONLY"),
 "os_server_release_rss":("UniFi OS Server 5.1.42","unifi-network","UNIFI_OS_SERVER_ONLY"),
 "dream_machines_release_rss":("UniFi OS - Dream Machines 5.1.33","unifi-gateway-cloudkey","UNIFI_OS_DREAM_MACHINES_ONLY"),
 "wifi_firmware_release_rss":("UniFi Access Point & Wireless Bridge 8.8.11","unifi-wireless","UNIFI_AP_WIRELESS_FIRMWARE_ONLY"),
 "switch_firmware_release_rss":("UniFi Switch 7.5.15","unifi-switching","UNIFI_SWITCH_FIRMWARE_ONLY")
}
def item(title,category,url=LINK):
    return ("<item><title>"+escape(title)+"</title><category>"+escape(category)+"</category><link>"+escape(url)+
            "</link><pubDate>Fri, 02 Oct 2026 12:31:01 GMT</pubDate></item>").encode()
def xml(*items):
    return b'<rss version="2.0"><channel>'+b"".join(items)+b'</channel></rss>'
class Response:
    def __init__(self,body,ctype="application/xml"):
        self.body=body;self.headers=type("Headers",(),{"get_content_type":lambda self:ctype})()
    def read(self,n):return self.body[:n]
    def __enter__(self):return self
    def __exit__(self,*args):return False
class Opener:
    def __init__(self,body,ctype="application/xml"):self.body=body;self.ctype=ctype
    def open(self,req,timeout=0):return Response(self.body,self.ctype)
def entry(key):
    return {"id":key,"kind":"release_rss","url":mod.RELEASE_RSS_SPECS[key]["url"]}
def parse(key,title,category):
    metadata={}
    with patch.object(mod,"_robot_ok"):
        body=mod.fetch_network_release_rss(entry(key),Opener(xml(item(title,category))),metadata)
    return body,metadata
class MultiProductOfficialRSS(unittest.TestCase):
    def test_each_verified_vendor_product_has_versioned_unreviewed_candidate(self):
        for key,(title,category,scope) in CASES.items():
            with self.subTest(key=key):
                content,metadata=parse(key,title,category)
                result=metadata["release_candidates"]
                self.assertEqual(len(result),1)
                self.assertEqual(metadata["product_scope"],scope)
                self.assertEqual(metadata["channel_scope"],"CHANNEL_UNVERIFIED_MANUAL_REVIEW_REQUIRED")
                self.assertEqual(result[0]["verification"],"CANDIDATE_UNREVIEWED")
                self.assertEqual(result[0]["release_channel"],"UNKNOWN_NOT_VALIDATED_FROM_RSS")
                self.assertEqual(result[0]["version"],title.split()[-1])
                self.assertIn(result[0]["product_label"].encode(),content)
    def test_category_and_title_must_both_match(self):
        for key,(title,category,_) in CASES.items():
            with patch.object(mod,"_robot_ok"),self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,"release_rss_no_scoped_product_entries"):
                    mod.fetch_network_release_rss(entry(key),Opener(xml(item(title,"security"))))
                with self.assertRaisesRegex(ValueError,"release_rss_no_scoped_product_entries"):
                    mod.fetch_network_release_rss(entry(key),Opener(xml(item("Unrelated hardware 1.2.3",category))))
    def test_mixed_ap_switch_category_does_not_double_count(self):
        src=entry("wifi_firmware_release_rss")
        both=xml(item("UniFi Switch 7.5.15","unifi-switching"),
                 item("UniFi Access Point & Wireless Bridge 8.8.11","unifi-wireless",
                      "https://community.ui.com/releases/UniFi-AP-8-8-11/0e8c3ef9-9ed4-4f11-a2a5-95e9dd7cf9c1"))
        meta={}
        with patch.object(mod,"_robot_ok"):
            mod.fetch_network_release_rss(src,Opener(both),meta)
        self.assertEqual(len(meta["release_candidates"]),1)
        self.assertEqual(meta["release_candidates"][0]["version"],"8.8.11")
    def test_safe_rss_link_and_exact_vendor_feed_url_enforced(self):
        key="protect_application_release_rss"
        with patch.object(mod,"_robot_ok"):
            src=entry(key);src["url"]="https://community.ui.com/rss/releases/Protect/random-feed"
            with self.assertRaisesRegex(ValueError,"invalid_release_rss_url"):
                mod.fetch_network_release_rss(src,Opener(xml(item(*CASES[key][:2]))))
            for url in ["https://fake-community.ui.com/releases/fake/123",
                        "http://community.ui.com/releases/UniFi/7853e377-dc73-4c41-9278-8174f252e3d2",
                        "https://community.ui.com/releases/UniFi/7853e377-dc73-4c41-9278-8174f252e3d2?x=1"]:
                with self.subTest(url=url),self.assertRaisesRegex(ValueError,"untrusted_release_item_url"):
                    mod.fetch_network_release_rss(entry(key),Opener(xml(item("UniFi Protect Application 7.3.70","unifi-protect",url))))
    def test_all_new_sources_are_catalogued_with_correct_module_scope(self):
        j=json.loads((ROOT/"sync/sources.json").read_text())
        byid={x["id"]:x for x in j["sources"]}
        self.assertEqual(len(byid),30)
        expected={"protect_application_release_rss":["M06","M10"],
                  "os_server_release_rss":["M01","M09","M10"],
                  "dream_machines_release_rss":["M01","M09"],
                  "wifi_firmware_release_rss":["M04"],
                  "switch_firmware_release_rss":["M05"]}
        for key,modules in expected.items():
            self.assertEqual(byid[key]["modules"],modules)
            self.assertEqual(byid[key]["url"],mod.RELEASE_RSS_SPECS[key]["url"])
            self.assertEqual(byid[key]["kind"],"release_rss")
            self.assertEqual(byid[key]["channel_policy"],"UNKNOWN_REQUIRES_MANUAL_VERIFICATION")
        self.assertEqual(json.loads((ROOT/"manifest.json").read_text())["source_count"],len(byid))
if __name__=="__main__":unittest.main()
