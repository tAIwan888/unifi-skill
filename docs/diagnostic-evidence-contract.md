# UniFi Skill 診斷證據關卡（離線驗證）

**目的：** 將 `SKILL.md` 與 `docs/evidence-and-acceptance.md` 的「文檔 ≠ Mock ≠ 實機」原則轉成可檢查的診斷報告契約。這是公用知識與合成驗證；**不得把 CI PASS 宣稱為已操作私人 UniFi 環境**。

## 強制入口

1. 每項 UniFi 工作開始前，以 GitHub Connector 讀取最新 `SKILL.md`，以及與任務相關的 modules、runbooks、`docs/evidence-and-acceptance.md`；記錄每個檔案完整 40 位 Git Blob SHA。
2. 依照目前版本的官方 Network API 文件與實際授權範圍進行唯讀查詢；官方網站僅核對／補充 Skill。Skill 不可讀時停止 Skill 診斷，不以官方網站冒充 Skill。
3. 對每個指標分開記錄 `OBSERVED`／`NOT_OBSERVED`、來源和觀測值；缺失資料不可當成 0。
4. 若任一必要實測欠缺，`verification_status=INCOMPLETE`；禁止配置變更建議。當全部必要指標有觀測，至多升為 `EVIDENCE_READY`，**不是已找到根因、不是 Lab 通過、不是授權變更**。
5. 變更提案必須具備 `basis`、`baseline`、`validation_plan`、`rollback_plan`，以及 `execution_status=NOT_EXECUTED_REQUIRES_APPROVAL`。禁止在未授權私人環境執行寫入。
6. 報告僅可保留脫敏欄位；**私人 MAC、IP、SSID、Serial、金鑰、Token、網路拓撲不可進公開 Repo 或 CI artifact**。此檢查器只會阻擋部分敏感欄位名，不能取代獨立 DLP／人工敏感度檢查。

## WiFi LAN 效能門檻

適用：`scope=wifi-lan-performance`，對應 M04 WiFi、M05 Switch、M10 API 與 RB03／RB04／RB05（以實際情境選用）。下面六個指標都需明確標示狀態：

- `ap_uplink_port_mapping`：確認 AP 對應哪個交換器埠，而不是推測其鏈路速率。
- `ap_uplink_negotiated_mbps`：該實際埠雙端協商速率。
- `client_band`：實際連線頻段，不是網卡硬體支援清單。
- `client_rssi_dbm`：同一 Client 的 RSSI 量測。
- `ap_radio_retry_pct`：AP Radio 重傳率（不得偽裝成該 Client 重傳率）。
- `lan_throughput_mbps`：內部 LAN 端到端吞吐；Windows PHY Link Rate、WAN 測速均不能代替。

不需要用外部測速服務。如果沒有 LAN 接收端，保留吞吐量為 `NOT_OBSERVED`，先做可支持的 RF／上聯排查，不作速度優化已驗證結論。

## 驗證工具

在本 Repo 的工作目錄中，對**已脫敏且未提交的本地 JSON 報告**執行：

```shell
python3 scripts/check_diagnostic_evidence.py ./sanitized-report.json
```

離線檢查包括路徑是否來自本 Repo、實際檔案 Git Blob SHA 是否匹配、引用模組與 Runbook 是否已載入、必要指標是否缺失、測試等級、變更提案是否安全，以及常見私密欄位名。檢查器不會連線 GitHub 或控制器，也不會自行聲稱已讀取 GitHub；**SHA 匹配只驗證檔案版本，不證明任何 AI 曾實際閱讀**。ChatGPT 的讀取紀錄仍需透過工具稽核。

CI 使用合成單元測試檢查 gate 的 fail-closed 行為，不儲存任何私人報告。本機腳本通過 `PASS` 只代表報告符合結構契約，**並不是現場網路效能 PASS**。

## Windows 實機資料蒐集：Skill 內建入口（預設）

**這是由 UniFi Skill 本身管理的本地唯讀蒐集器**，不需要再下載／解壓縮舊 v6 ZIP，也不需要第二台有線電腦、手機或外部 WAN 測速服務。Windows 本機需安裝 Python 3.9+，並有已授權的 UniFi Network Integration API Key；金鑰在終端機隱藏輸入，**不得傳給 ChatGPT 或 GitHub**。

在已取得的 Skill Repo 根目錄，PowerShell 執行：

```powershell
py -3 scripts\run_wifi_skill.py --local "https://unifi.local/proxy/network/integration/v1" --ca-cert "C:\local\unifi-local.pem" --out "$env:USERPROFILE\Documents\wifi-skill-evidence.json"
```

