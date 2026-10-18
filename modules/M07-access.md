# M07 — UniFi Access：Door Hub／Reader／門鎖／生命安全

**用途：** 公用架構知識與高風險操作阻擋規則，**不得將本文當消防／門禁施工規範**。  
**證據：** 官方 Help Center（2026-10-18 核對），`DOC_REVIEWED`、`LAB_NOT_RUN`。  
**操作邊界：** 不提供 Live Unlock、Emergency Lockdown、Evacuation 或 Door Wiring 的自動化指令；實際安裝須具資格的專業人員核對當地消防／建築／逃生要求。

## 學習目標與完成標準

1. 區分相容 UniFi Access Console、Control Hub、Reader、Door Lock、PoE/Power Supply、Request to Exit 與 Door Position Sensor 的分工。
2. 能選擇 Door／Gate／Elevator Hub 類別並認識對應的 Input/Output 支援差異。
3. 能區分 **Fail-safe（斷電開鎖）** 和 **Fail-secure（斷電維持上鎖）**，不得任意將其套用於應急出口。
4. 能說明 Emergency Evacuation、Emergency Lockdown 與 Fire Panel 連動的覆蓋優先權及法規風險。
5. 能從 RBAC/門禁權限、稽核記錄、訪客憑證與撤銷機制設計最小權限。

**完成標準：** 使用合成 Door/Reader/Lock/Hub 與火警模擬案例，正確指出需要現場消防承包商審查的項目；任何不具法規依據的自動 Lockdown/Unlock 流程都必須停止並請求明確安全審批。

## 核心概念

| 元件／功能 | 官方定位 | 重要限制 |
|---|---|---|
| UniFi Console | 託管 Access App 的相容 Console | 不能假設任何 Network Controller 都能安裝 Access |
| Control Hub | 連接 Door Lock／Reader／Exit／Position Sensor／Fire Panel | Door/Gate/Elevator Hub I/O 不同，須查 Tech Specs |
| Reader | NFC、PIN、訪客／授權方式依 Reader 型號 | Reader 不是安全出口唯一措施 |
| Fail-safe / Fail-secure | 前者在失電時釋放門鎖；後者在失電時保持鎖定 | 逃生動線／防火門需遵照當地規範並專業審查，不以行銷規格替代檢驗 |
| Request-to-Exit / Panic Bar | 提供出口使用，部分連接方式可直接切斷磁力鎖供電 | Life Safety、無障礙及清楚標示受當地法規規範 |
| Emergency Evacuation / Lockdown | 官方支援按站點／門設定緊急模式與 Fire Panel 自動觸發 | 緊急模式覆寫一般權限；錯誤自動化可能危及人身安全 |
| Fire Panel Terminal | 消防設備接入 Hub，觸發特定緊急模式 | 官方說明 Fire Panel 觸發的 Emergency Mode **不可由 Access App／Reader 直接解除** |

官方：
- https://help.ui.com/hc/en-us/articles/17452334269975-Getting-Started-with-UniFi-Access
- https://help.ui.com/hc/en-us/articles/23964054398871-Choosing-a-UniFi-Access-Control-Hub
- https://help.ui.com/hc/en-us/articles/17784702059415-Activating-Emergency-Mode-in-UniFi-Access
- https://help.ui.com/hc/en-us/articles/29703866324887-Configuring-UniFi-Access-Control-Hub-Terminals

## 官方建議做法

1. **資格與合規先行：** Door/Fire Panel/Exit Relay 電氣接線、當地 Fire/Building Code、無障礙及緊急出口必須由有資格的專業人員規劃驗證；不可只照網路教學連線。
2. **選相容 Host：** 比對 Access App、Hub、Reader、Lock、PoE 等設備之支援型號與功率限制，獨立驗證門禁失電與網路斷線情境。
3. **門鎖分類：** Fail-safe 斷電開鎖、Fail-secure 斷電保持鎖定；不同門位可能有不同法規限制，不可從「較安全」這個字判定唯一答案。
4. **Role 與 Credentials：** 按物理分區、時段、訪客最小權限配置，不共用管理員憑證。撤銷失竊 Card/Keyfob 及離職者存取，保留審計證據。
5. **緊急模式：** Evacuation 與 Lockdown 的預期狀態應在消防設計中決定；Fire Panel 的 Emergency Terminal 觸發行為不等同一般使用者可逆的 Unlock 操作。
6. **Fail-closed Automation：** 公用 Skill 可以提供離線 Simulation、API 文件索引與人工核對清單，但**不產生可直接執行的開門、全面鎖門或解除火警模式 Recipe**。
7. **資安／隱私：** Visitor/Access Logs、面部或照片、卡片識別碼應按資料最小化保留；不得上傳至公開 GitHub Issue 或整合 Workflow 的明文 Output。

