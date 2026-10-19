#!/usr/bin/env python3
"""Fixed monitoring roles; operational availability is never global knowledge."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED="REQUIRED_MONITORING"
OPTIONAL="OPTIONAL_REFERENCE_ONLY"
OPTIONAL_SOURCES={
    "official_releases":"https://community.ui.com/releases?view=latest",
    "software_downloads":"https://www.ui.com/download/unifi",
}
FIELDS=("required_total","required_healthy","required_failed","optional_total",
        "optional_healthy","optional_failed","operational_status")
STATUSES={"ERROR","UNCHANGED","CHANGED","FIRST_SEEN"}

def source_role(entry):
    if entry.get("enabled",True) is not True:
        raise ValueError("monitoring_source_must_remain_enabled:"+str(entry.get("id")))
    role=entry.get("monitoring_role",REQUIRED)
    if role not in (REQUIRED,OPTIONAL):
        raise ValueError("invalid_monitoring_role:"+str(entry.get("id")))
    if role==OPTIONAL and (entry.get("id") not in OPTIONAL_SOURCES
        or entry.get("url")!=OPTIONAL_SOURCES[entry["id"]]
        or entry.get("kind")!="release_index" or entry.get("enabled",True) is not True):
        raise ValueError("optional_reference_not_allowlisted:"+str(entry.get("id")))
    return role

def validate_catalog(catalog):
    by_id={}
    for entry in catalog:
        sid=entry["id"]
        if sid in by_id:raise ValueError("duplicate_source_id")
        source_role(entry)
        by_id[sid]=entry
    if not by_id:raise ValueError("empty_source_catalog")
    return by_id

def summarize(catalog,rows):
    by_id=validate_catalog(catalog)
    groups={REQUIRED:[],OPTIONAL:[]};seen=set()
    for row in rows:
        sid=row["id"]
        if sid not in by_id or sid in seen:raise ValueError("invalid_health_source")
        if row.get("status") not in STATUSES:raise ValueError("invalid_health_status")
        seen.add(sid)
        groups[source_role(by_id[sid])].append(row)
    result={}
    for prefix,role in (("required",REQUIRED),("optional",OPTIONAL)):
        result[prefix+"_total"]=len(groups[role])
        result[prefix+"_failed"]=sum(x["status"]=="ERROR" for x in groups[role])
        result[prefix+"_healthy"]=result[prefix+"_total"]-result[prefix+"_failed"]
    result["operational_status"]=("NO_REQUIRED_SOURCES_CHECKED" if not result["required_total"]
        else "REQUIRED_SOURCES_FAILED" if result["required_failed"]
        else "REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS" if result["optional_failed"]
        else "REQUIRED_SOURCES_PASS")
    return result

def exit_code(summary):
    if not summary["required_total"] or not summary["required_healthy"]:return 2
    return 4 if summary["required_failed"] else 0

def validate_health(catalog,health,require_scope=False,full=False):
    by_id=validate_catalog(catalog);rows=health["results"]
    expected=summarize(catalog,rows)
    if full and {x["id"] for x in rows}!={k for k,v in by_id.items() if v.get("enabled",True)}:
        raise ValueError("incomplete_monitoring_coverage")
    healthy=sum(x["status"]!="ERROR" for x in rows)
    for key,value in (("monitored",len(rows)),("healthy",healthy),("failed",len(rows)-healthy)):
        if type(health.get(key)) is not int or health[key]!=value:
            raise ValueError("health_count_mismatch:"+key)
    if health.get("freshness")!=("DEGRADED" if len(rows)!=healthy else "SOURCES_RETRIEVED_UNREVIEWED"):
        raise ValueError("health_freshness_mismatch")
    scoped=require_scope or any(k in health for k in FIELDS)
    if scoped:
        for row in rows:
            if row.get("url")!=by_id[row["id"]]["url"]:raise ValueError("health_source_url_mismatch")
        for key,value in expected.items():
            if health.get(key)!=value or type(health.get(key)) is not type(value):
                raise ValueError("health_scope_mismatch:"+key)
    return expected

def markdown(summary):
    return (f"- REQUIRED：{summary['required_healthy']}/{summary['required_total']}；失敗 {summary['required_failed']}\n"
            f"- OPTIONAL REFERENCE：{summary['optional_healthy']}/{summary['optional_total']}；失敗 {summary['optional_failed']}\n"
            f"- Operational status：{summary['operational_status']}\n"
            "- 全球入口未形成可驗證的完整 Release Manifest／最新穩定版／下載與機型相容性清單；不得升格知識。\n")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--github-output",type=Path)
    p.add_argument("--expected-exit-code",type=int)
    p.add_argument("--expected-degraded",choices=("true","false"))
    a=p.parse_args()
    try:
        cat=json.loads((a.root/"sync/sources.json").read_text())["sources"]
        health=json.loads((a.root/"sync/health.json").read_text())
        summary=validate_health(cat,health,require_scope=True,full=True)
        code=exit_code(summary)
        if a.expected_exit_code is not None and a.expected_exit_code!=code:
            raise ValueError("scanner_exit_does_not_match_required_health")
        if a.expected_degraded is not None and a.expected_degraded!=("true" if code else "false"):
            raise ValueError("reader_degraded_flag_does_not_match_required_health")
        if a.github_output:
            with a.github_output.open("a",encoding="utf8") as out:
                out.write("degraded="+("true" if code else "false")+"\n")
        print(markdown(summary),end="")
        return 0  # Valid evidence is publishable even when required health failed.
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print("MONITORING_SCOPE_BLOCKED: "+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":sys.exit(main())
