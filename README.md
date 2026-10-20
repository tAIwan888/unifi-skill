# UniFi Skill — 公用知識庫

**版本**：v0.7.0-public-draft；M01–M10 公用模組與合成測試已存在，**未完成完整實驗室／生產驗收**。公用模式不需要私人 Controller、拓撲、API Key 或設備資料。

## 已部署監測與正式驗收（2026-10-19）

<!-- monitoring-status:start -->
- **正式部署與驗收：已完成（2026-10-19）**。[PR #47](https://github.com/tAIwan888/unifi-skill/pull/47) 與 [PR #48](https://github.com/tAIwan888/unifi-skill/pull/48) 已合併；[Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7) 已結案。
- **正式 GitHub Runner**：來源同步 [Run #39261258785](https://github.com/tAIwan888/unifi-skill/actions/runs/39261258785) 的 `monitor`／`publish` 均 PASS；主線 CI [Run #39261259085](https://github.com/tAIwan888/unifi-skill/actions/runs/39261259085)、報告合併後 CI [Run #39262767557](https://github.com/tAIwan888/unifi-skill/actions/runs/39262767557) 均 PASS；正式同步執行 **219 個 Python 測試**。
- **來源健康**：REQUIRED **29/29**；OPTIONAL REFERENCE **0/2**（失敗 2）。運作狀態 `REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS`；原始來源紀錄仍為 **29/31／DEGRADED**。
- **歷史稽核**：[修復前官方同步 Run](https://github.com/tAIwan888/unifi-skill/actions/runs/39228248994)：29/31／DEGRADED；歷史結果沒有改成 PASS。
- **限制**：兩個全球導航頁仍無法提供完整可驗證版本資訊；不宣稱最新穩定版、發布渠道、機型相容性、下載完整性或升級授權。Metadata 自動驗證不等於知識審核。
- **紀錄日期：2026-10-19**，非即時狀態；請查看 [官方同步 Actions](https://github.com/tAIwan888/unifi-skill/actions/workflows/official-knowledge-sync.yml) 和 [main CI](https://github.com/tAIwan888/unifi-skill/actions/workflows/skill-ci.yml) 取得後續結果。
<!-- monitoring-status:end -->

狀態由 `manifest.json` 的正式 Runner 驗收證據與不可變歷史健康檔案產生；執行 `python3 scripts/render_source_monitoring_status.py --check` 以防止漂移，詳見 [監測規範](docs/required-source-monitoring.md)。

## 跨平台單次執行 CLI（開發驗證中）

- 目標：Windows x64、macOS Intel/ARM64、Linux x64/ARM64 五種一檔式 CLI；無需常駐服務、工作排程或目標端 Python 安裝。
- 完整契約見 [單次執行與簽署更新規劃](docs/portable-one-shot.md)。入口為 `unifi-skill --mock --out <私有輸出.json>`；執行時不自行下載執行新版程式碼。
- GitHub Actions 五平台打包、離線 Mock 與 Git Blob SHA 檢查屬於**合成 CI**，並非已簽章、公證或實機 WiFi/UniFi 驗收。可信的自動更新與 ChatGPT 私人網路連線功能目前仍待設計、簽署與驗收。

## 導覽

- [Skill 使用規則](SKILL.md)、[10 個知識模組](modules/)、[4 張決策樹](decisions/)、[5 份 Runbook](runbooks/)
- [n8n／唯讀 API Mock 與停用 Live 模板](recipes/)、[官方來源](docs/official-sources.md)
- [版本與相容性](docs/version-compatibility.md)、[官方同步](docs/official-sync.md)、[驗收界線](docs/evidence-and-acceptance.md)
- [機器來源 Metadata Gate](docs/automatic-machine-source-observations.md)、[來源限制歷史](docs/source-availability.md)

## 兩套自動流程與信任邊界

七類限定產品 RSS 在台灣時間週二／五 **15:00**（UTC 07:00）純唯讀掃描並上傳 Artifact；31-source 官方同步在週二／五 **17:00**（UTC 09:00）執行。已部署的流程沿用讀寫分離：無 repository 寫入權限的 Reader 讀取官方來源，受限 Writer 離線驗證同輪八個證據檔，再生成待審報告。新雙 Job 已於 2026-10-19 在正式 main Runner 通過驗收；後續執行情形以 GitHub Actions 為準。

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

以上歷史失敗與 DEGRADED 不因分類修正而改為成功。[PR #47](https://github.com/tAIwan888/unifi-skill/pull/47) 和 [PR #48](https://github.com/tAIwan888/unifi-skill/pull/48) 已合併，[Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7) 已結案，正式同步成功；仍不宣稱全產品最新穩定版或全球完整版本資訊。
