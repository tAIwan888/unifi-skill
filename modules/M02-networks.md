# M02 — UniFi Network：WAN、LAN、VLAN、DHCP、DNS 與 L3 Routing

**公用模組**：不需要私人網路資訊。**證據狀態**：`DOC_REVIEWED`（官方來源，核對 2026-10-18），尚未 Lab/Production 測試。

## 學習目標與完成標準

- 區分 L2 VLAN Tag、L3 Subnet、DHCP/DNS、Default Gateway 與 Firewall Policy 的作用。
- 分辨 UniFi Gateway 與 Third-Party Gateway 的網段建立責任；不能因 UniFi Switch/AP 看到 VLAN 就假設 Gateway 已提供 DHCP。
- 正確設計 Access Port（Native/Untagged）及需要的 Trunk/Tagged Networks，避免把管理 VLAN 困在錯誤的 Port。
- 評估 Gateway Inter-VLAN Routing 與 UniFi Layer 3 Switch Routing 的功能取捨、流量可見度及回滾。

**驗收：** 合成 Guest/IoT/Work 分段情境可以逐項回答 DHCP Lease、DNS、Guest → 管理網段、AP/Client VLAN、Uplink 預期封包標記；錯誤的管理 VLAN 方案需拒絕執行。

## 核心概念

| 元件 | 職責 | 重要邊界 |
|---|---|---|
| VLAN | 在支援的 L2 埠/SSID 間劃分廣播域 | VLAN ID 本身不保證安全隔離，跨網段存取需 L3 Policy |
| UniFi Gateway | WAN、LAN/DHCP、Routing、適用的 Firewall/Policy | 按產品/Network 版本有不同能力 |
| Third-Party Gateway | 在第三方 Router 建 VLAN/Subnet/DHCP、Inter-VLAN Policy | UniFi Network 使用 `Router: Third-party Gateway` 與一致 VLAN ID，不代管第三方 Router Firewall |
| Switch/Port Profile | Native VLAN、Tagged VLAN、PoE、LAG/STP | Trunk 與 Access Port 不可互換；任何上聯修改都需退路 |
| WiFi/SSID | 連線認證、安全模式與 Network/VLAN 對應 | 6 GHz、WPA3、IoT 相容性仍需 M04 查核 |
| L3 Switch Routing | 支援之交換器做 Inter-VLAN Route | 官方明示 Traffic Identification 與依賴它的功能**不支援**由 L3 Switch 管理的網段 |

官方：
- https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs
- https://help.ui.com/hc/en-us/articles/360042281174-Layer-3-Routing

## 官方建議做法

1. **先選 Router 類型**：Cloud Gateway/Independent UniFi Gateway or Third-party Gateway；第三方路由需先在第三方設備上建立相同 VLAN、Subnet、DHCP，再於 UniFi Network 定義。
2. **按安全域分網**：Management、Guest、IoT、Work/Server 為設計案例，不是要求所有部署都必須建立四種網路。
3. 逐一釐清誰提供 DHCP Server / Relay、DNS、IPv6、mDNS 轉送與 Inter-VLAN Policy。需要跨 VLAN 的 IoT 發現時，僅開放所需服務，不直接放通全部內網。
4. Switch Port/SSID **先試辦、後擴大**，特別是上聯 Trunk 和 AP 上行，避免因設定錯誤造成 AP 失聯。
5. **若需要 UniFi Gateway Traffic Identification／依賴它的安全/流量功能**，勿直接把 Inter-VLAN Routing 下放 L3 Switch；先對照官方功能限制。
6. Layer 3 Switch Routing 不只是勾選一個功能；官方說明啟用時會有特殊的 Inter-VLAN Routing Network，常見預設 VLAN ID **4040** 與網段 `10.255.253.0/24`，但實際可調整且需避免衝突；**不可把這些當作全網強制設定值**。

### VLAN Magic、第三方 Gateway 的適用性（公開來源核對，正式審核待 PR #6）

官方《Creating Virtual Networks (VLANs)》區分兩種 Routing Ownership：使用 UniFi Gateway 建立 Virtual Network 時，可設定 VLAN、Subnet、DHCP、DNS；使用第三方 Gateway 時，應先在第三方路由器建立一致 VLAN ID／Subnet／DHCP，然後在 UniFi Network 登記 `Router = Third-party Gateway`。**不能假設 Network UI 設定 VLAN 就會讓第三方路由器自動建立 DHCP 或 Inter-VLAN Routing**。

官方另說明「VLAN Magic」適合部分小型場域，但**不支援在 USW Flex、USW Flex Mini、USW Ultra、USW Flex 2.5G 系列及 ECS Aggregation 下游**使用。這是產品限定功能，不可當作全系列 UniFi Switch 都支援的快捷部署方式。

