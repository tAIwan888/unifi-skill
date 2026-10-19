"""Offline contract tests for non-promoting Cloud Key review queue."""
import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from scripts import export_cloudkey_review_packet as export
from scripts import probe_cloudkey_legacy_rss as rss
from scripts import probe_cloudkey_release_pages as posts

def report():
    entries = "".join(
        "<item><title>UniFi OS - Cloud Keys " + version + "</title><link>"
        + url + "</link><pubDate>Mon, 19 Oct 2026 03:00:00 GMT</pubDate></item>"
        for version,url in posts.TARGETS
    )
    data = rss.parse_feed(("<rss version='2.0'><channel>" + entries + "</channel></rss>").encode())
    data["transport"] = "LIVE_ANONYMOUS_HTTPS"
    return data

def sample(data):
    return {
        "status": "SAMPLED_POST_VISIBILITY_RESEARCH_NOT_APPROVED",
        "source_rss_digest_sha256": data["digest_sha256"],
        "human_reviewed": False, "is_global_release_source": False,
        "complete_current_cloudkey_coverage_verified": False,
        "release_channels_verified": False, "model_compatibility_verified": False,
        "download_authenticity_verified": False, "sample_count": 2,
        "posts": [
            {"version": version, "source_url": url,
             "post_status": "JS_SHELL_OR_INSUFFICIENT_VISIBLE_CONTENT",
             "release_channel": "UNKNOWN_NOT_VALIDATED_FROM_RSS",
             "device_model_scope": "NOT_VERIFIED", "verification": "CANDIDATE_UNREVIEWED"}
            for version,url in posts.TARGETS
        ]
    }

def renew_sha(data):
    data["digest_sha256"] = hashlib.sha256(
        json.dumps(data["candidates"], separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()

class ReviewQueue(unittest.TestCase):
    def test_live_evidence_exports_undecided_queue_only(self):
        data = report()
        result = export.build_packet(data, sample(data))
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["human_approvals"], 0)
        self.assertEqual(result["global_release_coverage"], "NOT_VERIFIED")
        self.assertTrue(all(r["review_status"] == "CANDIDATE_UNREVIEWED" for r in result["candidates"]))
        self.assertTrue(all(r["channel_review"] == "PENDING" for r in result["candidates"]))
        self.assertEqual(len(list(csv.DictReader(io.StringIO(export.render_csv(result))))), 2)
        self.assertIn(data["digest_sha256"], export.render_md(result))

    def test_missing_sample_remains_unsampled(self):
        self.assertEqual({x["sampled_html_status"] for x in export.build_packet(report())["candidates"]},
                         {"NOT_SAMPLED"})

    def test_tampered_digest_and_rss_url_fail_closed(self):
        data = report()
        data["candidates"][0]["version"] = "9.9.9"
        with self.assertRaisesRegex(ValueError, "rss_digest_mismatch"):
            export.build_packet(data)
        data = report()
        data["rss_url"] = "https://other.example/"
        with self.assertRaisesRegex(ValueError, "rss_source_mismatch"):
            export.build_packet(data)

    def test_promotion_even_with_updated_digest_is_blocked(self):
        for field,value in (("release_channel", "Official"),
                            ("verification", "APPROVED"),
                            ("product_scope", "UNIFI_GLOBAL"),
                            ("source_url", "https://evil.example/releases/a")):
            data = report()
            data["candidates"][0][field] = value
            renew_sha(data)
            with self.subTest(field=field), self.assertRaises(ValueError):
                export.build_packet(data)

    def test_post_digest_and_approval_flags_blocked(self):
        data = report()
        for change in ("digest", "approved", "html"):
            content = sample(data)
            if change == "digest":
                content["source_rss_digest_sha256"] = "0" * 64
            elif change == "approved":
                content["release_channels_verified"] = True
            else:
                content["posts"][0]["release_channel"] = "Official"
            with self.subTest(change=change), self.assertRaises(ValueError):
                export.build_packet(data, content)

    def test_bad_report_creates_no_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "invalid.json").write_text("{}", encoding="utf-8")
            rc = export.main(["--input-report", str(root / "invalid.json"),
                              "--output-dir", str(root / "out")])
            self.assertEqual(rc, 2)
            self.assertFalse((root / "out").exists())

    def test_cli_renders_offline_csv_and_md(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = report()
            (root / "report.json").write_text(json.dumps(data), encoding="utf-8")
            (root / "sample.json").write_text(json.dumps(sample(data)), encoding="utf-8")
            rc = export.main(["--input-report", str(root / "report.json"),
                              "--post-sample", str(root / "sample.json"),
                              "--output-dir", str(root / "output")])
            self.assertEqual(rc, 0)
            self.assertTrue((root / "output/cloudkey-review-queue.csv").is_file())
            self.assertTrue((root / "output/cloudkey-review-handoff.md").is_file())

if __name__ == "__main__":
    unittest.main()
