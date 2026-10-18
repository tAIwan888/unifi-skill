import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("help_api",ROOT/"scripts/check_official_updates.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ARTICLE_ID = 7605005245975
CANONICAL = "https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates"

def example_article(**changes):
    obj={
        "id": ARTICLE_ID,"locale":"en-us","draft":False,"title":"UniFi Updates",
        "updated_at":"2026-09-01T00:00:00Z",
        "body":"<h2>Managing UniFi Updates</h2><p>"+("These are public technical support instructions about application upgrades. "*9)+"</p>",
    }
    obj.update(changes)
    return {"article":obj}

class FakeHeaders:
    def __init__(self,ctype="application/json"):self.ctype=ctype
    def get_content_type(self):return self.ctype

class Response:
    def __init__(self,data,ctype="application/json"):
        self.data=data
        self.headers=FakeHeaders(ctype)
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.data[:n]

class FakeOpener:
    def __init__(self,obj=None,ctype="application/json",raw=None):
        self.obj=example_article() if obj is None else obj
        self.ctype=ctype
        self.raw=raw
        self.urls=[]
    def open(self,req,timeout=0):
        self.urls.append(req.full_url)
        raw=self.raw if self.raw is not None else json.dumps(self.obj).encode()
        return Response(raw,self.ctype)

def entry(url=CANONICAL):
    return {"id":"unifi_updates","url":url,"kind":"help_article","modules":["M01","M09"]}

class OfficialPublicHelpAPITests(unittest.TestCase):
    def read(self,obj=None,**kwargs):
        opener=FakeOpener(obj,**kwargs)
        with patch.object(mod,"_robot_ok") as robot:
            content=mod.fetch_public_help_article(entry(),opener)
            robot.assert_called_once()
        self.assertEqual(opener.urls,[
            "https://help.ui.com/api/v2/help_center/en-us/articles/7605005245975.json"
        ])
        return mod.normalize(content)

    def test_public_article_is_canonical_and_not_page_shell(self):
        text=self.read()
        self.assertIn("UniFi Updates",text)
        self.assertIn("Managing UniFi Updates",text)
        self.assertNotIn("<script>",text)
        self.assertGreater(len(text),200)

    def test_evidence_contains_public_version_context_without_full_text(self):
        evidence={}
        obj=example_article()
        with patch.object(mod,"_robot_ok"):
            result=mod.fetch_public_help_article(entry(),FakeOpener(obj),metadata=evidence)
        self.assertIn(b"UniFi Updates",result)
        self.assertEqual(evidence["article_id"],ARTICLE_ID)
        self.assertEqual(evidence["title"],"UniFi Updates")
        self.assertEqual(evidence["vendor_updated_at"],"2026-09-01T00:00:00Z")
        self.assertEqual(evidence["fetch_method"],"PUBLIC_ANONYMOUS_HELP_CENTER_API")
        self.assertGreater(evidence["body_word_count"],25)
        self.assertNotIn("body",evidence)
        self.assertNotIn("script",evidence)

    def test_metadata_update_without_content_does_not_change_digest(self):
        before=self.read(example_article(updated_at="2026-09-01T00:00:00Z"))
        after=self.read(example_article(updated_at="2026-10-18T10:00:00Z"))
        self.assertEqual(before,after)

    def test_reject_article_id_mismatch_unpublished_locale_and_body(self):
        cases=[
            example_article(id=ARTICLE_ID+1),
            example_article(draft=True),
            example_article(locale="fr"),
            example_article(title=""),
            example_article(body=""),
            {"not_article":{}}
        ]
        for obj in cases:
            with self.subTest(item=obj),self.assertRaises(ValueError):
                self.read(obj)

    def test_reject_invalid_json_and_content_type(self):
        for kwargs in [{"raw":b"not-json"},{"ctype":"text/html"}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                self.read(**kwargs)

    def test_reject_mismatched_domain_and_article_path(self):
        for url in [
            "https://evil.example/hc/en-us/articles/7605005245975-UniFi-Updates",
            "http://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates",
            "https://help.ui.com/hc/en-us/articles/banana",
            "https://help.ui.com/hc/en-us/articles/7605005245975?preview=true",
            "https://help.ui.com/hc/fr/articles/7605005245975",
        ]:
            with self.subTest(url=url),self.assertRaises(ValueError):
                mod.fetch_public_help_article(entry(url),FakeOpener())

    def test_disallowed_robots_prevents_article_request(self):
        opener=FakeOpener()
        with patch.object(mod,"_robot_ok",side_effect=ValueError("robots_disallowed")),self.assertRaisesRegex(ValueError,"robots_disallowed"):
            mod.fetch_public_help_article(entry(),opener)
        self.assertFalse(opener.urls)

if __name__=="__main__":
    unittest.main()
