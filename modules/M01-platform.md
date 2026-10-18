# M01 — UniFi 平台架構、控制面與遠端管理

**類型：** 公用知識模組；無私人設備資料。  
**文件核對日期：** 2026-10-18（官方 Help Center 人工查閱；排程自動爬取仍受 403 限制）。  
**支援分類：** 以下有官方來源者 `OFFICIAL_SUPPORTED`；選型順序為 `ENGINEERING_RECOMMENDATION`。  
**驗證分級：** `DOC_REVIEWED`，並非實驗室／生產環境實測。

## 學習目標與完成標準

1. 解釋 Control Plane（設備與 App 實際接受管理的位置）與 Site Manager（跨站存取入口）的差異。
2. 能依 **Gateway 類型** 與需要託管的 **UniFi Application** 選擇相容的 Hosting。
3. 正確辨識 UniFi OS Server、新舊自架 Network Server、Cloud Gateway、CloudKey、NVR 與 Official Hosting 的限制。
4. 提出 Offline/Local-only 與 Remote Management 選項的風險、可用性與安全差異。
5. 對任何 Controller 移轉提出備份、恢復與解除舊管理端競爭的程序。

**驗收：** 在不依賴真實使用者設備的情境題中，能區分「Cloud Gateway + 外部 UniFi OS Server」不可做的採用方案；說明 Protect 不能直接部署於 UniFi OS Server；產出完整的版本相容性及遷移回滾清單。

## 核心概念

