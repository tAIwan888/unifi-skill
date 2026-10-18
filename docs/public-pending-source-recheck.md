# 公開 UniFi 官方來源：23 筆待審指紋二次核對

## 2026-10-18 實測結果

在 GitHub Runner 上使用 PR #6 真實的 `sync/observed.json` 與 `sync/pending.json`，透過相同官方公開 HTTPS 讀取器重新取得 23 筆來源：

| 檢查結果 | 筆數 |
|---|---:|
| 與待審 SHA-256 完全一致 | 23 |
| 官方來源內容已變動 | 0 |
| 本輪讀取失敗 | 0 |
| 新增核准紀錄 | 0 |

實證：[GitHub Actions 23-source recheck](https://github.com/tAIwan888/unifi-skill/actions/runs/39115730339)。

**界線：** 同一份公開內容的 SHA 相符，只說明初次觀測至此次再檢查期間的內容指紋一致。它**不表示**該內容正確、最新版已發布、符合個別機型，也不表示 23 項人工來源審核已完成。

## 重現方式

本工具需要來源目錄及既有待審的兩個 JSON 檔（**不要**在正式 main 沒有 pending 時憑空產生核准）：

```bash
python3 scripts/recheck_pending_sources.py \
  --catalog sync/sources.json \
  --observed /path/to/pr6/sync/observed.json \
  --pending /path/to/pr6/sync/pending.json \
  --output /tmp/unifi-official-source-recheck.md \
  --json-output /tmp/unifi-official-source-recheck.json
```

腳本支援 19 個 Help Center Article JSON、3 個固定版本 Developer Markdown 及單一 Network Application RSS。只有官方網域、robots 規則許可的來源會被讀取；不收集任何人的 Controller、MAC、API Key 或其他私人資料。官方文章內文只在記憶體中用於正規化後的 SHA 比較，輸出只包含來源 ID、公開中繼資料、SHA 狀態和錯誤類別。

三種狀態：`MATCHES_PENDING`、`DRIFT_REQUIRES_REVIEW`、`UNAVAILABLE_NOT_REVIEWED`。若發生漂移或失敗，程式以非零碼結束，且不更動任何 Observed/Pending/Reviewed JSON。

## 人工內容審核還須逐筆完成

請在 [Draft PR #6](https://github.com/tAIwan888/unifi-skill/pull/6) 繼續：

1. 檢查各官方來源中的支援產品、最低 API/App/Firmware 版本及不相容項目。
2. 對照 M01–M10、Decision Trees、Runbooks，修改過時或沒有官方證據的指引，記錄審核結果。
3. 對 RSS 逐篇確認 Official、RC、EA；即使數字較大也不能直接推論為全部產品最新穩定版。
4. 由真正被授權的審核者核對並簽署來源。**不得把此機器報告當成人工審核**；待審 PR 的 Review Gate 在完成前應保持阻擋。
5. 另外保留 [Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7)：全產品 Release Index 和 Software Downloads 兩個來源仍缺乏 GitHub Runner 可驗證的結構化版本資料。

此流程不執行設備操作、不對任何真實 UniFi 系統進行實機驗證。
