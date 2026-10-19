#!/usr/bin/env python3
"""Offline Cloud Keys RSS -> manual claims, always UNREVIEWED, never a vendor fetch."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from scripts import import_official_release_evidence as intake

RSS = ("https://community.ui.com/rss/releases/UniFi-Cloud-Key-Firmware/"
       "c4ccd194-4cbf-4738-b07d-0aa6f04d178e")
CURRENT = re.compile(r"UniFi OS - Cloud Keys (\d{1,3}(?:\.\d{1,4}){2,3})\Z")
UUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
FIELDS = frozenset(("family", "product", "version", "official_release_url",
                    "rss_publication_date", "asserted_release_channel",
                    "checked_on", "short_evidence_excerpt"))

def require(value, label):
    if not value:
        raise ValueError(label)

def canonical_digest(entries):
    return hashlib.sha256(json.dumps(
        entries, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")).hexdigest()

def candidates_from_report(report):
    require(isinstance(report, dict), "invalid_rss_report")
    require(report.get("rss_url") == RSS
            and report.get("status") == "OFFICIAL_HOSTED_RSS_PROBE_NOT_APPROVED"
            and report.get("transport") == "LIVE_ANONYMOUS_HTTPS",
            "untrusted_rss_report")
    for name in ("human_reviewed", "is_global_release_source",
                 "complete_current_cloudkey_coverage_verified"):
        require(report.get(name) is False, "prohibited_review_promotion")
    rows = report.get("candidates")
    require(isinstance(rows, list) and 1 <= len(rows) <= 50, "bad_candidate_count")
    require(report.get("count") == len(rows), "rss_count_mismatch")
    digest = canonical_digest(rows)
    require(report.get("digest_sha256") == digest, "rss_digest_mismatch")
    require(report.get("current_os_cloud_keys_pointer_count") == len(rows),
            "rss_scope_count_mismatch")
    found, seen_urls = {}, set()
    for item in rows:
        require(isinstance(item, dict), "bad_rss_item")
        title = item.get("title")
        match = CURRENT.fullmatch(title) if isinstance(title, str) else None
        require(match is not None, "not_current_cloud_keys_title")
        version = match.group(1)
        require(item.get("product_scope") == "CURRENT_UNIFI_OS_CLOUD_KEYS"
                and item.get("version") == version
                and item.get("verification") == "CANDIDATE_UNREVIEWED"
                and item.get("release_channel") == "UNKNOWN_NOT_VALIDATED_FROM_RSS",
                "rss_version_or_approval_drift")
        url = item.get("source_url")
        intake.release_url(url)
        p = urlsplit(url)
        segments = p.path.split("/")
        require(p.hostname == "community.ui.com" and len(segments) == 4
                and segments[2] == "UniFi-OS-Cloud-Keys-" + version.replace(".", "-")
                and re.fullmatch(UUID, segments[3]) is not None,
                "unexpected_product_or_version_url")
        require(version not in found and url not in seen_urls, "duplicate_candidate")
        seen_urls.add(url)
        raw_date = item.get("publication_date")
        require(isinstance(raw_date, str), "bad_pubdate")
        try:
            dt = datetime.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError("bad_pubdate") from exc
        require(dt.tzinfo is not None and 2020 <= dt.year <= 2100, "bad_pubdate")
        found[version] = (url, dt.date().isoformat())
    return found, digest

def make_template(report):
    source, digest = candidates_from_report(report)
    return {
        "purpose": "MANUAL_CLAIM_TEMPLATE_NOT_REVIEWED",
        "rss_digest_sha256": digest,
        "human_reviewed": False,
        "rows": [{
            "family": "UniFi OS",
            "product": "UniFi OS - Cloud Keys",
            "version": version,
            "official_release_url": url,
            "rss_publication_date": date,
            "asserted_release_channel": None,
            "checked_on": None,
            "short_evidence_excerpt": "",
        } for version, (url, date) in sorted(source.items())],
    }

def import_completed(report, submitted):
    source, digest = candidates_from_report(report)
    require(isinstance(submitted, dict)
            and submitted.get("purpose") == "MANUAL_CLAIM_TEMPLATE_NOT_REVIEWED"
            and submitted.get("rss_digest_sha256") == digest
            and submitted.get("human_reviewed") is False,
            "untrusted_manual_submission")
    rows = submitted.get("rows")
    require(isinstance(rows, list) and 1 <= len(rows) <= len(source),
            "bad_manual_row_count")
    claims, seen = [], set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == FIELDS, "bad_manual_fields")
        version = row["version"]
        require(isinstance(version, str) and version in source and version not in seen,
                "unknown_or_duplicate_manual_version")
        seen.add(version)
        url, date = source[version]
        require(row["family"] == "UniFi OS"
                and row["product"] == "UniFi OS - Cloud Keys"
                and row["official_release_url"] == url
                and row["rss_publication_date"] == date, "manual_candidate_identity_drift")
        claims.append({k: row[k] for k in (
            "family", "product", "version", "official_release_url",
            "asserted_release_channel", "checked_on", "short_evidence_excerpt")})
    out = intake.parse_batch(claims)
    require(out["independent_vendor_fetch"] is False
            and all(x["channel_verified"] == "HUMAN_REVIEW_REQUIRED"
                    and x["review_status"] == "UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE"
                    and x["device_testing"] == "NOT_RUN" for x in out["candidates"]),
            "manual_importer_promotion")
    out["rss_digest_sha256"] = digest
    out["rss_bound_claims_unreviewed"] = True
    out["independent_human_review_completed"] = False
    return out

def load_json(path, maximum):
    require(path.stat().st_size <= maximum, "input_oversized")
    return json.loads(path.read_text(encoding="utf-8"))

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rss-report", type=Path, required=True)
    p.add_argument("--mode", required=True, choices=("template", "intake"))
    p.add_argument("--completed", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = load_json(args.rss_report, 200_000)
        if args.mode == "template":
            require(args.completed is None, "unexpected_completed_claims")
            result = make_template(report)
        else:
            require(args.completed is not None, "missing_completed_claims")
            result = import_completed(report, load_json(args.completed, 100_000))
        output = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print("CLOUDKEY_OFFLINE_HANDOFF_NOT_REVIEWED", len(result.get("rows", result.get("candidates", []))))
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print("MANUAL_HANDOFF_REJECTED " + type(exc).__name__, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
