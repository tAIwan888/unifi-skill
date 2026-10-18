#!/usr/bin/env python3
"""Record a *human-performed* review of public official-source evidence.

CLI cannot authenticate the claimed reviewer; enforce PR review separately.
Never invoked by the automated sync workflow. No network/Controller access.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]

def _load_gate():
    import importlib.util
    spec=importlib.util.spec_from_file_location("integrity_gate",Path(__file__).with_name("check_review_gate.py"))
    gate=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate

def approve(root,source,digest,reviewer,notes,evidence):
    gate=_load_gate()
    if not isinstance(digest,str) or not re.fullmatch(r"[a-f0-9]{64}",digest):
        raise ValueError("invalid digest")
    if not isinstance(reviewer,str) or not 2<=len(reviewer.strip())<=120:
        raise ValueError("reviewer required")
    if not isinstance(notes,str) or not 10<=len(notes.strip())<=2000:
        raise ValueError("review notes required")
    pp=root/"sync/pending.json";rp=root/"sync/reviewed.json";op=root/"sync/observed.json"
    cp=root/"sync/sources.json"
    pending=json.loads(pp.read_text(encoding="utf8"))
    reviewed=json.loads(rp.read_text(encoding="utf8"))
    observed=json.loads(op.read_text(encoding="utf8"))
    catalog=json.loads(cp.read_text(encoding="utf8"))
    catalog_matches=[x for x in catalog.get("sources",[]) if x.get("id")==source]
    if len(catalog_matches)!=1:
        raise ValueError("unknown or duplicate official source")
    official=catalog_matches[0]
    canonical=official.get("url")
    if not gate.valid_url(canonical):
        raise ValueError("untrusted official source URL")
    change=pending.get("changes",{}).get(source)
    if not isinstance(change,dict) or change.get("status")!="REVIEW_REQUIRED":
        raise ValueError("source not review-required")
    if change.get("current_sha256")!=digest:
        raise ValueError("pending digest differs")
    source_record=observed.get("sources",{}).get(source,{})
    if source_record.get("sha256")!=digest:
        raise ValueError("observed digest differs")
    if (change.get("url")!=canonical or source_record.get("url")!=canonical
        or change.get("modules")!=official.get("modules")):
        raise ValueError("source catalog/pending/observed mismatch")
    if not isinstance(evidence,list) or not evidence:
        raise ValueError("evidence Markdown is required")
    valid=[]
    for supplied in evidence:
        actual=gate.evidence_file(root,supplied)
        if actual is None:
            raise ValueError("evidence must be a safe in-repository Markdown")
        rel=actual.relative_to(root.resolve()).as_posix()
        if canonical not in actual.read_text(encoding="utf8"):
            raise ValueError("precise source URL missing: "+rel)
        valid.append(rel)
    record={
        "sha256":digest,"reviewer":reviewer.strip(),
        "reviewed_at":datetime.now(timezone.utc).isoformat(),
        "notes":notes.strip(),"evidence_files":sorted(set(valid)),
        "source_url":canonical
    }
    errors=gate.review_errors(root,source,record,canonical,digest)
    if errors:
        raise ValueError("invalid review record: "+"; ".join(errors))
    # All validation occurs before either JSON document is written.
    reviewed.setdefault("reviews",{})[source]=record
    del pending["changes"][source]
    rp.write_text(json.dumps(reviewed,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf8")
    pp.write_text(json.dumps(pending,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf8")
    return sorted(set(valid))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True);parser.add_argument("--digest",required=True)
    parser.add_argument("--reviewer",required=True);parser.add_argument("--notes",required=True)
    parser.add_argument("--evidence",required=True,nargs="+")
    parser.add_argument("--root",type=Path,default=ROOT)
    args=parser.parse_args()
    try:
        print("REVIEWED:",",".join(approve(args.root,args.source,args.digest,args.reviewer,args.notes,args.evidence)))
    except (ValueError,OSError,KeyError,TypeError) as e:
        print("REVIEW REJECTED: "+str(e),file=sys.stderr)
        sys.exit(2)
