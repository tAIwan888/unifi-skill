---
name: unifi-skill
description: 官方來源可追溯的公用 UniFi 規劃、設定、維運與 API 知識 Skill
---
# UniFi Skill
適用於家庭、SOHO、MSP、網管及自動化工程師。預設「公用知識模式」；**不主動蒐集使用者私人網路資訊、API Key、IP、拓撲、韌體清單**。
## 使用規則
1. 優先引用 https://help.ui.com/ 、https://developer.ui.com/ 、https://techspecs.ui.com/ 、https://academy.ui.com/ 及 https://ui.com/ 。
2. 明確標記官方支援、非官方建議、需實測驗證、失效／待審來源。
3. 對每個配置步驟註明產品及 UniFi OS、App、Firmware、API 版本適用性；不明則標示「需確認」，不得臆測。
4. Firewall、VLAN、VPN、Adoption、Migration、API 寫入均提供備份、驗證和回滾；不得未經明確授權對生產環境變更。
5. 由 `sync/pending.json` 偵測的新內容一律視為「待審」，直到對照官方文件並完成審核，不得宣稱自動習得。
6. 任何診斷或效能調整，先載入本 Skill、相關模組／Runbook 與 `docs/evidence-and-acceptance.md`，記錄各檔 Git Blob SHA，並依 `docs/diagnostic-evidence-contract.md` 標記證據缺口；必要實測不足時不可提出確定性的變更結論。
7. **Agent 自動化優先：** 有個案唯讀授權與本地執行端時，凡官方 API 或 Windows／macOS／Linux 可用的原生唯讀介面能取得的實測，先由 Skill 工具自動查詢、核對與驗收；不得先要求使用者到 UniFi UI 手動查埠、讀速率或截圖。若官方欄位無法證明對端交換器埠，標記資料缺口、已檢查的 API 來源及後續可驗證路徑；不得猜測。此公用 GitHub Skill 不直接連接私人設備；仍需受使用者控制的本地執行環境。
8. **跨平台單次執行：** 執行端支援 Windows／macOS／Linux 的按需觸發；不得預設安裝背景服務、開機啟動或定時排程。各平台 adapter 僅在接到授權診斷任務時啟動、蒐集脫敏證據、依版本／SHA／Evidence Gate 驗證，完成即退出。任何網路同步或程式更新必須有可驗證的版本與簽章，不得直接下載執行未核准的 GitHub 主線程式。
9. **通用 Collector，任務選擇：** 單次執行檔不是僅為 WiFi 而設。Agent 依目標選用已驗證的 Network Sites／Devices／Networks／Clients／Ports 官方唯讀 GET 蒐集模組；對 Gateway、Firewall、VPN、Protect、Access、Identity、Talk、Connect、EV、Backup 等尚未驗證 API 的能力，回報 `NOT_OBSERVED` 及原因碼，不得呼叫未列入版本化 API 能力清單的端點。必要數據未齊時禁止確定性的效能或設定結論，並以來源 Blob SHA 可驗證的脫敏報告回傳。
## 知識模組
M01 平台架構；M02 Network；M03 Firewall／VPN；M04 WiFi；M05 Switch；M06 Protect；M07 Access；M08 Identity／Talk／Connect／EV；M09 備份／安全／維運；M10 API／n8n。
## 同步
參見 `docs/official-sync.md`。僅連線公開官方來源、只讀監測；不連接任何 UniFi Controller。