UniFi 為混合式管理架構：控制面可在本地 Cloud Gateway、CloudKey、UniFi OS Server 或其他相容託管端，**Site Manager 是跨站統一入口，不是把每台設備的控制面搬到雲端**。資料實際流向仍須依所用應用及功能確認。參見官方 [Cloud Architecture](https://help.ui.com/hc/en-us/articles/30319146145175-Understanding-UniFi-Cloud-Architecture)。

| Control Plane / Hosting | Network 管理 | 主要定位 | 需要額外核對 |
|---|---|---|---|
| **Cloud Gateway** | 內建 UniFi Network | Gateway + Firewall + Control Plane | 各型號支援的其他 App 不同；**不能再採用到外部 UniFi OS Server** |
| **CloudKey** | 支援（依型號） | 專用控制面硬體，不一定擔任 Gateway | Protect/Access/Talk/Connect 依型號和容量 |
| **UniFi OS Server** | 自架 Network + 部分 OS 功能 | 自行負責 OS、安裝、維運、備份、上線時間 | 不可當獨立 Docker/Podman Container；**不能自行託管 Protect/Access/Talk/Connect** |
| **Legacy Network Server** | 舊版自架 Network | 遺留環境相容或遷移來源 | 功能與 UniFi OS Server 不相同；預設優先評估遷移 |
| **Official UniFi Hosting** | 代管 Network（與官方所列其他特定功能） | 不想自管控制面主機的人 | 代管範圍、訂閱、區域、出口及其他 App 相容性 |
| **NVR/安全控制面設備** | 通常不作為 Network Gateway | 依支援型號託管 Protect/Access 等 | 儲存、Retention、門禁緊急模式、備援 |

> **不可搭配情境：** Cloud Gateway 內建 UniFi Network，官方不支援把它交由外部 UniFi OS Server 接管。如果需要外部控制面的 Gateway，應按型號選用 **Independent Gateway / UXG 系列**，而不是再疊加另一個 Cloud Gateway。官方：https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi

## 官方建議做法

### 公用選型決策

- 需要一台兼具 Firewall／Gateway 與 Network Control Plane 的設備：優先評估 **Cloud Gateway**；其餘 App 能否安裝仍依該型號規格。
- 希望自架、需要 Organizations／IdP／Site Magic 等功能：比對 **UniFi OS Server** 的官方安裝支援與持續維護成本，並確認產品不是已內建控制面的 Cloud Gateway。
- 希望 OS/Controller 不依賴自管主機：比對 **CloudKey** 或 **Official UniFi Hosting**；後者不等同允許承載所有應用。
- 需要攝影機、門禁、VoIP、數位看板：選擇官方列明可託管 Protect / Access / Talk / Connect 的 **相容 UniFi Console**，不可因 Network 可用就推定其他 App 都可用。
- 若無法連外或要求本地獨立存取：規劃 **Local Management**，並確認 DNS、NTP、現場登入、離線復原方法；不應假設 Site Manager 永遠可用。

### Self-Hosting 界線

官方 UniFi OS Server 的 Linux 安裝涉及 systemd 與 Podman 等主機依賴；**Podman 作為其運作依賴，不代表可以自行封裝成官方支援的獨立 Docker／Podman Container**。勿把網路社群的不受支援容器版列為官方穩定安裝途徑。

舊 Network Server 轉 UniFi OS Server：先匯出備份，關閉舊服務，再安裝或移轉；需按 OS 平台、Port、URL、DNS 與 Inform 遷移差異逐項驗證。官方有提到 Captive Portal 連接埠差異，應按目標版本核對，不可照搬一份萬用 Port 清單。

官方：https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi

## UI 操作路徑

- 本地管理：與 UniFi Console／Server 同網段，透過其 HTTPS/IP 或相容 Console 的官方本地登入入口。Self-hosted Network Server 與其他 Console 的預設登入埠可能不同；不應將 8443/443 當成所有版本永遠固定的 Port。
- Site Manager：`https://unifi.ui.com/`，登入有授權之 UI Account 查看可管理的站點。
- 目前官方文件的遠端管理開關：`Settings > Control Plane > Console > Remote Management`；此 UI 路徑隨應用與版本可能更動。
- 管理人員權限：先區分 Owner / Super Admin / 每個 App 的授權；高權限視同系統管理員，不共享憑證。

官方：
- https://help.ui.com/hc/en-us/articles/28457353760919-UniFi-Local-Management
- https://help.ui.com/hc/en-us/articles/115012240067-Enabling-UniFi-Remote-Management
- https://help.ui.com/hc/en-us/articles/1500011491541-UniFi-Roles-Explained-Admins-and-Users-Members

## CLI / API 替代方法

- UniFi OS Server 官方 Linux 服務名稱與安裝方式依文件核對後可使用 `systemctl` 查狀態；不可因版本未知就直接停用、刪除或重裝服務。
- 官方 Network API 與 Site Manager API 是**兩個不同的 API Family**。由 M10 的 `docs/api-capabilities.json` 及安裝版本的 `Network > Integrations` 決定可行的唯讀端點；不使用未文件化的 Legacy API 作為通用 Skill 依賴。
- 公用知識模式只提供合成範例；**不要求提供私人 Controller IP、設備 Serial、拓撲或 API Key**。

## 常見情境範例

**情境 A：** 已有 Cloud Gateway，但需要管理另一個 Site Manager 組織 → 不是將 Cloud Gateway 掛入 UniFi OS Server，而是確認 Site Manager 的組織授權與個別 Console 的管理方法。

**情境 B：** 自架 Network 同時想管理 Camera → Network-only 控制面不能直接承載 Protect；選相容 UniFi Console/NVR，再依官方 App 支援搭配。

**情境 C：** 多站點不想依賴 Internet 遠端服務 → 保留各站本地控制面、獨立登入／維運與 VPN 備援；Site Manager 是選配的遠端存取途徑，取決於管理偏好。

## 風險與注意事項

- 同一設備不能同時由兩個 Network Hosts 接管；錯誤遷移可能出現 `Managed by Another Console`、Re-adoption、VPN / Site 失聯。
- Cloud Gateway 與 UXG Independent Gateway 的差異是重大架構決策，不能只按型號名稱中的「Gateway」推斷控制面。
- Site Manager 及 Remote Access 帶來便利，也需管理 MFA、RBAC、離職存取撤銷、審計及連線依賴；Local-only 有較高自行維運責任。
- 別把 `Remote Management` 的外連所需 TCP 443/8883 誤解成「必須對 Internet 開放入站管理埠」。若安全政策禁止雲端存取，優先本地／授權 VPN 設計。
- 文件的 `DOC_REVIEWED` **不代表真實主機部署完成**。

## 驗證方式

1. 核對型號與其支援的 UniFi OS／App；確認哪一個實例真正管理 Network、Protect、Access。
2. 核對登入模式（Local/Remote）、管理角色與救援登入方式。
3. 對移轉計畫確認備份類型、來源/目的地相容性、Inform Host、DNS/Firewall、回滾與可接受停機窗口。
4. 後續 Lab 結果須寫明 OS／App／Firmware／版本、拓撲範例、測試日期與錯誤範圍；未有實測不標記 Lab PASS。

## 故障排除流程

Controller 服務是否可用 → DNS/本地 HTTPS 可達性 → UI Account/Role → Site Manager 連線狀態 → TCP 443/8883（**Outbound**，僅使用 Remote Management 時）→ Device Adoption/Inform Host → 備份／移轉紀錄。任何變更先保存現有狀態並確認救援路徑。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/30319146145175-Understanding-UniFi-Cloud-Architecture
- https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi
- https://help.ui.com/hc/en-us/articles/4415364143511-Getting-Started-with-Official-UniFi-Hosting
- https://help.ui.com/hc/en-us/articles/28457353760919-UniFi-Local-Management
- https://help.ui.com/hc/en-us/articles/20680072882967-UniFi-Remote-Management-via-Site-Manager
- https://help.ui.com/hc/en-us/articles/1500011491541-UniFi-Roles-Explained-Admins-and-Users-Members
- https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi

## 待補實作

各硬體型號的具體 App 相容性及 License/Region 要求需按 Tech Specs、版本公告繼續補充，不能把本分類表當成全產品能力矩陣。GitHub Runner 官方文件自動同步仍失敗；此模組的官方文件是人工查閱，需定期重審。
