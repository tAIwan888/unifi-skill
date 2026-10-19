#!/usr/bin/env python3
"""Offline, unreviewed Cloud Key candidate packet from pinned Runner JSON."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from scripts import probe_cloudkey_legacy_rss as rss
from scripts import probe_cloudkey_release_pages as posts

SAMPLE_STATUS = frozenset((
    "VISIBLE_POST_BODY_UNREVIEWED",
    "JS_SHELL_OR_INSUFFICIENT_VISIBLE_CONTENT",
    "POST_FETCH_UNAVAILABLE", "ROBOTS_POLICY_UNAVAILABLE",
    "ROBOTS_DISALLOWED", "PINNED_RSS_POINTER_ABSENT_OR_DRIFTED"
))
COLUMNS = ("rss_pubdate_utc", "version", "product_scope", "official_release_url",
           "channel", "review_status", "sampled_html_status", "channel_review",
           "hardware_review", "download_review")

def require(test, reason):
    if not test:
        raise ValueError(reason)

def build_packet(report, sample=None):
    source = posts._valid_report(report)
    require(report.get("rss_url") == rss.RSS, "rss_source_mismatch")
    require(1 <= len(source) <= 50, "bad_rss_count")
    queue = []
    seen_versions = set()
    for item in source:
        require(isinstance(item, dict), "bad_candidate")
        title = item.get("title")
        require(isinstance(title, str), "bad_title")
        match = rss.CURRENT.fullmatch(title)
        older = rss.LEGACY.fullmatch(title)
        require(bool(match or older), "bad_title")
        scope = "CURRENT_UNIFI_OS_CLOUD_KEYS" if match else "LEGACY_CLOUD_KEY_FIRMWARE"
        version = (match or older).group("version")
        require(item.get("product_scope") == scope, "scope_mismatch")
        require(item.get("version") == version, "version_mismatch")
        require(item.get("verification") == "CANDIDATE_UNREVIEWED", "approval_forbidden")
        require(item.get("release_channel") == "UNKNOWN_NOT_VALIDATED_FROM_RSS", "channel_forbidden")
        url = item.get("source_url")
        require(isinstance(url, str), "bad_url")
        rss.official(url)
        path = urlsplit(url).path
        require(rss.RELEASE_PATH.fullmatch(path) is not None, "bad_path")
        parts = path.split("/")
        if len(parts) == 4:
            suffix = version.replace(".", "-")
            allowed = ({f"UniFi-OS-Cloud-Keys-{suffix}"} if match else
                       {f"UniFi-Cloud-Key-{suffix}", f"UniFi-Cloud-Key-Firmware-{suffix}"})
            require(parts[2] in allowed, "url_title_mismatch")
        stamp = item.get("publication_date")
        require(isinstance(stamp, str), "bad_date")
        try:
            date = datetime.fromisoformat(stamp)
        except ValueError as exc:
            raise ValueError("bad_date") from exc
        require(date.tzinfo is not None and 2020 <= date.year <= 2100, "bad_date")
        key = (scope, version)
        require(key not in seen_versions, "duplicate_product_version")
        seen_versions.add(key)
        queue.append({
            "rss_pubdate_utc": date.astimezone(timezone.utc).date().isoformat(),
            "version": version, "product_scope": scope,
            "official_release_url": url,
            "channel": "UNKNOWN_NOT_VALIDATED_FROM_RSS",
            "review_status": "CANDIDATE_UNREVIEWED",
            "sampled_html_status": "NOT_SAMPLED",
            "channel_review": "PENDING",
            "hardware_review": "PENDING",
            "download_review": "PENDING",
        })
    if sample is not None:
        require(isinstance(sample, dict), "bad_post_sample")
        require(sample.get("status") == "SAMPLED_POST_VISIBILITY_RESEARCH_NOT_APPROVED", "bad_post_sample")
        require(sample.get("source_rss_digest_sha256") == report["digest_sha256"], "post_digest_mismatch")
        for flag in ("human_reviewed", "is_global_release_source",
                     "complete_current_cloudkey_coverage_verified",
                     "release_channels_verified", "model_compatibility_verified",
                     "download_authenticity_verified"):
            require(sample.get(flag) is False, "post_approval_forbidden")
        samples = sample.get("posts")
        require(isinstance(samples, list) and len(samples) == len(posts.TARGETS)
                and sample.get("sample_count") == len(samples), "bad_sample_count")
        used = set()
        for item in samples:
            require(isinstance(item, dict), "bad_sample_row")
            pair = (item.get("version"), item.get("source_url"))
            require(pair in posts.TARGETS and pair not in used, "unknown_sample_url")
            used.add(pair)
            require(item.get("post_status") in SAMPLE_STATUS, "bad_post_status")
            require(item.get("release_channel") == "UNKNOWN_NOT_VALIDATED_FROM_RSS"
                    and item.get("device_model_scope") == "NOT_VERIFIED"
                    and item.get("verification") == "CANDIDATE_UNREVIEWED", "post_promotion_forbidden")
            matched = [r for r in queue if (r["version"], r["official_release_url"]) == pair]
            require(len(matched) == 1, "sample_not_in_rss")
            matched[0]["sampled_html_status"] = item["post_status"]
    queue.sort(key=lambda r: (r["rss_pubdate_utc"], r["version"]), reverse=True)
    return {
        "review_state": "UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE",
        "rss_url": rss.RSS, "candidate_sha256": report["digest_sha256"],
        "count": len(queue), "human_approvals": 0,
        "global_release_coverage": "NOT_VERIFIED",
        "source_health_repair": False, "candidates": queue,
    }

def render_csv(packet):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(packet["candidates"])
    return out.getvalue()

def render_md(packet):
    lines = [
        "# Cloud Keys RSS 候選人工審核交接表", "",
        "**研究用途／未審核；不可用於設備升級、正式版本判定或自動合併。**", "",
        "- 官方範圍限定 RSS：" + packet["rss_url"],
        "- 候選 SHA-256：" + packet["candidate_sha256"],
        "- 候選 " + str(packet["count"]) + " 筆，人工核准 0 筆。",
        "- 所有候選頻道為 UNKNOWN_NOT_VALIDATED_FROM_RSS，適用機型及下載來源未審核。",
        "- 原始 RSS SHA 不是廠商簽章；HTML 可見性不是發布頻道驗證。",
        "- 審核人必須獨立開啟官方貼文、記錄審核時間、型號、頻道、版本歷史與下載依據。",
        "- Issue #7 的 official_releases 與 software_downloads 仍為 DEGRADED。", "",
        "| RSS 日期 (UTC) | 版本 | 官方貼文 | HTML 直接讀取 | 審核 |",
        "|---|---|---|---|---|",
    ]
    for item in packet["candidates"]:
        lines.append("| " + item["rss_pubdate_utc"] + " | " + item["version"]
                     + " | [官方貼文](" + item["official_release_url"] + ") | "
                     + item["sampled_html_status"] + " | PENDING |")
    lines.extend(["", "本檔自動由唯讀 JSON 證據生成，不包含已核准的發布頻道或型號結論。", ""])
    return "\n".join(lines)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-report", type=Path, required=True)
    parser.add_argument("--post-sample", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(args.input_report.stat().st_size <= 180_000, "oversized_rss_report")
        report = json.loads(args.input_report.read_text(encoding="utf-8"))
        sample = None
        if args.post_sample is not None:
            require(args.post_sample.stat().st_size <= 20_000, "oversized_post_sample")
            sample = json.loads(args.post_sample.read_text(encoding="utf-8"))
        packet = build_packet(report, sample)
        csv_text, md_text = render_csv(packet), render_md(packet)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "cloudkey-review-queue.csv").write_text(csv_text, encoding="utf-8")
        (args.output_dir / "cloudkey-review-handoff.md").write_text(md_text, encoding="utf-8")
        print("CLOUDKEY_REVIEW_QUEUE_UNREVIEWED", packet["count"], packet["candidate_sha256"])
        return 0
    except (ValueError, TypeError, OSError, UnicodeError) as exc:
        print("REVIEW_QUEUE_FAIL_CLOSED", type(exc).__name__, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
