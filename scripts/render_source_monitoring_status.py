#!/usr/bin/env python3
"""Render pinned main Runner acceptance while preserving historical source failures."""
import argparse
from datetime import date
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
_SPEC=importlib.util.spec_from_file_location("readme_scope",Path(__file__).resolve().parent/"source_monitoring_scope.py")
scope=importlib.util.module_from_spec(_SPEC);_SPEC.loader.exec_module(scope)
START="<!-- monitoring-status:start -->"
END="<!-- monitoring-status:end -->"

def render(root=ROOT):
    cat=json.loads((root/"sync/sources.json").read_text())["sources"]
    contract=json.loads((root/"manifest.json").read_text())["monitoring_contract"]
    snapshot=contract["status_snapshot_date"]
    if not isinstance(snapshot,str) or date.fromisoformat(snapshot).isoformat()!=snapshot:
        raise ValueError("invalid_status_snapshot_date")
    scope.validate_catalog(cat)
    rows=[x for x in cat if x.get("enabled",True)]
    required=sum(scope.source_role(x)==scope.REQUIRED for x in rows)
    optional=len(rows)-required
    raw=(root/contract["historical_health_file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=contract["historical_health_sha256"]:
        raise ValueError("historical_health_fingerprint_mismatch")
    health=json.loads(raw)
    summary=scope.validate_health(cat,health,full=True)
    # Deployment statement requires pinned GitHub main Runner evidence.
    if contract.get("deployment_status")!="DEPLOYED_RUNNER_ACCEPTED":
        raise ValueError("deployment_acceptance_not_recorded")
    ev=contract.get("deployment_acceptance")
    if not isinstance(ev,dict):raise ValueError("missing_deployment_evidence")
    try:
        accepted=ev["accepted_on"]
        if (not isinstance(accepted,str) or date.fromisoformat(accepted).isoformat()!=accepted
            or accepted<snapshot):
            raise ValueError("invalid_deployment_date")
        for field in ("feature_main_sha","report_main_sha"):
            if not isinstance(ev[field],str) or not re.fullmatch("[0-9a-f]{40}",ev[field]):
                raise ValueError("invalid_deployment_sha:"+field)
        for field in ("feature_pr","report_pr","resolved_issue","official_sync_run",
                      "main_ci_run","report_main_ci_run","python_tests"):
            if type(ev[field]) is not int or ev[field]<1:
                raise ValueError("invalid_deployment_reference:"+field)
        for field in ("required_total","required_healthy","optional_total","optional_healthy"):
            if type(ev[field]) is not int or ev[field]!=summary[field]:
                raise ValueError("inconsistent_deployment_health:"+field)
        if (ev["required_total"]!=required or ev["optional_total"]!=optional or
            ev["required_healthy"]!=required or ev["knowledge_approvals"]!=0 or
            ev["complete_global_manifest_verified"] is not False):
            raise ValueError("unsafe_deployment_claim")
    except (KeyError,TypeError) as exc:
        raise ValueError("incomplete_deployment_evidence") from exc
    repo="https://github.com/tAIwan888/unifi-skill"
    def run(run_id):
        return f"[Run #{run_id}]({repo}/actions/runs/{run_id})"
    return "\n".join([
        START,
        f"- **正式部署與驗收：已完成（{accepted}）**。[PR #{ev['feature_pr']}]({repo}/pull/{ev['feature_pr']}) 與 [PR #{ev['report_pr']}]({repo}/pull/{ev['report_pr']}) 已合併；[Issue #{ev['resolved_issue']}]({repo}/issues/{ev['resolved_issue']}) 已結案。",
        f"- **正式 GitHub Runner**：來源同步 {run(ev['official_sync_run'])} 的 `monitor`／`publish` 均 PASS；主線 CI {run(ev['main_ci_run'])}、報告合併後 CI {run(ev['report_main_ci_run'])} 均 PASS；正式同步執行 **{ev['python_tests']} 個 Python 測試**。",
        f"- **來源健康**：REQUIRED **{ev['required_healthy']}/{required}**；OPTIONAL REFERENCE **{ev['optional_healthy']}/{optional}**（失敗 {optional-ev['optional_healthy']}）。運作狀態 `REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS`；原始來源紀錄仍為 **{health['healthy']}/{health['monitored']}／{health['freshness']}**。",
        f"- **歷史稽核**：[修復前官方同步 Run]({contract['historical_run']})：{health['healthy']}/{health['monitored']}／{health['freshness']}；歷史結果沒有改成 PASS。",
        "- **限制**：兩個全球導航頁仍無法提供完整可驗證版本資訊；不宣稱最新穩定版、發布渠道、機型相容性、下載完整性或升級授權。Metadata 自動驗證不等於知識審核。",
        f"- **紀錄日期：{accepted}**，非即時狀態；請查看 [官方同步 Actions]({repo}/actions/workflows/official-knowledge-sync.yml) 和 [main CI]({repo}/actions/workflows/skill-ci.yml) 取得後續結果。",
        END])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--check",action="store_true")
    a=p.parse_args()
    try:
        path=a.root/"README.md";text=path.read_text();block=render(a.root)
        if text.count(START)!=1 or text.count(END)!=1:raise ValueError("missing_unique_status_markers")
        before,tail=text.split(START);_,after=tail.split(END)
        expected=before+block+after
        if a.check:
            if text!=expected:raise ValueError("README_monitoring_status_drift")
        elif text!=expected:path.write_text(expected,encoding="utf8")
        print("MONITORING_DOCUMENT_STATUS_PASS: deployed evidence recorded and historical failures preserved")
        return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print("MONITORING_DOCUMENT_STATUS_BLOCKED: "+str(exc))
        return 1

if __name__=="__main__":raise SystemExit(main())
