import importlib.util
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("official_developer",ROOT/"scripts/check_official_updates.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BASE="https://developer.ui.com/network/v10.6.106/ai-gettingstarted.md"

class Headers:
    def __init__(self,type_="text/markdown"):self.type_=type_
    def get_content_type(self):return self.type_

class Response:
    def __init__(self,raw,ctype="text/markdown"):self.raw=raw;self.headers=Headers(ctype)
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,cap):return self.raw[:cap]

class Opener:
    def __init__(self,raw=None,ctype="text/markdown",robots_status=None):
        self.raw=raw if raw is not None else (
            "# UniFi Network API\n\nThis official Network API guide covers "
            "authentication, local application integration, versioned endpoints "
            "and examples for UniFi Network deployments. "*9
        ).encode()
        self.ctype=ctype;self.robots_status=robots_status;self.urls=[]
    def open(self,req,timeout=0):
        self.urls.append(req.full_url)
        if req.full_url.endswith("/robots.txt"):
            if self.robots_status is not None:
                raise HTTPError(req.full_url,self.robots_status,"robots unavailable",{},None)
            return Response(b"User-agent: *\nAllow: /\n",ctype="text/plain")
        return Response(self.raw,self.ctype)

def entry(url=BASE):
    return {"id":"network_api","url":url,"kind":"developer_markdown","modules":["M10"]}

class DeveloperMarkdownTests(unittest.TestCase):
    def test_version_bound_markdown_and_no_raw_content_evidence(self):
        o=Opener()
        evidence={}
        with patch.object(mod,"_robot_ok") as policy:
            raw=mod.fetch_official_developer_markdown(entry(),o,metadata=evidence)
            policy.assert_called_once()
        self.assertIn("Network API",mod.normalize(raw))
        self.assertEqual(evidence["api_family"],"network")
        self.assertEqual(evidence["doc_version"],"10.6.106")
        self.assertEqual(evidence["version_scope"],"PINNED_DOCUMENT_NOT_LATEST")
        self.assertNotIn("body",evidence)
        self.assertEqual(evidence["fetch_method"],"PUBLIC_OFFICIAL_VERSIONED_DEVELOPER_MARKDOWN")

    def test_no_arbitrary_domains_versions_or_markup(self):
        urls=[
            "http://developer.ui.com/network/v10.6.106/ai-gettingstarted.md",
            "https://developer.ui.com.evil.test/network/v10.6.106/ai-gettingstarted.md",
            "https://developer.ui.com/network/latest/ai-gettingstarted.md",
            "https://developer.ui.com/network/v10.6.106/ai-gettingstarted.md?token=secret",
            "https://developer.ui.com/network/v10.6.106/hidden.md",
        ]
        for url in urls:
            with self.subTest(url=url),self.assertRaises(ValueError):
                mod.fetch_official_developer_markdown(entry(url),Opener())

    def test_reject_wrong_product_empty_content_and_types(self):
        for o in [
            Opener(raw=b"An unrelated file"),
            Opener(raw=b"UniFi Protect is not UniFi Network. "*25),
            Opener(ctype="text/html"),
            Opener(raw=b"\xff"*750),
        ]:
            with self.subTest(ctype=o.ctype),self.assertRaises(ValueError):
                with patch.object(mod,"_robot_ok"):
                    mod.fetch_official_developer_markdown(entry(),o)

    def test_missing_robots_404_permitted_but_403_429_5xx_blocked(self):
        url=BASE
        try:
            mod._ROBOTS_CACHE.clear()
            allowed=Opener(robots_status=404)
            mod._robot_ok(url,allowed)
            self.assertIsNone(mod._ROBOTS_CACHE.get("developer.ui.com"))
            self.assertEqual(len(allowed.urls),1)
            for code in (403,429,500):
                mod._ROBOTS_CACHE.clear()
                with self.subTest(code=code),self.assertRaises(HTTPError):
                    mod._robot_ok(url,Opener(robots_status=code))
        finally:mod._ROBOTS_CACHE.clear()

    def test_present_disallow_robots_is_enforced(self):
        class Denied(Opener):
            def open(self,req,timeout=0):
                return Response(b"User-agent: *\nDisallow: /\n",ctype="text/plain")
        try:
            mod._ROBOTS_CACHE.clear()
            with self.assertRaisesRegex(ValueError,"robots_disallowed"):
                mod._robot_ok(BASE,Denied())
        finally:mod._ROBOTS_CACHE.clear()

if __name__=="__main__":unittest.main()
