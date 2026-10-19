# UniFi Skill — 公用知識庫

**版本**：v0.7.0-public-draft；M01–M10 公用模組與合成測試已存在，**未完成完整實驗室／生產驗收**。公用模式不需要私人 Controller、拓撲、API Key 或設備資料。

## 已部署與正式驗收（2026-10-19）

[PR #47](https://github.com/tAIwan888/unifi-skill/pull/47) 已合併至 main（`327fabad5766c9de5f726f24f9da6186beef04ce`）；[main CI #39261259085](https://github.com/tAIwan888/unifi-skill/actions/runs/39261259085) 與 [正式來源同步 #39261258785](https://github.com/tAIwan888/unifi-skill/actions/runs/39261258785) 均 **SUCCESS**。正式同步的 `monitor`／`publish` 雙 Job 通過，Python **219 個測試**通過。

- **必要監測來源 29/29**、參考來源 **0/2**；運作狀態：`REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS`。原始 31 來源報表依然為 **29/31、DEGRADED**，沒有掩蓋兩個全球入口的失敗。
- 僅自動驗證來源中繼資料（URL、SHA、解析證據）；不代表完整全球 Release Manifest、最新穩定版、發布渠道、下載完整性、型號相容性或設備升級獲核准。
- 下方「有日期的驗收快照」與歷史證據記錄的是**PR #47 合併之前**的狀態；不應被解讀成目前尚未部署。最新運作狀態以 [Actions](https://github.com/tAIwan888/unifi-skill/actions) 為準。

## 正式監測範圍與有日期的驗收快照

<!-- monitoring-status:start -->
- 宣告的機器監測範圍：**29 個 REQUIRED**；**2 個 OPTIONAL REFERENCE**；仍逐筆讀取共 **31 個**官方來源。
- **狀態快照日期：2026-10-19（非即時部署狀態）**。截至此日，PR #47 的本地提案**尚未部署／完成新規則的正式 Runner 驗收**。
- 最新狀態請查閱 [官方同步 Actions](https://github.com/tAIwan888/unifi-skill/actions/workflows/official-knowledge-sync.yml)、[PR #47](https://github.com/tAIwan888/unifi-skill/pull/47) 與 [Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7)；本快照不隨合併自動成為現況聲明。
- [既有正式失敗 Run](https://github.com/tAIwan888/unifi-skill/actions/runs/39228248994)：**29/31**、失敗 **2**、**DEGRADED**；歷史結果沒有改成 PASS。
- 僅將上述舊快照按提案角色分類：REQUIRED **29/29**；OPTIONAL **0/2**（失敗 2）。這不是新 Workflow 已正式 PASS 的證據。
- 完整 31/31 全球覆蓋、最新穩定版、下載資產完整性與逐機型相容性均**未獲證明**；Issue #7 的結案仍需正式 E2E 證據與獨立授權。
<!-- monitoring-status:end -->

狀態區由來源目錄與真實保存的健康快照產生；部署聲明僅適用所列快照日期，最新狀態以連結中的 Actions／PR／Issue 為準；執行 `python3 scripts/render_source_monitoring_status.py --check` 驗證，避免首頁與來源分類漂移。分類設計、退出碼、權限與正式驗收標準見 [必要來源監測規範](docs/required-source-monitoring.md)。

## 導覽

- [Skill 使用規則](SKILL.md)、[10 個知識模組](modules/)、[4 張決策樹](decisions/)、[5 份 Runbook](runbooks/)
- [n8n／唯讀 API Mock 與停用 Live 模板](recipes/)、[官方來源](docs/official-sources.md)
- [版本與相容性](docs/version-compatibility.md)、[官方同步](docs/official-sync.md)、[驗收界線](docs/evidence-and-acceptance.md)
- [機器來源 Metadata Gate](docs/automatic-machine-source-observations.md)、[來源限制歷史](docs/source-availability.md)

## 兩套自動流程與信任邊界

七類限定產品 RSS 在台灣時間週二／五 **15:00**（UTC 07:00）純唯讀掃描並上傳 Artifact；31-source 官方同步在週二／五 **17:00**（UTC 09:00）執行。PR #47 的設計沿用讀寫分離：無 repository 寫入權限的 Reader 讀取官方來源，受限 Writer 離線驗證同輪八個證據檔，再更新既有 Draft 分支。截至 2026-10-19 快照，新雙 Job 的正式 E2E 尚未完成；合併後的部署與驗收狀態須查閱上方最新 Actions，不能由本歷史快照推定。

來源只用固定官方 HTTPS、robots／同 Host Redirect、Article ID、文件版本與產品分類驗證。可自動 machine-accept SHA／URL／RSS 公告連結等 Metadata，但不能推定 Official／RC／EA、完整全球覆蓋、下載校驗、機型相容性或升級授權。`sync/reviewed.json` 不自動增加；`check_review_gate.py --mode machine` 不放寬。任一必要來源失敗仍 FAIL_CLOSED，只有兩個固定參考頁的缺口不再阻擋核心監測。

所有來源仍逐輪保留真實 ERROR／DEGRADED；失敗的版本來源必須清空本輪候選並標記 `UNAVAILABLE_THIS_RUN`。不開重複 PR／Issue，不自動 Merge、不繞過 main Ruleset、不讀取 Secrets、不操作私人設備。

## 本地回歸

```bash
python3 scripts/validate_knowledge.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_workflows.js
python3 scripts/validate_release_candidate_evidence.py
python3 scripts/check_review_gate.py --mode machine
python3 scripts/render_source_monitoring_status.py --check
```

`--mode human` 對未審核知識保持阻擋；離線 fixture／Mock 通過不能代表正式 Runner 或實機 PASS。

## 歷史證據（不改寫舊輪結果）

- [第一輪 0/24 失敗](https://github.com/tAIwan888/unifi-skill/actions/runs/39103031302)
- [Help Center 公開 JSON 19/19](https://github.com/tAIwan888/unifi-skill/actions/runs/39107846237)、[固定 Developer Markdown 3/3](https://github.com/tAIwan888/unifi-skill/actions/runs/39108698167)
- [早期 23/25 Audit](https://github.com/tAIwan888/unifi-skill/actions/runs/39111607487)、[PR #27 後 28/30](https://github.com/tAIwan888/unifi-skill/actions/runs/39119696504)
- [七類 RSS／127 範圍限定候選](https://github.com/tAIwan888/unifi-skill/actions/runs/39208902042)、[29/31 舊正式 Run](https://github.com/tAIwan888/unifi-skill/actions/runs/39209279906)
- [修正前歷史正式失敗 Run #39228248994](https://github.com/tAIwan888/unifi-skill/actions/runs/39228248994)

以上失敗與 DEGRADED 不因分類修正而改為成功。截至 2026-10-19 快照，Issue #7 為 OPEN，[PR #47](https://github.com/tAIwan888/unifi-skill/pull/47) 為待審工程工作包；之後狀態以即時連結為準，Issue 結案須有正式 E2E 證據與授權。後續一切以對應 GitHub Actions 與明確日期的證據為準，不宣稱全產品最新穩定版。
