# UniFi Skill — 公用知識庫

**版本**：v0.5-public-draft（GitHub PR 審核中）  
**基準日期**：2026-10-18  
**狀態**：公共知識框架、離線範例與官方版本監測；**未完成全模組深入驗收、未完成首次官方線上監測**。

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
`sync/sources.json` 列 23 個公開的官方來源，GitHub Actions 每週二／五 UTC 02:17 及手動觸發檢查。程式只讀公開網站、比對 SHA-256、產生待審核 Draft PR。**無自動合併、無自動改寫正式知識、無私人 UniFi 存取**。只有在 Workflow 位於預設分支且 Actions 設定允許時，排程才會生效。

## 本地驗證
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_workflows.js
python3 scripts/check_review_gate.py
```

所有正式設定都必須按產品、UniFi OS / App / Firmware / API 版本與 Release Channel 驗證；Mock PASS 不代表實機 PASS。
