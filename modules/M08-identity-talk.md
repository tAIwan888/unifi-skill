# M08 — UniFi Endpoint / Identity / Fabrics、Talk、Connect 與 EV

**定位：** 公用知識模組，橫跨零信任身分、VoIP、數位看板、照明、EV 充電。  
**來源：** Ubiquiti 官方 Help Center（2026-10-18 核對），`DOC_REVIEWED`，未進行付費服務啟用／現場設備測試。  
**隱私界線：** 不要求使用者 IdP Tenant、員工名冊、Talk 號碼、充電紀錄、私有 API Token。

## 學習目標與完成標準

1. 能區分 **UniFi Endpoint（用戶端 App）**、**UniFi Fabrics（跨站 Trust Domain）**、**Identity Provider (IdP)**、**RBAC／SCIM／SAML** 的角色。
2. 了解 Talk Subscription、已解鎖電話、第三方 SIP 與地區支援差異。
3. 說明 Connect 作為管理數位看板、A/V、照明及 EV 充電的應用，其 Console 相容性／內容格式／充電安全界線。
4. 對身份生命週期、離職撤權、無障礙與緊急通訊/物理設備提供驗證與回滾方案。

**完成標準：** 合成多站點案例可列出 Trust Domain、IdP Binding、端點服務及授權矩陣；Talk 新部署在不支援的區域不得承諾官方 Talk Subscription；EV 的充電與停用需另行確認現場電氣安全及使用者授權。

## 核心概念

| 平台 | 官方能力與定位 | 版本／區域／高風險限制 |
|---|---|---|
| UniFi Endpoint | 在支援平台提供 One-Click WiFi/VPN、Smart Door Access 等使用者入口 | 多站零信任須核對 Fabric 和 Consolidated People Management；Talk Softphone、EV Charging、Camera Sharing、File Access 官方標示 Single-Site Only |
| UniFi Fabrics | 建立跨多 Site 的 Trust Domain、People/Role/Permission、Identity Provider 整合 | 官方入門最低 UniFi OS **4.4+**；IdP Binding 還需**至少一台符合官方清單的 Console**，不能只看 OS 版本 |
| Identity / IdP | Entra、Google Workspace、LDAP/AD 等（按官方支援表），可使用 SAML SSO 與 SCIM 同步 | IdP 種類、SKU/License/Scope 不同；不能推定所有 IdP 支援每項同步 |
| UniFi Talk | 在相容 UniFi Console 上託管 VoIP，用官方 Talk Subscription 或第三方 SIP | 官方 Talk 訂閱僅在 US、UK、Canada 提供；全球可依條件使用解鎖 Talk Phone 加第三方 SIP |
| UniFi Connect | 支援的 Console 託管 Connect App，管理 A/V、Digital Signage、Lighting、EV Station | 不是所有 UniFi Console／所有設備可用；內容格式/Codec、控制界線與電力規格需逐型號核對 |
| EV Station | Connect 管理充電排程、使用者認證及看板 | 充電器涉及電氣安全、計費與實體操作；不產生預設可啟動／停止充電的公用自動化 |

官方：
- https://help.ui.com/hc/en-us/articles/16936895868823-UniFi-Endpoint-Overview
- https://help.ui.com/hc/en-us/articles/30979808349463-Getting-Started-with-UniFi-Fabrics
- https://help.ui.com/hc/en-us/articles/27057211577751-Getting-Started-with-UniFi-Talk
- https://help.ui.com/hc/en-us/articles/21171115391255-Getting-Started-with-UniFi-Connect

## 官方建議做法

1. **先分開 Admin 與 User/Member：** 在 Site / Fabric 以最小權限分配 Management Roles 與 Endpoint Services Permissions，不以同一最高權限帳號提供所有使用者服務。
2. **多站 Trust Domain：** 不要假設多個 UniFi Site 都應屬同一 Fabric。對不同客戶、不同法規或不同 IdP 的站點，應各自評估 Trust Domain 邊界。
3. **IdP Binding：** UniFi Fabrics 必須符合 Consoles、OS/功能與 Consolidated People Management 條件。SAML/SCIM 的實際支援項目需核對官方 IdP Integration 文件；先試辦少量合成 User，再批准正式人員同步。
4. **Endpoint One-Click WiFi/VPN：** 按 Role 與 Site Scope 發行，不把授權 Endpoint App 視為已授權存取所有內網。Smart Door Access 的 Remote Unlock 是高風險功能，官方說明預設停用；此公用 Skill 不啟動它。
5. **Talk：** 先檢查 Console、Phone Lock 狀態、地區、號碼、Subscription/Provider；不能將 US/UK/Canada 的官方 Subscription 定價與緊急電話保證外推全球。
6. **Connect：** 選對相容 Console、Device 類型與媒體規格（Codec/Size/Resolution）；EV Charging 由現場電氣承包人員審查供電、停電、充電服務與計費規則。
7. **審計：** 角色新增/撤銷、電話號碼/通話、數位看板素材與 EV 充電資料可能含個資或商業資料；指定保留期，保護輸出，不放進公用 GitHub Actions。

## UI 操作路徑

