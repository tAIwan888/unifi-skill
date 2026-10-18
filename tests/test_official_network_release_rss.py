import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rss_monitor",ROOT/"scripts/check_official_updates.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

FEED=mod.NETWORK_RELEASE_RSS_URL
def rss_item(version="10.6.106",url="https://community.ui.com/releases/UniFi-Network-Application-10-6-106/f206c01d-3f73-471b-b4a5-2da48f157ea6",category="unifi-network"):
    return ("<item><title>UniFi Network Application "+version+"</title>"
            "<link>"+url+"</link><pubDate>Thu, 10 Sep 2026 13:54:24 GMT</pubDate>"
            "<category>"+category+"</category></item>").encode()

def rss(items=None):
    if items is None:
        items=[rss_item(),rss_item(version="11.0.83",url="https://community.ui.com/releases/UniFi-Network-Application-11-0-83/d6940379-cd5a-4e61-8596-7e22d647a4ea")]
    return b'<?xml version="1.0"?><rss version="2.0"><channel><title>Network</title>'+b"".join(items)+b'</channel></rss>'

class Response:
    def __init__(self,data,ctype="application/xml"):
        self.data=data
        self.headers=type("Headers",(),{"get_content_type":lambda self:ctype})()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,limit):return self.data[:limit]

class Opener:
    def __init__(self,data=None,ctype="application/xml"):self.data=rss() if data is None else data;self.ctype=ctype
    def open(self,req,timeout=0):return Response(self.data,self.ctype)

def entry(url=FEED):
    return {"id":"network_application_release_rss","url":url,"kind":"release_rss","modules":["M02","M10"]}

class OfficialRSSMonitor(unittest.TestCase):
    def read(self,raw=None,ctype="application/xml"):
        out={}
        with patch.object(mod,"_robot_ok"):
            contents=mod.fetch_network_release_rss(entry(),Opener(raw,ctype),out)
        return mod.normalize(contents),out

    def test_valid_feed_yields_scoped_unreviewed_candidates(self):
        content,evidence=self.read()
        self.assertIn("UniFi Network Application 10.6.106",content)
        self.assertEqual(evidence["candidate_count"],2)
        self.assertEqual(evidence["product_scope"],"UNIFI_NETWORK_APPLICATION_ONLY")
        self.assertEqual(evidence["channel_scope"],"CHANNEL_UNVERIFIED_MANUAL_REVIEW_REQUIRED")
        self.assertEqual({x["version"] for x in evidence["release_candidates"]},{"10.6.106","11.0.83"})
        self.assertTrue(all(x["release_channel"]=="UNKNOWN_NOT_VALIDATED_FROM_RSS" for x in evidence["release_candidates"]))
        self.assertTrue(all(x["verification"]=="CANDIDATE_UNREVIEWED" for x in evidence["release_candidates"]))
        self.assertEqual(mod.validate_content(entry(),content),content)

    def test_reject_spoofed_feed_and_unsafe_release_link(self):
        with patch.object(mod,"_robot_ok"):
            for value in [FEED+"?x=1","http://community.ui.com/rss/releases/x",
                          "https://community.ui.com.evil.test/rss/releases/x"]:
                with self.subTest(value=value),self.assertRaises(ValueError):
                    mod.fetch_network_release_rss(entry(value),Opener())
            fake=rss([rss_item(url="https://not-ui.com/releases/a/b")])
            with self.assertRaisesRegex(ValueError,"untrusted_release_item_url"):
                mod.fetch_network_release_rss(entry(),Opener(fake))

    def test_category_excluded_and_duplicate_rejected(self):
        with patch.object(mod,"_robot_ok"):
            with self.assertRaisesRegex(ValueError,"release_rss_no_scoped_product_entries"):
                mod.fetch_network_release_rss(entry(),Opener(rss([rss_item(category="security")])))
            with self.assertRaisesRegex(ValueError,"duplicate_release_item"):
                mod.fetch_network_release_rss(entry(),Opener(rss([rss_item(),rss_item()])))

    def test_reject_html_xml_entity_and_empty_rss(self):
        with patch.object(mod,"_robot_ok"):
            for raw in [b"not-xml",b'<!DOCTYPE rss><rss><channel></channel></rss>',
                        b'<rss><channel></channel></rss>']:
                with self.subTest(raw=raw),self.assertRaises(ValueError):
                    mod.fetch_network_release_rss(entry(),Opener(raw))
            with self.assertRaisesRegex(ValueError,"unexpected_content_type"):
                mod.fetch_network_release_rss(entry(),Opener(ctype="text/html"))

    def test_rss_metadata_not_raw_copied_and_manifest_scope(self):
        content,evidence=self.read()
        self.assertNotIn("<item>",content)
        self.assertNotIn("Official",json.dumps(evidence))
        source=json.loads((ROOT/"sync/sources.json").read_text())
        entries=[s for s in source["sources"] if s["id"]=="network_application_release_rss"]
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]["kind"],"release_rss")
        self.assertEqual(entries[0]["modules"],["M02","M10"])
        manifest=json.loads((ROOT/"manifest.json").read_text())
        self.assertEqual(manifest["source_count"],len(source["sources"]))
if __name__=="__main__":unittest.main()
