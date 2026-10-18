# M10 — UniFi 官方 API、n8n 與自動化

**對象：** 家庭／SOHO／MSP／自架與自動化工程師。  
**狀態：** `DOC_REVIEWED`（下列端點已核對官方版本化文件）；`MOCK_TESTED`（Repo n8n Mock）；**沒有實機相容性驗證**。  
**知識適用性：** 以官方版本化文件和目標安裝版本為準；不得將某個 App/API 版的端點當作所有 UniFi 產品共用。

## 核心概念

UniFi 的管理 API 並不是單一服務：

| 官方 API | 控制面與定位 | 此處參考版本 | 重點限制 |
|---|---|---|---|
| **Network Integration API** | UniFi Network Application 的本地 REST API，可查設備、Sites、Clients、Networks，某些版本支援設定寫入 | Network v10.6.106（具體文件示例） | 實際應以安裝版 `Network > Integrations` 為準 |
| **Site Manager API** | UI Account 多站點/Host 監控，經 `api.ui.com` | Site Manager v1.0 | v1.0 Getting Started 明示 API Key 目前 read-only；後續版本需重新核對 |
| **Protect API** | Protect Application 的攝影機、NVR、Live Views 等 | v7.3.70，**Early Access（EA）文件示例** | Protect API 與 Network API 不可混用；影像/人員資料屬敏感資料 |
| **Access API** | 門禁、使用者、權限及排程整合 | 依官方 Access API PDF 與 Console 版本 | 涉及實體門鎖、緊急疏散，**不得泛用範例直接執行開門** |

### 認證與連線模式

- **本地 Network：** 在安裝版本支援的 Network Integrations UI 建立 API Key；官方文件說明 Local Application API 的說明可由 `Network > Integrations` 取得。
- **Site Manager：** UI Account 的 `unifi.ui.com > Settings > API Keys` 建立專用 Key，`X-API-Key` 認證；v1.0 官方明列目前 **read-only**，**不要套用此聲明到 Network Integration API**。
- **Cloud Connector：** Network v10.6.106 官方端點範例展示 `api.ui.com/v1/connector/consoles/{consoleId}/proxy/network/integration/v1/...`，該範例註明 Cloud Connector 需要對應 Console FW >= 5.0.3。這是該範例的前提，不應誤當所有 UniFi 裝置最低版本。
- **本地優先：** 在擁有者明確授權的私人環境才使用本地 URL、Credential Store 與 TLS CA；**公用 Skill 不請求個人 Controller 位址、API Key 或網路拓撲**。
- **Secrets：** 只透過 n8n Credential Store 或 Secret Manager 存取；不可在 JSON Workflow、Git Commit、Issue、CI Log、Webhook Query String 傳送。

## 官方建議做法

1. 以官方版本化端點、HTTP Method、Response Schema 建立 `docs/api-capabilities.json`；這是**已查證文件的索引**，不是實機證明。
2. 預設唯讀：`GET`、短逾時、Rate Limiting、分頁、重試上限、HTTP 401/403/429/5xx 錯誤分類；GET-only Workflow **不代表 API Key 只能讀**。
3. 對破壞性 POST/PATCH/DELETE 必須另有權限審批、設定備份、Idempotency 評估、Change ID、人工回滾與審計。
4. 多站點不得把 UI Account 的 Site Manager API 與每台 Console 的 Local Network API 混用。
5. Release Channel **Official / RC / EA** 分開記載。Protect v7.3.70 官方頁標為 EA，本範例不應被視為正式穩定版本。

## UI 操作路徑

- `Network > Integrations`：官方說明 Local Network API 文件位置；API Key 建立權限與介面依安裝版為準。
- `unifi.ui.com > Settings > API Keys`：Site Manager v1.0 文件列出的建立 API Key 方式。
- Protect／Access：只從實際安裝版官方文件確認角色、API 設定入口及服務埠；此處不宣稱通用 UI 路徑。

## CLI / API 替代方法

以下 **curl 模板不在此 Repo 執行**，也不包含私人 Host 或憑證；示範需由擁有者授權後在其環境自行配置。

```bash
# 變數由使用者自行設定在其私有環境；不存入公開 Repo。
# 使用受信任的 TLS 憑證，不要加 curl -k。
: "${UNIFI_NETWORK_BASE:?Set authorized Network Integration API base URL}"
: "${UNIFI_API_KEY:?Store in a private credential manager}"

curl --fail-with-body --silent --show-error --max-time 15 \
  -H "X-API-Key: ${UNIFI_API_KEY}" \
  -H "Accept: application/json" \
  "${UNIFI_NETWORK_BASE}/info"
```