## UI 操作路徑

- `UniFi Access > Devices`：依 Hub/Reader 型號與版本管理門、接線與管理狀態。
- `UniFi Access > Dashboard > Emergency Mode`：官方提供站點級 Evacuation／Lockdown，**本 Skill 僅介紹概念，不指示實際觸發**。
- `UniFi Access > Devices > [Hub] > Emergency`：官方文件的 Fire Panel 自動模式設定入口示例；真實配置須現場消防驗收。
- 身分與角色配置應依當版 Access / UniFi OS / Fabrics RBAC 模型確認，不假設所有版本使用相同 Role 路徑。

## CLI / API 替代方法

- 官方 Access API PDF：https://assets.identity.ui.com/unifi-access/api_reference.pdf 。**文件化端點不等於可安全直接連線**。
- 在不同官方資料中曾出現 Access API 連接埠描述差異；具體 HTTPS Port／Auth／Permission 一律依安裝版官方說明核實，**不能自行猜測固定埠**。
- 只允許使用合成 Door Status/Access Log 做離線研究；Access Emergency/Unlock API 即便存在，也須先通過專業現場設計與個別授權，此公用 Skill 不產生可執行寫入示例。
- 不保存真實人員識別、刷卡歷史、NFC Token、PII 或 Lock Control Key。

## 常見情境範例

**門禁設備選型：** 一個普通門、雙門、Gate 與 Elevator 有不同 Hub/I/O/電源／Exit Requirements；不可只按 Reader 外觀決定 Hub。

**停電導致門鎖狀態改變：** 先由施工及消防專業人員決定 fail-safe/secure 和逃生要求，再在隔離驗收場域實測，不應盲目遠端切換配置。

**火警介面自動化提案：** 必須先明確 Fire Panel Relay 訊號、法規、備援電源、Emergency Override 和現場測試驗收，沒有設計圖／批准前不得執行任何 Door Emergency API。

## 風險與注意事項

- **人身安全高風險**：錯誤 Lockdown/Fire Egress 設計可能妨礙緊急逃生。當地規範和合格驗收高於通用 Skill 的推論。
- Fail-safe 與 Fail-secure 在失電時有不同物理效果，不能混用；Door Hub 電力與 Relay 型式須依實際 Hardware Guide。
- Access 資料含員工與訪客存取時間、身份及可能生物辨識資訊，需遵守隱私與 Retention Policy。
- 官方 UL 294 第 1 級合規說明不表示每個安裝場域已符合當地消防建築法規。
- 不應在外部 SaaS／GitHub Actions 對私人門禁做未經批准的自動 Unlock、Emergency Mode 切換或敏感日誌外傳。

## 驗證方式

在隔離、獲專業審批的 Lab 驗證：設備型號與 App/Firmware 相容、PoE Budget、Lock/Panic Hardware 規格、Request to Exit、Door Position、Fire Panel 觸發後實際狀態、網路/斷電、誰有權撤銷或緊急處置。測試記錄必須描述通用場景，不公開真實人員和場域身份。

**公用文件通過不等於實際安全認證或施工驗收。**

## 故障排除流程

確認 Door/Hub/Reader 相容性 → Power/PoE → Network Link/Adoption → Reader Credential/Role → Door Sensor → Fail-safe/Secure Type → Fire Panel 覆寫狀態 → 授權專業人員現場評估。若涉及出口受阻或 Emergency Relay 異常，**立刻交由現場安全管理／消防人員處理**，不以遠端腳本試錯。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/17452334269975-Getting-Started-with-UniFi-Access
- https://help.ui.com/hc/en-us/articles/23964054398871-Choosing-a-UniFi-Access-Control-Hub
- https://help.ui.com/hc/en-us/articles/25740782409495-Choosing-a-UniFi-Access-Lock
- https://help.ui.com/hc/en-us/articles/25769197902615-Wiring-Exit-and-Entry-Request-Devices-to-the-UniFi-Access-Control-Hub
- https://help.ui.com/hc/en-us/articles/17784702059415-Activating-Emergency-Mode-in-UniFi-Access
- https://help.ui.com/hc/en-us/articles/29703866324887-Configuring-UniFi-Access-Control-Hub-Terminals
- https://help.ui.com/hc/en-us/articles/24999589457175-Secure-Reliable-and-UL-294-Compliant-Door-Access-Control-with-UniFi-Access
- https://assets.identity.ui.com/unifi-access/api_reference.pdf

## 待補實作

型號級 Door/Reader/Lock 相容性、法規及 UL294/Local Fire Code 差異、Fail-safe/secure 現場驗收、脫敏 API 唯讀能力，都要進一步依官方資料與獨立專業測試核對；不可宣稱自動具備門禁控制授權。
