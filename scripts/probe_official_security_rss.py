#!/usr/bin/env python3
"""Experimental READ-ONLY probe for an official-hosted Security RSS category.

NOT a global releases reader; NOT a source approval; NOT Runner-validated.
Uses only anonymous HTTPS on the single pinned official host, with fail-closed
robots/TLS/redirect/XML/provenance rules and no controller access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from email.utils import parsedate_to_datetime
from urllib import error, request, robotparser
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

FEED_URL = (
    "https://community.ui.com/rss/releases/Security/"
    "f3f45fa2-1784-4594-b48d-28baf317b208"
)
ROBOTS_URL = "https://community.ui.com/robots.txt"
UA = "UniFiSkillSecurityAdvisoryProbe/0.1 (+https://github.com/tAIwan888/unifi-skill)"
MAX_BYTES = 1_500_000
MAX_ROBOTS = 524_288
MAX_ITEMS = 50
RELEASE_PATH = re.compile(
    r"/releases/Security-Advisory-Bulletin-[A-Za-z0-9-]{1,60}/"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z"
)
ADVISORY_TITLE = re.compile(r"Security Advisory Bulletin (?P<number>\d{2,4})\Z")


class RejectRedirects(request.HTTPRedirectHandler):
    """No redirects at all: no off-domain or unvetted robots destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_not_approved")


def _verify_url(value: str, *, exact: str | None = None) -> None:
    p = urlsplit(value)
    if (
        p.scheme != "https"
        or p.netloc != "community.ui.com"
        or p.hostname != "community.ui.com"
        or p.username is not None
        or p.password is not None
        or p.port is not None
        or p.query or p.fragment
    ):
        raise ValueError("untrusted_official_url")
    if exact is not None and value != exact:
        raise ValueError("untrusted_official_url")


def _read(response, *, max_size: int, accepted_types: tuple[str, ...]) -> bytes:
    ctype = response.headers.get_content_type()
    if ctype not in accepted_types:
        raise ValueError("unexpected_content_type")
    body = response.read(max_size + 1)
    if len(body) > max_size:
        raise ValueError("payload_too_large")
    return body


def fetch_feed(opener=None):
    """Only exact public HTTPS RSS and robots URLs are requested."""
    opener = opener or request.build_opener(RejectRedirects())
    _verify_url(FEED_URL, exact=FEED_URL)
    _verify_url(ROBOTS_URL, exact=ROBOTS_URL)

    req = request.Request(ROBOTS_URL, headers={"User-Agent": UA, "Accept": "text/plain"})
    try:
        with opener.open(req, timeout=18) as response:
            robots_bytes = _read(
                response, max_size=MAX_ROBOTS,
                accepted_types=("text/plain", "application/octet-stream"),
            )
        robots = robotparser.RobotFileParser()
        robots.parse(robots_bytes.decode("utf-8", "strict").splitlines())
        if not robots.can_fetch(UA, FEED_URL):
            raise ValueError("robots_disallowed")
    except error.HTTPError as exc:
        # RFC 9309 allows HTTP 4xx other than authorization issues to mean
        # robots unavailable; accept ONLY 404, deny 401/403/429/5xx/errors.
        if exc.code != 404:
            raise ValueError("robots_unavailable_or_denied") from exc

    req = request.Request(
        FEED_URL,
        headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml"},
    )
    with opener.open(req, timeout=18) as response:
        payload = _read(
            response, max_size=MAX_BYTES,
            accepted_types=("application/rss+xml", "application/xml", "text/xml"),
        )
    return validate_feed(payload)


def validate_feed(raw: bytes) -> dict:
    """Parse *only* security-advisory pointers; preserve UNKNOWN release channel."""
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
        raise ValueError("invalid_or_oversize_xml")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("xml_entity_or_doctype_forbidden")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("invalid_rss_xml") from exc
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("invalid_rss_format")
    channel_title = (root.findtext("channel/title") or "").strip()
    if not re.search(r"security", channel_title, re.I):
        raise ValueError("wrong_rss_channel")
    items = root.findall("./channel/item")
    if not 1 <= len(items) <= MAX_ITEMS:
        raise ValueError("empty_or_unbounded_feed")

    seen_links, seen_numbers, out = set(), set(), []
    for item in items:
        title = (item.findtext("title") or "").strip()
        m = ADVISORY_TITLE.fullmatch(title)
        if not m:
            raise ValueError("non_advisory_item_or_unexpected_title")
        num = m.group("number")
        link = (item.findtext("link") or "").strip()
        _verify_url(link)
        if not RELEASE_PATH.fullmatch(urlsplit(link).path):
            raise ValueError("untrusted_advisory_url")
        if link in seen_links or num in seen_numbers:
            raise ValueError("duplicate_advisory")
        seen_links.add(link)
        seen_numbers.add(num)
        date_str = item.findtext("pubDate")
        try:
            dt = parsedate_to_datetime(date_str) if date_str else None
        except (TypeError, ValueError, IndexError) as exc:
            raise ValueError("invalid_pubdate") from exc
        if dt is None or dt.tzinfo is None or not 2020 <= dt.year <= 2100:
            raise ValueError("invalid_pubdate")
        out.append({
            "advisory_id": num,
            "title": title,
            "source_url": link,
            "publication_date": dt.isoformat(),
            "verification": "ADVISORY_POINTER_UNREVIEWED",
            "release_channel": "UNKNOWN_NOT_VALIDATED_FROM_RSS",
        })

    out.sort(key=lambda row: row["advisory_id"])
    normalized = json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "status": "OFFICIAL_HOST_CANDIDATE_NOT_APPROVED",
        "source": FEED_URL,
        "scope": "SECURITY_ADVISORY_POINTERS_ONLY_NOT_ALL_RELEASES",
        "source_digest_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "count": len(out),
        "advisories": out,
        "is_global_release_source": False,
        "human_reviewed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-xml", help="Use an existing official RSS sample; no network requests")
    args = p.parse_args()
    try:
        if args.input_xml:
            from pathlib import Path
            report = validate_feed(Path(args.input_xml).read_bytes())
            report["transport"] = "LOCAL_UNTRUSTED_XML_INPUT_NOT_RUNNER_EVIDENCE"
        else:
            report = fetch_feed()
            report["transport"] = "LIVE_ANONYMOUS_HTTPS_ROBOTS_CHECKED_IN_THIS_PROCESS"
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ValueError, error.URLError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED_NOT_VALIDATED", "error": type(exc).__name__}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
