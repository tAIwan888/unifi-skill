import importlib.util
from pathlib import Path
from urllib import request
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("source_redirect",ROOT/"scripts/check_official_updates.py")
monitor=importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

class SameHostRedirectSafety(unittest.TestCase):
    def setUp(self):
        self.handler=monitor.SafeRedirect()

    def redirect(self,old,new):
        req=request.Request(old,headers={"User-Agent":monitor.UA})
        return self.handler.redirect_request(req,None,302,"Found",{},new)

    def test_allow_valid_same_host_redirect(self):
        old="https://help.ui.com/hc/en-us/articles/7605005245975"
        new="https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates"
        answer=self.redirect(old,new)
        self.assertIsInstance(answer,request.Request)
        self.assertEqual(answer.full_url,new)

    def test_reject_redirect_between_different_official_hosts(self):
        hosts=[
            ("https://help.ui.com/hc/en-us/articles/7605005245975",
             "https://developer.ui.com/network/v10.6.106/ai-gettingstarted.md"),
            ("https://www.ui.com/download/unifi","https://ui.com/download/unifi"),
            ("https://community.ui.com/rss/releases/UniFi-Network-Application/x",
             "https://www.ui.com/download/unifi"),
            ("https://developer.ui.com/protect/v7.3.70/ai-gettingstarted.md",
             "https://help.ui.com/hc/en-us/articles/7605005245975")
        ]
        for old,new in hosts:
            with self.subTest(old=old,new=new),self.assertRaisesRegex(ValueError,"cross_host_redirect_disallowed"):
                self.redirect(old,new)

    def test_reject_external_host_unsafe_transport_and_credentials(self):
        src="https://help.ui.com/api/v2/help_center/en-us/articles/7605005245975.json"
        urls=[
            "https://evil.example/document",
            "http://help.ui.com/document",
            "https://help.ui.com:8443/document",
            "https://person:secret@help.ui.com/document",
            "https://help.ui.com/document#fragment"
        ]
        for url in urls:
            with self.subTest(url=url),self.assertRaises(ValueError):
                self.redirect(src,url)

    def test_robots_policy_redirect_is_also_same_host(self):
        src="https://help.ui.com/robots.txt"
        with self.assertRaisesRegex(ValueError,"cross_host_redirect_disallowed"):
            self.redirect(src,"https://developer.ui.com/robots.txt")
        self.assertEqual(
            self.redirect(src,"https://help.ui.com/static/robots.txt").full_url,
            "https://help.ui.com/static/robots.txt"
        )

    def test_cross_host_redirect_is_categorized_not_approved(self):
        self.assertEqual(monitor.error_code(ValueError("cross_host_redirect_disallowed")),
                         "CROSS_HOST_REDIRECT_DISALLOWED")

if __name__=="__main__":unittest.main()
