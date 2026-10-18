# 官方知識同步機制
## 行為
GitHub Actions 依排程或手動執行 `scripts/check_official_updates.py`，讀取允許的官方公開頁面，正規化後計算 SHA-256，與 `sync/observed.json` 比較。結果僅產生 `sync/pending.json` 與可閱讀的 `sync/latest-observed.md`。
首次觀測屬 FIRST_SEEN，**不表示已驗證或已更新知識**。任何 CHANGE 都須人工核對原始 URL、產品與版本、Release Channel、功能相容性及回滾，再更新 Skill；不自動合併 PR。
## 使用方式
```bash
python3 scripts/check_official_updates.py
python3 -m unittest discover -s tests -v
```
GitHub Actions Workflow `official-knowledge-sync.yml` 每週二、週五 UTC 02:17（排程可能延遲）及手動執行。新變化推送至 `automation/official-knowledge-sync` 並開 Draft PR。
CI 不允許 pending 未清或沒有相符審核 digest 的狀態通過。
## 安全
來源為固定白名單的公開 HTTPS；不下載私人 Controller 資料、不持有私人 API Key。HTML 為不可信輸入；不執行網頁腳本。限制大小、讀取逾時、依 robots.txt 允許情況存取。未能讀取應標 ERROR 而非假裝成功。
## 來源
https://help.ui.com/hc/en-us
https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API
https://developer.ui.com/
https://community.ui.com/releases
