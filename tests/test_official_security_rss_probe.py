"""Synthetic-only testing: real Runner fetch is still required, never faked."""
import importlib.util
import io
import sys
import unittest
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("probe_official_security_rss", ROOT / "scripts" / "probe_official_security_rss.py")
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)
LINK = "https://community.ui.com/releases/Security-Advisory-Bulletin-069-069/07e367a7-edec-4d85-a058-f97e5ce9ac9c"


def sample(*, title="Security Advisory Bulletin 069", link=LINK,
           date="Tue, 22 Sep 2026 12:00:00 GMT", channel="Security | Releases"):
    return (f'<?xml version="1.0"?><rss version="2.0"><channel><title>{channel}</title>'
            f'<item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate>'
            f'<category>security</category></item></channel></rss>').encode()


class Response:
    def __init__(self, text, mime):
        self.raw = io.BytesIO(text)
        self.headers = Message()
        self.headers["Content-Type"] = mime

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, count): return self.raw.read(count)


class FakeOpener:
    def __init__(self, *, robots=b"User-agent: *\nAllow: /rss/releases/\n", xml=None,
                 robots_status=200, xml_type="application/xml"):
        self.robots = robots
        self.xml = xml or sample()
        self.robots_status = robots_status
        self.xml_type = xml_type
        self.requests = []

    def open(self, req, timeout):
        self.requests.append(req.full_url)
        if req.full_url == probe.ROBOTS_URL:
            if self.robots_status != 200:
                raise HTTPError(req.full_url, self.robots_status, "robots-status", {}, None)
            return Response(self.robots, "text/plain")
        if req.full_url == probe.FEED_URL:
            return Response(self.xml, self.xml_type)
        raise AssertionError(f"Unexpected network target {req.full_url}")


class SecurityRSSProbeContract(unittest.TestCase):
    def test_synthetic_official_advisory_never_promoted(self):
        got = probe.validate_feed(sample())
        self.assertEqual(got["count"], 1)
        self.assertEqual(got["advisories"][0]["advisory_id"], "069")
        self.assertFalse(got["is_global_release_source"])
        self.assertFalse(got["human_reviewed"])
        self.assertEqual(got["advisories"][0]["release_channel"], "UNKNOWN_NOT_VALIDATED_FROM_RSS")
        self.assertRegex(got["source_digest_sha256"], "^[0-9a-f]{64}$")

    def test_exact_https_origin_and_slug_required(self):
        for bad in (LINK.replace("https:", "http:"), LINK.replace("community.ui.com", "evil.test"),
                    LINK + "?tracking=true", LINK.replace("Security-Advisory", "Other-Advisory"),
                    LINK.replace("community.ui.com", "community.ui.com@evil.test")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                probe.validate_feed(sample(link=bad))

    def test_invalid_item_and_wrong_channel_blocked(self):
        for xml in (sample(title="UniFi OS - Dream Machines 5.1.33"), sample(channel="WiFi Releases"),
                    sample(date="not a date"), sample(date="Tue, 22 Sep 2026 12:00:00")):
            with self.subTest(xml=xml[:80]), self.assertRaises(ValueError):
                probe.validate_feed(xml)

    def test_duplicate_titles_or_link_fail_closed(self):
        # Use a second identical item, regardless of its textual ordering.
        item = sample().split(b"<item>")[1].split(b"</item>")[0]
        xml = sample().replace(b"</channel>", b"<item>" + item + b"</item></channel>")
        with self.assertRaisesRegex(ValueError, "duplicate_advisory"):
            probe.validate_feed(xml)

    def test_xml_doctype_and_entity_fail_closed(self):
        raw = b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>' + sample()
        with self.assertRaisesRegex(ValueError, "xml_entity_or_doctype_forbidden"):
            probe.validate_feed(raw)

    def test_robots_allow_only_exact_urls(self):
        mock = FakeOpener()
        out = probe.fetch_feed(mock)
        self.assertEqual(out["count"], 1)
        self.assertEqual(mock.requests, [probe.ROBOTS_URL, probe.FEED_URL])

    def test_robots_disallow_or_http_403_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "robots_disallowed"):
            probe.fetch_feed(FakeOpener(robots=b"User-agent: *\nDisallow: /rss/\n"))
        with self.assertRaisesRegex(ValueError, "robots_unavailable_or_denied"):
            probe.fetch_feed(FakeOpener(robots_status=403))

    def test_only_404_robots_may_be_unavailable(self):
        ok = probe.fetch_feed(FakeOpener(robots_status=404))
        self.assertEqual(ok["count"], 1)
        with self.assertRaisesRegex(ValueError, "robots_unavailable_or_denied"):
            probe.fetch_feed(FakeOpener(robots_status=503))

    def test_wrong_content_type_and_length_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unexpected_content_type"):
            probe.fetch_feed(FakeOpener(xml_type="text/html"))
        with self.assertRaisesRegex(ValueError, "invalid_or_oversize_xml"):
            probe.validate_feed(sample()+b" "*probe.MAX_BYTES)

    def test_no_redirects_and_no_credentials_or_mutation(self):
        handler = probe.RejectRedirects()
        with self.assertRaisesRegex(ValueError, "redirect_not_approved"):
            handler.redirect_request(None, None, 302, "Found", {}, "https://attacker.test/")
        source=(ROOT / "scripts" / "probe_official_security_rss.py").read_text("utf-8")
        for forbidden in ("git push", "git commit", "approve_official_update.py", "sync/reviewed.json", "Authorization:", "X-API-Key"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__": unittest.main()
