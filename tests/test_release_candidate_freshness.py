import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_freshness",ROOT/"scripts/check_official_updates.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
RSS_ID="network_application_release_rss"
RSS_URL=mod.NETWORK_RELEASE_RSS_URL
INDEX_ID="official_releases"
INDEX_URL="https://community.ui.com/releases?view=latest"
DIGEST="b"*64

def html():
    return b"<html><main>"+(b"UniFi Network Application 10.7.123 publicly announced for the Network product. "*12)+b"</main></html>"

def source(root,kind="release_rss"):
    s={"id":RSS_ID,"url":RSS_URL,"kind":"release_rss","modules":["M02"]} if kind=="release_rss" else {
        "id":INDEX_ID,"url":INDEX_URL,"kind":"release_index","modules":["M01"]}
    (root/"sync").mkdir()
    (root/"sync/sources.json").write_text(json.dumps({"sources":[s]}))
    return s

def read(root,name):
    return json.loads((root/"sync"/name).read_text())

class CandidateFreshnessTests(unittest.TestCase):
    def test_rss_success_outage_recovery_and_prior_observed_digest(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); source(root)
            orig=mod.ROOT
            mod.ROOT=root
            def success(entry,opener,metadata=None):
                metadata.update({"fetch_method":"OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS",
                                 "release_candidates":[{
                                    "version":"10.7.123","release_channel":"UNKNOWN_NOT_VALIDATED_FROM_RSS",
                                    "verification":"CANDIDATE_UNREVIEWED",
                                    "source_url":"https://community.ui.com/releases/UniFi-Network-Application-10-7-123/ffffffff-ffff-4fff-8fff-ffffffffffff"
                                 }]})
                return html()
            try:
                with patch.object(mod,"fetch_network_release_rss",side_effect=success):
                    self.assertEqual(mod.run(),0)
                before=read(root,"observed.json")["sources"][RSS_ID]["sha256"]
                active=read(root,"version-candidates.json")["sources"][RSS_ID]
                self.assertEqual(active["source_status"],"VALIDATED_THIS_RUN")
                self.assertEqual(len(active["candidates"]),1)
                with patch.object(mod,"fetch_network_release_rss",side_effect=HTTPError(RSS_URL,503,"Unavailable",{},None)):
                    self.assertEqual(mod.run(),2)
                stale=read(root,"version-candidates.json")["sources"][RSS_ID]
                self.assertEqual(stale["source_status"],"UNAVAILABLE_THIS_RUN")
                self.assertEqual(stale["review_status"],"NO_CURRENT_VERIFIABLE_CANDIDATES")
                self.assertEqual(stale["failure_code"],"HTTP_503")
                self.assertEqual(stale["candidates"],[])
                self.assertEqual(stale["last_successful_sha256"],before)
                self.assertEqual(stale["last_successful_candidate_count"],1)
                self.assertEqual(read(root,"health.json")["unavailable_release_candidate_sources"],[RSS_ID])
                self.assertEqual(read(root,"observed.json")["sources"][RSS_ID]["sha256"],before)
                self.assertIn(RSS_ID,read(root,"pending.json")["changes"])
                with patch.object(mod,"fetch_network_release_rss",side_effect=success):
                    self.assertEqual(mod.run(),0)
                recovered=read(root,"version-candidates.json")["sources"][RSS_ID]
                self.assertEqual(recovered["source_status"],"VALIDATED_THIS_RUN")
                self.assertEqual(len(recovered["candidates"]),1)
                self.assertNotIn("last_successful_sha256",recovered)
                self.assertEqual(read(root,"health.json")["unavailable_release_candidate_sources"],[])
            finally:
                mod.ROOT=orig

    def test_release_index_failure_clears_old_candidates(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);source(root,kind="release_index")
            (root/"sync/version-candidates.json").write_text(json.dumps({
                "schema_version":1,"sources":{
                    INDEX_ID:{"source_url":INDEX_URL,"source_sha256":DIGEST,
                              "review_status":"CANDIDATES_NOT_VERIFIED",
                              "source_status":"VALIDATED_THIS_RUN",
                              "candidates":[{"version":"10.2.100","verification":"CANDIDATE_UNREVIEWED"}]}
                }}))
            old=mod.ROOT;mod.ROOT=root
            try:
                with patch.object(mod,"fetch",side_effect=HTTPError(INDEX_URL,403,"Forbidden",{},None)):
                    self.assertEqual(mod.run(),2)
                result=read(root,"version-candidates.json")["sources"][INDEX_ID]
                self.assertEqual(result["candidates"],[])
                self.assertEqual(result["last_successful_candidate_count"],1)
                self.assertEqual(result["last_successful_sha256"],DIGEST)
                self.assertEqual(result["failure_code"],"HTTP_403")
            finally:mod.ROOT=old

    def test_release_rss_without_verified_structured_candidates_fails(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);source(root)
            old=mod.ROOT;mod.ROOT=root
            try:
                # A syntactically plausible HTML fixture must not pass as
                # a structured official RSS release source.
                with patch.object(mod,"fetch_network_release_rss",return_value=html()):
                    self.assertEqual(mod.run(),2)
                row=read(root,"version-candidates.json")["sources"][RSS_ID]
                self.assertEqual(row["failure_code"],"RELEASE_RSS_MISSING_STRUCTURED_CANDIDATES")
                self.assertEqual(row["candidates"],[])
                self.assertNotIn(RSS_ID,read(root,"observed.json")["sources"])
            finally:mod.ROOT=old

    def test_repeated_failed_runs_keep_only_history_counts_not_versions(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);source(root)
            (root/"sync/version-candidates.json").write_text(json.dumps({
                "schema_version":1,"sources":{
                    RSS_ID:{"source_url":RSS_URL,"source_sha256":DIGEST,"candidates":[{"version":"11.0.83"}]}
                }}))
            old=mod.ROOT;mod.ROOT=root
            try:
                with patch.object(mod,"fetch_network_release_rss",side_effect=HTTPError(RSS_URL,404,"Not found",{},None)):
                    self.assertEqual(mod.run(),2)
                    self.assertEqual(mod.run(),2)
                row=read(root,"version-candidates.json")["sources"][RSS_ID]
                self.assertEqual(row["last_successful_candidate_count"],1)
                self.assertEqual(row["last_successful_sha256"],DIGEST)
                self.assertEqual(row["candidates"],[])
            finally:mod.ROOT=old

if __name__=="__main__":unittest.main()
