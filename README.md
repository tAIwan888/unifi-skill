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

## 官方 Help Center 公開 API 同步（PR #16，待合併）

舊版監測直接讀取公開 HTML，2026-10-18 的 GitHub Runner 實測為 **0/24**。PR #16 新增官方公開 Zendesk Article JSON API 作為 `help.ui.com` 文章專用讀取方法，**已在獨立 PR 實測 19/19 篇 Help Center 文章全部成功**。

完整 24 個來源測試結果：**19 個成功、5 個無法驗證**，整體仍標記 `DEGRADED`；3 個 Developer Portal URL HTTP 404、Release Index 與 Downloads 頁面沒有可讀版本條目。測試紀錄：[GitHub Runner 24-source audit](https://github.com/tAIwan888/unifi-skill/actions/runs/39108343611)。

新方法先尊重 robots.txt，使用同官方網域之 HTTPS、驗證文章 ID／發布狀態／語系，僅保留內容 SHA-256、文章標題、官方更新日期與字數；不提交官方文章全文，也不使用任何使用者 Controller 資料。

**目前功能仍在 [PR #16](https://github.com/tAIwan888/unifi-skill/pull/16)，尚未加入正式排程。** 未經人工審核的 Fingerprint 不會自動更新 M01–M10；正式分支最新同步狀態仍以當期 GitHub Actions 與健康 PR 為準。
