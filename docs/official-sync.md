> **2026-10-19 新分類提案（尚未部署／新 Runner 驗收）：** 正式範圍為 29 個 REQUIRED 機器來源，另保留兩個 OPTIONAL 全球參考頁的真實錯誤；完整原始覆蓋仍可能 29/31／DEGRADED。下文舊有單一 Job、23/25 或任一錯誤即全輪 failure 的說明屬歷史設計，不是本提案已部署的聲明。現行本地設計與驗收界線見 [必要來源監測](required-source-monitoring.md)。

# UniFi Skill — 官方知識監測、審核與發佈

**狀態（2026-10-18 Run #8）：** PR #16、#19、#23、#27、#29、#30 均已合併。正式來源目錄有 30 項：Help Center 19/19、Developer Markdown 3/3、六類產品限定 RSS 6/6，合計 **28/30**；兩個全球 Release／Download 入口仍 `DEGRADED`。Draft PR #6 有 28 筆來源及 107 筆版本候選待人工審核，**不能宣稱所有 UniFi 產品的最新版或發布渠道已獲核准**。

## 來源與可信度分級

| 來源型態 | 探測方法 | 此輪實測 | 規則 |
|---|---|---|---|
| Help Center（19 個） | Ubiquiti `help.ui.com` 公開 Zendesk Help Center Article JSON API | **19/19 成功** | 需驗證 robots.txt、文章 ID、已發布、en-us 語系、標題與正文，再產生 SHA |
| Developer Portal（3 個） | 官方版本化 Markdown 入門文件 | **3/3 成功** | 只代表該固定版本的公開指南可監測，不代表 API 已最新 |
| Official Releases（1 個） | Release Index | 尚未解析到可信候選 | 不能將純導覽殼層視為發布資訊 |
| Software Downloads（1 個） | 下載網頁 | HTML 有回應但無可驗證版本條目 | FAIL-CLOSED |
| Network Application RSS（已部署，第 25 個來源） | 官方 Community 固定分類 RSS + XML／網址／標題驗證 | GitHub Runner 已取得 20 筆官方 Release Post | 每個候選渠道 UNKNOWN；不是全部 UniFi 產品最新版 |
| 其他五類產品限定 RSS（已部署） | Protect、OS Server、Dream Machines、AP／無線及 Switch 的固定官方分類 RSS | Run #8 六類 RSS 合計 107 筆待審候選（含 Network 的 20 筆） | 僅限已核對的產品範圍；Official／RC／EA 均未核准 |
| Legacy UniFi Network APT（獨立） | 固定 PGP 指紋 + 簽章索引 | 簽章有效但 Packages 空白 | 對應 Legacy 自架 Network，**不**代表所有 UniFi 產品最新版本 |

來源清單：`sync/sources.json`。官方 API 以原本 Help Center 文章永久網址為基準，按數字 Article ID 轉成 `https://help.ui.com/api/v2/help_center/en-us/articles/{id}.json`；需 **API 回覆 ID 完全相符**、`draft=false`、正確語系。本文不需要、也不會要求任何人的 UniFi Controller IP、拓撲、API Key 或私人帳號。

