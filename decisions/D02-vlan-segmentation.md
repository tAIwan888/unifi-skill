# D02 — VLAN 分段決策樹

**標籤：工程架構建議（非官方固定模板）；版本相容性需依產品驗證。**

1. 先列出受信任管理面、一般使用者、Guest、IoT、Work、Server 與有線／無線用途。**不要硬性規定每個家庭都需要七個 VLAN**。
2. 若 Guest 無內部資源需求 → 獨立 VLAN、訪客隔離與明確 Internet/DNS 規則；確認 AP/Client 實際隔離行為。
3. IoT 需要跨 VLAN 的裝置發現？→ 分離控制面及 IoT 面，只針對必要目的地主機／服務開放 mDNS 或路由；避免放寬整個 RFC1918。
4. 管理 VLAN 變更風險高？→ 保留獨立救援 Port / 已驗證的管理路徑與匯出備份；分階段試辦一台可復原的終端。
5. Inter-VLAN 需 Gateway 的 Traffic / Firewall 可見性？→ 優先 Gateway Routing；若考慮 L3 Switch，先驗證其繞過的政策與日誌能力。
6. DHCP / DNS / IPv6 / Multicast → 逐個 VLAN 驗證租約、DNS、必要廣播轉發及 Internet 限制。

**Port 規則：** Access port = 預期 Native/untagged 網路；Trunk = 正確 Native + 有限 Tagged VLAN 列表；避免對所有 Port 放通所有 Tagged VLAN。

**驗收**：不同 VLAN 的 allow/deny Matrix，管理介面保持可達，Guest→管理面被拒，實際允許的 App 流量成功。

**回滾**：還原原 Network/SSID/Port 設定，若管理被鎖必須有獨立帶外／現場救援路徑。

官方：https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs
