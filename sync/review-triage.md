# 公開 UniFi 官方來源自動監測（機器來源資料，非升級核准）

> 無真人簽核；機器驗收的內容僅有來源 URL、SHA-256、範圍與解析器元資料。來源存在不等於發布渠道或設備相容性已驗證。

- 機器驗收來源：**29**
- 待人工簽核來源：**0**（此監測流程不再要求真人簽核）
- 官方全域入口失敗：**2**
- 最新來源健康：**29/31**；DEGRADED

- REQUIRED：29/29；失敗 0
- OPTIONAL REFERENCE：0/2；失敗 2
- Operational status：REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS
- 全球入口未形成可驗證的完整 Release Manifest／最新穩定版／下載與機型相容性清單；不得升格知識。


## 本輪失敗的來源

| 來源 | 錯誤類別 | 官方來源 |
|---|---|---|
| official_releases | UNREADABLE_OR_JS_ONLY | [官方來源](https://community.ui.com/releases?view=latest) |
| software_downloads | NO_VERIFIABLE_RELEASE_ENTRIES | [官方來源](https://www.ui.com/download/unifi) |

## 不得自動擴權的界線

- 29 筆機器來源記錄位於 sync/machine-accepted.json；0 筆知識、Release Channel 或設備升級授權。
- 7 個類別 RSS 的公告仍屬 CANDIDATE_UNREVIEWED，不能推論 Official / RC / EA 或單一型號支援。
- 失敗的全域 Release/Downloads 入口維持 DEGRADED；不得偽造完整版本清單。
- Source metadata gate 可自動通過，私人 UniFi 設備與知識內容絕不由此自動修改。
