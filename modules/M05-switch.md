# M05 — UniFi Switch、PoE、VLAN Port、RSTP 與有線網路

**用途：** 公用知識，不依賴任何個人 Switch 或線材資料。  
**證據：** 官方 Help Center，2026-10-18 查核；`DOC_REVIEWED`，未於真實 Switch/Lab 驗證。  
**安全性：** 所有 Port Profile、Management VLAN、STP、PoE、Aggregation 等變更，未有備援與授權不得直接執行。

## 學習目標與完成標準

1. 分辨 Native/Tagged VLAN、Access/Trunk Port、AP Uplink 與管理 VLAN 的連動。
2. 了解 802.3af／at／bt PoE 型式、單埠支援模式與整台 Switch **總功率預算** 是不同限制。
3. 了解 STP/RSTP、Root Priority、Port Edge、BPDU Guarding、Loop Protection、LAG/MLAG（視型號）的限制。
4. 辨識 Speed/Duplex Negotiation、SFP/SFP+ 模組、線材與光纖導致的吞吐瓶頸。
5. 對 AP 或 Switch 掉線、PoE 週期重啟、環路、管理 VLAN 錯誤建立有退路的排障流程。

**完成標準：** 合成 1 Core + 2 Edge Switch + 數台 AP/Camera 案例：能計算 PoE 上限與餘裕、分辨各 Port 的 Native/Tagged VLAN、標示 RSTP Root/Edge、保留管理救援路徑，且不得將 10 GbE Port 視為所有流量均達 10 Gbps。

## 核心概念

| 主題 | 官方行為 | 常見風險 |
|---|---|---|
| Native VLAN | Port 上未標記（untagged）封包所屬的 VLAN | Access Client 被分配到錯誤網段 |
| Tagged VLAN Management | `Allow All`、`Block All`、`Custom` 限制允許的 Tagged VLAN | 連到 AP/Switch 的上聯若不允許 SSID VLAN，會導致下游失聯 |
| Access vs Trunk | Access 通常只有 Native VLAN；Trunk 會承載多個經允許的 Tagged VLAN | 把 AP/下游 Switch 當一般 Access Port 使用 |
| PoE Budget | 必須考慮設備的最大耗電量、單 Port 最大 PoE 功率與 Switch Total Availability | 部分 Device 斷電、反覆 Reboot 或無法啟動 |
| STP/RSTP | 預設 RSTP 用來阻擋 L2 環路造成的廣播風暴，Root Switch 通常指定為 Core | 不當 STP Disable / Root 誤設會產生環路或 Port Block |
| Loop Protection | STP 以外的環路保護；觸發後可能永久封鎖 Port，需管理員介入復原 | 雖防風暴，但對無現場管理資源的遠端端點仍有中斷風險 |
| Jumbo Frames | 僅在路徑所有設備支援且設定一致才有效 | 部分服務超時、封包丟棄、疑難排解困難 |
| Link Speed / Duplex | 實際鏈路速率由雙端 Port、模組、距離及線材限制 | PHY Link Rate != LAN end-to-end/跨 VLAN 實際吞吐 |

官方：
- https://help.ui.com/hc/en-us/articles/26136855808919-Switch-Port-VLAN-Assignment-Trunk-Access-Ports
- https://help.ui.com/hc/en-us/articles/33402927617047-UniFi-Switch-Settings
- https://help.ui.com/hc/en-us/articles/24292724428311-Understand-and-Mitigate-Network-Loops-STP
- https://help.ui.com/hc/en-us/articles/115000263008-PoE-Availability-and-Modes

## 官方建議做法

1. **實體型號先於通用設定**：查 `techspecs.ui.com` 確認每台 Switch 的 RJ45/光纖 Port 速率、PoE 模式、整機功率、供電與韌體能力；不可把家族名稱當成每台 Switch 的實際能力。
2. **PoE 預算**：先加總所有 PoE Clients 的官方最大需求（非只採目前平均功耗）並留安全餘裕；兩層限制分別是各 Port 型式/上限與全 Switch 可用 PoE Budget。若有 PoE Injector，要檢查電源類型是否為 Passive 與終端相容性，避免將不適用 Injector 接至一般電腦或印表機。
3. **VLAN 範例**：普通終端使用所需 Native/Access VLAN；連 AP 的 Trunk Port 使用 AP 本身的管理 Native VLAN，Tagged VLAN 列出 SSID 所需網段；連 Switch 的 Uplink 必須有上下游所需的 Tagged VLAN。
4. **注意官方 AP 上聯提醒**：一般情況不要把 AP Port 的 Native VLAN 設成 AP 所廣播的相同 Client VLAN（VLAN 1 例外），否則可能導致用戶端無法加入；仍需依該 AP 管理 VLAN / Network Override 與實際版本核對。
5. **RSTP**：確認有 Core Root Switch，沿 Layer 設定 Root Priority（官方案例以 0、4096、8192 遞增）；Switch to Switch 保留 STP，Client Edge 可評估 STP Edge/BPDU Guarding。Gateway 內建 Switch Port 官方不支援 STP，不應當成一般 UniFi Core Switch。
6. **Loop Protection**：對環路風險及離線恢復能力評估後啟用；官方說明 Loop Protection 或 BPDU Guarding 觸發後可能需要手動解除封鎖。對無現場管理支援的遠端站點需評估事故可恢復性。
7. **其它功能**：802.1X、DHCP Guarding、Port Isolation、Voice VLAN、LLDP-MED、LAG、Flow Control 依型號/韌體核對。不要在沒有 VLAN/DHCP 檢查時全局啟用 Port Isolation 或 802.1X。
8. **管理 VLAN Network Override**：改動前保留 OOB 或本地救援 Port；Network Override 的 VLAN 若未在上聯 Allow Tagged 或與 Native VLAN 不相符，Switch 將可能變得不可管理。

