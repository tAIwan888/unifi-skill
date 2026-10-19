# M04 — UniFi WiFi／RF／6 GHz／SSID／漫遊

**用途：** 公用 UniFi Skill，適用多種 AP 型號，不預設任何個人部署。  
**證據：** Ubiquiti 官方 Help Center，2026-10-18 核對；`DOC_REVIEWED`，非 Lab 或實機部署驗證。  
**範圍：** WiFi 連線、安全性、SSID→VLAN、RF 規劃、6 GHz 地區限制、漫遊與故障復原。

## 學習目標與完成標準

1. 在規劃之前區分 **AP 硬體支援的頻段**、**當地法規核准**、**App/AP 最低版本**及 **Client 支援的安全／頻段**。
2. 能說明 2.4／5／6 GHz 的覆蓋、干擾、吞吐與相容性取捨，而不是固定宣稱一種頻道寬度「最好」。
3. 能規劃 Guest／IoT／員工 SSID 對應 VLAN；正確確認 AP Uplink 上的 Native/Tagged VLAN。
4. 能區分 BSS Transition、Band Steering、802.11r Fast Roaming 與用戶端自主漫遊判斷。
5. 能執行「小範圍試辦 → Client 實測 → 比對 → 回滾」的變更流程。

**完成標準：** 合成多 AP、混合 WiFi 5/6/6E/7 客戶端案例：產出合法頻段清單、SSID/安全模式、VLAN Trunk、預期 Roaming/訊號測試及回滾；若 6 GHz 不符合地區／裝置／版本條件，拒絕配置。

## 核心概念

| 主題 | 官方限制／典型行為 | 工程判斷 |
|---|---|---|
| 6 GHz | 需支援的 WiFi 6E/7 AP、WiFi Client、國家地區及所需 Network/AP 版本；戶外 6 GHz 在部分地區還需 AFC 和相容 AP | 先查地區表與產品 Tech Specs，不將戶外或 6 GHz 支援推定為全球通用 |
| WPA2/3／PMF | 多頻 SSID 可按產品／版本使用 WPA2/WPA3 Transition 兼容舊 2.4／5 GHz Clients，**但 6 GHz 無線連線本身只能使用 WPA3 或 OWE，不能使用 WPA2**；PMF 須符合實際協定要求 | 不可把 UniFi UI 顯示的 Transition／PMF Optional 選項解讀為 **6 GHz 可用 WPA2 或無 PMF**；針對各頻段、AP、Client 和當版韌體核對並測試 |
| IoT 舊設備 | 某些 Client 不支援 WPA2/3 Transition 或 6 GHz／PMF 行為 | 使用獨立 IoT SSID，限定合適安全與頻段；配合 VLAN 與 Firewall，別因此放寬主 SSID |
| Band Steering | 官方建議可採 BSS Transition 將相容 Client 引向 5 GHz；實際決策仍由 Client 參與 | 不保證強制所有裝置使用特定頻段 |
| Fast Roaming 802.11r | 可降低相容 Client 在 AP 間切換的握手成本；官方指出與 Switch Port Isolation 可能衝突 | 針對移動裝置測試，若有 IoT 或 Switch Isolation 問題先隔離變更 |
| Client Isolation | AP 同 SSID/同 AP Client 的局部隔離能力，不等於跨 VLAN 或 Wired Client 的完整 ACL | 另外驗證 Gateway Policy 與 Switch Port 行為 |

官方：
- https://help.ui.com/hc/en-us/articles/20407971377815-Getting-Started-with-6-GHz
- https://help.ui.com/hc/en-us/articles/8691786444567-Regions-Supporting-6-GHz
- https://help.ui.com/hc/en-us/articles/32065480092951-UniFi-WiFi-SSID-and-AP-Settings-Overview

## 官方建議做法

