> **歷史說明：** 本文件前段保留 2026-10-18 初期 HTML 讀取／403／0/24 等實測紀錄，並不代表目前正式程式仍不能讀取 Help Center 公開 API 或 Developer Markdown。更新狀態請參閱文末和最新 Actions Run。

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

## GitHub Runner 結構探測（2026-10-18）

一次性 Workflow 在同一 Runner 分別讀取 `https://www.ui.com/download/unifi` 與 `https://www.ui.com/download/utilities/`。
兩者皆讀到 **351,979 bytes** HTML，但結構偵測皆為：
- `script_tags=0`、`next_data=false`、`next_flight=false`
- `network_mentions=0`、`semver_mentions=0`、`release_title_mentions=0`

上述觀測可由 GitHub Actions Run 日誌查證：https://github.com/tAIwan888/unifi-skill/actions/runs/39099238168 。
未保存或重新發布網站全文，僅紀錄不含個人資訊的結構計數。
**因此新版內容驗證拒絕任何沒有可核對版本條目的 HTML**；此前 `software_downloads` 的 `FIRST_SEEN` 指紋需要標記為不可升格為知識，並在後續審核處理。

若本輪全部來源失敗，Workflow 仍會先寫出 `health.json` 與報告，建立或重用 Draft PR，再建立至多一個開啟狀態的維運 Issue，最後以 degraded failure 結束。這是刻意的 Fail-Closed，而非同步成功。

## 2026-10-18 更新：官方公開 Help Center API 已驗證

**此項改進已由 PR #16 合併至正式 `main`。** 以下 19/19 的數字是早期 Runner API 驗證快照，非本日最新完整來源覆蓋率。 舊版 GitHub Runner 直接讀取 Help Center HTML 會遇到 HTTP 403；同網域 `help.ui.com` 的**正式公開 Zendesk Article JSON API** 已成功經合法匿名請求讀取。新方法先查 `robots.txt`、使用固定 HTTPS 官方來源、檢驗文章 ID／發佈狀態／語系／內容，再只存 SHA 與公開中繼資料。

- 官方 API 可讀性探測（2/2）：https://github.com/tAIwan888/unifi-skill/actions/runs/39107535358
- 新增 Monitor 的 11 個來源實測（11/11）：https://github.com/tAIwan888/unifi-skill/actions/runs/39107789286
- 19 個 Help Center 來源完整實測（**19/19**）：https://github.com/tAIwan888/unifi-skill/actions/runs/39107846237
- 其餘 5 個來源（Developer Portal 3、Release Index 1、Downloads HTML 1）尚未經此 API 修復；以正式排程最新 `health.json` 確認。

**前述 0/24 與 403 的記錄是舊版 HTML 讀取法的歷史觀測，不能當成目前 PR #16 新讀取法的失敗結論。** 這項突破代表公開文章內容變更可持續偵測，但與 UniFi OS/App/Firmware 最新正式版驗證仍是不同能力。所有新來源指紋首次取回後必須由維護者審核，未經批准不可更新正式知識。

## 2026-10-18 進一步更新：3 個 Developer 官方 Markdown 可監測

先前的 Developer Portal 404 主要是站點 `/robots.txt` 自身回傳 404，而不是所有公開 API 文件都不存在。按照 [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html) 的「Unavailable robots」語意（只對確切 HTTP 404 採用，其他錯誤 Fail-Closed），已在原 Ubiquiti 官方域名讀取版本化 Markdown 入門文檔。三個來源均得到正常官方 Markdown 內容：

- `network_api`：Network v10.6.106 — https://developer.ui.com/network/v10.6.106/ai-gettingstarted.md
- `site_manager_api`：Site Manager v1.0.0 — https://developer.ui.com/site-manager/v1.0.0/ai-gettingstarted.md
- `protect_api`：Protect v7.3.70 — https://developer.ui.com/protect/v7.3.70/ai-gettingstarted.md

GitHub Runner **全 24 來源最新驗證為 22 個成功、2 個無可驗證資訊**：https://github.com/tAIwan888/unifi-skill/actions/runs/39109033130 。

尚未解決的 2 項：`official_releases=UNREADABLE_OR_JS_ONLY`，`software_downloads=NO_VERIFIABLE_RELEASE_ENTRIES`。因為這兩個來源涉及 Release Channel／最新版本，**不可宣稱官方所有產品的最新版已自動同步**，僅能說來源文章與固定 API Guide 的內容變更可監測。PR #16 已部署至 `main`。隨後 Network Application RSS 也已合併；正式分支最近一次完整已驗證為 **23/25**，兩個全產品版本來源持續降級。[正式 Runner](https://github.com/tAIwan888/unifi-skill/actions/runs/39111607487)。PR #27 擬加入五類額外產品 RSS，分支實測 **28/30**，仍需授權合併後再重新驗收 `main`。
