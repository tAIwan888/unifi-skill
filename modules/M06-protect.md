# M06 — UniFi Protect：錄影、儲存、Retention、隱私與匯出

**範圍：** 公用資料模型與架構規劃；不需要私人攝影機影像、Console IP、人物識別資料或 API Key。  
**證據狀態：** `DOC_REVIEWED`（官方 Help Center；核對 2026-10-18），**未做實際 Protect/NVR 測試**。  
**預設：** Local-first、最小權限、錄影保留政策明確、所有匯出經個別授權。

## 學習目標與完成標準

1. 能區分 UniFi Protect Console／NVR、Camera、PoE Switch、Storage、Recording Mode 與 Retention。
2. 能在不蒐集真實影像的情況下規劃 Recording Retention、Archive、Storage Resilience 與故障復原。
3. 明確知道 Enhanced Retention **需要 Protect 5.1+**，且舊影像降成低解析後**無法恢復為原始高解析**。
4. 了解本地儲存與選用 Off-Site Archiving 的差別，不把預設本地儲存說成資料絕對不可能上傳。
5. 能建立權限、稽核、錄影證據匯出與刪除/法遵保留的標準流程。

**驗收：** 合成 8 Camera + NVR 需求，輸出 `Camera Max Bitrate / Continuous vs Detection / Retention Days / Storage and RAID / Access Roles / Export Rules` 等欄位，不使用私人錄影片段。對不可逆降解析與刪除，必須提出審批與回滾不可行的警告。

## 核心概念

| 功能 | 官方描述 | 限制／風險 |
|---|---|---|
| Protect Hosting | 需要支援 Protect 的 UniFi Console、受支援 Camera／ONVIF 相容設備、PoE 與儲存 | **不能假設所有 Cloud Gateway、自架 UniFi OS Server 都支援 Protect**；逐型號核對 |
| Recording Mode | Always、Detection Only、Never，可設排程與 Event Buffer | Detection-only 不保證記錄每個需要的事件 |
| Storage／Retention | 容量、壓縮、影像品質、歷史保留期、錄影數及磁碟耐久 | 原始影像容量／天數受 Bitrate、VBR、Camera 數、可用空間及冗餘影響 |
| Enhanced Retention | Protect 5.1+ 可在設定期限後將較舊影像降為低解析 | **已降解析的錄影不可恢復為高解析**，變更前需評估證據需求 |
| 遠端觀看 | 官方說明在支援路徑中，Client ↔ Console 通訊採端對端加密、錄影預設保存在本地 | **Off-Site Archiving 是選用功能**，啟用後另有外部儲存／供應商隱私風險 |
| Stream Encryption | 在支援的 Camera/Gateway 型號與 Protect 5.2.42+ 可選用 Camera→Console Stream Encryption | 不等同所有攝影機或所有情境都支援；依產品功能核對 |
| Export / Archive | 個別片段可匯出，也可在支援版本配置 NAS／雲端歸檔 | 匯出敏感影像應記錄目的、授權、存放期限與刪除 |

官方：
- https://help.ui.com/hc/en-us/articles/27878858632599-Getting-Started-with-UniFi-Protect
- https://help.ui.com/hc/en-us/articles/29393161732119-Managing-Storage-and-Retention-in-UniFi-Protect
- https://help.ui.com/hc/en-us/articles/31234972188951-How-UniFi-Protect-Protects-Your-Data

## 官方建議做法

1. **選相容 Host：** 先查 Tech Specs 的 Application 支援、Max Cameras、PoE/交換器、儲存規格；不要把 Network 控制面和 Protect 控制面混用。
2. **儲存估算：** 先選 Always/Detection Only，再依實際 Bitrate、Camera 數、需求 Retention、硬碟可用容量與冗餘設計；不要用單一 Camera 規格承諾所有場域錄影天數。
3. **保留策略：** 根據用途／法規設定期間與權限；需保留完整解析證據者，在開啟 Enhanced Retention 前先做好 Export/Case 保留方案。
4. **隱私：** 預設以 Local-first；遠端觀看與 Off-site/Cloud Archive 是不同功能。若使用 Google Drive/OneDrive/Dropbox/NAS 歸檔，需審查額外資料接觸者、保留週期、Encryption 和 Access Logging。
5. **影像匯出：** 僅在具權限的人員提出明確目的時 Export clip；保存檔案 Hash、時間範圍、時間同步/NTP、處理者／接收者、合法保存期間。
6. **客戶端權限：** 避免共享 Super Admin、限制可觀看 Cameras 的角色，並定期撤銷不再需要的人員與第三方整合金鑰。
7. **防止誤刪與遷移：** Configuration Backup 並非整批 Protect 舊錄影備份；跨 Console Migration 請按 M09 另外確認歷史錄影與新錄影完整性。

### 官方 Camera／Console VLAN 前提（公開文件對照；正式審核仍待 PR #6）

官方《Getting Started with UniFi Protect》指出：**若使用 CloudKey 或 NVR，且網路中有多個 VLAN，攝影機應位於該 CloudKey/NVR 相同的 VLAN**。這是官方針對特定託管類型的建置提示，**不得無條件延伸為所有 UniFi Console 或所有 Protect 型號一律不可跨 VLAN**。實際 Camera/Console、L3 探索與支援限制應依安裝版、型號及官方 Adoption 文件核對。

