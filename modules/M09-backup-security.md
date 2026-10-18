# M09 — UniFi 備份、遷移、維運與安全

**對象：** 家庭、SOHO、MSP、UniFi 自架維運。  
**資料來源：** 2026-10-18 官方 Help Center 人工查核，不依賴私人 UniFi Console 資料。  
**支援分類：** 備份類型與遷移限制 `OFFICIAL_SUPPORTED`；DR 演練與維護窗口為 `ENGINEERING_RECOMMENDATION`。  
**測試等級：** `DOC_REVIEWED`／`LAB_NOT_RUN`／`PRODUCTION_NOT_RUN`。

## 學習目標與完成標準

1. 分辨 **System Config Backup**、**Network-only Backup** 及「應用錄影／資料本體」的差異。
2. 根據 Cloud Gateway／CloudKey／NVR／UniFi OS Server／Legacy Network Server 選出可行遷移方式。
3. 說明 Restore 的變更範圍、備份授權與備份檔敏感資訊處理方式。
4. 明確區分 Configuration Restore 與**實際資料復原**（例如 Protect 的舊錄影不可直接從一台 Console 轉移至另一台）。
5. 對變更或韌體升級產出可執行的前置查核、恢復時間目標、驗證與回滾方案。

**完成門檻：** 使用合成情境正確列出備份檔、目標型號／OS/App 相容性、Network Device Re-adoption、失敗回滾，並能阻止「只備份 Network，就聲稱 Protect 影片已完整備援」的錯誤。

## 核心概念

| 備份或移轉 | 適用情境 | 包含與不包含 | 必須驗證 |
|---|---|---|---|
| **System Config Backup** | 多數 Cloud Gateway／CloudKey／相容 Console | 系統、Apps 與裝置**設定**；不等於任意應用的完整原始錄影／檔案 | OS/App/型號相容、授權、需要的設定 |
| **Network-only Backup（.unf）** | Legacy Network Server、自架 Network、特殊 Site 移轉 | Network 設定及採用的網路裝置資訊；**不是所有 UniFi Apps 的完整備份** | UniFi Network 版本、Inform、原 Controller 關閉 |
| **Site Export / Import** | 特定舊版多站點 Network Hosting 需要搬移部分 Site | 選定 Site 與 Network 管理關係（需依產品/UI 版本驗證） | 對應 Site、Inform Host、DNS、Device Adoption |
| **Protect recording 原始資料** | 舊錄影保留、取證、Retention | **不能因 System Config Backup 就假設既有錄影可轉移到新 Console** | 舊主機保留、磁碟格式化風險、錄影存放和法規 |

官方首選：對 Cloud Gateway／CloudKey 使用 System Config Backup；Network-only Backup 主要用於 Legacy/self-host 等特定情境。來源：https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi

## 官方建議做法

### 1. 備份策略決策

- **容許雲端備份的部署：** 官方提供 Automated System Backups，於相容主機的 `Settings > Control Plane > Backups` 配置。官方文件描述每週與重大更新前自動備份的機制；**實際是否啟用及儲存位置需按 Console 版本和 Owner 授權核對**。
- **Local-only／不允許雲端：** 使用相容 Console 的離線 System Config Backup，將檔案存放於受限權限、加密、獨立於原控制面的位置。
- **自架／遺留 Network Server：** 保留與應用版本相容的 Network-only Backup（.unf）；目的控制面的 Console、OS/App、Adoption 能力皆需確認。
- **需要完整災難復原：** 將 UniFi Network 設定、Protect 錄影保留、Access 門禁資料與其他 App 的復原各自列入清單，不得用單一 Backup File 宣稱所有資料均已保護。

### 2. 遷移流程（供審核的通用骨架）

1. 定義來源／目標控制面類型、App、UniFi OS / Network 版本、Site、採用設備、WAN/DNS/SSH/Inform 依賴。
2. 建立**最後一次可恢復的備份**與版本記錄，另保存離線副本；驗證備份檔可下載、權限正確並可在隔離環境演練。
3. **同系列相容 Console**：按官方設定備份 Restore 流程移轉，避免同時讓來源與目標競爭 Device Adoption。
4. **Legacy Network Server**：僅使用 Network-only .unf 或目標所支援的 Site Export/Import；核對 `Inform Host`／L3 Adoption。
5. 如跨**不同 Cloud Gateway、CloudKey 或 NVR 型號**移轉，官方對新目的設備要求 **UniFi OS 3.1 或以上**；此限制並非所有移轉情境的通用最低版本。
6. 遷移後核對各 Site 及 Device 是否在線、管理權限、WAN/DNS、VPN、隔離政策、備份排程和日誌。
7. 如設備顯示 `Managed by Another Console`，按官方 Layer 3 Adoption/Forget/Re-adopt 流程處理；**Factory Reset 是高風險最後手段**，不能在未備份、未授權情況下直接執行。

