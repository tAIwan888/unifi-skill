# RB05 — n8n UniFi 官方 API Read-only Recipe
**support_class:** 官方 API 概念 + 非官方 n8n 編排範例。**test_status:** MOCK_TESTED / NO_LIVE_TEST。

## 前置條件
先以 Repo 中合成 Mock Flow 測試，不需任何私人 UniFi API Key。正式連線需另由環境擁有者授權，確認 UniFi API 文件版本、HTTPS 憑證、可行之最小權限與允許的來源 IP。

## 步驟
1. 匯入 `recipes/n8n/unifi-inventory-mock.json`，以 Manual Trigger 測試脫敏假資料；確認計數、未知狀態與分頁警示。
2. 若有明確授權，再複製 `recipes/n8n/unifi-inventory-live.json` 並於本機 n8n Credential Store 保存金鑰（不要記在 Workflow JSON），確認官方 API 路徑與實際版本。
3. 保持 Live Flow 預設停用。所有 HTTP Request 僅 GET；設置 Timeout、Rate Limit、TLS 憑證驗證與 401/403/429 錯誤處理。
4. 由環境管理員在測試 Site 驗證資料結構與 Cursor/Pagination；勿把 GET-only 視為 API Key 權限只讀。
5. 產出不含 MAC、IP、User ID、Secret 的彙總資料，再根據需要決定審計／排程配置。

## 驗證
Mock 測試 PASS，Live 必須另記平台/API 版本、HTTP 狀態、回傳欄位、分頁完整性及遮罩，才能宣稱正式整合完成。

## 風險與回滾
API Key 洩漏、TLS 略過及憑證過權均為資安風險。出現異常立刻停用 n8n Workflow、撤銷專用 Key、調查 Log；不得在未授權環境重放請求。

官方：
- https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API
- https://developer.ui.com/network