來源：https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs 。此為公開文件之適用性提示，不表示任何實體網路已測試，也不等於 PR #6 的來源正式核准。

## UI 操作路徑

- 官方 VLAN 建立流程：`UniFi Network > Settings > Networks` → Create Virtual Network → Router、Subnet、VLAN ID、DHCP、DNS。
- Third-party Gateway：先在該 Gateway 建好相容 Subnet/VLAN/DHCP，再於 UniFi Network 選 `Router: Third-party Gateway`。
- L3 Switch Routing：支援的 UniFi Network 版本可將 Virtual Network 的 Router 指向相容 L3 UniFi Switch；按目前官方文件測試 L3 Inter-VLAN Network 和 Static Route/DHCP Relay。
- WiFi 所屬 VLAN：按各 App 版本設定 SSID/VLAN；完成無線客戶端 DHCP、DNS 與防火牆連通性驗證。

## CLI / API 替代方法

- 只有在**目標 Network 版本**官方 `Network > Integrations` 或 Developer API 文件明確列出對應唯讀端點時，才可透過 `GET /v1/sites/{siteId}/networks` 等方法讀取。
- 公用 Skill 使用 Mock Data，不需任何 Site ID、Controller IP 或 API Key。API 寫入 VLAN/Firewall 屬高風險變更，未有相容矩陣與明確批准之前不提供通用可執行自動寫入。
- CLI（ip route、traceroute、dig、ping）適合作為隔離 Lab 驗證思路，但不能證明 Switch 裡的所有 Firewall 規則生效。

## 常見情境範例

**Guest VLAN：** Guest Client 應取得預期 DHCP/DNS、Internet 可達；Guest → Gateway 管理介面、其它內網子網應按明確 Policy 拒絕。不可把「不同 SSID」直接視為網路隔離。

**IoT 控制：** 控制裝置與 IoT 裝置在不同 VLAN 時，先列出 mDNS / Multicast / TCP/UDP 服務依賴，逐項建立必要政策與雙向觀測。

**L3 Switch 擴張：** 大量 LAN 內跨 VLAN 傳輸可評估 Switch Routing，但要明確接受 Gateway Traffic Identification 與 Policy 可見度差異；不可只因交換器有 10 GbE 埠就認定所有路由能力等同 Gateway。

## 風險與注意事項

- 改 Native/Tagged VLAN、Router、DHCP、Gateway Policy 可能立即中斷網路或失去設備管理存取。
- 第三方 Gateway 的 Routing/Firewall 必須由第三方設備管理；不能宣稱 UniFi Network UI 會自動替第三方 Router 建 Firewall。
- DHCP Address Collision、VPN Subnet Overlap、IPv6 SLAAC/RAs、STP Loop、PoE 上聯皆需獨立測試。
- 文件分類是 `DOC_REVIEWED`，所有具體 Port/ACL 改動需另有 Lab／正式環境授權。

## 驗證方式

`VLAN / Subnet / Gateway / DHCP / DNS / Client Role / Expected Allowed / Expected Denied` 逐列測試；確認每個 Client 的 Gateway 正確，管理埠仍可連，Guest/IoT 被阻隔，所需應用與 Multicast 正常。正式推送之前需能恢復原 Network、SSID、Port 與 Gateway 設定。

## 故障排除流程

未得到 IP → Client VLAN Tag → Switch/AP Port Profile → DHCP Server/Relay → WAN/Default Gateway → DNS → Firewall Zone/Policy → mDNS → L3 Switch 靜態路由與 Traffic Identification 限制。**管理 VLAN 一旦失聯，使用事先保留的現場救援 Port 或帶外路徑**，而不是盲目繼續切換所有上聯。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs
- https://help.ui.com/hc/en-us/articles/360042281174-Layer-3-Routing
- https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi
- https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- https://developer.ui.com/network/v10.6.106/getnetworksoverviewpage


### 已觀測官方來源補充索引（尚待人工內容覆核）

下列連結補齊來源監測的精確引用，狀態為 `SOURCE_OBSERVED_UNREVIEWED`。新增索引**不表示**逐頁比較已完成、版本渠道已核准或實驗室測試通過；正式來源審核仍依 Draft PR #6 與人工審核紀錄辦理。

- https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe （單一 Network Application RSS；Official／RC／EA 尚未核實）

## 待補實作

各系列 Switch、AP、Third-Party Gateway 的能力矩陣、DHCP/DNS/IPv6 驗收記錄與 Lab Packet Capture；不可把設計示例直接當成所有版本生產環境設定。