任何解決 Camera Adoption 的建議都應先核對受支援網路拓撲和同 VLAN 條件；不要以跨 VLAN 全開、防火牆全放行或對私人攝影機執行遠端腳本作為預設補救。

來源：https://help.ui.com/hc/en-us/articles/27878858632599-Getting-Started-with-UniFi-Protect 。這是公開文件核對，不代表對任何真實攝影機／影像作實機驗證；`SOURCE_OBSERVED_UNREVIEWED` 的來源審核仍未完成。

## UI 操作路徑

- `Protect > UniFi Devices > [Camera] > Recording Settings`：Always / Detection Only / Never 及依版本支援的錄影參數。
- `Protect > Settings > Storage Manager`：Retention 及 Enhanced Retention（Protect 5.1+）。
- `Protect > Settings > Off-Site Archiving`：選用外部歸檔目的地（只有需求確認／授權時啟用）。
- `Protect > Settings > System > Advanced`：受支援 Camera 的 Stream Encryption（官方 Protect 5.2.42+）。
- UI 路徑／存取權限隨 Protect App 及 Console 版本改變；請當版核對。

## CLI / API 替代方法

- Protect API 與 Network API 是不同服務與權限系統；先用官方版本化 Developer Documentation 查 GET 列表／Metadata 的能力。
- Live Snapshot／Stream／匯出影像會涉及敏感個資，不在公用 Repo 自動取得或傳送；**不新增預設會存入 GitHub Actions 或 SaaS 的攝影機影像 Workflow**。
- 若需要告警整合，公用 n8n 範例使用合成事件資料，且輸出只允許聚合計數，不包含可識別人士的 Media URL 或完整 Camera Serial。

## 常見情境範例

- **保留 30 天高解析影像：** 先估算實際容量，再判斷 Enhanced Retention 是否適合。不能假設設定 30 天高解析，31 天後仍能取回原始解析度。
- **重要事件需長期保存：** 依受支援 Case／Flag/Archive 工具存留，另確認處置期間、存取者與外部存儲位置。
- **全站更換 NVR：** 移轉設定不等同移轉舊錄影；按 M09 另訂歷史影像保存與新系統錄製的雙重驗收。

## 風險與注意事項

- 攝影機可能拍攝人、車牌、訪客與工作區域；資料保留、影像辨識與錄影通知規範隨地區/用途不同，需由資料控制者管理。
- Enhanced Retention 的低解析轉換不可逆；Hardware RAID／磁碟更換及 Retention 調整可造成長期資料損失。
- Protect 5.2.42+ Stream Encryption 不代表所有 Camera 支援；請核對官方所述 G4/G5/AI 系列與具體型號。
- 對任何影像的 Export、Off-Site Archive 或 AI 分析自動化，需有 Owner 明確授權；預設不生成或執行讀取私人攝影機的 Live Script。

## 驗證方式

`Console App Support / Camera Model / Max Bitrate / Recording Mode / Storage Usable / Retention / Evidence Export / Role & MFA / Time Sync / DR` 逐項驗證。測試要區分 **新錄影可用** 和 **歷史證據保存成功**。只做文件檢查只能標 `DOC_REVIEWED`；實驗室評估必須使用合成媒體。

## 故障排除流程

Camera PoE/Link → Protect Console/App 版本 → Adoption → Storage Health/Usage → Recording Mode/Schedule → Retention/Archive → Time Sync → Role Permissions → 是否使用 Off-Site Archiving → Evidence Export Audit。當疑似遺失錄影時，**先停止會破壞磁碟內容的格式化／修復操作**，以保全證據為優先。

## 官方文件連結

- https://help.ui.com/hc/en-us/articles/27878858632599-Getting-Started-with-UniFi-Protect
- https://help.ui.com/hc/en-us/articles/29393161732119-Managing-Storage-and-Retention-in-UniFi-Protect
- https://help.ui.com/hc/en-us/articles/31234972188951-How-UniFi-Protect-Protects-Your-Data
- https://help.ui.com/hc/en-us/articles/27723320017815-UniFi-Protect-Recording-Modes-Schedules
- https://help.ui.com/hc/en-us/articles/27723188678935-Exporting-Clips-Cloud-Archiving-with-UniFi-Protect


### 已觀測官方來源補充索引（尚待人工內容覆核）

下列連結補齊來源監測的精確引用，狀態為 `SOURCE_OBSERVED_UNREVIEWED`。新增索引**不表示**逐頁比較已完成、版本渠道已核准或實驗室測試通過；正式來源審核仍依 Draft PR #6 與人工審核紀錄辦理。

- https://developer.ui.com/protect/v7.3.70/ai-gettingstarted.md （固定版本文件；不是最新 API 或相容性保證）

## 待補實作

各 Protect Console 和 NVR 的 Camera/Storage 相容性與實際容量公式、Off-Site 歸檔 API/權限支援、Storage Restore Drill、保全證據簽章驗收，需要另外以官方版本及 Lab 測試證明。
