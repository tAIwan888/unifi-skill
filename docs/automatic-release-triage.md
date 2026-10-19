# UniFi 自動化官方 Release RSS 版本分流 — 例外才人工處理

## 行為和界線

- **零逐筆人工輸入**：自動讀取七個已在 `sync/sources.json` 登錄的 Ubiquiti Community 產品範圍 RSS。GitHub Runner 採用既有 HTTPS、robots.txt、來源完整性與 XML 限制；不存取使用者 Controller、憑證或現場硬體。
- **機器可認證的範圍**：官方 Community RSS 可存取、來源 SHA 符合本輪觀測、正式來源 URL／產品類別、RSS 貼文 UUID、日期與版本文字。正常指標自動進入 machine-indexed inventory；不須有人手動核准每一筆「收到貼文」的事實。
- **不可混淆的範圍**：來源 category 不等於 Official／RC／EA 發布頻道，RSS 的機型標題不等於完整裝置相容矩陣。沒有廠商可重現的個別正式結構化內容與下載證據時，`release_channel=UNKNOWN_NOT_VERIFIED_BY_RSS`、`hardware_compatibility=NOT_VERIFIED_FROM_RELEASE_NOTES`、`device_upgrade_authorized=false`；這不妨礙通用版本追蹤，但禁止進一步宣稱穩定版或觸發更新。
- **只看例外**：某一類來源 403／404／JS-only、SHA 失配、候選範圍漂移、重複 UUID、已記錄貼文資料突變等才進 alert。每次相同的候選不重送待審核任務。
- **RSS 是有限滾動視窗**：貼文從視窗消失並不表示撤回，不得把最高版號當所有型號最新版；來源無法讀取時不顯示歷史版本為「本輪已驗證」。
- **二個全球來源繼續 DEGRADED**：本工具不修復 `official_releases` 與 `software_downloads`，亦不改 `sync/reviewed.json`、PR #6、Review Gate、正式知識模組、現場裝置。

## 隔離 GitHub Runner 實測

研究工作流程 `.github/workflows/auto-release-triage-research.yml` 只在 `research/automated-release-triage` 分支的 Push 時執行（GitHub 手動 workflow_dispatch 需先位於 default branch 才能直接使用），僅有 `contents: read`、`actions: read`，且 checkout 停用持續化 Token。不寫回 Repo、不開 PR、不呼叫 Controller API、不合併。它先執行離線 1,000 次重複事件測試，再讀七個固定官方來源、驗證來源健康度、恢復上一次成功研究 Action 的 Artifact，計算新增／變更／滾動移出的事件，最後上傳 30 天 Artifact JSON 與 Markdown。沒有可證明的上一輪證據時不可靜默把差異當零。

研究 PR 未被授權 Merge，因此目前不執行 main 的週期排程；GitHub `schedule` 僅會在 workflow 進入 default branch 後生效。PR 已預置**台灣時間（Asia/Taipei，UTC+08:00）每週二、五下午 15:00** 的唯讀自動查核（GitHub Actions Cron：`0 7 * * 2,5`，UTC 每週二／五 07:00）。台灣沒有日光節約時間。GitHub Actions 的排程時間是觸發目標，實際執行可能因平台負載而延後。**只有工作流程被另外授權合併到 default branch 後，此排程才會啟用**；目前研究分支上的 Push 只能觸發測試，不能聲稱正式自動排程已生效。

可在既有 GitHub Runner 實測 JSON 檔案上純離線執行：

```bash
python3 scripts/auto_release_triage.py \
  --catalog sync/sources.json \
  --observed sync/observed.json \
  --health sync/health.json \
  --source-report sync/version-candidates.json \
  --output /tmp/auto-release-triage.json \
  --summary /tmp/auto-release-summary.md
```

自第二輪起再加入 `--previous /path/to/auto-release-triage.json`。無異常的正常候選不需交付真人逐筆核對；當需求是「確認某型號是否應安裝某版本／是否為官方穩定版」時，僅在取得來源可驗證機器證據後才允許相應自動結論。研究用摘要不代表完整全產品覆蓋，也不可用於無人值守升級。

## 第一次真實 Runner 來源驗收（2026-10-19）

研究 Runner #39199995020：六類官方 RSS 實測，總共 **107** 筆候選、**6/6** scoped sources 來源資訊驗證、**0** 筆異常。這是首輪 baseline，因此 **107** 個 `NEW_OFFICIAL_RSS_POINTER` 是首次觀測事件而不是 107 項人工待審任務。後續需以第二次 Runner 相同 SHA/URL 快照實測「unchanged=0 新事件」，並用 Actions Artifact 來保存每輪增量。所有發布頻道、機型和下載認證仍保持未知。

