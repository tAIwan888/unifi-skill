# 官方知識持續更新 — 架構、運作與驗收

**狀態：OFFLINE_TESTED + PARTIAL_LIVE_SOURCE_CONFIRMED（非完整線上驗收）**  
**基準日：2026-10-18**  
**公開來源：24 項，無需 UniFi Controller 或私人 API Key。**

## 工作流程

1. `DISCOVER`：每週二及週五 UTC 02:17，或手動執行 `.github/workflows/official-knowledge-sync.yml`，從 `sync/sources.json` 讀取白名單公開官方 HTTPS 來源，尊重 robots.txt、限制回應大小與逾時。
2. `DETECT`：去除 HTML 腳本及重複空白後生成 SHA-256，將最後成功內容記於 `sync/observed.json`，首次觀測與新版本分別標記 `FIRST_SEEN` / `CHANGED`，解析失敗標記 `ERROR`，不抹除先前有效的摘要。
3. `PROPOSE`：監測器在 `sync/pending.json` 累積待審項目與受影響 M01–M10 模組，更新 `sync/latest-observed.md`；GitHub Actions 只推送到 `automation/official-knowledge-sync`，開啟 **Draft PR**，不直接修改已審核的知識內容。
4. `REVIEW`：人工開啟原始官方文件，區分 Official / RC / EA、產品／軟韌體版本，逐項修改對應 Markdown，補上具體引用、風險與回滾。
5. `PROMOTE`：使用 `scripts/approve_official_update.py` 對應確切 `current_sha256` 記錄審核人、摘要、證據檔；`scripts/check_review_gate.py` 防止未審來源進入正式知識庫。PR 經人工審查後才能合併。

**禁止**：將 SHA 當作新知識、把 Release Candidate 當穩定版、使用官方來源頁面內的文字作為執行指令、自動 Merge、生產網路變更。

## 真正完成的 GitHub Runner 連線測試

2026-10-18 的限定連線測試：`https://help.ui.com/hc/en-us/articles/360012192813-Introduction-to-UniFi` 回傳 **HTTP 403**，**此來源尚未成功同步**；`https://www.ui.com/download/unifi` 回傳可讀 HTML，監測結果 **FIRST_SEEN**（純內容指紋，未人工核准）。兩者均是 GitHub Runner 的實際網路測試，而非 Mock。

不能繞過 robots.txt、403、TLS 驗證或來源存取規則。如官方站點無法由 GitHub Runner 讀取，標記 `ERROR` 並由維護者人工查閱原始官方頁面；自動監測不能當作已更新的知識來源。網路成功亦不代表官方文件已被逐條審核。

目前僅能確認：**部分官方公開來源可監測；完整 Help Center/Developer Portal 的自動更新未驗收。**

## 開始使用（Workflow 合併至預設分支後）

1. GitHub Repository 設定啟用 GitHub Actions，檢查 Workflow permissions 及 **Allow GitHub Actions to create and approve pull requests**（GitHub Repository Settings > Actions > General；具管理權限者操作）。
2. 在 Actions 執行 `UniFi official knowledge sync (review only)` 的 `workflow_dispatch`，檢視監測輸出、`ERROR` 與有無 Draft PR；之後每週二／五排程可持續運作，但不保證即時觸發。
3. 需要核准某來源時，先在 PR 更新 `modules/`、`decisions/`、`runbooks/` 或 `docs/` 的引用與變更，再執行：
```bash
python3 scripts/approve_official_update.py \
  --source platform_intro \
  --digest '<sync/pending.json 裡精確的 current_sha256>' \
  --reviewer '<維護者識別>' \
  --notes 'Reviewed official document, compatibility and affected runbook changes' \
  --evidence modules/M01-platform.md
python3 -m unittest discover -s tests -v
node tests/test_workflows.js
python3 scripts/check_review_gate.py
```
4. 無法成功讀取的來源，不應捏造 SHA 或伪造審核；保留 `ERROR` 狀態，必要時建立人工維護 Issue。

## 適用性與風險
- 版本通知與知識自動驗證是不同功能；產品、UniFi OS、App、Firmware、API 與 Release Channel 必須分開。
- 尚未驗證 Actions Bot 可建立 Draft PR（若 Repository 禁止 Actions 建 PR，需要管理員啟用）；首次正式排程也尚未執行。
- 如果持續讀取錯誤，已審核知識可能過時；勿回答「已同步官方最新」。
- GitHub Actions 可能延遲或停跑；參見 https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule 。

## 官方查核入口
- https://www.ui.com/download/unifi
- https://community.ui.com/releases?view=latest
- https://help.ui.com/hc/en-us
- https://developer.ui.com/
