# UniFi 自動化官方 Release RSS 版本分流 — 例外才人工處理

## 行為和界線

- **零逐筆人工輸入**：自動讀取六個已在 `sync/sources.json` 登錄的 Ubiquiti Community 產品範圍 RSS。GitHub Runner 採用既有 HTTPS、robots.txt、來源完整性與 XML 限制；不存取使用者 Controller、憑證或現場硬體。
- **機器可認證的範圍**：官方 Community RSS 可存取、來源 SHA 符合本輪觀測、正式來源 URL／產品類別、RSS 貼文 UUID、日期與版本文字。正常指標自動進入 machine-indexed inventory；不須有人手動核准每一筆「收到貼文」的事實。
- **不可混淆的範圍**：來源 category 不等於 Official／RC／EA 發布頻道，RSS 的機型標題不等於完整裝置相容矩陣。沒有廠商可重現的個別正式結構化內容與下載證據時，`release_channel=UNKNOWN_NOT_VERIFIED_BY_RSS`、`hardware_compatibility=NOT_VERIFIED_FROM_RELEASE_NOTES`、`device_upgrade_authorized=false`；這不妨礙通用版本追蹤，但禁止進一步宣稱穩定版或觸發更新。
- **只看例外**：某一類來源 403／404／JS-only、SHA 失配、候選範圍漂移、重複 UUID、已記錄貼文資料突變等才進 alert。每次相同的候選不重送待審核任務。
- **RSS 是有限滾動視窗**：貼文從視窗消失並不表示撤回，不得把最高版號當所有型號最新版；來源無法讀取時不顯示歷史版本為「本輪已驗證」。
- **二個全球來源繼續 DEGRADED**：本工具不修復 `official_releases` 與 `software_downloads`，亦不改 `sync/reviewed.json`、PR #6、Review Gate、正式知識模組、現場裝置。

## 隔離 GitHub Runner 實測

研究工作流程 `.github/workflows/auto-release-triage-research.yml` 只在 `research/automated-release-triage` 分支的 Push 時執行（GitHub 手動 workflow_dispatch 需先位於 default branch 才能直接使用），僅有 `contents: read`、`actions: read`，且 checkout 停用持續化 Token。不寫回 Repo、不開 PR、不呼叫 Controller API、不合併。它先執行離線 1,000 次重複事件測試，再讀六個固定官方來源、驗證來源健康度、恢復上一次成功研究 Action 的 Artifact，計算新增／變更／滾動移出的事件，最後上傳 30 天 Artifact JSON 與 Markdown。沒有可證明的上一輪證據時不可靜默把差異當零。

研究 PR 未被授權 Merge，因此目前尚未進入 main 排程；未合併時 GitHub `schedule` 不會為研究分支自動週期觸發。正式啟用須另外核准 merge／排程設定，不能報告已部署。

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
