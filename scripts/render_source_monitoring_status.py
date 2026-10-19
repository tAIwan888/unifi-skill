#!/usr/bin/env python3
"""Render declared scope and dated evidence; never claim an unrun deployment."""
import argparse
from datetime import date
import hashlib
import importlib.util
import json
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
    # Deployment acceptance requires a separate, real Runner; role arithmetic
    # over an older snapshot is explicitly not a newly passing workflow.
    if contract["deployment_status"]!="PROPOSED_NOT_RUNNER_ACCEPTED":
        raise ValueError("deployment_acceptance_requires_explicit_runner_evidence")
    return "\n".join([
        START,
        f"- 宣告的機器監測範圍：**{required} 個 REQUIRED**；**{optional} 個 OPTIONAL REFERENCE**；仍逐筆讀取共 **{len(rows)} 個**官方來源。",
        f"- **狀態快照日期：{snapshot}（非即時部署狀態）**。截至此日，PR #47 的本地提案**尚未部署／完成新規則的正式 Runner 驗收**。",
        "- 最新狀態請查閱 [官方同步 Actions](https://github.com/tAIwan888/unifi-skill/actions/workflows/official-knowledge-sync.yml)、[PR #47](https://github.com/tAIwan888/unifi-skill/pull/47) 與 [Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7)；本快照不隨合併自動成為現況聲明。",
        f"- [既有正式失敗 Run]({contract['historical_run']})：**{health['healthy']}/{health['monitored']}**、失敗 **{health['failed']}**、**{health['freshness']}**；歷史結果沒有改成 PASS。",
        f"- 僅將上述舊快照按提案角色分類：REQUIRED **{summary['required_healthy']}/{summary['required_total']}**；OPTIONAL **{summary['optional_healthy']}/{summary['optional_total']}**（失敗 {summary['optional_failed']}）。這不是新 Workflow 已正式 PASS 的證據。",
        "- 完整 31/31 全球覆蓋、最新穩定版、下載資產完整性與逐機型相容性均**未獲證明**；Issue #7 的結案仍需正式 E2E 證據與獨立授權。",
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
        print("MONITORING_DOCUMENT_STATUS_PASS: declared scope and historical evidence; not deployment acceptance")
        return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print("MONITORING_DOCUMENT_STATUS_BLOCKED: "+str(exc))
        return 1

if __name__=="__main__":raise SystemExit(main())
