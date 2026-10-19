#!/usr/bin/env python3
"""Offline public-source review triage. Never approve a digest automatically."""
import argparse
import html
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
_SPEC=importlib.util.spec_from_file_location("triage_scope",Path(__file__).resolve().parent/"source_monitoring_scope.py")
monitoring_scope=importlib.util.module_from_spec(_SPEC);_SPEC.loader.exec_module(monitoring_scope)
HOSTS={"help.ui.com","developer.ui.com","community.ui.com","www.ui.com","ui.com"}
SHA=re.compile(r"[0-9a-f]{64}\Z")
MID=re.compile(r"M(?:0[1-9]|10)\Z")

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def safe_cell(text):
    if not isinstance(text,str):return "—"
    return (html.escape(" ".join(text.split()),quote=True).replace("|",r"\|")
            .replace("[","&#91;").replace("]","&#93;").replace("`","&#96;")[:150] or "—")

def source_url(url):
    if not isinstance(url,str):raise ValueError("invalid_source_url")
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname not in HOSTS or p.port is not None or
        p.username or p.password or p.fragment or re.search(r"[\s<>\[\]\x60|]",url)):
        raise ValueError("invalid_source_url")
    return url

def build(root=ROOT):
    source_list=read(root/"sync/sources.json")["sources"]
    monitoring_scope.validate_catalog(source_list)
    sources={}
    for entry in source_list:
        sid=entry["id"]
        if sid in sources:raise ValueError("duplicate_source_id")
        source_url(entry["url"])
        sources[sid]=entry
    pending=read(root/"sync/pending.json")["changes"]
    observed=read(root/"sync/observed.json")["sources"]
    health=(read(root/"sync/health.json") if (root/"sync/health.json").exists() else
            {"monitored":0,"healthy":0,"failed":0,"freshness":"NO_HEALTH_REPORT_ON_MAIN","results":[]})
    scope_lines=[]
    if any(key in health for key in monitoring_scope.FIELDS):
        scope_lines=[monitoring_scope.markdown(monitoring_scope.validate_health(source_list,health)),""]
    machine_file=root/"sync/machine-accepted.json"
    if machine_file.exists() and not pending:
        machine=read(machine_file)
        observations=machine.get("observations",{})
        if (machine.get("mode")!="AUTOMATED_PUBLIC_SOURCE_METADATA_ONLY"
            or not isinstance(observations,dict)
            or len(observations)!=health.get("healthy")
            or set(observations)-set(sources)):
            raise ValueError("machine_archive_or_health_mismatch")
        failures=[]
        for item in health["results"]:
            if item["status"]=="ERROR":
                sid=item["id"]
                if sid not in sources:raise ValueError("health_unknown_source")
                failures.append((sid,safe_cell(item.get("detail")),source_url(sources[sid]["url"])))
        lines=[
            "# 公開 UniFi 官方來源自動監測（機器來源資料，非升級核准）","",
            "> 無真人簽核；機器驗收的內容僅有來源 URL、SHA-256、範圍與解析器元資料。來源存在不等於發布渠道或設備相容性已驗證。","",
            "- 機器驗收來源：**"+str(len(observations))+"**",
            "- 待人工簽核來源：**0**（此監測流程不再要求真人簽核）",
            "- 官方全域入口失敗：**"+str(len(failures))+"**",
            "- 最新來源健康：**"+str(health.get("healthy"))+"/"+str(health.get("monitored"))+"**；"+safe_cell(health.get("freshness")),"",
            *scope_lines,"## 本輪失敗的來源","",
            "| 來源 | 錯誤類別 | 官方來源 |","|---|---|---|"]
        for sid,detail,url in sorted(failures):
            lines.append("| "+sid+" | "+detail+" | [官方來源]("+url+") |")
        if not failures:lines.append("| 無 | — | — |")
        lines+=["","## 不得自動擴權的界線","",
                "- "+str(len(observations))+" 筆機器來源記錄位於 sync/machine-accepted.json；0 筆知識、Release Channel 或設備升級授權。",
                "- 7 個類別 RSS 的公告仍屬 CANDIDATE_UNREVIEWED，不能推論 Official / RC / EA 或單一型號支援。",
                "- 失敗的全域 Release/Downloads 入口維持 DEGRADED；不得偽造完整版本清單。",
                "- Source metadata gate 可自動通過，私人 UniFi 設備與知識內容絕不由此自動修改。",""]
        return "\n".join(lines)
    modules={}
    for file in sorted((root/"modules").glob("M[0-9][0-9]-*.md")):
        key=file.name[:3]
        if key in modules:raise ValueError("duplicate_module_file")
        modules[key]=file
    rows=[];missing=set()
    for sid in sorted(pending):
        if sid not in sources:raise ValueError("pending_unknown_source")
        change=pending[sid]
        item=observed.get(sid,{})
        digest=change.get("current_sha256")
        url=source_url(change.get("url"))
        if not isinstance(digest,str) or not SHA.fullmatch(digest):
            raise ValueError("invalid_source_digest:"+sid)
        if (item.get("sha256")!=digest or item.get("url")!=url or
            sources[sid]["url"]!=url):
            raise ValueError("pending_observed_mismatch:"+sid)
        if change.get("status")!="REVIEW_REQUIRED":
            raise ValueError("pending_not_review_required:"+sid)
        if change.get("modules")!=sources[sid]["modules"]:
            raise ValueError("module_mapping_mismatch:"+sid)
        checks=[]
        for mid in change["modules"]:
            if not isinstance(mid,str) or not MID.fullmatch(mid) or mid not in modules:
                raise ValueError("invalid_module:"+str(mid))
            present=url in modules[mid].read_text(encoding="utf-8")
            if not present:missing.add(mid)
            checks.append(mid+": "+("引用存在／未審核" if present else "缺少精確引用"))
        evidence=change.get("public_source_evidence") or {}
        if not isinstance(evidence,dict):raise ValueError("invalid_evidence")
        method=safe_cell(evidence.get("fetch_method","LEGACY_MONITOR"))
        title=safe_cell(evidence.get("title",""))
        scope=safe_cell(evidence.get("version_scope",""))
        rows.append((sid,url,"、".join(checks),"；".join(x for x in [method,title,scope] if x!="—"),digest[:12]))
    if health.get("monitored")!=len(health.get("results",[])):
        raise ValueError("health_count_mismatch")
    failures=[]
    for item in health["results"]:
        if item["status"]=="ERROR":
            sid=item["id"]
            if sid not in sources:raise ValueError("health_unknown_source")
            failures.append((sid,safe_cell(item.get("detail")),source_url(sources[sid]["url"])))
    lines=[
        "# 公開 UniFi 官方來源審核工作單（機器產生，未核准）","",
        "> 引用存在不代表已人工比對；內容指紋變更也不一定代表產品版本變更。","",
        "- 待審來源：**"+str(len(rows))+"**",
        "- 最新來源健康：**"+str(health.get("healthy","?"))+"/"+str(health.get("monitored","?"))+
            "**；失敗 "+str(health.get("failed","?"))+"；"+safe_cell(health.get("freshness")),
        "- 缺少精確來源引用的受影響模組數：**"+str(len(missing))+"**",
        "- 本清單只處理公開來源，不需要私人 UniFi 裝置資料。","",
        *scope_lines,"## 待審來源","",
        "| 官方來源 | 受影響模組與引用狀態 | 公開來源中繼資料 | SHA-256 前綴 |",
        "|---|---|---|---|"
    ]
    for sid,url,checks,description,digest in rows:
        lines.append("| ["+sid+"]("+url+") | "+checks+" | "+description+" | `"+digest+"` |")
    if not rows:lines.append("| 無待審來源 | — | — | — |")
    lines+=["","## 未能取得有效內容的來源","","| 來源 | 錯誤類別 | 網址 |","|---|---|---|"]
    for sid,detail,url in sorted(failures):
        lines.append("| "+sid+" | "+detail+" | [官方來源]("+url+") |")
    if not failures:lines.append("| 本輪無來源失敗 | — | — |")
    lines+=["","## 審核步驟","",
            "1. 親自閱讀每個官方來源，核對變動對產品、版本和 Official / RC / EA 渠道的影響。",
            "2. 對照模組、決策樹、Runbook 與 API Recipe。引用存在只代表字串匹配，非內容審核。",
            "3. 缺少精確來源引用者先補官方連結及正確適用範圍；不可自動補成已核准。",
            "4. 經審核後，使用 approve_official_update.py 記錄 Reviewer、SHA、說明與 Evidence。",
            "5. 確認 check_review_gate.py 和 CI 通過，才可依專案授權人工合併。","",
            "**本工具不讀取或更改 sync/reviewed.json，也不會自動核准或合併。**",""]
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path,default=ROOT/"sync/review-triage.md")
    args=parser.parse_args()
    try:
        content=build(args.root)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(content,encoding="utf-8")
        print("PUBLIC_REVIEW_TRIAGE_READY: no knowledge approval")
        return 0
    except (ValueError,TypeError,KeyError,OSError) as e:
        print("PUBLIC_REVIEW_TRIAGE_REJECTED: "+str(e),file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
