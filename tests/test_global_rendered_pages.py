"""Offline-only parser and authorization tests."""
import unittest
from unittest.mock import patch
from scripts import probe_global_rendered_pages as x

class RenderProbeTests(unittest.TestCase):
    def test_javascript_shell_never_approved(self):
        d=x.classify("<html><script>UniFi OS Server 5.1.42;UniFi OS - Cloud Keys 6.0.11</script><body>Loading Ubiquiti Community</body></html>")
        self.assertEqual(d["candidate_phrase_count"],0)
        self.assertEqual(d["status"],"NO_VERIFIABLE_RENDERED_VERSION_LIST")
    def test_visible_product_versions_remain_unreviewed(self):
        d=x.classify("<h2>UniFi Network Application 10.6.106</h2><h3>UniFi OS - Cloud Keys 6.0.11</h3>Official")
        self.assertEqual(d["candidate_phrase_count"],2)
        self.assertEqual(d["status"],"RENDERED_PARTIAL_VERSION_POINTERS_UNREVIEWED")
        self.assertFalse(d["release_channel_verified"])
        self.assertFalse(d["global_coverage_verified"])
        self.assertFalse(d["downloads_verified"])
    def test_large_content_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid_dom_size"):
            x.classify("a"*(x.MAX_HTML+1))
    def test_robots_disallow_prevents_browser_execution(self):
        with patch.object(x.monitor,"_robot_ok",side_effect=ValueError("robots_disallowed")),patch.object(x.subprocess,"run") as runner:
            with self.assertRaisesRegex(ValueError,"robots_disallowed"):
                x.inspect("official_releases","chrome")
            runner.assert_not_called()

if __name__=="__main__":
    unittest.main()
