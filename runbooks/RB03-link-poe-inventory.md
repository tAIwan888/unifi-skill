# RB03 — Switch 連線、PoE 與拓撲唯讀檢查
**support_class:** 官方設備功能及工程建議。**test_status:** DOC_REVIEWED / NOT_LAB_TESTED。

## 前置條件
具唯讀管理權限或合法管理者 UI，知道 Switch/AP 型號與韌體系列。不可要求公用 Skill 使用者交付任何私人拓撲。

## 步驟
1. 查官方 Tech Specs：各 Switch Port 最大速率、PoE 型別（af/at/bt）、總 PoE Budget、Uplink/光模組限制。
2. 在現行 Network UI 查看 Device > Ports / Topology（路徑依版本而異），記錄 Port Negotiated Speed、PoE Negotiation、Power Draw、Link State 與 LLDP 鄰居資料。
3. 將實體線材、標籤、SFP/模組相容性與假定拓撲比較；不要把自動產生的 Topology 視為完整實際佈線圖。
4. 核對 Tagged/Native VLAN、STP、LAG，確認備援路徑及可能的 Loop/Storm；先閱讀官方資料後再變更。
5. 若發現低速協商，先以非侵入檢查排除線材、對端能力、模組與功率限制。

## 驗證
Link Rate 與端到端用量合理、PoE 預算有餘裕、拓撲／LLDP 和實體標籤一致，未引起 Port flap。測試結果與版本分開記錄。

## 風險與回滾
無審批不得切換 PoE 模式、停 Port 或變更 STP/LAG。變更前匯出現有設定；失敗以原 Port Profile、線材及救援埠復原。

官方：
- https://help.ui.com/hc/en-us/articles/33402927617047-UniFi-Switch-Settings
- https://techspecs.ui.com/
