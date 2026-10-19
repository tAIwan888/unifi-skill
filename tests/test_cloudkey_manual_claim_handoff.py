"""Synthetic and offline only; never infer review status."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts import handoff_cloudkey_manual_claims as mod

URL_A = "https://community.ui.com/releases/UniFi-OS-Cloud-Keys-6-0-11/57843ee1-a7e5-4166-a416-f3b460effb8c"
URL_B = "https://community.ui.com/releases/UniFi-OS-Cloud-Keys-5-1-11/7c1b7350-df16-412a-8b51-b4764f467c33"

def report():
    rows = [{
        "title": "UniFi OS - Cloud Keys " + version,
        "version": version, "source_url": url,
        "product_scope": "CURRENT_UNIFI_OS_CLOUD_KEYS",
        "publication_date": "2026-10-18T15:30:00+00:00",
        "verification": "CANDIDATE_UNREVIEWED",
        "release_channel": "UNKNOWN_NOT_VALIDATED_FROM_RSS",
    } for version, url in (("6.0.11", URL_A), ("5.1.11", URL_B))]
    r = {
        "status": "OFFICIAL_HOSTED_RSS_PROBE_NOT_APPROVED",
        "transport": "LIVE_ANONYMOUS_HTTPS",
        "rss_url": mod.RSS, "count": 2, "current_os_cloud_keys_pointer_count": 2,
        "human_reviewed": False, "is_global_release_source": False,
        "complete_current_cloudkey_coverage_verified": False,
        "candidates": rows,
    }
    r["digest_sha256"] = mod.canonical_digest(rows)
    return r

def fill(x):
    x["asserted_release_channel"] = "Release Candidate"
    x["checked_on"] = "2026-10-19"
    x["short_evidence_excerpt"] = "Synthetic example only: human asserts RC, not verified by this program."

class Handoff(unittest.TestCase):
    def test_template_all_fields_explicitly_incomplete(self):
        t = mod.make_template(report())
        self.assertFalse(t["human_reviewed"])
        self.assertEqual(len(t["rows"]), 2)
        self.assertEqual({r["asserted_release_channel"] for r in t["rows"]}, {None})
        self.assertEqual({r["checked_on"] for r in t["rows"]}, {None})
        self.assertEqual({r["short_evidence_excerpt"] for r in t["rows"]}, {""})

    def test_completed_claims_remain_unreviewed(self):
        r = report()
        t = mod.make_template(r)
        fill(t["rows"][0])
        t["rows"] = t["rows"][:1]
        output = mod.import_completed(r, t)
        self.assertFalse(output["independent_vendor_fetch"])
        self.assertFalse(output["independent_human_review_completed"])
        self.assertEqual(output["rss_digest_sha256"], r["digest_sha256"])
        self.assertEqual(output["candidates"][0]["channel_verified"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(output["candidates"][0]["review_status"], "UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE")

    def test_unfilled_template_is_not_acceptable(self):
        r = report()
        with self.assertRaises(ValueError):
            mod.import_completed(r, mod.make_template(r))

    def test_digest_scope_and_url_tampering(self):
        for key, val in (("source_url", URL_B), ("product_scope", "UNIFI_GLOBAL"),
                         ("version", "9.9.9"), ("release_channel", "Official"),
                         ("verification", "REVIEWED")):
            r = report()
            r["candidates"][0][key] = val
            r["digest_sha256"] = mod.canonical_digest(r["candidates"])
            with self.subTest(key=key), self.assertRaises(ValueError):
                mod.make_template(r)

    def test_wrong_digest_no_trust(self):
        r = report()
        r["candidates"][0]["title"] = "Changed"
        with self.assertRaisesRegex(ValueError, "rss_digest_mismatch"):
            mod.make_template(r)

    def test_claim_identity_must_match_snapshot(self):
        for field,value in (("version","4.0.0"), ("official_release_url",URL_A),
                            ("product","UniFi OS - Server"),
                            ("rss_publication_date","2020-01-01")):
            r = report()
            t = mod.make_template(r)
            fill(t["rows"][0])
            t["rows"] = t["rows"][:1]
            t["rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.import_completed(r,t)

    def test_untrusted_submission_and_duplicates(self):
        r = report()
        t = mod.make_template(r)
        fill(t["rows"][0])
        t["rows"] = t["rows"][:1]
        for key,value in (("rss_digest_sha256","0"*64), ("human_reviewed", True)):
            bad = {**t, key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):
                mod.import_completed(r,bad)
        with self.assertRaises(ValueError):
            mod.import_completed(r,{**t,"rows":t["rows"]*2})

    def test_unsafe_extra_fields_rejected(self):
        r = report()
        t = mod.make_template(r)
        fill(t["rows"][0])
        t["rows"] = t["rows"][:1]
        t["rows"][0]["approved"] = True
        with self.assertRaises(ValueError):
            mod.import_completed(r,t)

    def test_cli_is_offline_and_outputs_safe_status(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"rss.json").write_text(json.dumps(report()),encoding="utf-8")
            self.assertEqual(mod.main(["--rss-report",str(root/"rss.json"),
                                       "--mode","template","--output",str(root/"template.json")]),0)
            claims=json.loads((root/"template.json").read_text())
            fill(claims["rows"][0])
            claims["rows"] = claims["rows"][:1]
            (root/"filled.json").write_text(json.dumps(claims),encoding="utf-8")
            self.assertEqual(mod.main(["--rss-report",str(root/"rss.json"),"--mode","intake",
                                       "--completed",str(root/"filled.json"),
                                       "--output",str(root/"claims.json")]),0)
            out=json.loads((root/"claims.json").read_text())
            self.assertEqual(out["candidates"][0]["review_status"],"UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE")

if __name__ == "__main__":
    unittest.main()
