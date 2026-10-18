# M03 — UniFi Zone-Based Firewall、VPN 與網路安全策略

**模式：** 公用知識，不需要私人網段／API Key。  
**來源核對日期：** 2026-10-18。  
**驗證：** `DOC_REVIEWED`；**沒有 Lab 或 Production 實機驗證**。  
**安全性：** 配置僅作為架構參考，未經使用者授權不得實際變更 Firewall、VPN、WAN 或管理介面。

## 學習目標與完成標準

1. 說明 Firewall Zone（網段／WAN／VPN 的集合）、Policy Direction、Built-in Rule 與 Zone Matrix 的作用。
2. 正確套用官方 **Zone-Based Firewall 的最低相容條件**：UniFi Network **9.0+**、UniFi（Cloud）Gateway **4.1+**，並需有支援的 Gateway。
3. 區分 VPN Server、VPN Client、Site-to-Site VPN，以及 Teleport、WireGuard、IPsec、Site Magic 的適用情境。
4. 對老式 LAN_IN／LAN_LOCAL／WAN_IN → Zone-Based Firewall Migration 進行規則對應驗證與回滾評估。
5. 建立「被允許」與「必須拒絕」同等重要的雙向驗收矩陣；尤其保護 Gateway Management、DNS、DHCP 與 VPN 管理面。

**完成標準：** 使用公開虛構拓撲擬定 Management、Guest、IoT、Server 和 VPN 的 Source/Destination Zone 及 Service Allow/Deny；在不滿足版本條件時拒絕提供 ZBF UI 配置步驟。

## 核心概念

| 主題 | 原理 | 適用性與風險 |
|---|---|---|
| **Zone-Based Firewall (ZBF)** | 介面／VLAN 分組至 Zone，由 Source→Destination Zone 指定 Policy | Network 9.0+、Gateway 4.1+ 且支援的 Gateway；需核對實際採用的 App/韌體 |
| **Gateway Zone** | 與 Gateway 本身的 DHCP、DNS、SSH/HTTPS 等流量 | 不能假設 LAN→LAN Policy 也會管到 Gateway Local Traffic |
| **External/Internal/VPN/Hotspot/DMZ** | 官方 Built-in Zones | 各 Zone 可包含多網段，不能只看 Zone 名稱就推斷所有流量均被允許/拒絕 |
| **Firewall Migration** | 舊 LAN_IN、LAN_LOCAL、WAN_IN 等自訂規則映射至新的 Zone Rules | 官方描述遷移時功能預期相同，仍需逐規則測試，可能產生重複政策 |
| **VPN Server / Teleport / WireGuard** | 提供遠端使用者安全進入特定網段 | Teleport 邀請單次設備使用且 24 小時失效；已接受後可撤銷 |
| **VPN Client** | 讓 Gateway 對外透過第三方 VPN Server | 需要明確的 Policy-Based Routing、DNS、Client Scope 與 Kill-switch/Failure 行為 |
| **Site-to-Site / Site Magic / IPsec** | 連結站點與本地資源 | Site Magic 取決於相容的 UniFi Gateway/管理架構；第三方設備互通宜考慮支援的 IPsec/OpenVPN |

官方：
- https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- https://help.ui.com/hc/en-us/articles/28223082254743-Migrating-to-Zone-Based-Firewalls-in-UniFi
- https://help.ui.com/hc/en-us/articles/7951513517079-UniFi-Gateway-Introduction-to-VPNs

## 官方建議做法

