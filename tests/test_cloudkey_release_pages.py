"""Offline synthetic samples: no HTTP traffic or channel approvals."""
import io
import hashlib
import json
import unittest
from email.message import Message
from urllib.error import HTTPError

from scripts import probe_cloudkey_release_pages as pages


class Response:
    def __init__(self, payload, kind):
        self.headers = Message()
        self.headers["Content-Type"] = kind
        self.stream = io.BytesIO(payload)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, amount): return self.stream.read(amount)


class Opener:
    def __init__(self, robots=b"User-agent: *\nAllow: /releases/\n", robots_error=None,
                 shell=False, post_error=None, mime="text/html"):
        self.robots = robots
        self.robots_error = robots_error
        self.shell = shell
        self.post_error = post_error
        self.mime = mime
        self.visited = []
    def open(self, req, timeout=18):
        self.visited.append(req.full_url)
        if req.full_url == pages.base.ROBOTS:
            if self.robots_error:
                raise HTTPError(req.full_url, self.robots_error, "robots", {}, None)
            return Response(self.robots, "text/plain")
        if req.full_url in dict((url, version) for version, url in pages.TARGETS):
            if self.post_error:
                raise HTTPError(req.full_url, self.post_error, "post", {}, None)
            ver = dict((url, version) for version, url in pages.TARGETS)[req.full_url]
            html = ("<html><script>UniFi OS - Cloud Keys %s Overview</script>Loading Ubiquiti Community</html>" % ver
                    if self.shell else
                    "<html><title>CloudKeys</title><main><h1>UniFi OS - Cloud Keys %s</h1>"
                    "<h2>Overview</h2><p>%s</p></main></html>" % (ver, "Example public body text " * 24))
            return Response(html.encode(), self.mime)
        raise AssertionError("Unexpected URL: " + req.full_url)


def feed():
    observed = {
        "status": "OFFICIAL_HOSTED_RSS_PROBE_NOT_APPROVED", "transport": "LIVE_ANONYMOUS_HTTPS",
        "human_reviewed": False, "is_global_release_source": False,
        "complete_current_cloudkey_coverage_verified": False,
        "candidates": [
            {"version": ver, "title": f"UniFi OS - Cloud Keys {ver}", "source_url": url,
             "product_scope": "CURRENT_UNIFI_OS_CLOUD_KEYS", "verification": "CANDIDATE_UNREVIEWED",
             "release_channel": "UNKNOWN_NOT_VALIDATED_FROM_RSS"}
            for ver, url in pages.TARGETS
        ],
    }
    observed["count"] = len(observed["candidates"])
    observed["current_os_cloud_keys_pointer_count"] = len(observed["candidates"])
    observed["digest_sha256"] = hashlib.sha256(json.dumps(
        observed["candidates"], separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()
    return observed


class DirectPosts(unittest.TestCase):
    def test_visible_public_html_never_upgrades_channel_or_model(self):
        opener = Opener()
        r = pages.inspect(feed(), opener)
        self.assertEqual(r["robots_policy"], "READABLE_AND_APPLIED")
        self.assertEqual(len(r["posts"]), 2)
        self.assertEqual(len(opener.visited), 3)
        self.assertTrue(all(x["post_status"] == "VISIBLE_POST_BODY_UNREVIEWED" for x in r["posts"]))
        self.assertTrue(all(x["release_channel"] == "UNKNOWN_NOT_VALIDATED_FROM_RSS" for x in r["posts"]))
        self.assertTrue(all(x["verification"] == "CANDIDATE_UNREVIEWED" for x in r["posts"]))
        self.assertFalse(r["release_channels_verified"])
        self.assertFalse(r["model_compatibility_verified"])
        self.assertFalse(r["human_reviewed"])
        self.assertFalse(r["complete_current_cloudkey_coverage_verified"])

    def test_javascript_shell_is_not_accepted_as_visible_post(self):
        r = pages.inspect(feed(), Opener(shell=True))
        self.assertEqual([x["post_status"] for x in r["posts"]],
                         ["JS_SHELL_OR_INSUFFICIENT_VISIBLE_CONTENT"] * 2)

    def test_disallowed_robots_never_requests_posts(self):
        op = Opener(robots=b"User-agent: *\nDisallow: /releases/\n")
        r = pages.inspect(feed(), op)
        self.assertEqual(op.visited, [pages.base.ROBOTS])
        self.assertEqual([x["post_status"] for x in r["posts"]], ["ROBOTS_DISALLOWED"] * 2)

    def test_robots_failure_even_404_is_fail_closed(self):
        for error_code in (403, 404):
            with self.subTest(error=error_code):
                op = Opener(robots_error=error_code)
                r = pages.inspect(feed(), op)
                self.assertEqual(op.visited, [pages.base.ROBOTS])
                self.assertEqual(r["robots_policy"], "UNAVAILABLE_FAIL_CLOSED")
                self.assertEqual([x["post_status"] for x in r["posts"]], ["ROBOTS_POLICY_UNAVAILABLE"] * 2)

    def test_pinned_pointer_drift_stops_unapproved_requests(self):
        f = feed()
        f["candidates"][0]["source_url"] += "?drift"
        f["digest_sha256"] = hashlib.sha256(json.dumps(
            f["candidates"], separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()
        op = Opener()
        r = pages.inspect(f, op)
        self.assertEqual(r["posts"][0]["post_status"], "PINNED_RSS_POINTER_ABSENT_OR_DRIFTED")
        self.assertNotIn(pages.TARGETS[0][1], op.visited)

    def test_blocked_http_and_unexpected_mime_never_promote(self):
        for opener in (Opener(post_error=403), Opener(mime="text/plain")):
            with self.subTest(opener=opener):
                r = pages.inspect(feed(), opener)
                self.assertEqual([x["post_status"] for x in r["posts"]], ["POST_FETCH_UNAVAILABLE"] * 2)
                self.assertFalse(r["release_channels_verified"])

    def test_digest_mismatch_never_fetches_posts(self):
        bad = feed()
        bad["candidates"][0]["title"] = "UniFi OS - Cloud Keys 5.1.33"
        op = Opener()
        with self.assertRaisesRegex(ValueError, "rss_digest_mismatch"):
            pages.inspect(bad, op)
        self.assertEqual(op.visited, [])

    def test_count_or_duplicate_pointer_drift_is_rejected(self):
        for mutate in (
            lambda x: x.update(count=999),
            lambda x: x.update(current_os_cloud_keys_pointer_count=999),
            lambda x: x["candidates"][1].update(source_url=x["candidates"][0]["source_url"]),
        ):
            with self.subTest(mutate=mutate):
                bad = feed()
                mutate(bad)
                bad["digest_sha256"] = hashlib.sha256(json.dumps(
                    bad["candidates"], separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()
                op = Opener()
                with self.assertRaisesRegex(ValueError, "rss_candidate_counts_invalid"):
                    pages.inspect(bad, op)
                self.assertEqual(op.visited, [])

    def test_untrusted_input_does_not_do_network(self):
        for broken in (None, {}, dict(feed(), transport="UNTRUSTED_LOCAL_FIXTURE"),
                       dict(feed(), human_reviewed=True), dict(feed(), digest_sha256="short")):
            with self.subTest(broken=broken):
                op = Opener()
                with self.assertRaises(ValueError):
                    pages.inspect(broken, op)
                self.assertEqual(op.visited, [])


if __name__ == "__main__":
    unittest.main()
