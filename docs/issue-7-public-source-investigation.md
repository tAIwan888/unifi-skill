# Issue #7 公開官方來源調查與五類 RSS 引用整合

## 基準與證據等級（2026-10-18）

- main：`0ea2d0533079f7e4e410998a87377a57205b96c1`，已包含 PR #27、#28。
- Draft [PR #6](https://github.com/tAIwan888/unifi-skill/pull/6) 證據基準：`3a2f79da1878287d00f17d772bae41ea09c7b609`；28 筆 `REVIEW_REQUIRED`、0 筆 Reviewed、107 筆 `CANDIDATE_UNREVIEWED`。
- [既有正式 Runner](https://github.com/tAIwan888/unifi-skill/actions/runs/39119696504)：28/30 有效、2 個全球來源降級。來源讀取、候選一致性稽核和測試步驟成功，但 `Flag degraded source health` 刻意失敗；整個 Run **不是 PASS**。
- 本次 SHA 核對於 **18:47:14 +08:00** 完成；入口診斷於 **18:49:29 +08:00** 完成，均在本機 macOS 執行，**不是新的 GitHub Runner 驗收**。
- 調查僅讀取公開官方 HTTPS 資料；遵循專案 `SKILL.md`、來源／審核完整性規範及既有讀取器。儲存庫與上層未發現 `AGENTS.md`，另遵循本次使用者提供的規則。

## 28 筆 SHA 重新核對

使用既有 `scripts/recheck_pending_sources.py`，以 PR #6 原始 Catalog、Observed、Pending 為輸入：

| 結果 | 筆數 |
|---|---:|
| `MATCHES_PENDING` | 28 |
| `DRIFT_REQUIRES_REVIEW` | 0 |
| `UNAVAILABLE_NOT_REVIEWED` | 0 |
| 新增人工核准 | 0 |

涵蓋 19 個 Help Center 公開文章 JSON、3 個固定版本 Developer Markdown 與 6 個產品限定 RSS。JSON 報告保留每筆完整官方 URL、基準與本次 SHA、公開產品範圍；不保存官方全文。

RSS 指紋來自解析後的產品標題、版本、文章 URL 和日期，**不是逐篇 Release 內文或渠道的審核證據**。即使 28 筆全部相符，仍需真正審核者逐項確認產品、機型、平台、Breaking Changes 與版本渠道。

## 九組引用的產品適用範圍

六個模組均在「已觀測官方來源補充索引（尚待人工內容覆核）」中使用 `SOURCE_OBSERVED_UNREVIEWED`，不改寫既有審核紀錄或提升證據等級。

| 官方 RSS | 補足模組 | 本次有效候選 | 僅可支持的索引範圍 |
|---|---|---:|---|
| [Dream Machines](https://community.ui.com/rss/releases/UniFi-OS-Dream-Machines/b0f0a740-021e-4027-a778-ceba983be74b) | M01、M09 | 18 | `UNIFI_OS_DREAM_MACHINES_ONLY`；不是所有 Console 的 UniFi OS，也未證明備份／回滾相容性 |
| [OS Server](https://community.ui.com/rss/releases/UniFi-OS-Server/76650b06-fc47-4892-9c12-25c64c39f842) | M01、M09、M10 | 9 | `UNIFI_OS_SERVER_ONLY`；不是 Legacy Network Server，也不證明其他 Apps、Docker、遷移或 API 契約 |
| [Protect Application](https://community.ui.com/rss/releases/UniFi-Protect-Application/aada5f38-35d4-4525-9235-b14bd320e4d0) | M06、M10 | 20 | `UNIFI_PROTECT_APPLICATION_ONLY`；不是 Camera／NVR 韌體或 Protect API 能力保證 |
| [AP／USW 混合分類](https://community.ui.com/rss/releases/UAP-USW-Firmware/9fc3b2fa-9e73-449a-924f-470e79884470) | M04 | 20 | 僅採 `unifi-wireless` 且符合標題格式者，含無線／橋接產品標題；不以此替代 Switch RSS，機型與地區支援仍待審 |
| [Switch](https://community.ui.com/rss/releases/UniFi-Switch/f5882c6b-e77f-45c1-b019-68fd20000c31) | M05 | 20 | 僅採 `unifi-switching` 且符合標題格式者；不證明所有 Switch、PoE、L3 功能相容 |

OS Server 即使位於 `unifi-network` 類別，仍須符合 `UniFi OS Server` 的專用標題格式；不能因此當成 Network Application 版本。上述五類共 87 筆，加上既有 [Network Application RSS](https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe) 20 筆為 107 筆；全部保留 `UNKNOWN_NOT_VALIDATED_FROM_RSS` 與 `CANDIDATE_UNREVIEWED`。

重新產生 `sync/review-triage.md` 後，原先 6 個模組／9 組精確引用缺口全部消除；28 筆待審與兩個失敗來源仍保留。這是引用覆蓋改善，**不是內容審核完成**。

## Issue #7：公開官方入口調查

先以公開搜尋發現入口，再由官方文章／現有讀取器核對；搜尋引擎的渲染結果未納入來源 SHA、版本候選或健康判定。

- 官方 [UniFi Updates](https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates) 文章明列 Community Releases。其 Update Manager 是站點更新管理功能，不是本案可連線的匿名全球版本資料來源；本次未連線 Site Manager 或私人 Controller。
- 官方 [Self-Hosting UniFi](https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi) 的已驗證公開 JSON 內含 `https://ui.com/download` 連結。將其視為另一個獨立、官方明列的入口診斷，未自動更換來源目錄或跟隨跨 Host 跳轉。
- 使用原有 `SafeRedirect`、`_robot_ok` 與有大小／MIME／逾時限制的 `fetch`，再套用現有內容驗證；僅記錄長度、SHA 與錯誤，不保存 HTML 全文。

| 官方入口 | 本機收到 bytes | 既有驗證結果 | 決定 |
|---|---:|---|---|
| https://community.ui.com/releases?view=latest | 2788 | `UNREADABLE_OR_JS_ONLY` | `official_releases` 維持失敗 |
| https://community.ui.com/releases | 2776 | `UNREADABLE_OR_JS_ONLY` | 官方文章指向的根入口也無可驗證發布內容 |
| https://www.ui.com/download/unifi | 351979 | `NO_VERIFIABLE_RELEASE_ENTRIES` | `software_downloads` 維持失敗 |
| https://ui.com/download | 351979 | `NO_VERIFIABLE_RELEASE_ENTRIES` | 與上述下載入口回應 SHA 相同，未取得合格替代資料 |

另外核對既有合法資料入口的用途：

| 入口 | 可支持的內容 | 無法替代全球 Release／Download 的原因 |
|---|---|---|
| `help.ui.com` 公開文章 JSON | 已發表文章的標題／正文指紋 | 更新指南不構成全產品版本、渠道與下載資產清單 |
| `developer.ui.com` 固定版本 Markdown | Network／Site Manager／Protect 指定版本指南 | 固定版本文件不代表最新 App／Firmware |
| 六類 `community.ui.com` 產品 RSS | 本次相符的 107 筆範圍限定公告候選 | 產品覆蓋不完整；不能僅由 RSS 證明 Official／RC／EA 或逐機型相容性 |
| [Legacy Network APT InRelease](https://www.ui.com/downloads/unifi/debian/dists/stable/InRelease) | PR #6 既有 Runner 簽章證據 | 僅 Legacy 自架 Network；既有證據為 `SIGNED_EMPTY_PACKAGES`／`NO_NEW_KNOWLEDGE`，本次未重新驗 PGP，不可據此推定版本 |

**結論：本次有限範圍調查未找到可取代兩個全球來源、且具新 Runner 重複驗證證據的可靠資料入口。** 這不是證明所有可能的官方來源均不存在。未新增傳輸方法、來源或 Workflow；維持 Catalog 30 個來源、正式既有證據 28/30、`DEGRADED`，Issue #7 應繼續開啟。

若後續發現官方明列的公開結構化入口，應另建來源工作包，在 GitHub Runner 重複驗證 robots、TLS、同 Host 重新導向、MIME／大小限制、產品／渠道／平台覆蓋與解析，並測試空白、JS 外殼、403、TLS、部分失敗均 Fail-Closed；不能將本機可讀等同 Runner 驗收，或用縮小全球來源範圍消除降級。

## 重現與驗證

在 PR #6 的確切證據副本執行，輸出使用獨立位置：

```bash
python3 scripts/recheck_pending_sources.py \
  --catalog sync/sources.json \
  --observed sync/observed.json --pending sync/pending.json \
  --output /tmp/unifi-pending-recheck.md \
  --json-output /tmp/unifi-pending-recheck.json
python3 scripts/build_review_triage.py --output /tmp/unifi-review-triage.md
python3 scripts/validate_knowledge.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_workflows.js
python3 scripts/validate_release_candidate_evidence.py
python3 scripts/check_review_gate.py
```

本次前述驗證通過（Python 129 tests、n8n Mock、候選／健康一致性）；最後 Review Gate 預期以 **exit 1／BLOCKED** 阻擋 28 筆 Pending 及缺少對應 Review。此阻擋必須保留，不得修改 `reviewed.json`、降低 Assertion 或替代人工核准。

本次未 Commit、Push、Merge、觸發新 Runner、修改 GitHub Issue／PR 內容或生產資料。外部效果僅為儲存庫／GitHub 資料讀取與官方公開 GET；未讀取 Secrets、設備資料或私人控制器。

下一個可獨立審查的 PR 工作包為「六模組九組 RSS 精確引用＋引用覆蓋回歸測試＋本調查文件」，基於上述 main 提交審查；PR #6 的 triage 由後續同步在同一 Draft PR 重新產生，28 筆人工審核仍另行完成。
