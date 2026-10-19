#!/usr/bin/env python3
"""Read-only global-source rendering feasibility; never approve release data."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from scripts import check_official_updates as monitor

URLS = {
    "official_releases": "https://community.ui.com/releases?view=latest",
    "software_downloads": "https://www.ui.com/download/unifi",
}
MAX_HTML = 4000000
PHRASE = re.compile(
    r"\b(?:UniFi|Enterprise Campus|UAP|USW|UTR)[A-Za-z0-9&+() ,./|\-]{2,105}?"
    r"\s+\d{1,3}(?:\.\d{1,4}){2,3}\b", re.I)

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocked = 0
        self.words = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template", "noscript", "svg"):
            self.blocked += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "noscript", "svg"):
            self.blocked = max(0, self.blocked-1)
    def handle_data(self, data):
        if self.blocked == 0 and data.strip():
            self.words.append(data.strip())

def classify(dom):
    if not isinstance(dom, str) or len(dom.encode("utf8")) > MAX_HTML:
        raise ValueError("invalid_dom_size")
    p = Visible()
    p.feed(dom)
    text = re.sub(r"\s+", " ", " ".join(p.words)).strip()
    found = sorted({m.group(0) for m in PHRASE.finditer(text)})
    return {
        "status": ("RENDERED_PARTIAL_VERSION_POINTERS_UNREVIEWED"
                   if len(found) >= 2 else "NO_VERIFIABLE_RENDERED_VERSION_LIST"),
        "visible_text_sha256": hashlib.sha256(text.encode("utf8")).hexdigest(),
        "visible_char_count": len(text),
        "candidate_phrase_count": len(found),
        "unreviewed_samples": [x[:155] for x in found[:12]],
        "release_channel_verified": False,
        "hardware_compatibility_verified": False,
        "downloads_verified": False,
        "global_coverage_verified": False,
        "knowledge_approved": False,
    }

def inspect(key, browser):
    if key not in URLS:
        raise ValueError("unknown_target")
    url = URLS[key]
    monitor.allowed_url(url)
    opener = monitor.request.build_opener(monitor.SafeRedirect())
    monitor._robot_ok(url, opener)
    with tempfile.TemporaryDirectory(prefix="unifi-public-global-") as profile:
        cmd = [browser, "--headless=new", "--dump-dom",
               "--disable-gpu", "--disable-extensions", "--disable-sync",
               "--disable-background-networking", "--disable-dev-shm-usage",
               "--no-first-run", "--timeout=10000",
               "--user-agent="+monitor.UA,
               "--user-data-dir="+profile, url]
        r = subprocess.run(cmd, capture_output=True, timeout=55, check=False)
        if r.returncode:
            raise ValueError("headless_browser_failed")
        if not r.stdout or len(r.stdout)>MAX_HTML:
            raise ValueError("empty_or_oversized_dom")
        dom = r.stdout.decode("utf8", "strict")
    return {"source_id": key, "url":url, **classify(dom)}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    args=ap.parse_args(argv)
    chrome=shutil.which("google-chrome") or shutil.which("chromium")
    report={
        "schema_version":1, "mode":"ANONYMOUS_RENDER_RESEARCH_NOT_APPROVED",
        "official_urls":URLS, "browser_available":bool(chrome),
        "keep_global_health":"DEGRADED_PENDING_VALIDATED_COMPLETE_SOURCE",
        "release_channels_approved":0, "device_models_approved":0,
        "download_files_verified":0, "knowledge_approved":False,
        "sources":{},
    }
    for key,url in URLS.items():
        try:
            if not chrome:
                raise ValueError("headless_browser_not_installed")
            item=inspect(key,chrome)
        except (ValueError, TypeError, OSError, subprocess.TimeoutExpired,
                UnicodeError) as exc:
            item={"source_id":key, "url":url,
                  "status":"RENDERED_SOURCE_NOT_VERIFIABLE",
                  "error_kind":type(exc).__name__,
                  "release_channel_verified":False,
                  "global_coverage_verified":False,
                  "knowledge_approved":False}
        report["sources"][key]=item
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("OFFICIAL_GLOBAL_RENDER_RESEARCH",json.dumps({
        k:{"status":v["status"],"phrases":v.get("candidate_phrase_count",0)}
        for k,v in report["sources"].items()},sort_keys=True))
    return 0 if all(v["status"]=="RENDERED_PARTIAL_VERSION_POINTERS_UNREVIEWED"
                    for v in report["sources"].values()) else 2

if __name__=="__main__":
    sys.exit(main())
