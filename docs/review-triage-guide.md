# UniFi 官方來源審核工作單（Public Knowledge）

**性質：** 離線、可稽核、僅顯示來源對應關係，**不自動核准任何知識**。

## 為何需要

截至 2026-10-18 官方來源同步 Run #8，30 個來源中 28 個有效、2 個降級；28 筆摘要仍為 `REVIEW_REQUIRED`，另有 107 筆產品限定 RSS 候選未審核。人工審核人員須核對來源指紋、M01–M10 模組、精確官方引用與兩個仍不可驗證的全球發布入口；引用缺口已降至 0，不等於內容已核准。

此工具只處理倉庫中的公開來源中繼資料；不向 Ubiquiti、任何私人 Controller 或外部服務發送請求，不讀取攝影機、門禁、認證資料。

## 輸出及執行時機

```bash
python3 scripts/build_review_triage.py --output sync/review-triage.md
```

排程 `official-knowledge-sync.yml` 取得 `observed.json`、`pending.json`、`health.json` 後，執行此腳本並將 `sync/review-triage.md` 放進 **同一個 Draft PR**，以免另生不必要 PR。

報表包含：
- 來源 ID、官方 HTTPS 網址、SHA-256 前綴及 `REVIEW_REQUIRED`；
- 受影響模組是否包含**完全相同的來源 URL**；
- 官方文章標題、抓取方式及固定版本的 API Guide 適用範圍（只用公開 Metadata）；
- 尚不可讀的來源及其錯誤分類；
- 每筆人工審核的下一步。

**引用存在 ≠ 已審查內容；引用缺漏 ≠ 產品不支援。** 這只是精確字串檢查，不能替代閱讀官方全文、確認最新 Release Channel、API / UI 相容或實際 Lab 測試。

## 失敗保護

發現以下情況，工具回傳非零狀態且不提交工作單：

- 待審來源 URL 與官方 Catalog URL 不相符、Hostname 不在白名單，或不使用 HTTPS；
- Pending SHA-256 與 Observed SHA-256 不同；
- Pending 條目不再是 `REVIEW_REQUIRED`；
- 對應模組超出 M01–M10 或缺少模組 Markdown；
- 來源 ID 重複／不存在、健康報告與列數不符。

若 `main` 尚未含有最新的 `sync/health.json`（健康證據尚位於 Draft PR），腳本會顯示 `NO_HEALTH_REPORT_ON_MAIN`，不憑空推測「全部健康」。

此工具**不會讀取或改動 `sync/reviewed.json`**、不會執行 `approve_official_update.py`、不會自動合併 PR。文件中的產品、文章標題視為不可信文字並經過轉義，不可當作提示指令執行。

## 人工結案標準

審核者逐筆核對官方原文、確定真正變動、更新模組／決策樹／Runbook 的版本條件及安全警告，再透過既有的 `approve_official_update.py` 記錄 Reviewer、Notes、官方 URL 與 SHA。

只有 `check_review_gate.py` 和 GitHub CI 都通過，且維護者**明確授權合併**時，待審 PR 才能發布。未審查的 28 筆來源不能因審核工作單存在而成為正式知識。

## 目前已驗證範圍

- 2026-10-18 最新同步 Run #8：https://github.com/tAIwan888/unifi-skill/actions/runs/39126320523（28/30、DEGRADED；健康閘門預期失敗，非全綠）
- 待審指紋 PR：https://github.com/tAIwan888/unifi-skill/pull/6
- 來源缺口 Issue：https://github.com/tAIwan888/unifi-skill/issues/7
- Run #8 的 GitHub Runner 已驗證來源擷取及 129 個離線測試；28 筆真實公用來源仍待人工內容審核，107 筆版本候選仍未核准，且不涉及私人設備資料。