## UI 操作路徑

- `UniFi Network > Ports` → 選 Port → Native VLAN / Network、Tagged VLAN Management、PoE、Link Speed（依 Network 版本／Switch 硬體）。
- `UniFi Devices > Switch > Ports > Port Manager` → Port Settings，包括 Native/Tagged VLAN、PoE、Mirroring、LAG（依型號）。
- `UniFi Devices > Switch > Settings` → Network Override、STP Priority、IP Settings 等；務必先確認管理 Uplink。
- `Settings > Networks` → Global Switch Settings：RSTP、DHCP Guarding 等（實際條目依版本/型號）。
- 不假設特定端口號、SFP 規格、外掛控制面的 Switch 都支援同一功能。

## CLI / API 替代方法

- 以官方當版 Network GET API、合成 PoE Device Spec Table 與明確的計算公式展示唯讀監測；**不得以民間未文件化 API 對正式 Port 直接停用／PoE Cycle／重啟**。
- PoE 容量檢查採每個 Device 的 `max_watts`，加總並比對 `switch_budget_watts`，另驗證每個 Port 的 802.3af/at/bt 能力。
- 遙控 SSH、Port Disable、Firmware Rollback 為高風險命令；此公用模組不直接提供無版本確認的寫入操作。

## 常見情境範例

**AP 連上但 SSID Client 沒有 DHCP：** 先查 AP Switch Port Native VLAN、Tagged VLAN（SSID VLAN）、上游 Switch Uplink、DHCP Server/Relay，再查 Firewall；不要直接 Factory Reset AP。

**PoE Camera/AP 間歇重啟：** 比對實際 PoE 供電與官方最大功率、總功率、單埠 PoE Class、線材/供電品質；先分批減載或改為相容外部供電（需授權），而非盲目強制輸出 PoE++。

**多條 Uplink 導致網路風暴：** 檢查 STP Root/Blocked Ports、第三方 Bridge/Smart Home Mesh、是否建立正確 LAG；在確認後才移除冗餘線路／恢復 Port。

## 風險與注意事項

- AP Uplink 誤設 VLAN、Management Network Override、STP Root/BPDU Guard、Loop Protection、Port Isolation、LAG 都可能導致大規模斷網。
- PoE Injector 不等於所有 Type 都能無風險接所有終端；尤其 Passive PoE 需查電壓與相容性。
- 配置 Native/Tagged VLAN 時，持續維持 Gateway、DHCP/DNS、管理 Console 的路由與可達性。
- 交換器及 AP 型號／韌體可能改變 QoS、RSTP、LAG、802.1X 的可用性；需引用具體 Tech Specs 和官方 release notes。

## 驗證方式

- **Port Mapping**：Switch/Port→對端裝置、Link Speed、Media Type、Native/Tagged VLAN、PoE Mode，須與實體標籤及預期網段一致。
- **PoE Budget**：官方最大功耗總和 **小於** Switch 可用功率，另保留合理餘裕；每埠功率不超過規格。
- **STP**：Root Switch 符合拓撲、冗餘鏈路無環路，Edge Port 的 BPDU Guard 依風險設計，觸發保護後有恢復 Runbook。
- **VLAN**：各 SSID/Client 可以取得預期 DHCP/DNS，Guest/IoT 不可直連可信任管理面。
- **回滾**：還原 Port Profile／Native/Tagged VLAN／PoE／STP Priority，復原管理 Console 與關鍵 AP/Camera 連線；必要時現場帶外救援。

## 故障排除流程

PoE/Power Budget → Link Speed/Media → STP/Blocked Port → Port VLAN Native/Tagged → AP/Downstream Uplink → DHCP/DNS → Gateway Policy → Management VLAN Override → Adoption/Inform；先分析唯讀資訊，再考慮停 Port/Restart/Reset。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/26136855808919-Switch-Port-VLAN-Assignment-Trunk-Access-Ports
- https://help.ui.com/hc/en-us/articles/33402927617047-UniFi-Switch-Settings
- https://help.ui.com/hc/en-us/articles/24292724428311-Understand-and-Mitigate-Network-Loops-STP
- https://help.ui.com/hc/en-us/articles/115000263008-PoE-Availability-and-Modes
- https://help.ui.com/hc/en-us/articles/9592924981911-Virtual-Network-VLAN-Troubleshooting
- https://techspecs.ui.com/


### 已觀測官方來源補充索引（尚待人工內容覆核）

下列連結補齊來源監測的精確引用，狀態為 `SOURCE_OBSERVED_UNREVIEWED`。新增索引**不表示**逐頁比較已完成、版本渠道已核准或實驗室測試通過；正式來源審核仍依 Draft PR #6 與人工審核紀錄辦理。

- https://help.ui.com/hc/en-us/articles/360042281174-Layer-3-Routing （公開官方文章；內容差異尚待核對）
- https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs （公開官方文章；內容差異尚待核對）

## 待補實作

各型號 Switch/LAG/RSTP/PoE 的細分支援表、實機功耗、光模組互通與 MTU Lab 測試。未有真機證據不可標記 `LAB_TESTED`。