1. **先確定能不能用：** 確認 AP 支援頻段、安裝地區（包含戶外許可與 AFC）、UniFi Network／AP Firmware 版本，以及終端設備（Client）的 WiFi 6E/7 與安全協定支援。
2. **先以 UniFi 預設 WiFi 設定為基線：** 若無充分量測，官方通常建議保留可相容的預設設定、Band Steering 與 BSS Transition；優化時每次只變動少數參數。
3. **6 GHz 試辦：** 在相容 SSID/AP 上啟用 6 GHz，核對 Security／PMF 行為；不能加入的舊客戶端用另一個不包含 6 GHz 的 SSID。
4. **檢查覆蓋：** 官方指出 6 GHz 覆蓋通常短於 5 GHz；AP 佈建不能只看 PHY Link Rate，也需看 SNR、RSSI、干擾、封包重傳與實際應用。
5. **頻道寬度為建議而非永遠固定：** 2.4 GHz 20 MHz；5 GHz 常見 40／80 MHz；6 GHz 可評估 160／320 MHz，但取決於 AP／Client／環境／地區及當版支援。高密度場景可能需要更窄頻道以降低競爭。
6. **安全分段：** SSID 不等同完整 VLAN 隔離。AP Uplink 需允許 SSID 所用 Tagged VLAN，也必須維持 AP 自身管理 Network 可達。絕不在未備援時把 AP Uplink 改成錯誤 Native VLAN。
7. **Roaming：** 在同一 SSID、多 AP 同服務網段測試切換，注意 Fast Roaming、BSS Transition 與 Client/IoT 的相容性；勿保證特定品牌裝置一定無縫切換。
8. **Channel AI：** 官方案例可參考 AirView/Radios 的 Channel AI 結果，但是否採用應審核當前 RF 環境與變更窗口；不要把建議頻道誤當不可撤銷的絕對值。

### PPSK 與 6 GHz 安全模式的限制（公開來源核對，正式審核待 PR #6）

官方《UniFi WiFi SSID and AP Settings Overview》說明：Private Pre-Shared Keys（PPSK）允許同一 SSID 以不同密碼分配 VLAN，**但此功能目前要求 WPA2 相容加密**。6 GHz 頻段依無線安全標準須使用 **WPA3 或 OWE**，因此不可建議把 WPA2 PPSK 直接搬到 6 GHz 當作同等可用方案。

WiFi 7 Multi-Link Operation（MLO）應只在 AP 與 Client 均支援時評估；啟用時採 WPA3，可能使舊型 IoT Client 無法連線。6 GHz-only SSID 對部分終端的探索與初次連線也可能存在限制，官方建議依相容性考慮多頻 SSID；仍須核對當地 6 GHz 法規、型號及安裝版。

來源：https://help.ui.com/hc/en-us/articles/32065480092951-UniFi-WiFi-SSID-and-AP-Settings-Overview 。此為公開文件限制，不能被當作實測通過或 PR #6 已核准。

## UI 操作路徑

- `UniFi Network > Settings > WiFi` → SSID → `WiFi Band`、`Security Protocol`、`Advanced`（名稱可能依 Network 版本調整）。
- `UniFi Network > Radios` 或 `UniFi Devices > AP > Settings` → Radio Band、Channel、Channel Width、Tx Power。
- `AirView > Radios > Channel AI View`：官方目前的 Channel AI 入口示例，需依已安裝版本核對。
- `Ports > AP Uplink`：核對 Native VLAN 與 Tagged VLAN；若 Client 無法 DHCP，先排查上聯 Tag，而非直接重置 AP。

## CLI / API 替代方法

- 只用官方 Network API 在指定版本中已文件化的 GET 查 WiFi 設定，且只在獲得個別部署授權時連線；公用 Skill 不需要私人的 SSID、站點 ID、Controller IP 或 Key。
- 合成 Lab 測試可用頻譜量測和 Client 連線統計做離線示例；此處不生成「直接寫入生產 SSID／安全設定」的 API 呼叫。

## 常見情境範例

**舊 IoT 無法加入 6 GHz 主 SSID：** 保留主 SSID 的現代安全模式，額外建立較相容的 IoT SSID；將 IoT VLAN 與可信任網段用 L3 ACL 隔離。不得將主 SSID 全面降級為 WPA2。

**穿牆後 6 GHz 變慢：** 先確認 Client 是否停留在弱 6 GHz、比較 5 GHz RSSI/SNR，再調整 AP 位置、頻道與 Tx Power；不要直接把所有 AP 功率調最大。

**漫遊時語音斷線：** 量測切換前後 SSID/BSSID、實際重新認證延遲、802.11r Client 支援及 AP 上聯 VLAN；先測小部分裝置，再決定 Fast Roaming 改動。

## 風險與注意事項

- 地區／AFC 不符合規定時，不能套用 6 GHz 戶外規劃。
- WPA2/3 Transition、PMF、802.11r 可能影響舊設備；改動主 SSID 會影響大量 Clients，應分階段推出。
- 6 GHz 覆蓋與吞吐受硬體、天線、空間、干擾及 Client 能力影響，任何固定距離／速率都不能當實測保證。
- RF Optimization、Channel AI、Channel Width 變更前應有備份與原 Radio/SSID 設定快照。
- 認證安全、Guest ACL、網段隔離須與 M02/M03 的 VLAN/Firewall 一起驗收。

## 驗證方式

- **能力矩陣：** AP Model、Region、Indoor/Outdoor/AFC、Network/AP Firmware、SSID 安全模式與 Client 支援（合成或產品規格）。
- **正反測試：** 相容 WiFi 6E/7 終端可以加入 6 GHz；不相容 Client 有受限 SSID 可加入；無權限 Client 不能跨網段連管理面。
- **RF 測試：** 一段時間內的 RSSI、SNR、Retry／Roaming、Latency 及 Packet Loss；同條件前後測試，不只比較 SpeedTest 峰值。
- **回滾：** 還原原 SSID Security、Band、Port VLAN、Radio 與 Tx Power；檢查所有受影響 AP 與 Client 重新連線。

## 故障排除流程

AP Region/Model → Network/AP Firmware → 6 GHz Region/AFC → SSID Band/Security/PMF → AP Uplink Tagged VLAN → Client DHCP/DNS → RF RSSI/SNR → Band Steering/Fast Roaming → Gateway Isolation；每一步都可恢復前一狀態。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/20407971377815-Getting-Started-with-6-GHz
- https://help.ui.com/hc/en-us/articles/8691786444567-Regions-Supporting-6-GHz
- https://help.ui.com/hc/en-us/articles/26136823938583-Creating-UniFi-WiFi-SSIDs
- https://help.ui.com/hc/en-us/articles/32065480092951-UniFi-WiFi-SSID-and-AP-Settings-Overview
- https://help.ui.com/hc/en-us/articles/37367741854743-UniFi-Channel-AI-and-Automated-WiFi-Optimization
- https://help.ui.com/hc/en-us/articles/221029967-Optimizing-WiFi-Connectivity-and-Reducing-Latency
- https://techspecs.ui.com/

### 已觀測官方來源補充索引（尚待人工內容覆核）

下列連結補齊來源監測的精確引用，狀態為 `SOURCE_OBSERVED_UNREVIEWED`。新增索引**不表示**逐頁比較已完成、版本渠道已核准或實驗室測試通過；正式來源審核仍依 Draft PR #6 與人工審核紀錄辦理。

- https://community.ui.com/rss/releases/UAP-USW-Firmware/9fc3b2fa-9e73-449a-924f-470e79884470 （AP／USW 混合分類，僅採納 `unifi-wireless` 且符合標題格式的 AP／無線與橋接候選；Switch 另依專用 RSS；Official／RC／EA 尚未核實，機型與地區相容性仍待核對）

## 待補實作

各 AP 型號可用的 6 GHz／320 MHz／Roaming 頻段與相容性需以官方 Tech Specs／版本公告持續補齊；測試等級仍是 `DOC_REVIEWED`，不等於某一實際場域 RF 驗收。
