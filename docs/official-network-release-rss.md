# 官方 Ubiquiti Community RSS — Network Application（審核候選）

**用途：** 針對單一產品家族的公開 Release 訊號，不代表全 UniFi 產品公告索引或最新穩定版清單。

## 已核對的官方來源

- Ubiquiti Community 官方網域：
  `https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe`
- 2026-10-18 GitHub Runner 實測：官方 `robots.txt` 可讀且允許；RSS 回傳 `application/xml`、20 筆條目、20 筆符合官方網域的 Release Post。
- Network Application 20 篇標題提供產品名稱、版本號、文章 URL、公開日期，但 `<category>unifi-network</category>` **沒有明確 Official / RC / EA 渠道資訊**。

[官方 RSS 原始讀取及格式驗證](https://github.com/tAIwan888/unifi-skill/actions/runs/39110374263)；
[新版 Monitor 完整鏈路測試](https://github.com/tAIwan888/unifi-skill/actions/runs/39110874346)。

## 解析與審核邊界

`scripts/check_official_updates.py` 中的 `fetch_network_release_rss`：

1. 僅接受上方已核對的完整 RSS 官方 HTTPS URL，遵守官方 robots.txt、拒絕非白名單重新導向，且限制 1.5 MB。
2. 用標準函式庫 XML Parser 讀取，不執行 HTML 或 XML 內容；拒絕 DTD、ENTITY、不合格式與重複 URL。
3. 只接收 `unifi-network` 分類且標題格式為 `UniFi Network Application x.y.z` 的條目。
4. 每項 Release URL 必須位於 `community.ui.com/releases/` 之下，帶有有效 UUID 型式，並附帶可解析的公開日期。
5. 僅以標題、版本、官方文章 URL、日期等公開中繼資料產生穩定來源指紋，不儲存全文／附件／留言。
6. 資料寫入 `sync/version-candidates.json`，每筆版本固定標為 `CANDIDATE_UNREVIEWED`，發布渠道固定標為 `UNKNOWN_NOT_VALIDATED_FROM_RSS`。
7. 加入 `sync/pending.json` 的來源變動仍為 `REVIEW_REQUIRED`，只經人工逐篇開啟官方公告、核對 Official／RC／EA、支援產品、Breaking Changes 後才能核准。

這 20 筆是**一輪 RSS 視窗內可見候選**，可能包括舊版、RC、EA、分階段推出版本，不能直接以最高版號當成所有設備應安裝的版本。

## 已確認的限制

- 官方 Community 全站 `/releases` HTML 在目前 GitHub Runner 仍只有網頁外殼，沒有可驗證的版本條目。此 RSS **不取代** 原始 `official_releases` 來源，仍須保持其降級告警。
- `software_downloads` 網頁也未經可驗證的版本擷取。
- RSS 產品分類不代表官方簽章驗證；它是官方網域公開公告的觀測資料，與 Legacy Self-hosted APT 的 PGP 驗簽屬不同證據型態。
- 即使 RSS 中有某個高版本，不能自動推定已對所有硬體平台正式發行，必須保留逐產品／渠道查證。

## 預期 GitHub Actions 行為

PR #19 已授權合併，正式來源清單為 **25 個**；2026-10-18 GitHub Runner 正式驗收為 **23/25**，其中 RSS 產生 1 筆待審來源指紋與 20 筆 `CANDIDATE_UNREVIEWED` 版本候選。參見 https://github.com/tAIwan888/unifi-skill/actions/runs/39111607487 。

只要原來兩個來源仍無有效資料，即使 RSS 成功，整體同步仍應標示 `DEGRADED`、保留 Issue #7。

不對任何私人 Controller、網路、攝影機、門禁執行任何讀取或修改。

### 版本候選新鮮度／中斷安全規則（PR 待審）

上次成功讀取的 RSS／Release Index 候選**不等同於本輪仍可用**。若來源讀取失敗，`sync/version-candidates.json` 在該來源設定 `source_status=UNAVAILABLE_THIS_RUN`、`review_status=NO_CURRENT_VERIFIABLE_CANDIDATES` 且 `candidates=[]`，僅保留上次成功 SHA 與候選數供稽核。恢復並重新驗證後，才可重新產生標記 `VALIDATED_THIS_RUN` 的待審候選；成功仍不代表 Official/RC/EA 渠道已核准。
