# UniFi Skill — 公用知識庫

**版本**：v0.7.0-public-draft（M01–M10 公用內容已納入 `main`）  
**基準日期**：2026-10-18  
**狀態**：十個知識模組均具通用文件與部分合成測試；**尚未完整實驗室／生產驗收**。2026-10-19 最新正式來源驗證為 **29/31 來源合格、2 個全球發布來源降級**；仍不表示已核准完整官方版本知識。

建立給任何 UniFi 使用者、家庭與 SOHO 網管、MSP、自架與自動化開發者使用。**建立及使用公用知識庫不需要提供私人設備、Controller IP、拓撲或 API Key。**

## 導覽
- [Skill 使用規則](SKILL.md)
- [10 個知識模組](modules/)
- [4 張架構決策樹](decisions/)
- [5 份可回滾 Runbook](runbooks/)
- [n8n / API 離線 Mock 與停用 Live 模板](recipes/)
- [官方資料來源](docs/official-sources.md)
- [官方版本相容性政策](docs/version-compatibility.md)
- [官方自動同步與審核](docs/official-sync.md)
- [同步審核清單](docs/sync-review-checklist.md)
- [證據與驗收](docs/evidence-and-acceptance.md)

## 自動同步原則
正式 `main` 的 `sync/sources.json` 已收錄 **31 個公開官方來源**。GitHub Actions 有兩個不同工作流程：**七類限定產品 RSS 的純唯讀自動版本分流**於台灣時間週二／五 **15:00**（UTC 07:00）執行，只上傳候選／異常 Artifact；**31 來源官方知識同步（審核用）**另於台灣時間週二／五 **17:00**（UTC 09:00）執行，可更新未審核 Draft PR 與現存維護 Issue，但不自動合併或核准知識。來源驗證與 SHA 比對失敗時均 Fail-Closed，不宣稱完整同步成功。**無自動合併、無自動改寫正式知識、無私人 UniFi 存取**。只有在 Workflow 位於預設分支且 Actions 設定允許時，排程才會生效。

