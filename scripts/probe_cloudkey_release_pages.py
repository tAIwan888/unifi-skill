#!/usr/bin/env python3
"""Research-only anonymous HTML visibility check of two pinned Cloud Keys posts.

Not a release-channel, model, completeness, or download validation mechanism.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from urllib import error, request, robotparser

from scripts import probe_cloudkey_legacy_rss as base

TARGETS = (
    ("5.1.11", "https://community.ui.com/releases/UniFi-OS-Cloud-Keys-5-1-11/7c1b7350-df16-412a-8b51-b4764f467c33"),
    ("6.0.11", "https://community.ui.com/releases/UniFi-OS-Cloud-Keys-6-0-11/57843ee1-a7e5-4166-a416-f3b460effb8c"),
)
MAX_HTML = 700_000


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template", "noscript"):
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "noscript") and self.ignored:
            self.ignored -= 1

    def handle_data(self, text):
        if not self.ignored:
            self.parts.append(text)


def _valid_report(report):
    if not isinstance(report, dict):
        raise ValueError("bad_input_report")
    if (report.get("status") != "OFFICIAL_HOSTED_RSS_PROBE_NOT_APPROVED"
            or report.get("transport") != "LIVE_ANONYMOUS_HTTPS"
            or report.get("human_reviewed") is not False
            or report.get("is_global_release_source") is not False
            or report.get("complete_current_cloudkey_coverage_verified") is not False
            or not isinstance(report.get("candidates"), list)
            or not re.fullmatch(r"[0-9a-f]{64}", str(report.get("digest_sha256", "")))):
        raise ValueError("unvalidated_rss_input")
    candidates = report["candidates"]
    # The checksum is an integrity link to the observed RSS candidate payload,
    # not a vendor signature, channel approval or proof of completeness.
    canonical = json.dumps(candidates, separators=(",", ":"), sort_keys=True)
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != report["digest_sha256"]:
        raise ValueError("rss_digest_mismatch")
    if (not candidates or any(not isinstance(x, dict) for x in candidates)
            or report.get("count") != len(candidates)
            or report.get("current_os_cloud_keys_pointer_count") != sum(
                x.get("product_scope") == "CURRENT_UNIFI_OS_CLOUD_KEYS" for x in candidates)
            or len({x.get("source_url") for x in candidates}) != len(candidates)):
        raise ValueError("rss_candidate_counts_invalid")
    return candidates


def inspect(report, opener=None):
    candidates = _valid_report(report)
    opener = opener or request.build_opener(base.BlockRedirect())
    result = {
        "status": "SAMPLED_POST_VISIBILITY_RESEARCH_NOT_APPROVED",
        "source_rss_digest_sha256": report["digest_sha256"],
        "human_reviewed": False,
        "is_global_release_source": False,
        "complete_current_cloudkey_coverage_verified": False,
        "release_channels_verified": False,
        "model_compatibility_verified": False,
        "download_authenticity_verified": False,
        "sample_count": len(TARGETS),
        "posts": [],
    }
    robots = None
    try:
        base.official(base.ROBOTS, exact=base.ROBOTS)
        with opener.open(request.Request(base.ROBOTS, headers={"User-Agent": base.USER_AGENT, "Accept": "text/plain"}), timeout=18) as resp:
            raw = base.response_bytes(resp, base.MAX_ROBOTS, ("text/plain", "application/octet-stream"))
        robots = robotparser.RobotFileParser()
        robots.parse(raw.decode("utf-8", "strict").splitlines())
        result["robots_policy"] = "READABLE_AND_APPLIED"
    except (ValueError, error.URLError, OSError, UnicodeError) as exc:
        result["robots_policy"] = "UNAVAILABLE_FAIL_CLOSED"
        result["robots_error_type"] = type(exc).__name__

    for version, url in TARGETS:
        row = {
            "version": version,
            "source_url": url,
            "release_channel": "UNKNOWN_NOT_VALIDATED_FROM_RSS",
            "device_model_scope": "NOT_VERIFIED",
            "verification": "CANDIDATE_UNREVIEWED",
        }
        matches = [x for x in candidates if isinstance(x, dict) and x.get("version") == version]
        if len(matches) != 1 or any(
            matches[0].get(field) != expected for field, expected in (
                ("title", f"UniFi OS - Cloud Keys {version}"),
                ("source_url", url),
                ("product_scope", "CURRENT_UNIFI_OS_CLOUD_KEYS"),
                ("verification", "CANDIDATE_UNREVIEWED"),
                ("release_channel", "UNKNOWN_NOT_VALIDATED_FROM_RSS"),
            )
        ):
            row["post_status"] = "PINNED_RSS_POINTER_ABSENT_OR_DRIFTED"
        elif robots is None:
            row["post_status"] = "ROBOTS_POLICY_UNAVAILABLE"
        elif not robots.can_fetch(base.USER_AGENT, url):
            row["post_status"] = "ROBOTS_DISALLOWED"
        else:
            try:
                base.official(url, exact=url)
                with opener.open(request.Request(url, headers={"User-Agent": base.USER_AGENT, "Accept": "text/html"}), timeout=18) as resp:
                    raw_html = base.response_bytes(resp, MAX_HTML, ("text/html",))
                text_reader = VisibleText()
                text_reader.feed(raw_html.decode("utf-8", "strict"))
                visible = re.sub(r"\s+", " ", " ".join(text_reader.parts)).strip()
                row["html_sha256"] = hashlib.sha256(raw_html).hexdigest()
                row["post_status"] = (
                    "VISIBLE_POST_BODY_UNREVIEWED" if
                    f"UniFi OS - Cloud Keys {version}" in visible
                    and "Overview" in visible and len(visible) >= 150
                    else "JS_SHELL_OR_INSUFFICIENT_VISIBLE_CONTENT"
                )
            except (ValueError, error.URLError, OSError, UnicodeError) as exc:
                row["post_status"] = "POST_FETCH_UNAVAILABLE"
                row["post_error_type"] = type(exc).__name__
        result["posts"].append(row)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        data = json.loads(args.input_report.read_text(encoding="utf-8"))
        result = inspect(data)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("SAMPLED_CLOUD_KEY_POST_RESEARCH", result["robots_policy"],
              ",".join(x["post_status"] for x in result["posts"]))
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("FAIL_CLOSED_POST_RESEARCH", type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
