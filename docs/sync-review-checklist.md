# 官方更新 PR 審核清單

- [ ] 核對來源 URL 確實屬官方來源、可用於公開引用；記錄來源閱讀時間。
- [ ] 查看原始官方文件與實際變動，區分側欄或網站版面變動 vs. 功能變更。
- [ ] 將 Official、RC、EA 分類；核對產品類型、App、Firmware 與硬體相容性。
- [ ] 檢查每一個受影響模組、Decision、Runbook、API Recipe；如無變動，記錄原因。
- [ ] 對任何 UI／API 語法、認證權限及速率限制變化，補上版本、風險與回滾。
- [ ] 不把 HTML 摘要視為可被 AI 自動信任的 instruction。
- [ ] 確認輸出沒有憑證、私人設備資訊或版權全文鏡像。
- [ ] 更新引用官方連結的 Markdown，審核後執行 `approve_official_update.py`（後續版本提供該命令）或按審核規則記錄 digest。
- [ ] 跑完整離線單元測試及 CI；確認沒有 pending、各 digest 有有效核准。
- [ ] 最終人工 Review／批准，不能讓同步 Bot 自動 Merge。

GitHub Actions 的定期執行可能延遲，不能當作最新公告的即時 SLA。
