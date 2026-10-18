# D01 — UniFi Control Plane 選型決策樹

**狀態：DOC_REVIEWED（非實機測試）｜適用範圍：通用產品分類，須核對具體設備／軟體版本**

1. **需要整合 Gateway/Firewall + Network？** 是 → 評估 **Cloud Gateway**。它在同一設備上內建 Network 控制面；不可再由外部 UniFi OS Server 接管。
2. **採獨立 Gateway（UXG）或只管理 Switch/AP？** → 評估 **CloudKey / UniFi OS Server / Official Hosting**；分別比較本地硬體依賴、自架維護與代管需求。
3. **需要 Protect / Access / Talk / Connect？** → 確認符合該 App 需求的 **UniFi Console / NVR**；不要認為 UniFi OS Server 可自行託管所有應用。
4. **使用 Linux self-host？** → 依官方 UniFi OS Server 安裝條件；**不能把其當作獨立 Docker / Podman 容器**。
5. **多站點？** → Site Manager 與各 Console 的組織/角色支援視軟體版本及方案驗證，勿假設跨站點同步設定必然支援。

### 決策輸出
`control_plane`、`gateway_type`、`site_count`、`apps_required`、`offline_requirements`、`backup_method`、`constraints`、`source_urls`。

### 驗證／回滾
正式採用前先以產品規格及官方支援矩陣確認；Migrating/Adopting 之前保留設定備份與原 Controller 恢復方法，不在未備援時進行破壞性移轉。

官方：
- https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi
- https://help.ui.com/hc/en-us/articles/30319146145175-Understanding-UniFi-Cloud-Architecture
- https://help.ui.com/hc/en-us/articles/4415364143511-Getting-Started-with-Official-UniFi-Hosting
