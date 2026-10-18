#!/usr/bin/env python3
"""Recheck official public source SHA claims without approving any knowledge."""
import argparse
from datetime import datetime,timezone
import hashlib,html,importlib.util,json,re,sys
from pathlib import Path
from urllib import request
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("monitor",ROOT/"scripts/check_official_updates.py")
monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)
def read(path,key):
    obj=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(obj,dict) or not isinstance(obj.get(key),dict):raise ValueError("invalid_"+key)
    return obj[key]
def fetch(entry,meta):
    op=request.build_opener(monitor.SafeRedirect())
    kind=entry.get("kind")
    if kind=="help_article":return monitor.fetch_public_help_article(entry,op,metadata=meta)
    if kind=="developer_markdown":return monitor.fetch_official_developer_markdown(entry,op,metadata=meta)
    if kind=="release_rss":return monitor.fetch_network_release_rss(entry,op,metadata=meta)
    raise ValueError("unsupported_kind")
def audit(catalog,observed,pending,fetcher=None):
    sources={}
    for e in json.loads(catalog.read_text(encoding="utf8"))["sources"]:
        k=e["id"];monitor.allowed_url(e["url"])
        if k in sources:raise ValueError("duplicate_source_id")
        sources[k]=e
    obs=read(observed,"sources");claims=read(pending,"changes")
    if not claims:raise ValueError("no_pending_evidence")
    rows=[]
    for key,c in sorted(claims.items()):
        if key not in sources or key not in obs:raise ValueError("unknown_pending_source")
        src=sources[key];baseline=c.get("current_sha256")
        if (not isinstance(baseline,str) or not re.fullmatch("[a-f0-9]{64}",baseline)
            or c.get("url")!=src["url"] or obs[key].get("url")!=src["url"]
            or obs[key].get("sha256")!=baseline or c.get("status")!="REVIEW_REQUIRED"
            or c.get("modules")!=src.get("modules")):
            raise ValueError("inconsistent_pending_evidence:"+key)
        row={"source_id":key,"url":src["url"],"modules":src["modules"],
             "baseline_sha256":baseline,"kind":src.get("kind")}
        meta={}
        try:
            raw=fetcher(src,meta) if fetcher else fetch(src,meta)
            value=monitor.validate_content(src,monitor.normalize(raw))
            if src.get("kind")=="release_rss" and not meta.get("release_candidates"):
                raise ValueError("missing_rss_candidates")
            current=hashlib.sha256(value.encode("utf8")).hexdigest()
            row["current_sha256"]=current
            row["status"]="MATCHES_PENDING" if current==baseline else "DRIFT_REQUIRES_REVIEW"
            row["public_metadata"]={k:meta[k] for k in ("title","vendor_updated_at",
                 "doc_version","version_scope","product_scope","candidate_count","channel_scope")
                 if k in meta}
        except (OSError,ValueError,KeyError,TypeError,UnicodeError) as exc:
            row["status"]="UNAVAILABLE_NOT_REVIEWED"
            row["error_code"]=monitor.error_code(exc)
        rows.append(row)
    totals={state:sum(r["status"]==state for r in rows) for state in
            ("MATCHES_PENDING","DRIFT_REQUIRES_REVIEW","UNAVAILABLE_NOT_REVIEWED")}
    return {"schema_version":1,"kind":"PUBLIC_FINGERPRINT_CHECK_NOT_APPROVAL",
            "checked_at_utc":datetime.now(timezone.utc).isoformat(),
            "pending_count":len(rows),"summary":totals,
            "review_status":"INDEPENDENT_HUMAN_REVIEW_REQUIRED","rows":rows}
def safe(s):
    return html.escape(" ".join(str(s).split()),quote=True).replace("|",r"\|")[:140]
def markdown(result):
    d=result["summary"]
    lines=["# 官方來源待審 SHA 二次核對報告","",
        "**SHA 相符並不等於已審核、最新穩定版、版本相容或實機測試通過。**","",
        "- UTC："+safe(result["checked_at_utc"]),
        "- 待審："+str(result["pending_count"]),
        "- 相符："+str(d["MATCHES_PENDING"]),
        "- 已變動："+str(d["DRIFT_REQUIRES_REVIEW"]),
        "- 無法讀取："+str(d["UNAVAILABLE_NOT_REVIEWED"]),"",
        "| 官方來源 | 模組 | SHA 檢查 | 公開 Metadata |","|---|---|---|---|"]
    for r in result["rows"]:
        meta="；".join(safe(k+"="+str(v)) for k,v in sorted(r.get("public_metadata",{}).items()))
        if "error_code" in r:meta="失敗："+safe(r["error_code"])
        lines.append("| ["+safe(r["source_id"])+"]("+r["url"]+") | "+safe(",".join(r["modules"]))+
                     " | "+safe(r["status"])+" | "+(meta or "—")+" |")
    lines+=["","## 尚未完成","",
        "1. 人工閱讀官方全文並核對功能、最低版本、安全風險與適用產品。",
        "2. RSS 候選逐篇核對 Official / RC / EA；不得把高版本自動視為正式版。",
        "3. 若 SHA 漂移或本次失敗，先重新建立來源證據，禁止使用舊摘要核准。",
        "4. 必須維持真實人員審核及獨立合併授權；本腳本不更新審核紀錄。",""]
    return "\n".join(lines)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",type=Path,default=ROOT/"sync/sources.json")
    p.add_argument("--observed",type=Path,required=True)
    p.add_argument("--pending",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--json-output",type=Path)
    a=p.parse_args()
    try:
        report=audit(a.catalog,a.observed,a.pending)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(markdown(report),encoding="utf8")
        if a.json_output:a.json_output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        print("PUBLIC_SOURCE_RECHECK",json.dumps(report["summary"],sort_keys=True))
        return 0 if report["summary"]["MATCHES_PENDING"]==report["pending_count"] else 4
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print("PUBLIC_SOURCE_RECHECK_REJECTED",type(exc).__name__,str(exc),file=sys.stderr)
        return 2
if __name__=="__main__":sys.exit(main())