### 3. UniFi Network 設備採用（Adoption）的連線診斷：依部署模式區分

官方《UniFi - Device Adoption》對 **Network AP／Switch 與 CloudKey／Self-Hosted Network** 提供不同情境的檢查點：

- **同 VLAN（Same-VLAN）**：先確認 Host 正在運作、裝置供電及能看見 `Pending Adoption`；若無法發現，檢查**設備與 UniFi Network Host 之間**的 TCP **8080** 和 UDP **10001** 是否遭該網段內的防火牆或安全軟體阻擋。此項為特定連線的診斷依據，**不是要求在 WAN、全部 VLAN 或全部裝置全面開放連接埠**。
- **不同 VLAN／子網（Layer 3）**：先確認路由、Network Host 可達性及官方 Layer 3 Adoption 適用條件；官方此情境特別列出 **TCP 8080** 的設備至 Host 通訊需求。**不可把同 VLAN 的 UDP 10001 發現條件直接視為跨 VLAN 的萬用開埠建議**。避免在公開文件中產生可直接作用於私人 Host 的 SSH `set-inform`、Port Forwarding 或採用指令。
- **Protect Camera／NVR** 採用的網路、連接埠與 VLAN 條件另依 Protect 官方文件及 M06 核對，不應以 UniFi Network AP／Switch 的 8080／10001 組合取代。

無論哪一種情境，**Factory Reset 只能當作有完整備份、已核對主機所有權與回復途徑後的最後手段**；本公用知識模組不提供未經授權的實機重置或全面放行操作。來源：https://help.ui.com/hc/en-us/articles/360012622613-UniFi-Device-Adoption 。本段僅是公開文件層級的排障對照，不代表 PR #6 的該來源已獲獨立真人批准。

### 4. Protect 遷移的資料保存

官方明確說明：將 Protect 設定 Restore 至另一台 UniFi Console 後，攝影機可在新系統重新錄影，但**舊錄影不可直接跨 Console 轉移**，若要再利用舊硬碟可能需重新格式化，會破壞原有錄影。應先依保存期限與法律要求保留舊主機／錄影，再確認新系統實際錄影與時間戳。來源同上。

### 不可混淆設定還原與 Protect 舊錄影遷移（公開來源核對，正式審核待 PR #6）

官方《Backups and Migration in UniFi》將 **System Config Backup**（OS／應用／設備設定）和 **Network-only Backup**（較常用於 Gen1 CloudKey 或 Self-Hosted Network Server）分開。備份檔有助於還原設定，但**不是對 Protect 歷史影像的整批移轉**。

- 官方指出：在不同 Cloud Gateway／CloudKey／UNVR 型號之間遷移，新的目的地設備需為 **UniFi OS 3.1 或更新**（仍需核對特定型號與 App 支援）。
- **既有 Protect Recordings 不能直接在 UniFi Consoles 之間轉移**；舊錄影保留在原 Host 的儲存裝置，直到移除／重新格式化。若將硬碟拿去新 Console 並需要重新格式化，可能**永久刪除原本影像**。
- 正確驗收必須分別確認「新 Console 成功接管／錄製新影像」及「舊 Host 上的歷史證據仍可依需求取回」。不可因 Setting Restore 成功就宣稱舊錄影已搬遷。

來源：https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi 。涉及實際錄影／磁碟的操作需要獨立授權與保存政策；本文件未觸及任何真實 Protect 資料。

## UI 操作路徑

- 常見 Console：`Settings > Control Plane > Backups` → 下載、Restore 或設定 Auto Backup（視版本與權限）。
- 官方文件亦提到 `Settings > Control Plane > Console` 及部分較舊 Network 設定路徑；不要把其中一個視為所有版本固定入口。
- 在多站點／舊版 Network Hosting 可按版本尋找 `Site Management > Export Site` 和 Import Site；此操作需核對來源與目標是否真的支援。
- 備份與還原權限視 Owner 與 Admin Role 決定，應避免共享 Owner 帳號。Cloud Backup 通常由對應 UI Account 控制。

