# 28 個公用來源 SHA 唯讀複核（僅供人工審核）

此手動 GitHub Actions Workflow 使用 `main` 上已存在的 `scripts/recheck_pending_sources.py`，重新安全讀取 PR #6 的 28 筆官方來源，檢查最新內容 SHA 與 Pending／Observed 是否相符。**即使 28/28 都相符，也不代表內容、版本渠道、產品相容性或審核者身分已獲核准**。

## 操作步驟

1. 開啟 [Draft PR #6](https://github.com/tAIwan888/unifi-skill/pull/6)，確認仍是 Draft、未合併，從頁面取得**完整 40 碼 HEAD SHA**；執行前請再確認 SHA 是否改變。
2. 開啟 GitHub Actions → **UniFi pending-source SHA recheck (read only)** → **Run workflow**，選擇 `main`。
3. 將剛才的完整 SHA 填入 `expected_pr6_head_sha`，執行。
4. 執行結果的 Summary 會顯示每項來源的 `MATCHES_PENDING`、`DRIFT_REQUIRES_REVIEW` 或 `UNAVAILABLE_NOT_REVIEWED`。Artifacts（14 天保存）提供 `report.md`、`report.json`，包含完整 SHA 與公開來源 Metadata，**不包含官方全文或私人資料**。
5. 若 Draft PR #6 更新、來源漂移或官方存取受阻，結果必須為非零／失敗。不要重新執行直到綠燈才自行核准；應先重新核對新的來源證據及官方內容。

## 安全邊界

- 觸發限制為 `main`，Global Workflow Token 只有 `contents: read`，兩次 checkout 都使用 `persist-credentials: false`。
- 唯一執行的來源複核 Python 腳本來自**可信的 `main` checkout**；PR #6 checkout 只作資料來源，不執行其中的程式或指令。
- 執行時依既有安全讀取器限制官方網域、HTTPS、robots、TLS、重新導向、MIME 與 timeout。沒有任何私人 Controller、API Key 或繞過方式。
- 不操作 GitHub PR、Issue、`sync/pending.json`、`sync/reviewed.json`，不做 Commit、Push 或 Merge；Actions 報告 Artifact 不是 Repository Commit。
- 此流程不會修復 Issue #7 兩個全球來源；因為它只重查 28 筆既有 Pending，不假裝全球 Release Index 完整。
- 必須由真人完成來源全文及版本渠道審核，留下審核紀錄並經專案指定的 GitHub 正式審查程序。

**目前基線：** 2026-10-18 Run #9，PR #6 HEAD `7dad85cbf528a08d2eaf98257400cf52d5d80122`、28 個 Pending、0 Reviewed、107 個 RSS 候選，28/30 來源可監測。此 SHA 只是一個歷史快照，實際執行時應由 PR 頁面重新取得。
