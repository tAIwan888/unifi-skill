"""Offline synthetic fixtures only, no vendor network requests."""
import importlib.util
import io
import sys
import unittest
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cloudkey_probe", ROOT/"scripts"/"probe_cloudkey_legacy_rss.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
URL = "https://community.ui.com/releases/UniFi-OS-Cloud-Keys-6-0-11/57843ee1-a7e5-4166-a416-f3b460effb8c"
OLD = "https://community.ui.com/releases/UniFi-Cloud-Key-Firmware-1-1-19/7e6b3ea9-4c4e-42e7-b73a-fd615bc058d3"
DATE = "Thu, 15 Oct 2026 09:00:00 GMT"

def doc(*entries):
    return ('<?xml version="1.0"?><rss version="2.0"><channel><title>UniFi Cloud Key Firmware</title>' + ''.join(
        f'<item><title>{t}</title><link>{url}</link><pubDate>{date}</pubDate></item>' for t,url,date in entries
        )+'</channel></rss>').encode()

class Resp:
    def __init__(self, body, mime):
        self.headers = Message()
        self.headers['Content-Type'] = mime
        self.stream = io.BytesIO(body)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.stream.read(n)

class Opener:
    def __init__(self, *, robots=b'User-agent: *\nAllow: /rss/releases/\n', robots_code=200, mime='application/xml'):
        self.robots, self.robots_code, self.mime = robots, robots_code, mime
        self.urls=[]
    def open(self, req, timeout=18):
        self.urls.append(req.full_url)
        if req.full_url == mod.ROBOTS:
            if self.robots_code != 200:
                raise HTTPError(req.full_url, self.robots_code, 'robots', {}, None)
            return Resp(self.robots, 'text/plain')
        if req.full_url == mod.RSS:
            return Resp(doc(('UniFi OS - Cloud Keys 6.0.11', URL, DATE)), self.mime)
        raise AssertionError('Unexpected request '+req.full_url)

class Probe(unittest.TestCase):
    def test_current_match_remains_unreviewed(self):
        r=mod.parse_feed(doc(('UniFi OS - Cloud Keys 6.0.11', URL, DATE)))
        self.assertEqual(r['current_os_cloud_keys_pointer_count'],1)
        self.assertFalse(r['legacy_only'])
        self.assertFalse(r['human_reviewed'])
        self.assertFalse(r['complete_current_cloudkey_coverage_verified'])
        self.assertEqual(r['candidates'][0]['release_channel'],'UNKNOWN_NOT_VALIDATED_FROM_RSS')
    def test_legacy_rss_cannot_be_called_current_os_coverage(self):
        r=mod.parse_feed(doc(('UniFi Cloud Key Firmware 1.1.19',OLD,DATE)))
        self.assertTrue(r['legacy_only'])
        self.assertEqual(r['current_os_cloud_keys_pointer_count'],0)
    def test_mixed_feed_does_not_imply_global_coverage(self):
        x=doc(('UniFi OS - Cloud Keys 6.0.11', URL, DATE),('Unrelated Product 5.0.1', OLD, DATE))
        r=mod.parse_feed(x)
        self.assertEqual(r['ignored_nonmatching_items'],1)
        self.assertFalse(r['is_global_release_source'])
    def test_no_matching_titles_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'no_cloudkey_items'):
            mod.parse_feed(doc(('UniFi Talk Application 5.4.5',URL,DATE)))
    def test_untrusted_sources_blocked(self):
        for url in (URL.replace('https:', 'http:'),URL.replace('community.ui.com','evil.example'),URL+'?x=1',URL.replace('Cloud-Keys','Cloud-Keys@evil.test')):
            with self.subTest(url=url), self.assertRaises(ValueError):
                mod.parse_feed(doc(('UniFi OS - Cloud Keys 6.0.11', url, DATE)))
    def test_xml_entities_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'xml_entities_forbidden'):
            mod.parse_feed(b'<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///etc/passwd">]>'+doc(('UniFi OS - Cloud Keys 6.0.11', URL, DATE)))
    def test_duplicates_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'duplicate_release_post'):
            mod.parse_feed(doc(('UniFi OS - Cloud Keys 6.0.11', URL, DATE),('UniFi OS - Cloud Keys 6.0.11', URL, DATE)))
    def test_release_url_title_product_and_version_must_match(self):
        for bad in (
            URL.replace('UniFi-OS-Cloud-Keys-6-0-11', 'UniFi-OS-Dream-Machines-6-0-11'),
            URL.replace('UniFi-OS-Cloud-Keys-6-0-11', 'UniFi-OS-Cloud-Keys-5-1-33'),
        ):
            with self.subTest(url=bad):
                with self.assertRaisesRegex(ValueError, 'release_slug_title_mismatch'):
                    mod.parse_feed(doc(('UniFi OS - Cloud Keys 6.0.11', bad, DATE)))

    def test_invalid_date_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'invalid_date'):
            mod.parse_feed(doc(('UniFi OS - Cloud Keys 6.0.11', URL, 'invalid')))
    def test_only_exact_vendor_urls_robots_required(self):
        op=Opener()
        self.assertEqual(mod.live_read(op)['count'],1)
        self.assertEqual(op.urls,[mod.ROBOTS,mod.RSS])
        with self.assertRaisesRegex(ValueError,'robots_denied'):
            mod.live_read(Opener(robots=b'User-agent: *\nDisallow: /rss/\n'))
    def test_robots_error_and_content_type_fail_closed(self):
        for code in (403, 404):
            with self.subTest(code=code):
                with self.assertRaisesRegex(ValueError,'robots_unavailable'):
                    mod.live_read(Opener(robots_code=code))
        with self.assertRaisesRegex(ValueError,'unexpected_mime'):
            mod.live_read(Opener(mime='text/html'))
    def test_redirects_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'redirect_forbidden'):
            mod.BlockRedirect().redirect_request(None,None,302,'go',{},'https://evil.test')
    def test_no_write_approval_or_device_credentials(self):
        text=(ROOT/'scripts/probe_cloudkey_legacy_rss.py').read_text()
        for name in ('approve_official_update.py','sync/reviewed.json','git push','git commit','Authorization:', 'X-API-Key'):
            self.assertNotIn(name,text)

if __name__=='__main__': unittest.main()