## Cloud Keys 限定來源納入計畫（PR #40，2026-10-19）

- 官方 RSS 使用 `https://community.ui.com/rss/releases/UniFi-Cloud-Key-Firmware/c4ccd194-4cbf-4738-b07d-0aa6f04d178e`。其歷史名稱並不代表只有舊型 Cloud Key 韌體；Runner 本輪透過 **嚴格的 UniFi OS - Cloud Keys 標題與產品／版本網址驗證** 取得 20 個範圍內的當前候選指標。
- [七來源唯讀實測 #39208664078](https://github.com/tAIwan888/unifi-skill/actions/runs/39208664078)：七類官方 RSS 皆可讀，前六類 107 筆，加 Cloud Keys 20 筆，合計 **127 筆來源指標，0 例外**。這是首次建立的 127 個事件，不表示 127 筆人工待審任務。
- Cloud Keys 的 RSS 只提供產品版本指標，**不驗證** Official／RC／EA、實際相容機型、Download 檔案或跨產品最新版本。原有的兩個全球來源 `official_releases`／`software_downloads` 仍需保持 DEGRADED 與 Issue #7 OPEN。
- 在 PR #40 尚未合併前，正式 `main` 仍僅執行原本六個來源的排程；研究分支的成功 Runner 不等於已啟用第七來源的正式排程。此 PR 合併後，才會由 GitHub Actions 在**台灣時間每週二／五 15:00** 的原排程執行七來源掃描，不增加 ChatGPT 任務或設備讀寫。

## 自動化可靠性補強（待驗收）

- 若候選來源的健康／SHA／範圍或交叉來源 UUID 資訊產生矛盾，產生可追查的 JSON／Markdown 異常證據後，**GitHub Actions 應以非零退出碼失敗**，不能出現綠燈隱藏異常。
- 同一 UUID 在不同官方分類 RSS 內有相互矛盾的產品名稱、版本、貼文 URL 或發文日期時，整個 UUID 不進入自動索引；第三個來源不能重新帶入已拒絕的 UUID，且先前的新增事件不得保留為有效候選。
- 正常未變更的資料仍採 0 異常、0 新事件；此修正不增加逐筆人工操作，不核准頻道或硬體相容性，也不改已定的 **台灣時間週二、週五 15:00** 排程。

## 歷史 RSS 版本指標台帳（待合併驗收）

- 週期掃描的 `inventory` 只代表本輪七個分類 RSS 滾動視窗內的已驗證官方貼文指標。新增 `auto-release-history.json` 保存曾經由**成功且全部七來源通過的 GitHub Runner** 驗證過的指標；即使之後滑出 RSS 視窗，仍以 `historical_not_in_current_rss_window` 計數，但**不可宣稱仍為目前可下載版本**。
- 所有歷史紀錄明確保留 `UNREVIEWED`，不存私人裝置資料、不儲存韌體檔案、不授權部署、不推論 Official／RC／EA 或機型相容性。僅使用官方 URL、來源分類、版本文字、日期與其 SHA-256 指標。每筆由既有嚴格 RSS 產品與 UUID 驗證器重新核查。
- 上限 **5,000 筆不重複歷史指標**，離線測試包含 **1,000 個真正不同的 UUID** 跨十個滾動視窗（不同於 1,000 次重複相同 120 筆），及重覆掃描 0 新增、回流版本 0 新增、篡改歷史 SHA／變造來源拒絕。達到上限或發現歷史相同 UUID 的產品／版本內容漂移時 fail-closed，不能靜默丟棄或宣稱成功。
- 台帳與例外 JSON 一同保存在 **30 天 GitHub Actions Artifact**，每次成功排程會以同分支最近成功的 Artifact 串接歷史；首次升級可由前一版 `auto-release-triage.json` 接續。**若所有成功 Runner 斷檔超過 Artifact 保存期，必須人工處理來源連續性，不能假裝歷史完整**。目前此台帳不是永久儲存庫或廠商全球版本清單。
- PR 未合併前，正式 `main` 不會生成此新檔案。正式七類 RSS 排程仍是台灣週二、五 15:00；31 來源審核工作流程仍是台灣週二、五 17:00，由 GitHub Actions 執行。
