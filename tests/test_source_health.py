import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("monitor_v06",ROOT/"scripts/check_official_updates.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def html_fixture(body):
    return ("<html><main>"+body+"</main></html>").encode()

class SourceHealthTests(unittest.TestCase):
    def test_reject_release_landing_page_without_version(self):
        s="UniFi downloads and products. "+("Find releases here. "*18)
        with self.assertRaisesRegex(ValueError,"no_verifiable_release_entries"):
            mod.validate_content({"kind":"release_index"},mod.normalize(html_fixture(s)))

    def test_accept_release_page_with_product_and_semver(self):
        text=mod.normalize(html_fixture("UniFi Network Application 10.6.106 for macOS. "+"Release Notes and Download. "*14))
        self.assertEqual(mod.validate_content({"kind":"release_index","url":"https://www.ui.com/download/unifi"},text),text)

    def test_error_classification(self):
        self.assertEqual(mod.error_code(HTTPError("https://help.ui.com",403,"Forbidden",{},None)),"HTTP_403")
        self.assertEqual(mod.error_code(ValueError("no_verifiable_release_entries")),"NO_VERIFIABLE_RELEASE_ENTRIES")
        self.assertEqual(mod.error_code(ValueError("no secrets here")),"FETCH_ERROR")

    def test_https_allowlist_redirect_rejection(self):
        for s in ["http://www.ui.com/download/unifi","https://www.ui.com:8443/download/unifi",
                  "https://evil.example/download","https://guest:secret@www.ui.com/download/unifi",
                  "https://www.ui.com/download/unifi#fragment"]:
            with self.subTest(url=s):
                with self.assertRaises(ValueError): mod.allowed_url(s)

    def test_observed_digest_unchanged_after_network_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"sync").mkdir()
            path=root/"sync/sources.json"
            path.write_text(json.dumps({"sources":[
                {"id":"doc1","url":"https://help.ui.com/hc/en-us/articles/test","modules":["M01"],"kind":"help_article"}
            ]}))
            old=mod.ROOT
            try:
                mod.ROOT=root
                text=html_fixture("Documentation details with validated content. "*15)
                self.assertEqual(mod.run(fetcher=lambda e:text),0)
                observed=json.loads((root/"sync/observed.json").read_text())
                digest=observed["sources"]["doc1"]["sha256"]
                self.assertEqual(mod.run(fetcher=lambda e: (_ for _ in ()).throw(HTTPError(e["url"],403,"",{},None))),2)
                after=json.loads((root/"sync/observed.json").read_text())
                self.assertEqual(after["sources"]["doc1"]["sha256"],digest)
                health=json.loads((root/"sync/health.json").read_text())
                self.assertEqual(health["freshness"],"DEGRADED")
                self.assertEqual(health["results"][0]["detail"],"HTTP_403")
                pending=json.loads((root/"sync/pending.json").read_text())
                self.assertIn("doc1",pending["changes"])
            finally:
                mod.ROOT=old

    def test_source_renamed_url_must_reverify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"sync").mkdir()
            filename=root/"sync/sources.json"
            filename.write_text(json.dumps({"sources":[
                {"id":"source","url":"https://www.ui.com/download/unifi","modules":["M09"],"kind":"release_index"}
            ]}))
            old=mod.ROOT
            try:
                mod.ROOT=root
                good=html_fixture(("UniFi Network Application 10.6.106 for macOS. "*9))
                self.assertEqual(mod.run(fetcher=lambda e:good),0)
                filename.write_text(json.dumps({"sources":[
                    {"id":"source","url":"https://www.ui.com/download/utilities/","modules":["M09"],"kind":"release_index"}
                ]}))
                self.assertEqual(mod.run(fetcher=lambda e:good),0)
                pending=json.loads((root/"sync/pending.json").read_text())["changes"]["source"]
                self.assertEqual(pending["previous_sha256"],None)
                self.assertEqual(pending["status"],"REVIEW_REQUIRED")
            finally:
                mod.ROOT=old

if __name__=="__main__":
    unittest.main()
