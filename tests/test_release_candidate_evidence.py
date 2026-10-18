import importlib.util,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("evidence",ROOT/"scripts/validate_release_candidate_evidence.py")
gate=importlib.util.module_from_spec(s);s.loader.exec_module(gate)
URL="https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe"
INDEX="https://community.ui.com/releases?view=latest"
SHA="a"*64
def setup(root):
 (root/"sync").mkdir()
 files={
 "sources.json":{"sources":[{"id":"rss","url":URL,"kind":"release_rss"},{"id":"index","url":INDEX,"kind":"release_index"}]},
 "observed.json":{"sources":{"rss":{"url":URL,"sha256":SHA}}},
 "health.json":{"monitored":2,"unavailable_release_candidate_sources":["index"],"results":[{"id":"index","status":"ERROR","detail":"UNREADABLE_OR_JS_ONLY"},{"id":"rss","status":"UNCHANGED","detail":"OK"}]},
 "version-candidates.json":{"sources":{
   "rss":{"source_url":URL,"source_sha256":SHA,"source_status":"VALIDATED_THIS_RUN",
          "review_status":"CANDIDATES_NOT_VERIFIED","candidates":[{"release_channel":"UNKNOWN_NOT_VALIDATED_FROM_RSS","verification":"CANDIDATE_UNREVIEWED"}]},
   "index":{"source_url":INDEX,"source_status":"UNAVAILABLE_THIS_RUN",
           "review_status":"NO_CURRENT_VERIFIABLE_CANDIDATES","failure_code":"UNREADABLE_OR_JS_ONLY","candidates":[]}}}
 }
 for name,obj in files.items():(root/"sync"/name).write_text(json.dumps(obj))
def mutate(root,name,fn):
 path=root/"sync"/name;d=json.loads(path.read_text());fn(d);path.write_text(json.dumps(d))
class EvidenceTests(unittest.TestCase):
 def test_valid_and_failed_candidates_are_distinguished(self):
  with TemporaryDirectory() as d:
   root=Path(d);setup(root)
   self.assertEqual(gate.validate(root),[])
 def test_failure_cannot_retain_stale_versions(self):
  with TemporaryDirectory() as d:
   root=Path(d);setup(root)
   mutate(root,"version-candidates.json",lambda x:x["sources"]["index"]["candidates"].append({"version":"99.0.0"}))
   self.assertIn("STALE_ACTIVE_CANDIDATES:index",gate.validate(root))
 def test_validated_source_must_match_observed_sha(self):
  with TemporaryDirectory() as d:
   root=Path(d);setup(root)
   mutate(root,"version-candidates.json",lambda x:x["sources"]["rss"].update(source_sha256="b"*64))
   self.assertIn("SOURCE_SHA_MISMATCH:rss",gate.validate(root))
 def test_candidate_cannot_claim_channel_or_approval(self):
  with TemporaryDirectory() as d:
   root=Path(d);setup(root)
   mutate(root,"version-candidates.json",lambda x:x["sources"]["rss"]["candidates"][0].update(release_channel="OFFICIAL",verification="APPROVED"))
   self.assertIn("UNREVIEWED_CHANNEL_REQUIRED:rss",gate.validate(root))
 def test_error_status_and_health_list_must_agree(self):
  with TemporaryDirectory() as d:
   root=Path(d);setup(root)
   mutate(root,"health.json",lambda x:x.update(unavailable_release_candidate_sources=[]))
   self.assertIn("UNAVAILABLE_LIST_MISMATCH",gate.validate(root))
 def test_unknown_release_source_must_be_rejected(self):
  with TemporaryDirectory() as d:
   root=Path(d);setup(root)
   mutate(root,"version-candidates.json",lambda x:x["sources"].update({"evil":{"candidates":[]}}))
   self.assertIn("UNREGISTERED_CANDIDATE_SOURCE:evil",gate.validate(root))
if __name__=="__main__":unittest.main()
