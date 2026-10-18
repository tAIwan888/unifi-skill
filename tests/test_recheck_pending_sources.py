import hashlib,importlib.util,json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("recheck",ROOT/"scripts/recheck_pending_sources.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
URL="https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates"
BODY=("<html><main>"+"This is official public UniFi Updates guidance on application upgrades and release safety. "*12+"</main></html>").encode()
def setup(root):
    (root/"sync").mkdir()
    text=mod.monitor.validate_content({"id":"unifi_updates","kind":"help_article"},mod.monitor.normalize(BODY))
    digest=hashlib.sha256(text.encode("utf8")).hexdigest()
    files={
        "sources.json":{"sources":[{"id":"unifi_updates","url":URL,"kind":"help_article","modules":["M01","M09"]}]},
        "observed.json":{"sources":{"unifi_updates":{"url":URL,"sha256":digest}}},
        "pending.json":{"changes":{"unifi_updates":{"url":URL,"current_sha256":digest,
                    "modules":["M01","M09"],"status":"REVIEW_REQUIRED"}}},
        "reviewed.json":{"reviews":{}}
    }
    for name,obj in files.items():(root/"sync"/name).write_text(json.dumps(obj),encoding="utf8")
    return (root/"sync/sources.json",root/"sync/observed.json",root/"sync/pending.json")
class RecheckTests(unittest.TestCase):
    def test_matching_sha_still_requires_human_review(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths=setup(root)
            old=(root/"sync/reviewed.json").read_bytes()
            result=mod.audit(*paths,fetcher=lambda entry,meta:BODY)
            self.assertEqual(result["summary"]["MATCHES_PENDING"],1)
            self.assertEqual(result["review_status"],"INDEPENDENT_HUMAN_REVIEW_REQUIRED")
            self.assertEqual(old,(root/"sync/reviewed.json").read_bytes())
            self.assertIn("不等於已審核",mod.markdown(result))
    def test_drift_must_not_auto_accept(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths=setup(root)
            newer=BODY.replace(b"official",b"updated")
            result=mod.audit(*paths,fetcher=lambda entry,meta:newer)
            self.assertEqual(result["summary"]["DRIFT_REQUIRES_REVIEW"],1)
            self.assertTrue((root/"sync/pending.json").is_file())
    def test_http_unavailable_is_not_matching(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths=setup(root)
            def fail(entry,meta):raise HTTPError(URL,403,"Forbidden",{},None)
            result=mod.audit(*paths,fetcher=fail)
            self.assertEqual(result["summary"]["UNAVAILABLE_NOT_REVIEWED"],1)
            self.assertEqual(result["rows"][0]["error_code"],"HTTP_403")
    def test_reject_tampered_url_digest_or_status(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths=setup(root)
            p=root/"sync/pending.json";original=p.read_text()
            for key,value in (("url","https://evil.test/a"),("current_sha256","c"*64),
                              ("status","APPROVED"),("modules",["M02"])):
                item=json.loads(original);item["changes"]["unifi_updates"][key]=value
                p.write_text(json.dumps(item))
                with self.subTest(field=key),self.assertRaisesRegex(ValueError,"inconsistent_pending_evidence"):
                    mod.audit(*paths,fetcher=lambda e,m:BODY)
    def test_no_full_vendor_document_copied_to_report(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths=setup(root)
            result=mod.audit(*paths,fetcher=lambda entry,meta:BODY)
            md=mod.markdown(result)
            self.assertNotIn("This is official public UniFi Updates",md)
            self.assertIn("unifi_updates",md)
if __name__=="__main__":unittest.main()