## CLI / API 替代方法

- **公用 Skill 不自動上傳／下載真實備份檔、不要求使用者提供 Token。**
- 版本化官方 API 若明確支援唯讀的備份狀態，才能加入相對應的 GET Recipe；**不能使用未公開 Legacy API 修改備份或還原狀態**。
- SSH／Inform Host 的變更屬高風險部署步驟，只可依現場授權及官方文件，以完整回滾方案操作。此處不提供未驗證的通用重設指令。

## 常見情境範例

- **Cloud Gateway 更換新型號：** 查看目標 OS、Backup 版本與 NIC/Port 差異；還原設定後逐項核對 WAN、LAN、VPN、Switch/AP Adoption。
- **Network Server 遷至 UniFi OS Server：** 使用 .unf 及官方遷移導引，備妥 Inform Host、DNS/Firewall、停止舊控制面，必要時採 Site Export。
- **Protect NVR 升級：** 將設定遷移與「舊錄影保留」分成兩項驗收，不以恢復攝影機上線取代錄影資料完整性驗證。
- **防止人為失誤：** 在專用隔離 Lab 進行 Restore Drill，測試不相容版本時預期失敗分支，並記錄恢復時間／所需權限。

## 風險與注意事項

- 不相容備份版本、遺漏 Apps、重採用、網段／管理 VLAN 改動、Door/Camera 離線、違反 Retention，皆可能帶來實際風險。
- 備份檔本身可能包含系統設定、站點資訊、認證或 SSH 相關敏感資訊；加密保存、最小化授權、保留時效與安全刪除流程必須明確。
- RPO/RTO 是管理政策與演練結果，不是 UniFi 官方一定能達成的保證；沒有實驗室或故障演練不得標示 DR PASS。
- 每一筆 Upgrade / Migration 均需獨立的 `upgrade_window`、`backup_sha256`、`rollback_plan`、`owner`、`post_checks`（可為合成範本欄位，不提供私人值）。

## 驗證方式

- 來源／目標型號與 App/OS 版本支持備份 Restore／Export/Import；備份檔讀取權限適當。
- 恢復後網路設備全數採用、管理連線／VPN／必要 Firewall、DNS/DHCP、應用功能可用。
- Protect 的歷史錄影保存與新錄影運行**分別**驗收。
- 紀錄成功與失敗狀態、原 Control Plane Recovery、Rollback 事件；不能只看到 UI 「Restore completed」即宣稱完整 DR 成功。

## 故障排除流程

備份檔類型 → Source/Target 產品與 App/OS 相容性 → Restore Logs → Site & Device Adoption → DNS/Inform Host → WAN/VPN/Policy → 個別 UniFi App 啟動／儲存與 Retention → 已備妥回滾的復原流程。錯誤若涉及 Factory Reset 或錄影格式化，應**停下來要求明確變更授權**。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi
- https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi
- https://help.ui.com/hc/en-us/articles/115012240067-Enabling-UniFi-Remote-Management
- https://help.ui.com/hc/en-us/articles/1500011491541-UniFi-Roles-Explained-Admins-and-Users-Members


### 已觀測官方來源補充索引（尚待人工內容覆核）

下列連結補齊來源監測的精確引用，狀態為 `SOURCE_OBSERVED_UNREVIEWED`。新增索引**不表示**逐頁比較已完成、版本渠道已核准或實驗室測試通過；正式來源審核仍依 Draft PR #6 與人工審核紀錄辦理。

- https://help.ui.com/hc/en-us/articles/360012622613-UniFi-Device-Adoption （公開官方文章；內容差異尚待核對）
- https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates （公開官方文章；內容差異尚待核對）
- https://community.ui.com/rss/releases/UniFi-OS-Dream-Machines/b0f0a740-021e-4027-a778-ceba983be74b （僅 Dream Machines 系列 UniFi OS 公告；升級、備份還原與回滾相容性仍待逐機型核對；Official／RC／EA 尚未核實）
- https://community.ui.com/rss/releases/UniFi-OS-Server/76650b06-fc47-4892-9c12-25c64c39f842 （僅 UniFi OS Server 公告；不證明 Legacy Network 備份、跨平台遷移或其他 Apps 資料可還原；Official／RC／EA 尚未核實）

## 待補實作

逐一依產品線補充 Restore Compatibility Matrix、Protect Recording Retention 演練、Access 生命安全管制、Release Channel/版本升級順序；需有實驗室證據才可升格為 `LAB_TESTED`。
