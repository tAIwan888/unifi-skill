#!/usr/bin/env python3
"""Fail-closed, read-only probe for one historically documented official Cloud Key RSS.

Transport/content success != present-day UniFi OS Cloud Keys release coverage.
Never use these pointers as approvals, stable-channel proof or device updates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib import error, request, robotparser
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

RSS = ("https://community.ui.com/rss/releases/UniFi-Cloud-Key-Firmware/"
       "c4ccd194-4cbf-4738-b07d-0aa6f04d178e")
ROBOTS = "https://community.ui.com/robots.txt"
USER_AGENT = "UniFiSkillLegacyCloudKeyRSSProbe/0.1 (+https://github.com/tAIwan888/unifi-skill)"
MAX_RSS = 1_500_000
MAX_ROBOTS = 524_288
RELEASE_PATH = re.compile(r"/releases/(?:[A-Za-z0-9-]{2,110}/)?[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\Z")
VERSION = r"\d{1,3}(?:\.\d{1,4}){2,3}"
CURRENT = re.compile(r"UniFi OS - Cloud Keys (?P<version>" + VERSION + r")\Z")
LEGACY = re.compile(r"UniFi Cloud Key(?: Firmware)? (?P<version>" + VERSION + r")\Z")

class BlockRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_forbidden")


def official(url, *, exact=None):
    p = urlsplit(url)
    if p.scheme != "https" or p.netloc != "community.ui.com" or p.username or p.password or p.port or p.query or p.fragment:
        raise ValueError("untrusted_host_url")
    if exact and url != exact:
        raise ValueError("unexpected_url")


def response_bytes(resp, maximum, types):
    if resp.headers.get_content_type() not in types:
        raise ValueError("unexpected_mime")
    raw = resp.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("payload_too_large")
    return raw


def parse_feed(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_RSS:
        raise ValueError("invalid_rss_length")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("xml_entities_forbidden")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("invalid_xml") from exc
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("not_rss")
    posts = root.findall("./channel/item")
    if not 1 <= len(posts) <= 50:
        raise ValueError("no_or_too_many_items")
    seen = set()
    matched = []
    ignored = 0
    for item in posts:
        title = (item.findtext("title") or "").strip()
        current = CURRENT.fullmatch(title)
        legacy = LEGACY.fullmatch(title)
        if not current and not legacy:
            ignored += 1
            continue
        url = (item.findtext("link") or "").strip()
        official(url)
        release_path = urlsplit(url).path
        if not RELEASE_PATH.fullmatch(release_path):
            raise ValueError("untrusted_release_path")
        # RSS headlines alone cannot assign a Cloud Keys scope to a different
        # product or version's official release UUID. UUID-only links remain
        # permitted, since the legacy official URL format also supports them.
        path_parts = release_path.split("/")
        if len(path_parts) == 4:
            version_slug = (current or legacy).group("version").replace(".", "-")
            allowed_slugs = (
                {f"UniFi-OS-Cloud-Keys-{version_slug}"} if current else
                {f"UniFi-Cloud-Key-{version_slug}",
                 f"UniFi-Cloud-Key-Firmware-{version_slug}"}
            )
            if path_parts[2] not in allowed_slugs:
                raise ValueError("release_slug_title_mismatch")
        if url in seen:
            raise ValueError("duplicate_release_post")
        seen.add(url)
        try:
            date = parsedate_to_datetime(item.findtext("pubDate"))
        except (TypeError, ValueError, IndexError) as exc:
            raise ValueError("invalid_date") from exc
        if date is None or date.tzinfo is None or not (2020 <= date.year <= 2100):
            raise ValueError("invalid_date")
        matched.append({
            "title": title, "product_scope": "CURRENT_UNIFI_OS_CLOUD_KEYS" if current else "LEGACY_CLOUD_KEY_FIRMWARE",
            "version": (current or legacy).group("version"),
            "source_url": url, "publication_date": date.isoformat(),
            "verification": "CANDIDATE_UNREVIEWED", "release_channel": "UNKNOWN_NOT_VALIDATED_FROM_RSS",
        })
    if not matched:
        raise ValueError("no_cloudkey_items")
    matched.sort(key=lambda x: (x["source_url"], x["version"]))
    payload = json.dumps(matched, separators=(",", ":"), sort_keys=True)
    current_count = sum(x["product_scope"] == "CURRENT_UNIFI_OS_CLOUD_KEYS" for x in matched)
    return {
        "status": "OFFICIAL_HOSTED_RSS_PROBE_NOT_APPROVED",
        "rss_url": RSS, "count": len(matched), "ignored_nonmatching_items": ignored,
        "current_os_cloud_keys_pointer_count": current_count,
        "legacy_only": current_count == 0,
        "digest_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "human_reviewed": False, "is_global_release_source": False,
        "complete_current_cloudkey_coverage_verified": False,
        "candidates": matched,
    }


def live_read(opener=None):
    opener = opener or request.build_opener(BlockRedirect())
    official(RSS, exact=RSS)
    official(ROBOTS, exact=ROBOTS)
    try:
        with opener.open(request.Request(ROBOTS, headers={"User-Agent": USER_AGENT, "Accept": "text/plain"}), timeout=18) as resp:
            robots = response_bytes(resp, MAX_ROBOTS, ("text/plain", "application/octet-stream"))
        policy = robotparser.RobotFileParser()
        policy.parse(robots.decode("utf-8", "strict").splitlines())
        if not policy.can_fetch(USER_AGENT, RSS):
            raise ValueError("robots_denied")
    except error.HTTPError as exc:
        # This restricted research probe requires readable robots policy;
        # fail closed even for a 404 rather than silently skipping the check.
        raise ValueError("robots_unavailable") from exc
    with opener.open(request.Request(RSS, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml"}), timeout=18) as resp:
        data = response_bytes(resp, MAX_RSS, ("application/xml", "text/xml", "application/rss+xml"))
    return parse_feed(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-xml", type=Path, help="Read preexisting XML only; not proof of Runner availability")
    args = p.parse_args()
    try:
        value = parse_feed(args.input_xml.read_bytes()) if args.input_xml else live_read()
        value["transport"] = "UNTRUSTED_LOCAL_FIXTURE" if args.input_xml else "LIVE_ANONYMOUS_HTTPS"
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (ValueError, error.URLError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED_NOT_VALIDATED", "error_type": type(exc).__name__}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
