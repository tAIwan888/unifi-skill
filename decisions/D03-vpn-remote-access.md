# D03 — VPN 與遠端存取決策樹

**狀態：官方功能分類已核對，部署前請依版本及 NAT/ISP 條件確認。**

- **偶爾遠端從 WiFiman 存取 UniFi？** → 評估 **Teleport**；邀請有期限與單裝置限制，核對受支援的 OS/裝置及撤銷流程。
- **需要標準用戶端、可匯入配置檔、自主管理 Peer？** → 評估 **WireGuard VPN Server**；需核對公開 WAN、UDP 連線、AllowedIPs、DNS 與金鑰管理。官方文件列 UDP 51820 為預設，實際可以不同。
- **多站點 Gateway 互連？** → 評估 **Site Magic SD-WAN**；需確認 Site Manager/組織權限與設備相容性；不宜假設能連任意第三方 Gateway。
- **需與非 UniFi 網路互連？** → 依設備支援的 **IPsec/OpenVPN Site-to-Site** 選型。
- **自動化／機器對機器？** → 將最小權限、憑證輪替、審計、Split Tunnel 與 DNS 洩漏測試納入 Runbook。

**驗證：** 連通性、可存取範圍、DNS、撤銷權限、VPN 斷線回復。**回滾：** 撤銷 Peer/Invitation、移除新增 route，保留帶外管理路徑。

官方：
- https://help.ui.com/hc/en-us/articles/7951513517079-UniFi-Gateway-Introduction-to-VPNs
- https://help.ui.com/hc/en-us/articles/5246403561495-UniFi-Gateway-Teleport-VPN
- https://help.ui.com/hc/en-us/articles/115005445768-UniFi-Gateway-WireGuard-VPN-Server
