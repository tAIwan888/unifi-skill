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
