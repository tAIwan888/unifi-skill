#!/usr/bin/env python3
"""Offline review-record integrity gate. Not proof of human review."""
import argparse,json,re,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
SHA=re.compile(r"[a-f0-9]{64}\Z")
ID=re.compile(r"[a-z][a-z0-9_]*\Z")
HOSTS={"help.ui.com","developer.ui.com","community.ui.com","ui.com","www.ui.com"}
EVIDENCE_ROOTS={"modules","runbooks","decisions","docs"}

def read(root,name,key):
    data=json.loads((root/"sync"/name).read_text(encoding="utf8"))
    if not isinstance(data,dict) or not isinstance(data.get(key),dict):
        raise ValueError("invalid_"+name)
    return data[key]

def valid_url(url):
    if not isinstance(url,str):return False
    try:p=urlsplit(url)
    except ValueError:return False
    return (p.scheme=="https" and p.hostname in HOSTS and
            p.username is None and p.password is None and p.port is None and
            not p.fragment and not re.search(r"[\s<>\[\]`|]",url))

def evidence_file(root,path):
    if not isinstance(path,str) or not path or "\\" in path:return None
    p=Path(path)
    if (p.is_absolute() or ".." in p.parts or "." in p.parts or
        len(p.parts)<2 or p.parts[0] not in EVIDENCE_ROOTS or p.suffix!=".md"):
        return None
    try:
        base=root.resolve(strict=True)
        full=(base/p).resolve(strict=True)
        full.relative_to(base)
        return full if full.is_file() else None
    except (ValueError,OSError):return None

def review_errors(root,sid,record,url,digest):
    errors=[]
    if not isinstance(record,dict):return ["INVALID_REVIEW_RECORD "+sid]
    if record.get("sha256")!=digest:errors.append("MISSING_MATCHING_REVIEW "+sid)
    if record.get("source_url")!=url:errors.append("REVIEW_SOURCE_URL_MISMATCH "+sid)
    who=record.get("reviewer")
    if not isinstance(who,str) or not 2<=len(who.strip())<=120:
        errors.append("REVIEWER_REQUIRED "+sid)
    note=record.get("notes")
    if not isinstance(note,str) or not 10<=len(note.strip())<=2000:
        errors.append("REVIEW_NOTES_REQUIRED "+sid)
    try:
        stamp=record["reviewed_at"]
        if not isinstance(stamp,str):raise ValueError()
        t=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        if t.tzinfo is None or t>datetime.now(timezone.utc)+timedelta(minutes=10):
            raise ValueError()
    except (ValueError,TypeError,KeyError):
        errors.append("REVIEW_TIMESTAMP_INVALID "+sid)
    files=record.get("evidence_files")
    if (not isinstance(files,list) or not 1<=len(files)<=20 or
        not all(isinstance(x,str) for x in files) or len(files)!=len(set(files))):
        errors.append("REVIEW_EVIDENCE_REQUIRED "+sid)
    else:
        for path in files:
            full=evidence_file(root,path)
            if full is None:errors.append("REVIEW_EVIDENCE_PATH_INVALID "+sid)
            elif url not in full.read_text(encoding="utf8"):
                errors.append("REVIEW_EVIDENCE_SOURCE_URL_MISSING "+sid)
    return errors

def validate(root):
    try:
        catalog=json.loads((root/"sync/sources.json").read_text(encoding="utf8"))
        obs=read(root,"observed.json","sources")
        pending=read(root,"pending.json","changes")
        reviewed=read(root,"reviewed.json","reviews")
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as exc:
        return ["INVALID_REVIEW_INPUT "+type(exc).__name__]
    errors=[];by_id={}
    for entry in catalog.get("sources",[]):
        if not isinstance(entry,dict):errors.append("INVALID_CATALOG_ENTRY");continue
        sid=entry.get("id")
        if not isinstance(sid,str) or not ID.fullmatch(sid):
            errors.append("INVALID_CATALOG_ID");continue
        if sid in by_id:errors.append("DUPLICATE_CATALOG_ID "+sid)
        if not valid_url(entry.get("url")):errors.append("INVALID_CATALOG_URL "+sid)
        by_id[sid]=entry
    if not by_id:errors.append("EMPTY_SOURCE_CATALOG")
    for sid,item in sorted(pending.items()):
        errors.append("PENDING "+sid)
        if sid not in by_id or sid not in obs:
            errors.append("PENDING_UNKNOWN_OR_UNOBSERVED "+sid);continue
        record=obs[sid]
        if not isinstance(item,dict) or item.get("status")!="REVIEW_REQUIRED":
            errors.append("INVALID_PENDING_STATUS "+sid);continue
        if (not isinstance(record,dict) or item.get("current_sha256")!=record.get("sha256")
            or item.get("url")!=record.get("url")
            or item.get("modules")!=by_id[sid].get("modules")):
            errors.append("PENDING_EVIDENCE_MISMATCH "+sid)
    for sid,record in sorted(obs.items()):
        if sid not in by_id:errors.append("UNREGISTERED_OBSERVED_SOURCE "+sid);continue
        if not isinstance(record,dict):errors.append("INVALID_OBSERVATION "+sid);continue
        digest,url=record.get("sha256"),record.get("url")
        if not isinstance(digest,str) or not SHA.fullmatch(digest):
            errors.append("INVALID_OBSERVED_DIGEST "+sid)
        if url!=by_id[sid].get("url") or not valid_url(url):
            errors.append("OBSERVED_SOURCE_URL_MISMATCH "+sid)
        if sid not in reviewed:errors.append("MISSING_MATCHING_REVIEW "+sid)
        elif isinstance(digest,str) and isinstance(url,str):
            errors.extend(review_errors(root,sid,reviewed[sid],url,digest))
    return sorted(set(errors))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=ROOT)
    args=parser.parse_args()
    errs=validate(args.root)
    if errs:
        print("BLOCKED: "+"; ".join(errs),file=sys.stderr)
        sys.exit(1)
    print("PASS: all observations have matching public-source review evidence")
    print("NOTICE: CI checks metadata, not reviewer identity; require actual GitHub PR review.")