- `Site Manager > Fabrics > [Fabric] > Settings > Identity`：官方 IdP Binding 與 UniFi Endpoint Services 的入口示例；僅適用符合當版支援的 Fabrics。
- `Site Manager > Fabrics > [Fabric] > People`：跨站 People 與 Role/Permission 管理。
- `UniFi Network > Settings > Identity`：官方描述的 Single-Site Endpoint 設定入口示例；版本與功能可能不同。
- `UniFi Talk`：依 Console/Region/Talk App UI 選擇 Subscription、Phone、Extension、Group 與第三方 SIP。
- `UniFi Connect > Devices / Media Content / Automations`：依 Device Type 配置 Display/EV，僅在合法支援且經授權時操作。

## CLI / API 替代方法

- 如需讀取 Site/Host 狀態，優先使用 M10 的官方版本化 Site Manager GET API 及允許的本地 API；不要把 Third-Party Unofficial/Legacy Endpoint 當穩定介面。
- SCIM／SAML／IdP Sync 為帳號生命週期高影響服務，公用 Repo 只提供 Mock Identity／Role Schema，禁止提交真實 Access Token、SCIM Secret、Directory Export 或員工資料。
- Talk Dial、Call Forwarding、EV Charging Start/Stop、Connect Playlist 上架及 Remote Door Unlock 屬外部影響或安全敏感行為，不提供未經明確授權的執行式 Recipe。

## 常見情境範例

**多客戶 MSP：** 客戶 A、B 若擁有不同 IdP/政策，需明確隔離 Fabric/Trust Domain 及 Admin Scope；不能因 Site Manager 可同時看到站點，就假定能共用全部使用者身份。

**跨站員工 VPN：** 先確認 Fabric 角色、One-Click VPN Scope、MFA/IdP 同步與分流方式，再以測試身分驗證 Only Authorized Sites 的連線。

**區域不支援 Talk Subscription：** 應改為評估已解鎖 Talk Phone + 第三方 SIP（若當地法規及設備支援），而不是承諾訂閱服務可以在所有地區開通。

**校園 Connect/EV：** Digital Signage 需媒體格式/大小正確；EV 充電時程、使用權限與計費由建築電氣／營運團隊批准，不能以一般 n8n 自動化繞過安全控制。

## 風險與注意事項

- 同一人擁有多個 Role 時，實際權限可能是更寬鬆角色的聯集，需避免誤授予跨站存取。
- UniFi OS 4.4+ 是官方入門對 Fabrics 的最低 OS 門檻，**不是任何型號/訂閱/區域都能使用所有 IdP/Endpoint 功能的保證**。
- 任何涉及生物辨識、門禁 Remote Unlock、Talk Emergency Calling 或實體 EV 充電行為都必須加入專業合規及人身安全審查。
- Talk Subscription 官方提供地區可能改變，應由官方最新清單與 Telephony 法規確認，不能以文檔版次假設永久有效。
- 公用知識不收集你的 UniFi App/OS 版本、私人 IdP 或人員資料；這些只在未來有明確授權的個別部署才可能需要。

## 驗證方式

`Site/Fabric Trust Domain / Console Compat / IdP Type & License / RBAC / MFA / Endpoint Allowed Services / Talk Region / Connect Device Support / EV Professional Safety` 逐項標明實際驗證層級。用合成 User、合成電話號碼、合成 EV 站點做設計審查，不宣稱真實 IdP／Talk／EV 已部署。

## 故障排除流程

UniFi OS & App Version → Console Support → Site/Fabric/Trust Domain → IdP Binding/MFA/SCIM → Role and Site Scope → Endpoint User Invite → Single-Site vs Fabric Service Limit → Talk Region/Subscription/SIP → Connect App/Device/Media → EV Power/Safety；高風險症狀交由授權專業人員處理。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/16936895868823-UniFi-Endpoint-Overview
- https://help.ui.com/hc/en-us/articles/30979808349463-Getting-Started-with-UniFi-Fabrics
- https://help.ui.com/hc/en-us/articles/31557442664983-Configuring-UniFi-Endpoint-For-Zero-Trust-Network-Access-ZTNA
- https://help.ui.com/hc/en-us/articles/30967924245527-Binding-an-Identity-Provider-IdP-To-A-UniFi-Fabric
- https://help.ui.com/hc/en-us/articles/31557407384343-Managing-UniFi-Fabric-People-Roles-and-Permissions
- https://help.ui.com/hc/en-us/articles/27057211577751-Getting-Started-with-UniFi-Talk
- https://help.ui.com/hc/en-us/articles/360058776614-Manage-UniFi-Talk-Subscriptions
- https://help.ui.com/hc/en-us/articles/21171115391255-Getting-Started-with-UniFi-Connect
- https://help.ui.com/hc/en-us/articles/15670911603223-Understanding-Media-Compatibility-for-UniFi-Connect
- https://help.ui.com/hc/en-us/articles/21170042012439-Managing-EV-Stations-in-UniFi-Connect

## 待補實作

Fabric 的不同版本與支援型號矩陣、Talk Region/Subscriptions 最新政策、Connect／EV 型號及 IoT Media/Charging 的 Lab 測試；無外部設備授權時不做實機驗證。
