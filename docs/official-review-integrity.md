# UniFi 官方來源審核完整性與 GitHub 人工核准

**定位：** 公用 UniFi Skill 離線審核，不接觸私人 Controller、設備、API Token。此政策不允許自動核准來源或自動合併 PR。

## 現在可由 CI 檢查的資料

審核閘門依來源目錄、Observed、Pending、Reviewed 的資訊交叉核對：

- 每個已觀測來源都必須在來源白名單中登錄，網址必須是符合官方網域的 HTTPS，觀測 SHA-256 必須是 64 碼。
- 任何 Pending 項目都會阻擋通過；對應網址、SHA 或模組有差異則額外回報。
- 每份來源審核紀錄必須包含精確 SHA、官方 URL、審核人字串、足夠的備註、包含時區且非未來的審核時間。
- 引用證據須位於 modules/、runbooks/、decisions/ 或 docs/，是 Repository 內實際存在的 Markdown，並出現對應的精確官方 URL。
- 審核指令在寫入審核 JSON 前，同樣會核對來源白名單、Pending／Observed 指紋及引用路徑；檢驗失敗不得改寫核准狀態。

**CI 只能驗證 Metadata 和來源對應關係，無法證明誰實際閱讀官方文件。** Git 中自填的 reviewer 欄位並非可信的 GitHub 身分或獨立批准；也不能由引用字串存在推斷內容正確、發布渠道已驗證或已完成實驗室測試。

## 另需由倉庫管理員實施的審核

可考慮在 GitHub Settings → Rules → Rulesets，或 Branches → Branch protection 為 main 設定：

1. Require a pull request before merging，及 Require status checks to pass（選取本儲存庫實際的 UniFi Skill CI Job）。
2. 有第二位具 Write 權限且能獨立覆核的協作者時，啟用 Require approvals，並視實際風險採用 dismiss stale reviews 和 last push approval。
3. 如使用 CODEOWNERS，確保 Code Owner 具 Write 權限、配置檔本身也受到保護；經評估後可啟用 Require review from Code Owners。
4. 評估限制 Force Push、Branch Delete 和 Bypass，但應先核對排程建立 Draft PR 的運作需求。

單人維護者不能將自己的 PR 變成「另一人已獨立批准」。未有第二名審核者時，不應虛構 GitHub Approve；仍須留下來源審核與使用者明確合併授權的稽核紀錄。

GitHub 官方說明：
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners

**本 PR 不會替你修改 Branch Protection、GitHub Permissions 或 Rulesets。**

## 目前待審證據

截至 2026-10-18 Run #8，官方同步 Draft PR #6 有 28 筆 `REVIEW_REQUIRED`、0 筆 Reviewed、107 筆 `CANDIDATE_UNREVIEWED`；30 個來源僅 28 個有效，兩個全球 Release／Download 入口仍 DEGRADED。39 組精確引用均存在，但並非語意審核。PR #6 的 Review Gate 必須繼續阻擋，直到審核者逐一閱讀官方內容、核對產品／機型／渠道／Breaking Changes 並留下真實證據；不得以來源可讀或版號較大推定最新正式版。

建議本地驗證順序：

- python3 scripts/check_review_gate.py
- python3 scripts/validate_knowledge.py
- python3 -m unittest discover -s tests -p 'test_*.py' -v

注意：main 分支的 Observed 目前仍為空白；直接在 main 執行 Review Gate 即使 PASS，也不代表 Draft PR #6 的 28 筆來源已核准，須在審核 PR 的實際資料上驗證。
