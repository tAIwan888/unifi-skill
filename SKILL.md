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
## 知識模組
M01 平台架構；M02 Network；M03 Firewall／VPN；M04 WiFi；M05 Switch；M06 Protect；M07 Access；M08 Identity／Talk／Connect／EV；M09 備份／安全／維運；M10 API／n8n。
## 同步
參見 `docs/official-sync.md`。僅連線公開官方來源、只讀監測；不連接任何 UniFi Controller。