- `unifi.local` 是**範例本地 mDNS 名稱**，需使用你個案已授權的 RFC1918／.local 端點；若已有經核對的 Console CA PEM，才使用 `--ca-cert`，未提供時採 Windows 系統可信任 CA。不得停用 TLS 驗證。
- 範例是唯讀 GET `/info`、`/sites`、`/sites/{siteId}/devices`、`/sites/{siteId}/devices/{deviceId}` 與 `/statistics/latest`；不掃描網段、不開啟 LAN 伺服器、不操作設備、不對外聯絡測速網站。
- 同一台 Windows 電腦由原生 WLAN API 或明確 `netsh` 欄位取得**當前關聯**的頻段、RSSI（如果 Windows 權限與網卡驅動有提供）；PHY 速率不得充當吞吐量。
- 輸出只有非識別型量測、Skill 完整 Blob SHA 與證據缺口，儲存在本機 Repo **之外**的 `wifi-skill-evidence.json`，程式以 `check_diagnostic_evidence.py` fail-closed 驗證。使用者應先檢查脫敏內容再決定是否分享。
- 測量不能唯一確認 AP→Switch Port 或在沒有 LAN 接收端時測得實際端到端吞吐；兩項保持 `NOT_OBSERVED`，驗證狀態 `INCOMPLETE`，不得因此建議改動 WiFi。
- 緊急停止：直接結束程式即可；本工具不寫入 UniFi，沒有設定回滾動作。若日後另經授權執行 RF／Port 變更，必須先保存基線並按 M04/M05 對應 Runbook 驗證與回滾。

完全離線合成 Smoke：

```powershell
py -3 scripts\run_wifi_skill.py --mock --out "$env:TEMP\wifi-skill-mock.json"
```

舊 v6 ZIP 可以透過 `--collector-dir "C:\local\unifi-v6"` 相容使用，但**非必需**。CI 的 Ubuntu 與 Windows 合成測試只驗證程式安全與資料轉換，**不等於你本人 Intel AX211/U7 Pro 版本已實機驗收**。

**目前已知限制（原版 v6）：** v6 原始資料沒有可靠的 AP 上聯 Switch Port Mapping 與協商速率，也沒有 Windows WiFi RSSI dBm 或已驗證連線頻段，沒有內網對端時亦無端到端吞吐；因此缺少這些證據的 v6 報告，轉換結果保持 `INCOMPLETE`，而不是以 6 GHz 硬體支援、Windows Signal %、PHY Link Rate、任一 Switch Port 的 2.5 GbE 數值或外網頻寬補上缺口。只有 1 台 AP 的情況下，若 API 即時統計有效，才可記錄 AP **radio** 重傳率，且不得當作特定 Windows Client 的重傳率。

`PASS` 只表示來源檔 SHA 與報告契約檢查通過；**不是**效能已驗收或裝置有被修改。對 API 網路適用性、版本、地區法規與現場鏈路證據仍要另行驗收。


## Windows 實測擴充（2026-10-20，PR 待實機驗證）

本 Repo 增加 `scripts/windows_wlan_native.py` 與 `scripts/windows_netsh_localized.py`，由 `scripts/run_v6_wifi_skill.py` 在既有 v6 本地蒐集後執行；不需要第二台電腦、手機或外網測速。

1. **第一優先**：Microsoft 原生 WLAN API 的「目前關聯 BSSID」與 `WlanGetNetworkBssList`，僅在 BSSID + SSID 同時唯一匹配時輸出該 BSS 的 `ulChCenterFrequency`（kHz → MHz → 2.4/5/6 GHz）及 `lRssi`（dBm），而不是 WiFi 網卡支援頻段或相鄰 AP 的 6 GHz 廣播。
2. **後備**：唯讀 `netsh wlan show interfaces`，只解析當前介面的明確 `Band/頻帶`、`RSSI/Rssi` 等行；英文及繁體中文皆有合成測試。`Signal/訊號 %` 不換算成 dBm，Channel 85 不視為 6 GHz 證據。
3. Windows 未授予定位權限、Native WLAN BSS 不存在、無法唯一比對 BSSID 或有多個 WiFi 介面時，保留未知或使用明確欄位的後備結果；不繞過 Windows 權限、不外傳 SSID/BSSID/MAC/IP。
4. `convert_v6_wifi_evidence.py` 僅接受 `WINDOWS_WLAN_API_ASSOCIATED_BSS` 或 `WINDOWS_NETSH_EXPLICIT_CURRENT_INTERFACE` 來源的有限範圍 RSSI 與 2.4/5/6 GHz；僅本機 `collection_mode=local` 可以將其標記為 `OBSERVED`。此為同一 Windows Client 的當下鏈路觀測，不是整體 RF KPI、不是 LAN 真實 Mbps。

**AP 上聯限制由正式 API 文件確認**：UniFi Network 10.6.106 的官方 GET `/sites/{siteId}/devices/{deviceId}` `uplink.deviceId` 定義上游裝置；但公開回應範例沒有可直接唯一指認該上游 **Switch Port** 的屬性。單純找到父設備或其若干 2.5/5/1 GbE UP ports 不是 AP 與 Port 的證明，仍須由經授權的 UniFi Port/Topology UI 與 LLDP／現場證據確認。沒有可核對的 Port 對應便保留 `ap_uplink_port_mapping=NOT_OBSERVED` 與 `ap_uplink_negotiated_mbps=NOT_OBSERVED`，不嘗試未文件化的 Legacy API、SSH、SNMP 設定更改或公開倉庫儲存實際拓撲。

官方補充：
- https://developer.ui.com/network/v10.6.106/getadopteddevicedetails
- https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_bss_entry
- https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlangetnetworkbsslist

**驗收分界**：GitHub CI 的 Linux 合成測試不能驗證 Intel AX211／Windows 11 的實際 native ABI、定位隱私權、真實 6 GHz 接收或 UniFi Network 10.6.106 API 取樣。實機成功報告仍需取得使用者同意在其本機唯讀執行後驗證；否則最多只能聲稱程式與合成測試 PASS。
