import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime,timezone
import unittest

ROOT=Path(__file__).resolve().parents[1]
URL="https://help.ui.com/hc/en-us/articles/360012192813-Introduction-to-UniFi"
DIGEST="a"*64
SOURCE="platform_intro"

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/(name+".py"))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
review=load("approve_official_update")
gate=load("check_review_gate")

def fixture(root):
    (root/"sync").mkdir()
    (root/"modules").mkdir()
    files={
      "sources.json":{"sources":[{"id":SOURCE,"url":URL,"modules":["M01"],"kind":"help_article"}]},
      "pending.json":{"changes":{SOURCE:{"url":URL,"current_sha256":DIGEST,"modules":["M01"],"status":"REVIEW_REQUIRED"}}},
      "observed.json":{"sources":{SOURCE:{"sha256":DIGEST,"url":URL}}},
      "reviewed.json":{"reviews":{}},
    }
    for name,data in files.items():
        (root/"sync"/name).write_text(json.dumps(data))
    path=root/"modules/M01-platform.md"
    path.write_text("# Platform\n\nSource: "+URL)
    return path

def approve(root):
    return review.approve(root,SOURCE,DIGEST,"reviewer-id","Reviewed latest source updates against the public document",["modules/M01-platform.md"])

class HumanApproval(unittest.TestCase):
    def test_requires_exact_digest_and_cited_markdown(self):
        with TemporaryDirectory() as d:
            root=Path(d);fixture(root)
            self.assertTrue(gate.validate(root))
            with self.assertRaises(ValueError):
                review.approve(root,SOURCE,"b"*64,"reviewer-id","Reviewed latest source changes",["modules/M01-platform.md"])
            with self.assertRaises(ValueError):
                review.approve(root,SOURCE,DIGEST,"reviewer-id","Reviewed latest source changes",["modules/missing.md"])
            self.assertEqual(approve(root),["modules/M01-platform.md"])
            self.assertEqual(gate.validate(root),[])
            recorded=json.loads((root/"sync/reviewed.json").read_text())["reviews"][SOURCE]
            self.assertEqual(recorded["sha256"],DIGEST)
            self.assertEqual(recorded["source_url"],URL)

    def test_review_gate_rejects_mutated_identity_url_digest_and_evidence(self):
        with TemporaryDirectory() as d:
            root=Path(d);fixture(root);approve(root)
            baseline=(root/"sync/reviewed.json")
            original=json.loads(baseline.read_text())
            mutations=[
                ("sha256","b"*64,"MISSING_MATCHING_REVIEW"),
                ("source_url","https://help.ui.com/hc/en-us/articles/999","REVIEW_SOURCE_URL_MISMATCH"),
                ("reviewer","","REVIEWER_REQUIRED"),
                ("notes","tiny","REVIEW_NOTES_REQUIRED"),
                ("reviewed_at","2035-12-31T00:00:00+00:00","REVIEW_TIMESTAMP_INVALID"),
                ("evidence_files",[],"REVIEW_EVIDENCE_REQUIRED"),
                ("evidence_files",["../other.md"],"REVIEW_EVIDENCE_PATH_INVALID"),
                ("evidence_files",["modules/none.md"],"REVIEW_EVIDENCE_PATH_INVALID"),
            ]
            for field,value,code in mutations:
                with self.subTest(field=field,value=value):
                    changed=json.loads(json.dumps(original))
                    changed["reviews"][SOURCE][field]=value
                    baseline.write_text(json.dumps(changed))
                    self.assertTrue(any(code in e for e in gate.validate(root)))
            baseline.write_text(json.dumps(original))
            self.assertEqual(gate.validate(root),[])

    def test_review_gate_rejects_observation_not_registered_and_url_drift(self):
        with TemporaryDirectory() as d:
            root=Path(d);fixture(root);approve(root)
            observed_path=root/"sync/observed.json"
            obj=json.loads(observed_path.read_text())
            obj["sources"][SOURCE]["url"]="https://help.ui.com/hc/en-us/articles/999"
            observed_path.write_text(json.dumps(obj))
            self.assertTrue(any("OBSERVED_SOURCE_URL_MISMATCH" in e for e in gate.validate(root)))
            obj["sources"][SOURCE]["url"]=URL
            obj["sources"]["unknown"]={"sha256":DIGEST,"url":URL}
            observed_path.write_text(json.dumps(obj))
            self.assertTrue(any("UNREGISTERED_OBSERVED_SOURCE" in e for e in gate.validate(root)))

    def test_approval_does_not_write_when_catalog_or_evidence_tampered(self):
        with TemporaryDirectory() as d:
            root=Path(d);path=fixture(root)
            p=root/"sync/pending.json";r=root/"sync/reviewed.json"
            original_p,original_r=p.read_bytes(),r.read_bytes()
            cfg=root/"sync/sources.json"
            obj=json.loads(cfg.read_text())
            obj["sources"][0]["url"]="https://ui.com.example.test/fake"
            cfg.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):approve(root)
            self.assertEqual(p.read_bytes(),original_p)
            self.assertEqual(r.read_bytes(),original_r)
            obj["sources"][0]["url"]=URL
            cfg.write_text(json.dumps(obj))
            path.write_text("# no official citation present")
            with self.assertRaises(ValueError):approve(root)
            self.assertEqual(p.read_bytes(),original_p)
            self.assertEqual(r.read_bytes(),original_r)

    def test_review_metadata_cannot_prove_actual_human_approval(self):
        with TemporaryDirectory() as d:
            root=Path(d);fixture(root);approve(root)
            self.assertEqual(gate.validate(root),[])
            # GitHub's actual PR reviewer identity and authorization must
            # be checked by branch rules; this offline data cannot prove it.
            self.assertTrue((root/"sync/reviewed.json").is_file())

if __name__=="__main__":unittest.main()