1. **先做支援檢查**：核對 Gateway 類型、UniFi Network 版本、UniFi Gateway 韌體版本；若 ZBF 不滿足上述最低條件，只能提供相容舊版的架構概念與官方回溯文件，不可硬給新版 UI 路徑。
2. **政策最小化**：列出服務清單與 Source/Destination；先保留管理介面、DHCP/DNS、DNS Forwarder、站點 VPN 的必要控制面連通性，避免盲目 `Deny Any` 鎖死管理。
3. 分段先創建明確的隔離需求，再根據 ZBF `Internal`、`Gateway`、`VPN`、`Hotspot` 等 Zone 設計 allow/deny；**不因 Firewall 名稱「Secure」就推定已被隔離**。
4. 從舊 Rule Set 遷移時先匯出 Network/System 設定，建立 Legacy→New Mapping 清單。官方 ZBF Migration 對映包含 `LAN_IN`、`LAN_OUT`、`LAN_LOCAL`、`WAN_IN`、`WAN_LOCAL` 等；新政策可能增多，刪除冗餘之前要先觀測。
5. VPN：個人或小量遠端存取依需要比較 **Teleport**（簡化使用）與 **WireGuard Server**（可客製 Peer/AllowedIPs），多站點比較 Site Magic、IPsec；**不得把 Site Manager 遠端 UI 登入等同 VPN 對內網的存取能力**。
6. 第三方 IPsec 需比對 Local/Remote Subnets、NAT、密鑰交換、加密演算法與 PFS 等能力；不要把 Site Magic 假設能直接連結任意非 UniFi Gateway。

### Zone-Based Firewall 變更的官方特殊風險（公開文件對照；正式審核仍待 PR #6）

官方 Zone-Based Firewall 文件明確指出：

- **刪除自訂 Zone 會一併刪除該 Zone 所關聯的 Firewall Policies**。因此不能把刪 Zone 當成無風險清理；必須先匯出並盤點關聯規則、準備回滾和可達性驗證。
- **限制 Gateway Zone 的流量可能破壞 DHCP、DNS 等必要功能**。驗收應獨立列出 Gateway Local（DHCP/DNS/Management）與 Inter-VLAN 等路徑，而不是僅測外網能否連通。
- 官方分版本 UI 範例：Network 9.4 可由 `Settings > Zones > Create Policy` 或 `Settings > Policy Table > Create New Policy`；Network 9.3 使用 `Settings > Policy Engine > Zones > Create Policy`。**不得將固定點選路徑套到所有 9.x／10.x 版本**。
- 官方描述建立的 Policy 與 Built-in Rule 有優先權與雙向流量語意；操作前應根據安裝版核對，不可單憑 Zone Matrix 顏色宣稱配置已經實際生效。

來源：https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi 。這是文件層級補充、未實施 Firewall Change，並不等於 PR #6 已由人員完成正式來源審核。

## UI 操作路徑

- 官方 ZBF 說明：`UniFi Network > Security / Firewall` 的 Zone Matrix 與 Zones；實際 UI 路徑需依 Network 9.x/10.x 版本核對。
- 官方舊規則升級流程：`Security > Traffic & Firewall Rules > Upgrade`，**僅限該舊版 Migration UI 確實提供此項的安裝版**。
- VPN：`UniFi Network > Settings > VPN`（依版本與 Gateway 型號）。Teleport、WireGuard Server、IPsec 相關選項名稱可能不同；不應假設所有型號同時支援。

## CLI / API 替代方法

- 最初採唯讀官方 Network API（M10）核對 Networks 與相關設備；**Firewall Rule 寫入只在有官方當版 Endpoint、可審計 Change、備份、回滾及明確授權時考慮**。
- 先使用合成封包流量矩陣測試，不使用私人 Site ID、Guest MAC、WAN 位址。
- WireGuard Peer Configuration、IPsec Shared Key 等均屬敏感材料，不可放入公用 Repository、GitHub Issue 或直接貼給 AI Agent。

## 常見情境範例

**Guest WiFi 隔離：** Guest → WAN/DNS 可以按需求 Allow；Guest → Management/Server 必須 Deny；Guest → Gateway Local Management 需與 Guest → 其它 VLAN 分開驗證。

**IoT Controller：** 管理端 → IoT 服務只開必要 TCP/UDP/MQTT/mDNS；IoT → Work/Management 預設不允許。雙向回應與 Stateful Rule 行為必須測試。

