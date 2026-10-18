# UniFi 版本相容性政策

**通用原則**：禁止將「最新版」視為一個全域數字。將每條可執行建議依以下四層標示：

| 層級 | 必填欄位 | 驗證來源 |
|---|---|---|
| UniFi OS / Control Plane | console_family, os_version, hosting_mode | Console Settings / 官方說明 |
| UniFi Application | app_name, app_version, ui_path, features | Network / Protect / Access / Talk 官方 App 文件 |
| Device Firmware | device_family, firmware_version, interface_speed, PoE, capabilities | https://techspecs.ui.com/ 與設備版本說明 |
| API / Release Channel | api_family, api_version, endpoint, auth, channel | https://developer.ui.com/ 或 App Integrations |

### Release Channels
`Official`、`Release Candidate`、`Early Access` 不可混用。官方 Release Index 的 HTML 僅是「變更候選」，不能靠字串排序判定最新穩定版；人員須核對目標產品與相容性。

### 標準記錄格式
```yaml
platform: Cloud Gateway | CloudKey | UniFi OS Server | Official Hosting | NVR | other
unifi_os_version: unknown
app_name: Network
app_versions: unknown
firmware_family: unknown
api_version: unknown
release_channel: unknown
support_class: needs_version_validation
verified_on: 2026-10-18
test_status: DOC_REVIEWED
source_url: https://help.ui.com/
```

### 變更時
對照 `sync/pending.json` 的受影響模組，列出 API/UI/防火牆的 breaking changes、影響版本與可回滾方式。正式知識更新必須經 `sync/reviewed.json` 與 PR 審核；不能把內容指紋視為功能已實測。