Network v10.6.106 已核對下列唯讀端點：`GET /v1/info`、`GET /v1/sites`、`GET /v1/sites/{siteId}/devices`、`GET /v1/sites/{siteId}/clients`、`GET /v1/sites/{siteId}/networks`。清單端點採 `offset`、`limit`、`count`、`totalCount`，**必須依 totalCount 走完分頁**，不可將單頁統計寫成全站總量。

Site Manager v1.0 公開範例為 `GET https://api.ui.com/v1/hosts`，認證一樣採 `X-API-Key`。官方 Getting Started 列出 v1 stable 為每分鐘 10,000 次、EA 每分鐘 100 次；**此限制只屬於該頁的 Site Manager API，不能轉用到 Network 或 Protect**。遇 HTTP 429 必須尊重 `Retry-After`。

Protect API 的 GET 攝影機清單／影像快照必須比照版本化官方文件與權限核對；**影像不可預設上傳到第三方 SaaS**。Access API 只引導官方 PDF，不生成未經核對的開門指令。

## 常見情境範例

- **定期唯讀設備盤點：** `Network GET /sites` → `/devices` 分頁 → 限制輸出欄位 → 彙總數量與狀態；公開報告必須排除真實 MAC、IP、Serial 與 User ID。
- **n8n 維運告警：** 手動匯入 `recipes/n8n/unifi-inventory-mock.json`、先用合成資料驗證狀態與分頁，再視明確授權使用停用的 Live 模板。
- **跨站監控：** 考慮 Site Manager v1.0 API；不得誤稱它能在 v1.0 寫入各站 Firewall。
- **門禁／錄影：** 先審查隱私、Access 緊急模式、Retention 與審計要求，採最小權限整合，必要時要求實驗室獨立驗證。

## 風險與注意事項

API Key 外洩、授權過度、TLS 驗證停用、重試風暴、分頁不完整、敏感資料外流、破壞性 Endpoint 誤用，均應視為阻擋正式自動化的風險。使用第三方 n8n 節點或 Workflow 模板前須檢查 Node 來源與依賴版本，勿在正式 Controller 上不經審核地執行。

## 驗證方式

- 文件驗證：端點/Method/版本/Release Channel/Response Schema 有官方 URL。
- Mock：Code Node 對 `data[]`、`totalCount`、401/429、空集合、隱私遮罩的測試；不代表真人設備可用。
- Lab：測試 Gateway／App/韌體組合，證明 TLS、最小權限、分頁、告警與撤銷動作。
- Production：須另外授權、變更審批、可追溯執行紀錄與回滾；未經同意絕不試接私人環境。

## 故障排除流程

確認 API family + 版本 → 區分 Local/Cloud Connector → 核對 Endpoint/Verb → 確認權限 → TLS 憑證 → 計算 Rate Limits/Retry-After → 分頁完整性 → 最小測試集 → 觀測且保護日誌。任何異常先停用 n8n Workflow，再由所有者撤銷或輪替 Key；不要在 GitHub Issue 張貼敏感 Request Headers。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API
- https://developer.ui.com/network/v10.6.106/getinfo
- https://developer.ui.com/network/v10.6.106/getsiteoverviewpage
- https://developer.ui.com/network/v10.6.106/getadopteddeviceoverviewpage
- https://developer.ui.com/network/v10.6.106/getconnectedclientoverviewpage
- https://developer.ui.com/network/v10.6.106/getnetworksoverviewpage
- https://developer.ui.com/site-manager/v1.0.0/gettingstarted
- https://developer.ui.com/protect/v7.3.70/quick_start.ansible (**EA 範例**)
- https://assets.identity.ui.com/unifi-access/api_reference.pdf

**未驗證：** Access API 的實機認證、連接埠及安全的緊急模式自動化；Protect EA v7.3.70 的生產環境可用性；任何未被官方文件明列的 Legacy API。


### 已觀測官方來源補充索引（尚待人工內容覆核）

下列連結補齊來源監測的精確引用，狀態為 `SOURCE_OBSERVED_UNREVIEWED`。新增索引**不表示**逐頁比較已完成、版本渠道已核准或實驗室測試通過；正式來源審核仍依 Draft PR #6 與人工審核紀錄辦理。

- https://developer.ui.com/network/v10.6.106/ai-gettingstarted.md （固定版本文件；不是最新 API 或相容性保證）
- https://developer.ui.com/site-manager/v1.0.0/ai-gettingstarted.md （固定版本文件；不是最新 API 或相容性保證）
- https://developer.ui.com/protect/v7.3.70/ai-gettingstarted.md （固定版本文件；不是最新 API 或相容性保證）
- https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe （單一 Network Application RSS；Official／RC／EA 尚未核實）
