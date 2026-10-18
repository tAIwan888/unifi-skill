# RB01 — UniFi 備份與復原前查核（通用）
**support_class:** 官方文件支援概念；UI 依版本確認。**test_status:** DOC_REVIEWED / NOT_LAB_TESTED。

## 前置條件
具相應 Console/Admin 權限、官方相容的備份格式與安全儲存位置；不需將檔案交給 Skill 作者。提前界定 RPO、RTO、金鑰保管與是否包含 App 個別資料。

## 步驟
1. 確認管理模式（Cloud Gateway、CloudKey、UniFi OS Server、Legacy Network Server、Official Hosting），記錄 UniFi OS / Network / 其他 App 版本。
2. 在支援的管理 UI 依官方備份文件導出適用類型的備份；切勿假設備份涵蓋 Protect 錄影或所有外掛應用資料。
3. 以離線加密位置儲存備份，限制下載與上傳者。確保檔名、時間、來源設備類型、版本與校驗值可追溯。
4. 在隔離環境以相容版本進行**還原演練**，確認網段、站點、權限、Adoption 與日誌是否恢復。

## 驗證
備份可讀、加密權限正確、版本相容、可恢復管理介面；演練前後設備運作正常。**沒有演練不得標成 DR PASS。**

## 風險與回滾
正式還原可能覆蓋現有設定、造成重採用或中斷；事前保存兩份獨立副本、確認救援路徑與允許停機窗口。失敗還原以原備份及原控制面接管流程復原。

官方：https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi
