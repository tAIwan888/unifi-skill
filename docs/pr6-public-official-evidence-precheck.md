# PR #6 — 官方公開來源內容預先對照（2026-10-19，非人工核准）

> **EVIDENCE_PRECHECK_ONLY / NOT_HUMAN_APPROVAL / DO_NOT_PROMOTE.**
> 本文由 AI 輔助閱讀公開官方頁面，對照既有 M01–M10 的**指定高風險敘述**，不是完整逐段法律／產品相容性審核，亦不能證明本次網頁內容等同 GitHub Runner 正規化後的 SHA-256。網頁檢索可能使用先前快取，故不宣稱 2026-10-19 最新全文已逐位元重新讀取。以下 `observed SHA prefix` 來自 PR #6 的 `sync/pending.json`，不是此次 Web 閱讀重新計算。只有實際具權限的真人審核才能更新 `sync/reviewed.json`。

## 來源狀況：不能混淆不同層級

- **31/31 清單項目：** 19 個官方 Help Center 文章、3 個固定版本 Developer Markdown、7 個產品限定 Community RSS、2 個全球 Release / Downloads 頁面。
- **29/31 GitHub Runner 正常取得內容指標；2 個全球來源 DEGRADED。** 現有審核資料仍為 **29 筆 `REVIEW_REQUIRED`，0 筆已核准**。
- 本文列出 **19 個 Help Center URL**，其中 **19 個均已核對至少一項與 Skill 對應的具體技術敘述**（本輪補齊 `platform_intro`：Hosting、Cloud Gateway / CloudKey / NVR、控制面與 Site Manager 角色）；此仍不是逐篇全文審核，不能獨立重新生成 GitHub Runner SHA。其他 3 個版本固定 Developer Markdown 和 7 個 RSS 的來源機器驗證來自 GitHub Runner，**本輪沒有從 Web 獨立重新計算 SHA**。
- 精確引用缺口為 **0**。此結果代表字串可追蹤，不代表每一個來源都已人工比對或發布渠道已核准。

## 19 筆 Help Center 來源：指定高風險敘述預審

| Source ID / 模組 | 官方文章與觀測 SHA 前綴 | 預先核對的公開原文事實（仍未核准） |
|---|---|---|
| `access` / M07 | [Getting Started with UniFi Access](https://help.ui.com/hc/en-us/articles/17452334269975-Getting-Started-with-UniFi-Access) · `40c012b59ca0` | Reader 與 Hub 要在同 L2；Hub 與 Console 在具路由條件時可跨 VLAN；不同 Hub 供電方式不可混用。消防逃生、門禁解鎖不可自動部署。 |
| `adoption` / M09 | [UniFi - Device Adoption](https://help.ui.com/hc/en-us/articles/360012622613-UniFi-Device-Adoption) · `d453882cee8f` | 同 VLAN 的 AP／Switch 採用檢查 TCP 8080 與 UDP 10001；跨 VLAN 的 Network 主機路由檢查 TCP 8080。Protect Camera 的採用連接埠是另一組，不能混用。 |
| `backup_migration` / M09 | [Backups and Migration in UniFi](https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi) · `c52ff3e75245` | 跨型號 Cloud Gateway／CloudKey／UNVR 目的端需 UniFi OS 3.1+；System Config Backup 不等於 Protect 舊錄影能轉移，移動原硬碟並格式化有破壞風險。 |
| `cloud_architecture` / M01 | [Understanding UniFi Cloud Architecture](https://help.ui.com/hc/en-us/articles/30319146145175-Understanding-UniFi-Cloud-Architecture) · `c6a651bcf695` | Site Manager 為集中遠端管理入口，控制面部署位置可以是 Cloud Gateway、CloudKey、自架 OS Server、官方 Hosting 或 NVR，不可把 Site Manager 當成控制面全數搬到雲端。 |
| `identity` / M08 | [UniFi Endpoint Overview](https://help.ui.com/hc/en-us/articles/16936895868823-UniFi-Endpoint-Overview) · `7f0d24e5ec41` | One-Click WiFi/VPN 與 Smart Door Access 是 Endpoint 功能；Talk Softphone、EV、Camera Sharing、File Access 明列 Single-Site Only；不能推定多站權限自動通用。 |
| `isolation` / M02、M03 | [Implementing Network and Client Isolation](https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi) · `f5c7f11eb299` | ZBF 在閘道層、Switch ACL 在交換器層、AP Client Isolation 在 AP 本機作用；三者不可互相替代，Network Isolation 是另一種簡化跨 VLAN 隔離設定。 |
| `l3_routing` / M02、M05 | [Layer-3 Routing](https://help.ui.com/hc/en-us/articles/360042281174-Layer-3-Routing) · `d54c96a0efe4` | L3 UniFi Switch 的 Inter-VLAN Route 預設 VLAN **4040（不可修改）**，預設 10.255.253.0/24；第三方 Gateway 需要對應 VLAN Tag 與靜態路由，L3 Switch 本身不做 NAT。 |
| `official_api` / M10 | [Official UniFi API](https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API) · `ec591973b946` | Site Manager API 是跨站高層視角；Local Application API 是各站的本地控制面 API。Network 在安裝版 `Network > Integrations` 提供相應文件，不可混用兩個 API Scope。 |
| `official_hosting` / M01 | [Official UniFi Hosting](https://help.ui.com/hc/en-us/articles/4415364143511-Getting-Started-with-Official-UniFi-Hosting) · `de5023a42ece` | 官方直接 Hosting **Network** 與 **Talk Relay（第三方 PBX）**；Protect / Access 需要由其他相容 Console／NVR／CloudKey 補足，並非同一託管產品直接支援全部 Apps。 |
| `platform_intro` / M01 | [Introduction to UniFi](https://help.ui.com/hc/en-us/articles/360012192813-Introduction-to-UniFi) · `6e57b0a84530` | **已核對正文的指定敘述：** 官方列 Network、Protect、Access、Talk、Connect 為不同 Apps；Cloud Gateway 通常內建 Network 並可依型號託管其他 App；CloudKey 與 UNVR 是其他控制面類型；Site Manager 是跨部署遠端管理入口，不代表每一個 App 在任意主機皆可託管。此為產品分類／部署概念核對，非各型號完整相容矩陣。 |
| `protect` / M06 | [Getting Started with UniFi Protect](https://help.ui.com/hc/en-us/articles/27878858632599-Getting-Started-with-UniFi-Protect) · `c375d90b001d` | Protect 需相容 Console 與 Camera；官方明列 ONVIF 相容第三方 Camera 的支援例外，CloudKey／NVR 多 VLAN 安裝須獨立核對採用網段。 |
| `self_hosting` / M01、M09 | [Self-Hosting UniFi](https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi) · `4cc08843fe86` | UniFi OS Server 不支援直接託管 Protect、Access、Talk、Connect；不支援獨立 Docker/Podman 容器。Cloud Gateway 內建 Network 控制面不能再由外部 OS Server 接管；配對須評估 UXG 獨立 Gateway。 |
| `switch` / M05 | [UniFi Switch Settings](https://help.ui.com/hc/en-us/articles/33402927617047-UniFi-Switch-Settings) · `1443f8667c29` | UniFi Switch 設定依 VLAN、設備能力和 Gateway 不同；mDNS 跨 VLAN 要求 UniFi Gateway，不可推定所有交換器皆具完整 L3／mDNS 功能。 |
| `talk` / M08 | [Getting Started with UniFi Talk](https://help.ui.com/hc/en-us/articles/27057211577751-Getting-Started-with-UniFi-Talk) · `7c26b546f6dc` | 官方訂閱鎖定的 Talk Phone 僅在美國、加拿大、英國適用；解鎖機種可依條件使用第三方 SIP，不能把官方訂閱地域外推全球。 |
| `unifi_updates` / M01、M09 | [UniFi Updates](https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates) · `87fdad1b32f9` | Update Manager 與 Release Channel 由對應 Console／Site Manager 管理；Official 和 Early Access 不可混為同一渠道。更新仍需依機型、安裝環境及來源核對。 |
| `vlan` / M02、M05 | [Creating Virtual Networks (VLANs)](https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs) · `66224041e9be` | 第三方 Gateway 須先自行建立 Subnet/VLAN/DHCP，Network UI 中對應相同 VLAN ID；VLAN Magic 不支援在 USW Flex / Mini / Ultra / Flex 2.5G、ECS Aggregation 下游使用。 |
| `vpn` / M03 | [Introduction to VPNs](https://help.ui.com/hc/en-us/articles/7951513517079-UniFi-Gateway-Introduction-to-VPNs) · `456eb1bc7963` | Site-to-Site VPN 可使用 IPsec、OpenVPN；Site Magic 為 UniFi Gateway 間的 SD-WAN 管理方法，不能當成所有第三方 VPN／所有硬體均支援。 |
| `wifi` / M04 | [UniFi WiFi SSID and AP Settings](https://help.ui.com/hc/en-us/articles/32065480092951-UniFi-WiFi-SSID-and-AP-Settings-Overview) · `9aa9d109a494` | PPSK 目前要求 WPA2 相容；6 GHz 連線使用 WPA3／OWE，WiFi 7 MLO 要求相容 Client 並啟用 WPA3。不可把 WPA2 PPSK 宣稱直接適用 6 GHz。 |
| `zbf` / M03 | [Zone-Based Firewalls](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi) · `f2f8be483412` | 最低條件 UniFi Network 9.0+、Gateway 4.1+；封鎖 Gateway Zone 可能中斷 DHCP/DNS，刪除 Zone 會刪除相關 Firewall Policy，不能無備份自動套用。 |

**重大限制：** 本表只對公開網頁上上述特定論點做比對，沒有經過真人審核、沒有本輪與 `sync/observed.json` 同算法重算 SHA，也沒有驗證 19 篇**所有段落**或各設備環境。無法據此解除 `REVIEW_REQUIRED`。

## 其餘十個可機器觀測的來源（未核准）

- **3 個版本固定 Developer Markdown：** `network_api`、`protect_api`、`site_manager_api`，由先前 GitHub Runner 證實可讀固定文件版本，但本輪 Web Reader 無法重新讀取這三份 Markdown。只維持 `PUBLIC_OFFICIAL_VERSIONED_DEVELOPER_MARKDOWN` 和 `PINNED_DOCUMENT_NOT_LATEST`，不認定最新官方 API。
- **7 個分類 RSS：** `network_application_release_rss`、`protect_application_release_rss`、`os_server_release_rss`、`dream_machines_release_rss`、`wifi_firmware_release_rss`、`switch_firmware_release_rss`、`cloud_keys_release_rss`。先前唯讀 Runner 有 **127** 筆公開發佈指標，沒有確認每篇的 Official／RC／EA、精確機型清單、下載真實性；仍 `CANDIDATE_UNREVIEWED`。
- **2 個全球來源：** `official_releases` / `software_downloads` 未符合 GitHub Runner 驗證要求，**DEGRADED**，另見 Issue #7。搜尋引擎能讀到部分索引，不足以作為完整的正式全產品版本清單。

## 正式簽核的必要條件

1. 以真實官方來源現況重新取得可對應的 Title + 正文及 SHA，對照對應的 PR #6 `sync/observed.json`、`sync/pending.json` 與 M01–M10，**確認資料沒有漂移**。
2. 由具責任的維護者對個別來源實際完成內容差異、發布渠道／型號適用性審核，留下審核者身分、日期、證據和必要的修改理由。
3. 再依 `scripts/approve_official_update.py` 與正式 PR 審核建立 `sync/reviewed.json` 紀錄。此預審文件本身絕不寫入該檔案。
4. CI `check_review_gate.py` 在 29 筆仍為 Pending 的階段 **必須保持 BLOCKED**；不可為了綠燈無證據解封，也不可把官方 RSS 標題當作可實際升級設備的授權。