**家庭遠端管理：** 如希望從外部連入，優先考慮使用符合 Gateway 支援的 VPN，而不是公開 Internet 上的 UniFi Admin Web UI；Teleport 邀請需過期／撤銷紀錄。

**第三方辦公室 IPsec：** 先核對 Remote LAN 和本地是否重疊、ISP 是否 CGNAT、UDP/IPsec 可達、NAT-T、PFS 及兩邊 Time/Encryption 相容，再依雙方防火牆規則測試。

## 風險與注意事項

- Firewall 政策若錯置 Zone 或 Direction，可能讓 Guest 進入管理網段、讓 VPN 使用者擁有不必要權限，或讓管理者自己失去存取。
- Zone Matrix 視覺上反映的是當前規則，但**不等同已驗證的實際封包可達性**；需 Allow 和 Deny 都做測試。
- Gateway 本地流量與 Inter-VLAN Policy 應區分；若 L3 Routing 發生在 Switch，Gateway 的 Traffic Identification／部分政策並不涵蓋該網段，需先核對 M02。
- Site Magic/WireGuard/Teleport 受到 Gateway 型號、管理與區域網路條件影響；不應引用一個最小版本套用到所有 VPN 功能。
- L2TP 為舊方案，官方目前更推薦 Teleport 或 WireGuard；不應將 legacy VPN 作為預設新部署建議。

## 驗證方式

| 測試 | 允許方向（範例） | 拒絕方向（範例） |
|---|---|---|
| Guest | Guest → Public DNS / WAN 按需 | Guest → Management / Gateway Admin |
| IoT | 管理端 → 特定 IoT 服務 | IoT → Work、全部 RFC1918 任意存取 |
| VPN | 授權 Peer → 指定子網/服務 | VPN → 不授權站點和管理介面 |
| Local Gateway | 合法 Admin → Gateway 管理服務 | 無授權 Client → Gateway SSH/HTTPS |
| Zone Migration | 遷移前後所有既有允許的業務路徑 | 遷移前後所有既有拒絕路徑 |

**驗收要求：** 記錄來源/目的地 Zone、服務、預期規則、實測 allow/deny、變更前備份、回滾期限；VPN 測試還需 DNS 洩漏、Client Subnet、Revoke 與斷線失效狀態。

## 故障排除流程

Gateway/App Firmware 版本 → Zone 成員 → Rule Direction/Priority → Gateway Local/Inter-VLAN 差異 → NAT/Static Route → VPN Tunnel/AllowedIPs/DNS → Session/Log → 安全撤銷／回滾。驗證失敗時還原前一份已核對的設定，而不是持續放寬 ACL。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- https://help.ui.com/hc/en-us/articles/28223082254743-Migrating-to-Zone-Based-Firewalls-in-UniFi
- https://help.ui.com/hc/en-us/articles/7951513517079-UniFi-Gateway-Introduction-to-VPNs
- https://help.ui.com/hc/en-us/articles/5246403561495-UniFi-Gateway-Teleport-VPN
- https://help.ui.com/hc/en-us/articles/115005445768-UniFi-Gateway-WireGuard-VPN-Server
- https://help.ui.com/hc/en-us/articles/7983431932439-UniFi-Gateway-Site-to-Site-IPsec-VPN-with-Third-Party-Gateways-Advanced


### 已觀測官方來源補充索引（尚待人工內容覆核）

下列連結補齊來源監測的精確引用，狀態為 `SOURCE_OBSERVED_UNREVIEWED`。新增索引**不表示**逐頁比較已完成、版本渠道已核准或實驗室測試通過；正式來源審核仍依 Draft PR #6 與人工審核紀錄辦理。

- https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi （公開官方文章；內容差異尚待核對）

## 待補實作

針對正式 UniFi Network 9.x/10.x、Gateway OS 4.1+ 型號實測完整 Zone Mapping 與 VPN 功能矩陣；在未取得 Lab 證據之前不能標記互通或性能 PASS。
