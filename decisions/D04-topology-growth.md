# D04 — 家庭、SOHO、多樓層、多站點擴張

1. **一個站點**：確認 ISP/WAN、Gateway 防火牆效能、Switch PoE 功率預算、AP 佈點與有線回程，再依需要選擇 Cloud Gateway 或獨立 Control Plane。
2. **多樓層**：優先以牆體/訊號量測決定 AP 位置；跨樓層規劃有線回程、光模組/SFP 相容性、LAG 與 STP。RF 頻道不要固定照搬。
3. **多站點**：定義管理責任與容錯、設定模板範圍、VPN/SD-WAN、角色及備份歸屬，再比較 Site Manager/Organizations 和各站點 Console。
4. **相機/門禁**：另外確認 Protect/Access Hosting、儲存 Retention、PoE 與安全法規，不把 Network 功能表等同其他 App 能力。
5. **監控與維運**：站點／裝置監控、異常告警、維護窗口、韌體逐批升級、備份還原演練。

**輸出：** 功能矩陣、PoE/WAN 容量估算、版本與設備型號矩陣、風險登錄、驗收及回滾。

**驗收：** 無單點失效未被標注、PoE 預算不超配、無線覆蓋已規劃驗證、控制面與管理權限一致。此為通用工程決策，不保證現場性能。

官方：
- https://design.ui.com/
- https://techspecs.ui.com/
- https://help.ui.com/hc/en-us/articles/30319146145175-Understanding-UniFi-Cloud-Architecture
