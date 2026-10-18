# RB02 — VLAN 與 Firewall 分階段變更
**support_class:** 工程建議（非官方固定配置）。**test_status:** DOC_REVIEWED / LAB_NOT_RUN。

## 前置條件
具 Network 管理權限、確認 Gateway 與 Switch 功能、已備份設定並測試管理救援 Port；將來源、目的地與服務需求列成 Allow/Deny Matrix。

## 步驟
1. 記錄目前 Network / DHCP / DNS / SSID / Switch Port / Firewall 所依版本；先規劃新 VLAN ID、子網，檢查與 VPN/既有 LAN 是否衝突。
2. 在 UniFi Network 的 Networks / WiFi / Switch Port 與 Firewall/Policy 頁依目前版本對照官方 UI 調整；**不要預先改掉管理 VLAN**。
3. 先以一個可恢復的測試 Port/SSID 或非關鍵 Client 驗證 DHCP/DNS/Internet。
4. 建立最小可用的跨 VLAN allow 規則，再驗證預期 deny；若需 mDNS，僅針對所需發現/服務範圍處理。
5. 經現場維護窗口與變更審核後，再逐批遷移其他 Port/SSID；每批記錄觀測結果。

## 驗證
用戶端得到正確網段及 DNS，隔離矩陣 allow/deny 實測符合預期，管理介面和 Gateway 可達，不依賴假定的規則優先順序。

## 風險與回滾
錯誤 Native/Tagged VLAN 或 Policy 可能斷網及鎖死管理。若驗證失敗，先還原試辦 Port 和 SSID，再依備份回復 Network / Firewall；無救援路徑時禁止變更管理網段。

官方：
- https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs
- https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
