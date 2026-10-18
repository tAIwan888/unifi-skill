# UniFi Official API / n8n Recipes

- `n8n/unifi-inventory-mock.json`：完全離線，三筆虛構裝置資訊，手動觸發，僅輸出彙總。
- `n8n/unifi-inventory-live.json`：**預設停用**，僅在有明確授權的使用者部署時才依其 Network 版本、Site ID、HTTPS/CA 和 n8n Credential Store 配置；示例使用 `example.invalid` 與虛構 UUID。
- `js/inventory-transform.js`：無副作用的摘要邏輯，輸出不含 Device MAC、IP、Serial、Host Name。

## 安全邊界
GET-only 是流程行為而非 API Key 最小權限保證。請由使用者環境管理員另行驗證 Key 的權限、速率限制、證書鏈與回應分頁；不可在此公用 Repo 存 Secret。
`hasMoreOrUnknownPages=true` 時不允許把單頁結果冒充完整庫存。
本公開範例沒有自動排程和任何私人 UniFi Gateway 連線，不代表實機驗收。

官方：
- https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API
- https://developer.ui.com/network
