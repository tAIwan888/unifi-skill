#!/usr/bin/env python3
"""Offline validation of public UniFi Skill structure and source provenance.

No network calls and no Controller access. This validates the documented
contracts, not the truth/freshness of individual official-source claims.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
_SPEC=importlib.util.spec_from_file_location("knowledge_scope",Path(__file__).resolve().parent/"source_monitoring_scope.py")
scope=importlib.util.module_from_spec(_SPEC);_SPEC.loader.exec_module(scope)
OFFICIAL_HOSTS = {
    "help.ui.com", "developer.ui.com", "community.ui.com",
    "ui.com", "www.ui.com", "techspecs.ui.com",
    "academy.ui.com", "assets.identity.ui.com"
}
HEADINGS = (
    "## 核心概念",
    "## 官方建議做法",
    "## UI 操作路徑",
    "## CLI / API 替代方法",
    "## 風險與注意事項",
    "## 驗證方式",
    "## 故障排除流程",
    "## 官方文件連結",
)

def validate_sources(catalog, module_ids, expected_count):
    problems = []
    rows = catalog.get("sources")
    if not isinstance(rows, list):
        return ["catalog: sources must be a list"]
    try:scope.validate_catalog(rows)
    except (ValueError,KeyError,TypeError) as exc:problems.append("catalog: "+str(exc))
    if len(rows) != expected_count:
        problems.append(f"catalog: count mismatch expected={expected_count} observed={len(rows)}")
    ids = set()
    mapped = set()
    for i, item in enumerate(rows):
        label = f"catalog[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{label}: invalid entry")
            continue
        source_id = item.get("id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*",source_id):
            problems.append(f"{label}: invalid source id")
        elif source_id in ids:
            problems.append(f"{label}: duplicate source id")
        else:
            ids.add(source_id)
        url = item.get("url","")
        try:
            parts = urlsplit(url)
            if (parts.scheme != "https" or parts.hostname not in OFFICIAL_HOSTS
                or parts.username or parts.password or parts.port is not None
                or parts.fragment):
                raise ValueError("unapproved official HTTPS URL")
        except (TypeError, ValueError):
            problems.append(f"{label}: unapproved official HTTPS URL")
        modules = item.get("modules")
        if not isinstance(modules,list) or not modules:
            problems.append(f"{label}: missing module mapping")
        else:
            for key in modules:
                if key not in module_ids:
                    problems.append(f"{label}: unknown module {key}")
                else:
                    mapped.add(key)
    for key in sorted(module_ids-mapped):
        problems.append(f"catalog: module {key} has no official source mapping")
    hosts = catalog.get("trusted_hosts",[])
    if not isinstance(hosts,list) or not set(hosts).issubset(OFFICIAL_HOSTS):
        problems.append("catalog: trusted_hosts contain unapproved domains")
    return problems

def validate_module(text, module_id):
    problems = []
    for heading in HEADINGS:
        if heading not in text:
            problems.append(f"{module_id}: missing heading {heading}")
    if "DOC_REVIEWED" not in text:
        problems.append(f"{module_id}: missing evidence grade (DOC_REVIEWED)")
    if "https://help.ui.com/" not in text and "https://developer.ui.com/" not in text:
        problems.append(f"{module_id}: missing official Help Center or Developer link")
    return problems

def validate(root=ROOT):
    problems = []
    try:
        manifest = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
        catalog = json.loads((root/"sync/sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        return ["manifest/catalog: missing or invalid JSON ("+type(exc).__name__+")"]
    module_ids = manifest.get("modules")
    if not isinstance(module_ids,list) or module_ids != [f"M{i:02d}" for i in range(1,11)]:
        return ["manifest: expected exactly M01-M10 in order"]
    if manifest.get("knowledge_mode") != "PUBLIC_KNOWLEDGE":
        problems.append("manifest: must use PUBLIC_KNOWLEDGE mode")
    if manifest.get("requires_personal_device_data") is not False:
        problems.append("manifest: private device data dependency forbidden")
    if manifest.get("requires_api_key") is not False:
        problems.append("manifest: public Skill must not require API keys")
    if manifest.get("live_private_controller_connections_by_default") is not False:
        problems.append("manifest: live private controller access must be disabled")
    snapshot = manifest.get("operational_snapshot",{})
    if not isinstance(snapshot,dict) or snapshot.get("is_live_status") is not False:
        problems.append("manifest: operational snapshot must not claim live status")
    expected_count = manifest.get("source_count")
    if type(expected_count) is not int or expected_count <= 0:
        problems.append("manifest: invalid source_count")
    else:
        problems.extend(validate_sources(catalog,set(module_ids),expected_count))
    docs = sorted((root/"modules").glob("M[0-9][0-9]-*.md"))
    if len(docs) != len(module_ids):
        problems.append(f"modules: expected {len(module_ids)} files, found {len(docs)}")
    seen = set()
    for doc in docs:
        key = doc.name[:3]
        if key in seen or key not in module_ids:
            problems.append(f"modules: duplicate/unknown {key}")
        seen.add(key)
        problems.extend(validate_module(doc.read_text(encoding="utf-8"), key))
    for key in set(module_ids)-seen:
        problems.append(f"modules: missing {key}")
    return problems

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print("KNOWLEDGE_AUDIT_FAILED", file=sys.stderr)
        for problem in errors:
            print("- "+problem, file=sys.stderr)
        sys.exit(1)
    print("KNOWLEDGE_AUDIT_PASS: 10 modules, source provenance and public privacy contract")
