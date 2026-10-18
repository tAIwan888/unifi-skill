# Changelog

## 0.7.0-public-draft — 2026-10-18

- M01–M10 十個公用知識模組已於正式 `main` 完成首輪文件深化；`DOC_REVIEWED` **不等於**實驗室或現場驗證。
- 官方來源監測已部署並首次執行。GitHub Runner 實測 24 個來源均未取得合格技術內容，已建立降級健康 PR #6、告警 Issue #7；Fail-Closed，不聲稱同步成功。
- 新增離線知識結構／官方來源白名單／版本狀態誠實性驗證；CI 自動阻擋個人資料依賴與不可信來源網址。
- 更新 manifest/README，移除「首次同步尚未啟用」及「官方下載頁已成功取得版本」的過時描述。

## 0.5.0-public-draft — 2026-10-18
- 新增 10 個公用模組基礎框架、4 張決策樹、5 份 Runbook。
- 官方來源監測從 5 增至 23，使用只讀 HTTPS、SHA-256 與 Draft PR 人工審核管線。
- 新增停用的 n8n Live GET 模板、離線 Mock Workflow 與安全驗證。
- 官方 Release Channel、版本相容性、資訊最小化納入治理規則。
- 首次線上同步及 Repository 的 Actions PR 權限尚待實際驗證。

## 0.4.0-public-draft
- 初版公用官方同步設計與審核規則。
