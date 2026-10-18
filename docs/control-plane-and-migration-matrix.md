# UniFi Control Plane 與遷移相容性矩陣

**來源：** Ubiquiti 官方 Help Center，人工核對日 2026-10-18。  
**驗證：** DOC_REVIEWED；尚無實機證據。  
**限制：** 這是**產品家族級**控制面關係，不保證某型號、某 OS/App 版本可執行全部功能；差異需官方 Tech Specs 覆核。

## Control Plane 組合

| 現有／目標類型 | 官方支持方向 | 結論 |
|---|---|---|
| Cloud Gateway → 外部 UniFi OS Server 管理其 Network | **不支援** | Cloud Gateway 已有內建 Network Control Plane，不能交由外部 Server Adopt |
| Independent Gateway (UXG) + UniFi OS Server | **可評估** | UXG 沒有內建控制面，適合與外部 UniFi Network Control Plane 配對；仍需核對具體型號與版本 |
| CloudKey + UniFi OS Server 兩者同時管理相同 Network devices | **不支援** | 同一 Network 設備不能交給兩個控制面同時管理 |
| UniFi OS Server 自架 Protect、Access、Talk、Connect | **不支援** | UniFi OS Server 只提供 Network + 部分 UniFi OS 功能；其他 Apps 需相容 UniFi Console |
| Cloud Gateway + Site Manager 遠端管理 | **官方支持** | Site Manager 是統一管理入口，與 Gateway 上的本地控制面不同 |
| 所有部署統一遠端登入與本地單獨登入 | **可設計** | Local-only 與 Remote Management 是部署決策；使用者權限／Outbound 需求按設定核對 |

官方：
- https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi
- https://help.ui.com/hc/en-us/articles/30319146145175-Understanding-UniFi-Cloud-Architecture
- https://help.ui.com/hc/en-us/articles/28457353760919-UniFi-Local-Management

## 備份與資料移轉分類

| 流程 | 配置可移轉？ | 舊的錄影資料能同步移轉？ | 主要必要條件 |
|---|---|---|---|
| Cloud Gateway／CloudKey → 相容新 Console，System Config Backup | 官方文檔有支援流程 | **不代表** Protect 的舊錄影可移轉 | 來源/目標 OS/App、權限、恢復窗口；跨不同型號目的 UniFi OS >= 3.1（針對官方描述情境） |
| Network Server → UniFi OS Server／新 Network Host，Network .unf | 依官方流程 | 不適用於完整 Protect 影片備份 | Network Backup 支援、Inform、DNS、採用狀態、停用舊 Controller |
| Site Export／Import | 僅特定支援此操作的舊多站點來源與目標 | 不適用 | 對應 Site 與 UI 版本、Device Adoption |
| Protect 設定移轉至新 UniFi Console | 設定依 Backup Restore | **官方明示舊錄影無法直接轉移** | 舊 Console/硬碟保留、Retention 法規、恢復後的新錄影驗證 |

官方：https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi

## 使用者可自行套用的驗收問題

- 目標需要管理 **Network、Protect、Access、Talk 還是全部？**
- Source/Target 的產品家族及 **UniFi OS / Application / Firmware** 實際支援範圍是否經官方型號文件確認？
- 備份 Restore 是用於 **設定**、**站點** 還是 **原始資料**？要保留哪些類別？
- 是否有明確的 Version Matrix、Device Adoption/Inform、故障時的原系統復原方式及 Approval？
- 是否有 Local-only/MFA/RBAC/Cloud Restriction 的管理政策？

公用 Skill 階段**不主動蒐集任何私人設備清單**；只有使用者另行請求其環境部署時才需這些資訊。
