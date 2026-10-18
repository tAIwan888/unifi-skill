import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("triage",ROOT/"scripts/build_review_triage.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

URL="https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs"
DIGEST="a"*64

def make_repo(tmp, citation=True):
    root=Path(tmp)
    (root/"sync").mkdir()
    (root/"modules").mkdir()
    (root/"modules/M02-networks.md").write_text("# M02\n"+(URL if citation else "missing source")+"\n",encoding="utf-8")
    def dump(file,obj):
        (root/"sync"/file).write_text(json.dumps(obj),encoding="utf-8")
    dump("sources.json",{"sources":[{"id":"vlan","url":URL,"modules":["M02"],"kind":"help_article"}]})
    dump("pending.json",{"changes":{"vlan":{"current_sha256":DIGEST,"url":URL,
         "modules":["M02"],"status":"REVIEW_REQUIRED","public_source_evidence":{
             "fetch_method":"PUBLIC_ANONYMOUS_HELP_CENTER_API",
             "title":"VLANs | <script>alert('x')</script>","body_word_count":400}}}})
    dump("observed.json",{"sources":{"vlan":{"sha256":DIGEST,"url":URL}}})
    dump("health.json",{"monitored":1,"healthy":1,"failed":0,"freshness":"SOURCES_RETRIEVED_UNREVIEWED",
                         "results":[{"id":"vlan","status":"FIRST_SEEN","detail":"OK"}]})
    dump("reviewed.json",{"reviews":{}})
    return root

class TriageTests(unittest.TestCase):
    def test_ref_citation_found_does_not_auto_approve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=make_repo(tmp)
            before=(root/"sync/reviewed.json").read_bytes()
            report=module.build(root)
            self.assertIn("待審來源：**1**",report)
            self.assertIn("M02: 引用存在／未審核",report)
            self.assertIn("&lt;script&gt;",report)
            self.assertNotIn("<script>",report)
            self.assertEqual(before,(root/"sync/reviewed.json").read_bytes())
            self.assertEqual(module.build(root),report)
    def test_missing_citation_flagged_without_adding_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=make_repo(tmp,citation=False)
            report=module.build(root)
            self.assertIn("M02: 缺少精確引用",report)
            self.assertEqual((root/"modules/M02-networks.md").read_text(),"# M02\nmissing source\n")
    def test_reject_tampered_digest_or_untrusted_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=make_repo(tmp)
            filename=root/"sync/pending.json"
            value=json.loads(filename.read_text())
            value["changes"]["vlan"]["current_sha256"]="b"*64
            filename.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,"pending_observed_mismatch"):
                module.build(root)
            value["changes"]["vlan"]["current_sha256"]=DIGEST
            value["changes"]["vlan"]["url"]="https://help.ui.com.evil.example/attack"
            filename.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,"invalid_source_url"):
                module.build(root)
    def test_reject_auto_approved_pending_and_misassigned_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=make_repo(tmp)
            filename=root/"sync/pending.json"
            obj=json.loads(filename.read_text())
            obj["changes"]["vlan"]["status"]="REVIEWED"
            filename.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,"pending_not_review_required"):
                module.build(root)
            obj["changes"]["vlan"]["status"]="REVIEW_REQUIRED"
            obj["changes"]["vlan"]["modules"]=["M03"]
            filename.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,"module_mapping_mismatch"):
                module.build(root)
    def test_empty_main_without_health_report_is_not_claimed_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=make_repo(tmp)
            (root/"sync/health.json").unlink()
            (root/"sync/pending.json").write_text('{"changes":{}}')
            report=module.build(root)
            self.assertIn("NO_HEALTH_REPORT_ON_MAIN",report)
            self.assertIn("待審來源：**0**",report)
    def test_block_unrecognised_health_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=make_repo(tmp)
            path=root/"sync/health.json"
            h=json.loads(path.read_text())
            h["results"]=[{"id":"spoofed","status":"ERROR","detail":"FETCH_ERROR"}]
            path.write_text(json.dumps(h))
            with self.assertRaisesRegex(ValueError,"health_unknown_source"):
                module.build(root)

if __name__=="__main__":unittest.main()
