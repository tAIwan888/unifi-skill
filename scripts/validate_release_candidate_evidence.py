#!/usr/bin/env python3
"""Fail-closed consistency check for UNREVIEWED official release candidates."""
import argparse,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA=re.compile(r"[0-9a-f]{64}\Z")
RELEASE_KINDS={"release_index","release_rss"}

def read(path,key):
    obj=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(obj,dict) or not isinstance(obj.get(key),dict):
        raise ValueError("invalid_schema:"+path.name)
    return obj[key]

def validate(root=ROOT):
    catalog=json.loads((root/"sync/sources.json").read_text(encoding="utf8"))["sources"]
    observed=read(root/"sync/observed.json","sources")
    data=read(root/"sync/version-candidates.json","sources")
    health=json.loads((root/"sync/health.json").read_text(encoding="utf8"))
    rows=health["results"]
    if len(rows)!=health["monitored"]:
        raise ValueError("health_count_mismatch")
    checks={x["id"]:x for x in rows}
    if len(checks)!=len(rows):raise ValueError("duplicate_health_source")
    allowed={x["id"]:x for x in catalog if x.get("kind") in RELEASE_KINDS}
    errors=[]
    for key in data:
        if key not in allowed:errors.append("UNREGISTERED_CANDIDATE_SOURCE:"+key)
    for key in sorted(allowed):
        if key not in checks:
            # --only mode can legitimately exclude this source.
            continue
        entry=allowed[key]
        if key not in data:
            errors.append("RELEASE_EVIDENCE_MISSING:"+key);continue
        rec=data[key]
        valid=checks[key]["status"]!="ERROR"
        expected="VALIDATED_THIS_RUN" if valid else "UNAVAILABLE_THIS_RUN"
        if rec.get("source_url")!=entry["url"]:
            errors.append("SOURCE_URL_MISMATCH:"+key)
        if rec.get("source_status")!=expected:
            errors.append("STALE_STATUS:"+key)
        candidates=rec.get("candidates")
        if not isinstance(candidates,list):
            errors.append("INVALID_CANDIDATES:"+key);continue
        if valid:
            sha=observed.get(key,{}).get("sha256")
            if not isinstance(sha,str) or not SHA.fullmatch(sha) or rec.get("source_sha256")!=sha:
                errors.append("SOURCE_SHA_MISMATCH:"+key)
            if rec.get("review_status")!="CANDIDATES_NOT_VERIFIED":
                errors.append("CANDIDATES_INCORRECT_REVIEW_STATUS:"+key)
            if entry.get("kind")=="release_rss" and not candidates:
                errors.append("EMPTY_VALIDATED_RSS:"+key)
            for candidate in candidates:
                if (not isinstance(candidate,dict) or
                    candidate.get("verification")!="CANDIDATE_UNREVIEWED" or
                    not str(candidate.get("release_channel","")).startswith("UNKNOWN_")):
                    errors.append("UNREVIEWED_CHANNEL_REQUIRED:"+key)
        else:
            if candidates or rec.get("review_status")!="NO_CURRENT_VERIFIABLE_CANDIDATES":
                errors.append("STALE_ACTIVE_CANDIDATES:"+key)
            if rec.get("failure_code")!=checks[key].get("detail"):
                errors.append("FAILURE_CODE_MISMATCH:"+key)
    declared=health.get("unavailable_release_candidate_sources")
    expected=sorted(k for k,v in checks.items() if k in allowed and v["status"]=="ERROR")
    if declared!=expected:errors.append("UNAVAILABLE_LIST_MISMATCH")
    return sorted(set(errors))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    args=p.parse_args()
    try:
        problems=validate(args.root)
    except (KeyError,TypeError,ValueError,OSError) as exc:
        print("RELEASE_EVIDENCE_REJECTED "+str(exc),file=sys.stderr)
        sys.exit(2)
    if problems:
        print("RELEASE_EVIDENCE_BLOCKED "+"; ".join(problems),file=sys.stderr)
        sys.exit(1)
    print("RELEASE_EVIDENCE_PASS: source status, candidate SHA, channel and health agree; still UNREVIEWED")
