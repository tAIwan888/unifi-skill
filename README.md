# UniFi Skill — 公用知識庫

**版本**：v0.7.0-public-draft（M01–M10 公用內容已納入 `main`）  
**基準日期**：2026-10-18  
**狀態**：十個知識模組均具通用文件與部分合成測試；**尚未完整實驗室／生產驗收**。官方版本監測已部署，但目前對 24 個來源皆無法取得合格內容（2026-10-18 實測快照），同步狀態為 `DEGRADED`。

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
`sync/sources.json` 列 24 個公開的官方來源，GitHub Actions 每週二／五 UTC 02:17 及手動觸發檢查。程式只讀公開網站、比對 SHA-256、產生待審核 Draft PR 並記錄健康度；若所有來源失效則 Fail-Closed，不宣稱同步成功。**無自動合併、無自動改寫正式知識、無私人 UniFi 存取**。只有在 Workflow 位於預設分支且 Actions 設定允許時，排程才會生效。

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
- `sync/version-candidates.json` 僅記錄未審核的版本候選，不能當最新穩定版公告。
- 來源全數失敗時，Workflow 在提交健康報告後標示失敗，等待人工處理；不自動變更知識。

## 知識庫品質驗證
```bash
python3 scripts/validate_knowledge.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_workflows.js
python3 scripts/check_review_gate.py
```
上述驗證只確認**文件結構與離線行為**，不代表 UniFi 官方網站現在可達，也不代表任何型號已經實測。

官方來源監測於 2026-10-18 的實際結果：24 個來源中 0 個取得合格內容；參見 [首次降級來源監測](https://github.com/tAIwan888/unifi-skill/actions/runs/39103031302)、[維運 Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7) 與 [健康報告 PR #6](https://github.com/tAIwan888/unifi-skill/pull/6)。請以 GitHub Actions 的**最新執行結果**為現況，不要把這份歷史快照視為即時同步成功證明。

## 官方公開 API／Developer Markdown 同步（PR #16，待合併）

2026-10-18 GitHub Runner 完整實測：**24 個官方來源有 22 個可讀且通過來源內容驗證**（19 個 Help Center Article JSON、3 個固定版本 Developer Markdown）。剩下 2 個是 Release Index 和 Software Downloads 的版本資訊不足，因此整體健康仍是 `DEGRADED`。

- [Help Center 19/19 成功](https://github.com/tAIwan888/unifi-skill/actions/runs/39107846237)
- [Developer Markdown 3/3 成功](https://github.com/tAIwan888/unifi-skill/actions/runs/39108698167)
- [完整 24-source Audit：22/24 成功，2 來源未通過](https://github.com/tAIwan888/unifi-skill/actions/runs/39109033130)

監測程式使用固定 HTTPS 官方白名單、Article ID／發布狀態、Markdown URL 版本／產品類別、robots.txt RFC 9309 適當處理與內容指紋；僅保存公開文章中繼資料，不提交原文全文。首次成功將形成 `REVIEW_REQUIRED`，**不能自動被視為目前 UniFi OS、Firmware、API 的最新正式版本**。

**這些修復目前位於 [PR #16](https://github.com/tAIwan888/unifi-skill/pull/16)，並非已部署的正式 `main`。** 目前 `manifest.json` 的 0/24 是上一輪實際排程的歷史快照，待 PR 合併、正式同步驗收後再更新，不可冒充即時成功。
