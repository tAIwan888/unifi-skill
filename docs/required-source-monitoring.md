# 必要監測來源與非阻擋全球參考頁（PR #47 本地提案）

**2026-10-19 狀態快照：截至此日尚未部署或取得新雙 Job Workflow 的正式 Runner E2E 驗收。** 最新狀態以 [官方同步 Actions](https://github.com/tAIwan888/unifi-skill/actions/workflows/official-knowledge-sync.yml)／[PR #47](https://github.com/tAIwan888/unifi-skill/pull/47)／[Issue #7](https://github.com/tAIwan888/unifi-skill/issues/7) 為準。 舊 Run [#39228248994](https://github.com/tAIwan888/unifi-skill/actions/runs/39228248994) 的 29/31／DEGRADED／failure 保留為歷史證據；不得重新標為 PASS。

## 固定範圍與成功條件

`sync/sources.json` 是來源目錄，`monitoring_role` 缺省為 `REQUIRED_MONITORING`。僅以下兩個精確 ID／URL／kind=`release_index` 可標記為 `OPTIONAL_REFERENCE_ONLY`，且仍須啟用與逐輪讀取：

- `official_releases`：https://community.ui.com/releases?view=latest
- `software_downloads`：https://www.ui.com/download/unifi

其他來源、變造網址、錯誤 kind 或未知角色均拒絕；在網路讀取及任何證據寫入之前即停止。7 類 RSS、19 篇 Help Center 與3 個固定版本 Developer Markdown 仍為必要來源。分類不增加來源、來源信任、權限或知識核准。

原始 `monitored`／`healthy`／`failed`／`freshness` 和每筆狀態保持真實：29/31、2 ERROR、DEGRADED 可以和正式範圍的成功共存，但不能寫成 31/31。新增欄位由當輪結果動態計算，不硬編碼成功數量：

| 欄位／狀態 | 意義 |
|---|---|
| `required_total/healthy/failed` | 選定必要來源的總數、合格數、錯誤數 |
| `optional_total/healthy/failed` | 選定參考來源的相同計數 |
| `REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS` | 必要來源全正常，但參考來源有缺口；掃描 exit 0 |
| `REQUIRED_SOURCES_PASS` | 必要來源全正常且本輪沒有參考缺口；仍不構成全球版本 Manifest |
| `REQUIRED_SOURCES_FAILED` | 必要來源有失敗；部分合格 exit 4、必要來源全失敗 exit 2 |
| `NO_REQUIRED_SOURCES_CHECKED` | 沒有驗證任何必要來源，exit 2，不宣稱正式服務 PASS |

`--only` 是診斷範圍，不代表完整正式監測；Workflow 必須另外核對所有已啟用來源都在健康報告中。Reader 和 Writer 都用 `source_monitoring_scope.py` 重新驗算，拒絕偽造計數、錯誤網址、缺失列與錯誤 operational status。舊健康 JSON 沒有這些欄位時只是舊輪證據，不能假裝是新規則驗收。

## 資料、權限與失敗保護

沿用 PR #47：Reader 只有 `contents: read`／`actions: read`、不保存 Git 憑證；外網讀取只在 Reader 發生。Writer 只下載同輪 Artifact，在可信 main 腳本上離線驗證八個精確證據檔案、大小、無 symlink、完整分類、候選 SHA／健康一致性、機器來源 Gate 及 triage 重建一致性，之後才切換既有 Draft 分支。不新增 Job 或權限。

- `monitor.outputs.degraded` 只由重新驗算的**必要來源**失敗產生。Writer 的維運 Issue 與最後 Fail-Closed 都依此旗標；只有兩個參考頁失敗時只警告，不建立新的重大阻擋 Issue。
- 必要來源部分失敗時，可驗證的機器 Metadata 與健康證據仍先交給 Writer，之後整輪必須 failure。必要來源全失敗而機器 Gate 拒絕空的成功集時，Reader 不會被報成成功、Writer 不執行；保留完整健康 Artifact 作診斷，不偽造機器 receipt 來強行發布。
- 參考頁回傳 HTML 外殼、即使含產品／版號文字，也不能證明完整全球覆蓋、渠道與下載資產溯源。兩個固定頁面不會產生可核准的全球版本候選；失敗仍 `UNAVAILABLE_THIS_RUN`、`candidates=[]`，只保留歷史 SHA／Count。
- `auto_accept_source_observations.py::verified` 與 `check_review_gate.py --mode machine` 不放寬。機器只核對來源 URL／SHA／解析元資料，不要求真人逐筆簽署來源 SHA；`reviewed.json` 不寫入，知識／渠道／機型／升級仍無自動批准。
- 相同資料的第二、第三輪掃描不得因縮排、欄位順序或狀態已穩定的內容製造額外提交。保留 PR #47 的 machine receipt 語意相同即不改寫原始 bytes 行為。

## 狀態文件維護與正式驗收

Writer 以完整八檔證據重算 REQUIRED 結果，並核對 Reader 的 `degraded` 輸出；即使健康數字正確，錯誤的失敗旗標也會在任何分支／Issue 寫入前被拒絕，不能跳過 final FAIL_CLOSED。

README 狀態區由 `python3 scripts/render_source_monitoring_status.py` 依來源分類、manifest 的有日期部署快照標記及固定的舊輪健康證據產生；`--check` 與回歸測試會阻擋過期狀態。舊輪證據逐 byte 保存於 `docs/evidence/official-sync-39228248994-health.json`，由 manifest SHA-256 檢查，與當輪會變動的 `sync/health.json` 分開，避免真正的必要來源故障因 README 快照漂移而阻止 Writer 留存健康證據。每輪即時狀態由 Workflow summary 和 `sync/health.json` 的動態欄位呈現，不把 README 的舊輪數字偽裝成即時狀態。

manifest 的舊 `operational_snapshot` 不重寫，另以 `monitoring_contract` 描述提案及既有正式 Run。正式 E2E 完成後需另以真實 Run URL、對應 main SHA 與健康證據更新部署聲明；文件生成本身不是部署驗收。

取得明確 Commit／Push 授權後，只更新既有 PR #47，不開另一個 PR。待 GitHub CI、Ruleset 所需審查及額外 Merge 授權後，才能部署 main；再以既有 Workflow 在 main 完成新雙 Job 正式 E2E。不得以舊 204-test CI 或本機 fixture 當成正式 E2E。

正式完整 31-source Run 必須同時證明：29/29 REQUIRED 成功、2/2 OPTIONAL 客觀失敗仍保留、整輪依正式服務範圍 PASS、零知識核准、再跑一次沒有相同資料 PR 假變動。才可按授權更新 Issue #7，說明原先把全球導航頁誤列為必要來源、已更正 scope；不得宣稱兩頁已修好或全球最新版本能力已具備。未完成前 Issue #7 保持 OPEN。
