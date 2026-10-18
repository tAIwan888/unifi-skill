import importlib.util
from pathlib import Path
from urllib import request, robotparser
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("source_redirect",ROOT/"scripts/check_official_updates.py")
monitor=importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

class SameHostRedirectSafety(unittest.TestCase):
    def setUp(self):
        monitor._ROBOTS_CACHE.clear()
        # A previously robots-checked source with an absent robots.txt.
        monitor._ROBOTS_CACHE["help.ui.com"]=None
        self.handler=monitor.SafeRedirect()

    def tearDown(self):
        monitor._ROBOTS_CACHE.clear()

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

    def test_same_host_redirect_must_respect_destination_robots_path(self):
        policy=robotparser.RobotFileParser()
        policy.parse(["User-agent: *","Disallow: /private","Allow: /public"])
        monitor._ROBOTS_CACHE["help.ui.com"]=policy
        src="https://help.ui.com/public/article"
        with self.assertRaisesRegex(ValueError,"robots_disallowed_redirect"):
            self.redirect(src,"https://help.ui.com/private/secret")
        allowed=self.redirect(src,"https://help.ui.com/public/updated")
        self.assertEqual(allowed.full_url,"https://help.ui.com/public/updated")

    def test_document_redirect_without_prior_robots_check_fails(self):
        del monitor._ROBOTS_CACHE["help.ui.com"]
        with self.assertRaisesRegex(ValueError,"redirect_without_checked_robots"):
            self.redirect("https://help.ui.com/public/article",
                          "https://help.ui.com/public/updated")

    def test_same_host_robots_resource_can_redirect_before_its_rules_load(self):
        monitor._ROBOTS_CACHE.clear()
        req=self.redirect("https://help.ui.com/robots.txt",
                          "https://help.ui.com/static/robots.txt")
        self.assertEqual(req.full_url,"https://help.ui.com/static/robots.txt")

    def test_cross_host_redirect_is_categorized_not_approved(self):
        for category in ("cross_host_redirect_disallowed",
                         "redirect_without_checked_robots",
                         "robots_disallowed_redirect"):
            self.assertEqual(monitor.error_code(ValueError(category)),category.upper())

if __name__=="__main__":unittest.main()
