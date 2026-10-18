# UniFi Skill 證據與驗收規範

## 支援分類
- **OFFICIAL_SUPPORTED**：當前產品／版本的官方文件直接支持，引用精確連結。
- **ENGINEERING_RECOMMENDATION**：通用工程設計；明確標示為非官方，不能冒充原廠建議。
- **COMMUNITY_PRACTICE**：社群使用方式，必須明示非官方、可重現條件和風險。
- **NEEDS_LAB_VALIDATION**：官方未明確表述或需特殊裝置驗證。

## 測試分級
`DOC_REVIEWED` ≠ `MOCK_TESTED` ≠ `LAB_TESTED` ≠ `PRODUCTION_VERIFIED`。
- 文檔層確認：查到對應版本的官方原文連結。
- Mock：測試資料模式、輸入輸出、錯誤分支，不證明 UniFi 真機相容。
- Lab：有模型、韌體、UniFi OS / App 與結果紀錄。
- Production：必須獲明確授權、可稽核、能回滾，並記錄維護窗口。

## Runbook 必填
前置條件、UI 路徑／版本差異、步驟、風險／權限、驗證（正反例）、回滾、來源。Access 緊急模式與消防疏散必須另行評估生命安全和法規，禁止簡化成通用自動化。

## 個人資訊治理
公用模式不蒐集任何人的 Console IP、MAC、Serial、Token、設定匯出、拓撲；用 `example.invalid`、RFC 5737 IP 或合成資料。任何私人環境診斷都要由個案提出且授權後才做。