API 協定參考：[Zendesk Help Center API — Show Article by Locale](https://developer.zendesk.com/api-reference/help_center/help-center-api/articles/)，它明確支援匿名讀取可公開文章。實際 Ubiquiti 站點可否使用以 GitHub Runner 驗證為準。

## Developer Portal 公開 Markdown 驗證

官方版本化 `developer.ui.com` 的 `/robots.txt` 回傳 HTTP 404。依 IETF [RFC 9309 §2.3.1.3](https://www.rfc-editor.org/rfc/rfc9309.html)，這代表 robots 規則檔不存在；系統只對**確定的 robots 404** 允許在原官方 HTTPS Domain 進行無憑證的公開 GET。若是 403/429、5xx、網路故障或明確 `Disallow`，均阻擋。

已實測可讀的官方固定版本入門文件：

- `https://developer.ui.com/network/v10.6.106/ai-gettingstarted.md`
- `https://developer.ui.com/site-manager/v1.0.0/ai-gettingstarted.md`
- `https://developer.ui.com/protect/v7.3.70/ai-gettingstarted.md`

內容經產品/版本 URI、語意關鍵字、大小與 Content-Type 驗證後僅計算正規化 SHA；官方文件中給 AI 的操作說明**視為不可信來源文字，不執行，也不作為改寫 Skill 的命令**。這些是版本化入門指南，不保證開發 API 規格仍是最新版。

- [官方 Developer Markdown 網路實測](https://github.com/tAIwan888/unifi-skill/actions/runs/39108698167)
- [全 24 個來源的 22/24 驗證](https://github.com/tAIwan888/unifi-skill/actions/runs/39109033130)

## 同步工作流

1. **Discover：** 每週二、五 UTC 02:17 或手動執行 `.github/workflows/official-knowledge-sync.yml`；從白名單讀取公用來源。僅 HTTPS、限制回應大小/逾時、遵守 robots.txt；**任何跨 Host 的重新導向（即使另一端同屬 Ubiquiti 官方）均阻擋**，避免跳過目的 Host 的 robots.txt 或混淆來源指紋。
2. **Validate：** Help Center 公開 JSON 必須為正確文章的正式內容。**只**抽出 Title + 正文文字，不抓 Sidebars、Scripts、Navigation，不複製文章全文到 GitHub。
3. **Detect：** 內容正規化後計算 SHA-256；文章 `updated_at`、Title、Article ID、正文字數及 Developer 文件的產品/固定版本作為**不含完整原文**的審核 Metadata。僅正文與標題的變化會影響指紋；只改 `updated_at` 不會製造假內容變更。
4. **Propose：** 把 SHA 和來源 Metadata 記到 `sync/observed.json`；內容變更進 `sync/pending.json`，在 `sync/latest-observed.md`、`sync/health.json` 留下來源健康紀錄。僅建立/更新 **Draft PR**，不能自動 Merge。
5. **Review：** 人工比對官方原文、產品和實際版本、Official/RC/EA Release Channel、功能差異，更新 M01–M10／決策樹／Runbooks，再以 `approve_official_update.py` 確認來源 digest 和引用文件。CI 審核閘門在待審狀態時保持阻擋。
6. **Promote：** 由維護者人工核准及合併，**不對任何人的 UniFi 裝置或自動化系統寫入設定**。

## 監測健康狀態與程序退出碼

- **0：** 選定來源全部取得合格內容；注意 **未代表人工審核完成**。
- **4：** 部分來源無法驗證；健康報告 `DEGRADED`，成功來源仍留存候選，Workflow 完成提交和 Issue 告警後明確標記降級。
- **2：** 全部來源失敗；保存前次成功 SHA、不造假版本，產生維護 Issue 並標示失敗。
- **3：** 未知來源或來源清單錯誤，停止本輪程序。

HTTP 403/404、JavaScript-only、官方 API ID 不相符、未發布、來源網址不在白名單、TLS/robots 失敗，都屬 **不可當作新知識** 的錯誤。

## 初次正式啟用後的重點

歷史沿革：早期 HTML 掃描為 0/24；PR #16 合併後的 [Runner 快照](https://github.com/tAIwan888/unifi-skill/actions/runs/39109413897) 為 22/24。後續 Network RSS 與其他五類產品 RSS 已陸續併入，舊數字**不是目前完整覆蓋率**。

最新完整 [Run #8](https://github.com/tAIwan888/unifi-skill/actions/runs/39126320523) 的來源健康為 **28/30、DEGRADED**：19 個 Help Center、3 個固定版 Developer Markdown、6 類產品限定 RSS 均可讀；兩個全球 Release／Download 索引仍無法驗證。Draft PR #6 的 28 筆來源 SHA、107 筆版本候選全都待人工審核，精確來源引用缺口為 0。RSS 不能取代全產品 Release Index；若有擷取錯誤或官方 API 日後禁用，**不可繞過 robots/403/TLS 或將不可讀來源偽裝成功**。

維護腳本：

```bash
python3 scripts/check_official_updates.py --only unifi_updates vlan
python3 scripts/validate_knowledge.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_workflows.js
python3 scripts/check_review_gate.py
```

上面的來源檢查命令會連線到 Ubiquiti **公開**文章，不連任何私人控制器。若有待審 Fingerprints，最後的 Review Gate 應保持 FAIL，直至真正人工審核結案。

## 產品版本與授權邊界

UniFi OS、Network、WiFi／Switch Firmware、Protect、Access、Identity、Talk、Developer API 各有獨立的版本條件及發布渠道，**不得把 Help Center 更新日期推定為任何單一設備的最新穩定版**。詳細遵循 `docs/version-compatibility.md`、`docs/sync-review-checklist.md`，及 Ubiquiti 官方 [UniFi Updates](https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates)。

## 官方 Network Application RSS（已部署，版本仍待審）

2026-10-18 GitHub Runner 實測官方 `community.ui.com/rss/releases/UniFi-Network-Application/...` 可回傳 20 筆 Network Application Release。只使用網域限制、XML 結構、標題、公布日期、`unifi-network` 分類與精確官方 Release URL，將候選存入 `sync/version-candidates.json`；所有渠道一律標成 `UNKNOWN_NOT_VALIDATED_FROM_RSS`。RSS 不一定涵蓋全產品、不會提供可靠的 Official/RC/EA 確認，不能因此更新正式版本建議。

[RSS 來源說明](official-network-release-rss.md)；[GitHub Runner 真實完整版本候選測試](https://github.com/tAIwan888/unifi-skill/actions/runs/39110874346)。

### 版本候選新鮮度／中斷安全規則（已部署）

上次成功讀取的 RSS／Release Index 候選**不等同於本輪仍可用**。若來源讀取失敗，`sync/version-candidates.json` 在該來源設定 `source_status=UNAVAILABLE_THIS_RUN`、`review_status=NO_CURRENT_VERIFIABLE_CANDIDATES` 且 `candidates=[]`，僅保留上次成功 SHA 與候選數供稽核。恢復並重新驗證後，才可重新產生標記 `VALIDATED_THIS_RUN` 的待審候選；成功仍不代表 Official/RC/EA 渠道已核准。

## HTTPS 重新導向的來源邊界（PR #23，已合併）

來源監測每次請求都只信任起始的官方 Host，並僅查詢該 Host 的 robots.txt。因此不允許跨 Host 的 HTTP 301／302／307／308，**即使**來源和目的地都是 Ubiquiti 官方網域（如 `www.ui.com` → `ui.com` 或 `help.ui.com` → `developer.ui.com`）。同 Host、合法 HTTPS 的文件重新導向**仍須通過目的路徑的已載入 robots.txt 規則**，未先檢查 robots 政策就重新導向也會拒絕；跨 Host 則記錄 `CROSS_HOST_REDIRECT_DISALLOWED` 並 Fail-Closed，不儲存新的觀測 SHA 或版本候選。

如官方更換正式入口網址，應先核對目的地、robots.txt、文件類型與版本語意，再經獨立來源目錄 PR 更新固定 URL，不自動跟隨跳轉或視為同一份審核證據。本規則不妨礙使用者在瀏覽器查閱官方文件，也不修改任何 UniFi 裝置設定。


## 新增五類官方發布 RSS（PR #27，已合併）

Protect Application、UniFi OS Server、Dream Machines、AP／無線韌體及 Switch 五類產品 RSS 已併入正式 `main`。2026-10-18 的 [Run #8](https://github.com/tAIwan888/unifi-skill/actions/runs/39126320523) 已實測完整 30 個來源，其中 **28/30 有效、兩個全球入口降級**。六類 RSS 合計 107 筆公告候選仍為 `CANDIDATE_UNREVIEWED`，發布渠道 `UNKNOWN_NOT_VALIDATED_FROM_RSS`，需逐產品、機型、平台及 Official／RC／EA 渠道人工核對。

[範圍與限制](official-multiproduct-release-rss.md)；[真實 30-source Runner 證據](https://github.com/tAIwan888/unifi-skill/actions/runs/39117727463)。