## 本地驗證
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_workflows.js
python3 scripts/check_review_gate.py
```

所有正式設定都必須按產品、UniFi OS / App / Firmware / API 版本與 Release Channel 驗證；Mock PASS 不代表實機 PASS。

## 官方同步健康度（已部署；歷史觀測）
- [官方來源實測限制與降級政策](docs/source-availability.md)
- `sync/health.json` 區分 HTTP 403／404／JavaScript-only／內容品質失敗。
- `sync/version-candidates.json` 的候選必須同時檢查 `source_status=VALIDATED_THIS_RUN`；來源失敗時將本輪 `candidates` 清空，僅保留歷史來源指紋與數量。所有候選仍未審核，不能當作最新穩定版公告。
- 來源部分或全數失敗時，Workflow 在提交健康報告後標示降級失敗，等待人工處理；不自動變更知識。

## 知識庫品質驗證
```bash
python3 scripts/validate_knowledge.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_workflows.js
python3 scripts/check_review_gate.py
```
上述驗證只確認**文件結構與離線行為**，不代表 UniFi 官方網站現在可達，也不代表任何型號已經實測。

第一輪 HTML 監測曾為 0/24，歷經官方公開文章 API、Developer Markdown 與限定 Network RSS 修復，2026-10-18 正式同步已驗證 **23/25**；參見 [首次降級來源監測](https://github.com/tAIwan888/unifi-skill/actions/runs/39103031302)、[維運 Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7) 與 [健康報告 PR #6](https://github.com/tAIwan888/unifi-skill/pull/6)。請以 GitHub Actions 的**最新執行結果**為現況，不要把這份歷史快照視為即時同步成功證明。

## 官方公開 API／Developer Markdown 同步（已在 main 啟用）

2026-10-18 正式同步觀測：**25 個官方來源中有 23 個內容有效**（19 個 Help Center Article JSON、3 個固定版本 Developer Markdown、1 個限定 Network Application RSS）。剩下 2 個是 Release Index 和 Software Downloads 的版本資訊不足，因此整體健康仍是 `DEGRADED`。

- [Help Center 19/19 成功](https://github.com/tAIwan888/unifi-skill/actions/runs/39107846237)
- [Developer Markdown 3/3 成功](https://github.com/tAIwan888/unifi-skill/actions/runs/39108698167)
- [正式 25-source Audit：23/25 成功，2 來源未通過](https://github.com/tAIwan888/unifi-skill/actions/runs/39111607487)

監測程式使用固定 HTTPS 官方白名單、Article ID／發布狀態、Markdown URL 版本／產品類別、robots.txt RFC 9309 適當處理與內容指紋；僅保存公開文章中繼資料，不提交原文全文。首次成功將形成 `REVIEW_REQUIRED`，**不能自動被視為目前 UniFi OS、Firmware、API 的最新正式版本**。

**PR #16、#19 已合併並完成正式驗收**：[main 23/25 同步](https://github.com/tAIwan888/unifi-skill/actions/runs/39111607487)。`manifest.json` 的 0/24 是第一次同步的歷史快照，不可當成現在狀態。

## Network Application 官方 Release RSS（已在 main 啟用）

Ubiquiti Community 官方 RSS 已於 GitHub Runner 真實驗證：Network Application 分類的 20 筆 Release Post 可讀。現已新增**第 25 個受範圍限制的監測來源**，僅輸出 `UNKNOWN_NOT_VALIDATED_FROM_RSS` 發布渠道及 `CANDIDATE_UNREVIEWED` 版本候選；它不能取代全產品 Release Index，也不能推定任何版本為最新穩定版。詳見 [官方 RSS 檢驗及範圍](docs/official-network-release-rss.md)。


## 多產品官方 Release RSS 擴充（PR #27，尚待合併）

本 PR 擬將來源清單由 **25 增加至 30**，增設 Protect Application、UniFi OS Server、Dream Machines、AP／無線韌體及 Switch 五類官方 RSS。2026-10-18 的隔離 GitHub Runner 完整測試：**28/30** 公開來源取得有效內容，**87 筆新產品分類 RSS 版本候選**；仍有原本 2 個全產品 HTML Release／Downloads 來源失敗，並保留 `DEGRADED`。

所有新 RSS 內容只儲存公開來源指紋與文章中繼資料，`CANDIDATE_UNREVIEWED`、`UNKNOWN_NOT_VALIDATED_FROM_RSS`；不得推定最新穩定版、同款所有型號相容，也不代表人員已核准。測試分支的 28 筆 Pending 為初次觀測，只有正式合併後的例行同步才會更新既有待審 PR #6。詳細限制：[官方多產品 RSS 範圍](docs/official-multiproduct-release-rss.md)。正式 `main` 尚未合併 PR #27 時，維持既有 **23/25** 的最近驗收紀錄。

## 2026-10-19 維護狀態與排程校正

- 已合併 PR #39、#40、#41；七類限定產品 RSS 包含 Cloud Keys。 [七來源實測 Runner](https://github.com/tAIwan888/unifi-skill/actions/runs/39208902042) 共 127 筆機器候選、第二次執行 0 個新增事件，未驗證發布頻道或機型相容性。
- [31 來源正式同步 #39209279906](https://github.com/tAIwan888/unifi-skill/actions/runs/39209279906)：29 成功、2 全球來源仍 DEGRADED。即使來源失敗，仍會提交**未核准**審核資料至 Draft PR，不寫入 `sync/reviewed.json`。
- RSS 唯讀掃描及知識同步是**兩套獨立 GitHub Actions**，執行時間與權限不同。前者唯讀、只上傳證據；後者為了維護 Draft PR／Issue 具有受限的 GitHub 寫入權限，但不存取任何私人 UniFi 設備。
- Issue #7 是固定維護追蹤項目；其**標題可以編輯**，工作流程不應因標題修改而建立重複 Issue。全球來源保持 DEGRADED，直到官方完整機器證據在 Runner 通過獨立驗證。
- 以下以「PR #27 尚待合併」、「25 來源」描述的部分是 2026-10-18 的**歷史里程碑**，不得當成目前部署狀態。
