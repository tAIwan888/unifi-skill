# RB04 — WiFi 6 GHz / WPA3 SSID 試辦
**support_class:** 官方產品規格及工程建議。**test_status:** DOC_REVIEWED / LAB_NOT_RUN。

## 前置條件
確認 AP、地區無線法規、WiFi App 版本、終端裝置與 WPA3/PMF 需求；記錄原 SSID/頻道/功率設定，選定非關鍵測試區。

## 步驟
1. 對照官方 Tech Specs 判斷 AP 是否支援 6 GHz，並核對地區法規與運作模式，**不要因產品名稱自行推定支援頻段**。
2. 在 Network WiFi UI 新增測試 SSID（不改既有主 SSID），依版本選擇合適 WPA3/PMF 設定。
3. 先測一台支援 6 GHz 的終端，確認實際頻段、驗證機制、DHCP、DNS、吞吐和漫遊；再確認不支援 6 GHz 的終端仍有適當 SSID。
4. 比對 Channel / Tx Power / 邊緣訊號，避免沒有 RF 資料即強制全場固定高功率或單一頻道。
5. 若有多 AP，再測 Fast Roaming（802.11r）相容性；對 IoT/舊設備請採審慎隔離、兼容性設計。

## 驗證
連線能取得正確網段、WPA3 成功、封包遺失可接受、移動測試無持續斷線。不可僅用 PHY Link Rate 當效能結果。

## 風險與回滾
設定變更可能使舊終端無法連線。關閉測試 SSID、恢復原頻道/功率/安全性，驗證原 SSID 正常，再擴大佈署。

官方：
- https://help.ui.com/hc/en-us/articles/32064585817495-WiFi-Troubleshooting-Guide
- https://techspecs.ui.com/
