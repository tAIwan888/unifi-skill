# 官方 UniFi Release 備援證據匯入（離線、人工審核）

**目的（2026-10-18 Run #8）：** 30 個來源中有 28 個可透過官方公開 API、固定版本 Markdown 與產品限定 RSS 監測；全產品 Release Index 與 Software Downloads 兩個全球入口仍無可靠版本資料。因此保留「由維護者核對精確官方頁面、以結構化欄位登錄、提交待審 PR」的離線備援管線。這**不是**背景自動抓取、全產品最新版驗證或知識自動核准。

## 官方優先資料來源

- 正式／RC／EA Releases：https://community.ui.com/releases?view=latest
- Software Downloads：https://www.ui.com/download/unifi
- 官方升級指引：https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates

UniFi 的 Official、Release Candidate、Early Access **不是同一版本渠道**。Release 網頁上的不同硬體系列、UniFi OS／Network／Firmware 都不可單一版本號排序。

## 操作流程

1. 維護者以一般瀏覽器閱讀**個別官方 Release Post** 或指定官方 Software Download 頁，核對產品、版本、發布渠道，保存可公開查證的精確 URL。
2. 在本地建立 JSON 清單，每個來源紀錄：`family`、`product`、`version`、`asserted_release_channel`、`official_release_url`、`checked_on`、`short_evidence_excerpt`。
3. 執行：

```bash
python3 scripts/import_official_release_evidence.py \
  --input examples/synthetic-official-release-evidence.json \
  --output /tmp/unifi-public-release-candidates.json
```

**重要：** 上述範例是完全合成、不真實存在的版本和 Release URL，不能發佈成官方版本資料。

4. 工具驗證資料型別、來源 Domain 與精確 Release URL、發布渠道、版本格式、日期、重複資料及明顯憑證洩漏。產出只包含 Hash 與 Metadata，不複製官方 Release 全文。
5. 維護者將**真實來源且已核對**的候選 JSON 加入專用知識 PR，審核人再親自點開官方文章核對是否有 Breaking Changes、支援產品與正確 Release Channel。
6. 最後的正式知識模組更新，依 `docs/sync-review-checklist.md` 及 CI 進行人工審查；此工具的 `UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE` 永遠**不代表獲得核准**。

## 安全與完整性

- 僅離線解析，不連接任何使用者的 UniFi Controller，也不發送外部 HTTP。
- 發布渠道為 **維護者聲稱的值**，因為此工具不能自動證實來源原文。
- 不儲存原文證據全文，僅保留 `excerpt_sha256`，可降低版權複製與敏感資料外洩風險；Hash 不表示證據真實，也不能代表原始官方網頁的完整內容指紋。
- 嚴禁將用戶私人 API Key、Tenant、MAC、Serial、Topology、Camera Media、Access Log 放進 JSON。
- **此備援管線不替代自動來源健康度檢查**；即使人工匯入候選，官方自動同步狀態仍可能是 `DEGRADED`。

## 驗收狀態

- `tests/test_official_release_intake.py` 使用合成官方格式案例，檢查非法網址、未辨識渠道、不合法版號、重複項與憑證拒絕。
- `DOC_REVIEWED` 是人工引用驗證，不等於 GitHub Runner 即時官方網站可達、也不等於某台實體設備可用。

## 官方 RSS 的補充與限制（PR #19）

[Network Application 官方 RSS](official-network-release-rss.md) 已隨 PR #19 合併，另外五類產品限定 RSS 已隨 PR #27 併入正式排程。最新 Run #8 共產生 107 筆未審核公告候選（其中 Network Application 20 筆），但無法僅從 RSS 證實 Official／Release Candidate／Early Access。人工備援匯入仍須針對**精確官方 Release Post**逐筆核對渠道、產品與相容性，不可用最高版號自動簽核。


## Cloud Keys RSS 人工聲明離線橋接（草稿 PR #38）

研究 PR #37 的唯讀 GitHub Runner 可提供 `response.json`，其中的 Cloud Keys 版本及官方 URL 僅是 **CANDIDATE_UNREVIEWED**。RSS 不含已核准的 Official／RC／EA、機型適用性或軟體下載佐證。以下橋接器只使用本地檔案，不會讀取設備或連上廠商 API。

先由已下載的 Runner Artifact 產生空白人工審核模板（不填入任何發布頻道）：

```bash
python3 -B -m scripts.handoff_cloudkey_manual_claims \
  --rss-report /path/to/response.json \
  --mode template \
  --output /tmp/cloudkey-manual-template.json
```

維護者必須在正常瀏覽器獨立閱讀 **精確官方貼文**，逐筆填寫 `asserted_release_channel`、`checked_on` 及 `short_evidence_excerpt`。若只有部分貼文得到足夠證據，應只保留已填完的 `rows`；不可將空白的項目帶入匯入。`rss_publication_date` 是 RSS 發文日期，不可充作人工審閱日期。不要猜測頻道、支援硬體或下載來源。

把人工填好的模板以 `--completed` 提供後，執行下列離線交接：

```bash
python3 -B -m scripts.handoff_cloudkey_manual_claims \
  --rss-report /path/to/response.json \
  --mode intake \
  --completed /tmp/cloudkey-manual-template.json \
  --output /tmp/cloudkey-manual-evidence-unreviewed.json
```

工具檢查 Runner 回報的固定官方 RSS URL、原始候選列表 SHA-256、筆數、產品名稱、版本與精確貼文 URL，並呼叫既有 `import_official_release_evidence.py`。與原始 RSS 不一致、未完成、非法 Official／RC／EA、非官方 URL、密鑰字樣、重複版本或額外核准欄位都會拒絕。請注意：此 SHA 只驗證本地候選一致性，**不是 Ubiquiti 數位簽章**，也不能證明有人實際完成來源審閱。

輸出明確標示 `UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE`、`HUMAN_REVIEW_REQUIRED`、`independent_vendor_fetch=false` 與 `independent_human_review_completed=false`。維護者聲稱的頻道不是經程式驗證的事實，仍需由獨立審核者核查原始官方貼文、機型與引用記錄，依 `docs/sync-review-checklist.md` 和 PR Review Gate 核准。**不得修改 `sync/reviewed.json` 或把這份資料拿去更新設備。**

此工具只服務 Cloud Keys 專用 RSS；不取代全產品 Release Index 或 Software Downloads。Issue #7 的兩個全球來源維持 DEGRADED，PR #6 與 PR #37／#38 的治理限制不變。
