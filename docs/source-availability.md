# 官方來源同步：實測可用性與降級治理（2026-10-18）

**狀態：部分官方網站有讀取限制；完整自動版本更新未完成驗收。**

## 官方網站
- https://help.ui.com/hc/en-us — GitHub Runner 使用正常允許的公開 HTTPS 流程，文章讀取回傳 HTTP 403；**不繞過 robots.txt、TLS 或存取控制**。
- https://developer.ui.com/ — 原本的 `/network`、`/site-manager`、`/protect` 在 Runner 回傳 HTTP 404；已將監測索引改成有明確版本的官方文件 URL，是否可由 Runner 取得內容仍待驗證。
- https://community.ui.com/releases — Release Index 在 Runner 只能取得不足以解析版本的網頁內容，標為 ERROR；不自行假裝 Release Channel 已確認。
- https://www.ui.com/download/unifi — 舊版 SHA 監測可取得 HTML，但 2026-10-18 的 v0.6 網路實測證明該內容**沒有可驗證的 UniFi Release 條目**，因此新版標示 `NO_VERIFIABLE_RELEASE_ENTRIES`。

## 偵測狀態語意

| 類型 | 意義 | 能否直接當成新知識 |
|---|---|---|
| `FIRST_SEEN` | 首次取得符合品質檢查的官方文件指紋 | 否 |
| `CHANGED` | 官方內容指紋變化（可能是版面改動） | 否 |
| `UNCHANGED` | 本次成功取得內容，與最後摘要一致 | 否；既有審核結果仍須有效 |
| `ERROR: HTTP_403` | 來源不允許目前請求 | 否；人工查閱 |
| `ERROR: HTTP_404` | 官方網址失效、重新導向或不允許存取 | 否；核對新官方 URL |
| `ERROR: NO_VERIFIABLE_RELEASE_ENTRIES` | 只取得網頁外殼，無可靠版本條目 | 否；不標記成功 |
| `ERROR: NETWORK_ERROR` | 網路或 DNS/TLS 連線錯誤 | 否；保留前次成功指紋 |

`sync/health.json` 是**本輪檢查的狀態**；`sync/observed.json` 保留最後成功來源 SHA；`sync/version-candidates.json` 只存來源支持但尚未審核的版本候選，不宣稱 Official 或最新穩定版。

## 審核與停止條件

沒有有效來源時，同步 Job 應先提交 `health.json`、`latest-observed.md` 等待審查，接著以 `DEGRADED` 結束；不能回報成功。
人工審核的 PR 除非逐項完成官方內容、版本、適用產品、CLI/API 相容性與 Runbook 更新，否則不可 Merge。

初始觀測 PR #2：https://github.com/tAIwan888/unifi-skill/pull/2 （仍然 Draft；內含舊版 HTML 指紋，此指紋**不是驗證版本內容**）。

## 發布管理

版本比較必須分別看 **UniFi OS、Network、Protect、Access、Firmware 與 API**；同一產品不同平台版本不可用單一數字排名。官方資料可利用公開瀏覽器人工驗證：
- https://www.ui.com/download/unifi
- https://community.ui.com/releases
- https://developer.ui.com/network/v10.6.106/getinfo
- https://developer.ui.com/site-manager/v1.0.0/gettingstarted
- https://developer.ui.com/protect/v7.3.70/quick_start.ansible

上面版本化 API URL 是明確的文件快照，**不代表今日最新版本**。任何無憑證 API／Release 讀取問題須保留 `需人工查證`，不應把網站鏡像、論壇或第三方服務當成同等官方來源。
