#!/usr/bin/env python3
"""Offline manual intake of public, official UniFi release evidence.

Does not access vendor sites, user equipment, or private credentials.
Accepts statements as *unreviewed claims*, not proof that they match official
release posts. PR human review remains required for knowledge promotion.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_FAMILIES={
    "Network":"M02","UniFi OS":"M01","Protect":"M06",
    "Access":"M07","WiFi":"M04","Switching":"M05",
    "Talk":"M08","Connect":"M08","Identity":"M08",
    "Site Manager":"M01","Device Firmware":"M09"
}
CHANNELS={"Official","Release Candidate","Early Access"}
MAX_INPUT=200000
MAX_ENTRIES=50

def release_url(value):
    if not isinstance(value,str):raise ValueError("invalid_official_release_url")
    p=urlsplit(value)
    if p.scheme!="https" or p.username or p.password or p.port is not None or p.fragment:
        raise ValueError("invalid_official_release_url")
    if p.hostname=="community.ui.com":
        # Require an individual official release post, not a moving index page.
        if not re.fullmatch(r"/releases/[0-9a-fA-F-]{36}",p.path) or p.query:
            raise ValueError("exact_release_post_required")
    elif p.hostname in {"ui.com","www.ui.com"}:
        if not p.path.startswith("/download/") or p.query:
            raise ValueError("official_download_release_link_required")
    else:
        raise ValueError("untrusted_release_hostname")
    return value

def iso_date(value):
    if not isinstance(value,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
        raise ValueError("invalid_checked_date")
    checked=date.fromisoformat(value)
    if checked>date.today():
        raise ValueError("future_review_date")
    return value

def parse_batch(data):
    if not isinstance(data,list) or not (1<=len(data)<=MAX_ENTRIES):
        raise ValueError("invalid_batch_size")
    items=[]
    seen=set()
    for idx,row in enumerate(data):
        if not isinstance(row,dict):
            raise ValueError("invalid_item_type")
        family=row.get("family")
        if family not in ALLOWED_FAMILIES:
            raise ValueError("unknown_product_family")
        product=row.get("product")
        if not isinstance(product,str) or not (4<=len(product)<=110) or not re.fullmatch(r"[A-Za-z0-9 ()+_./-]+",product):
            raise ValueError("invalid_product_label")
        version=row.get("version")
        if not isinstance(version,str) or not re.fullmatch(r"\d{1,4}(?:\.\d{1,4}){2,3}",version):
            raise ValueError("invalid_version")
        channel=row.get("asserted_release_channel")
        if channel not in CHANNELS:
            raise ValueError("unrecognized_release_channel")
        url=release_url(row.get("official_release_url"))
        checked=iso_date(row.get("checked_on"))
        excerpt=row.get("short_evidence_excerpt")
        if not isinstance(excerpt,str) or not (20<=len(excerpt)<=240):
            raise ValueError("invalid_evidence_excerpt")
        if re.search(r"(?i)(BEGIN PRIVATE KEY|X-API-Key|Authorization:\s*Bearer|secret\s*[:=])",excerpt):
            raise ValueError("possible_secret_in_evidence")
        sig=(family,product,version,channel,url)
        if sig in seen:raise ValueError("duplicate_official_release_claim")
        seen.add(sig)
        items.append({
            "family":family,"affected_module":ALLOWED_FAMILIES[family],
            "product":product,"version":version,
            "asserted_release_channel":channel,
            "channel_verified":"HUMAN_REVIEW_REQUIRED",
            "official_release_url":url,"checked_on":checked,
            "excerpt_sha256":hashlib.sha256(excerpt.strip().encode("utf-8")).hexdigest(),
            "review_status":"UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE",
            "device_testing":"NOT_RUN"
        })
    return {"schema_version":1,"source_mode":"OFFLINE_MANUAL_PUBLIC_OFFICIAL_RELEASE_EVIDENCE",
            "independent_vendor_fetch":False,"candidates":items}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",type=Path,default=ROOT/"sync/manual-release-candidates.json")
    args=parser.parse_args(argv)
    if args.input.stat().st_size>MAX_INPUT:raise ValueError("input_file_too_large")
    data=json.loads(args.input.read_text(encoding="utf-8"))
    result=parse_batch(data)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(f"Imported {len(result['candidates'])} UNREVIEWED official-release evidence claims; no automatic knowledge promotion.")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as exc:
        print("RELEASE_EVIDENCE_REJECTED: "+type(exc).__name__,file=sys.stderr)
        sys.exit(2)
