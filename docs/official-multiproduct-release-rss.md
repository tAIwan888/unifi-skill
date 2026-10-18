# Ubiquiti Community 官方產品分類 RSS — 待審版本候選

## 官方來源的可驗證性

2026-10-18 的 GitHub Runner 直接向 **Ubiquiti 官方 `community.ui.com`** 讀取六個公開 RSS（非透過第三方鏡像），並以現有 HTTPS／同 Host Redirect／robots.txt／大小及安全 XML 限制驗證：

| 分類 | 官方網域 RSS 範圍 | 2026-10-18 官方來源實測（歷史） | PR #27 導入紀錄 |
|---|---|---:|---|
| UniFi Network Application | Network App 版本公告 | 20 筆（此前實測） | 已於 main |
| UniFi Protect Application | Protect App 公告 | 20 筆 | 是 |
| UniFi OS Server | OS Server 公告 | 9 筆 | 是 |
| UniFi OS — Dream Machines | Dream Machine 類 OS 公告 | 20 筆 | 是 |
| UAP／USW Firmware | AP／無線與部分 Switch Firmware 混合分類 | 20 筆，解析時僅保留 unifi-wireless | 是 |
| UniFi Switch | Switching 類韌體／設備公告 | 20 筆 | 是 |
| Security | Security Advisory Bulletin | 20 筆 | **否，不能混成韌體版本** |

實證：[產品 RSS 原始官方驗證](https://github.com/tAIwan888/unifi-skill/actions/runs/39117046127)。上述數量是**當輪 RSS 回傳的文章筆數**，不是獨立版本、已核准版本或穩定版數量；在 parser 過濾產品分類、標題後的有效版本候選數可能較少。

## 溯源與適用範圍

- Network Application：https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe
- Protect：https://community.ui.com/rss/releases/UniFi-Protect-Application/aada5f38-35d4-4525-9235-b14bd320e4d0
- OS Server：https://community.ui.com/rss/releases/UniFi-OS-Server/76650b06-fc47-4892-9c12-25c64c39f842
- Dream Machines：https://community.ui.com/rss/releases/UniFi-OS-Dream-Machines/b0f0a740-021e-4027-a778-ceba983be74b
- AP／無線韌體：https://community.ui.com/rss/releases/UAP-USW-Firmware/9fc3b2fa-9e73-449a-924f-470e79884470
- Switch：https://community.ui.com/rss/releases/UniFi-Switch/f5882c6b-e77f-45c1-b019-68fd20000c31
- Security Advisory（此 PR **不納入**版本候選）：https://community.ui.com/rss/releases/Security/f3f45fa2-1784-4594-b48d-28baf317b208

每筆候選記錄官方文章 URL、標題所推導的 Product Label／Version、公告日期，不下載安裝套件。**RSS 類別或版號不能證明 Official、Release Candidate、Early Access；也不能證明該版本對個別 Console、Switch、AP 型號的相容性。**

## 程式保護

`scripts/check_official_updates.py` 的固定 RSS 來源清單：

1. 精確比對來源 ID 與固定官方 URL，遵守 robots.txt；只允許官方同 Host HTTPS Redirect，目的路徑必須允許。
2. 限制 Content Type／Timeout／1.5MB；拒絕 DTD／ENTITY、無效 XML、重複文章 URL、非 Ubiquiti 的文章 URL。
3. 同時核對單篇文章的 **產品類別與嚴格標題版本格式**；UAP／USW 混合來源只收 `unifi-wireless`，Switch 由獨立來源處理。
4. 找不到任何符合範圍的版本時報 ERROR，不將 RSS 空白頁視作成功。
5. 僅產生 `CANDIDATE_UNREVIEWED`，發布渠道固定 `UNKNOWN_NOT_VALIDATED_FROM_RSS`。
6. 來源失敗時使用已部署的 fail-closed，`candidates=[]`，保留最後成功 SHA/Count 作歷史稽核，不沿用舊版候選。
7. 來源首次成功時寫入既有 **Draft PR #6** 的 `REVIEW_REQUIRED` 指紋；不會直接更改正式知識、`sync/reviewed.json` 或合併 PR。

## 不能宣稱的成果

PR #27 已正式合併，將來源清單由 **25 增至 30**。最新完整 [Run #8](https://github.com/tAIwan888/unifi-skill/actions/runs/39126320523) 已在 `main` 執行：**28/30 有效、兩個全球來源 DEGRADED**；這是已驗證結果，不再只是部署前預期。六類 RSS 共 107 筆候選仍為未審核狀態，非最新穩定版清單。

`official_releases`（全產品 Release Index HTML）與 `software_downloads`（全部下載資產與平台資訊）**仍然沒有 GitHub Runner 可穩定驗證的資料**。這五個分類 RSS 不涵蓋所有 UniFi 硬體、OS、App 及通路，因此不構成全產品最新穩定版監測；Issue #7 仍應開啟。

同樣地，**Draft PR #6 的 28 筆待審來源 SHA 不因 RSS 可讀、重新核對 SHA 或補上精確官方引用而自動升格為已審核**；其 107 筆候選亦須人工確認渠道與產品適用範圍。實機測試及版本相容性仍應依實際硬體／軟體版本另行確認；不得要求使用者提供私人 Controller 憑證到公開 Repository。
