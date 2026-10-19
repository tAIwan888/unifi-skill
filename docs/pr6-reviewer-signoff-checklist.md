# PR #6 — 29 筆待簽核官方來源總清單（2026-10-19）

> **NOT_APPROVED — WORKSHEET ONLY**。AI 與 GitHub Runner 不能代替維護者真人簽核。此清單只是根據 PR #6 的 `sync/sources.json`、`sync/observed.json` 與 `sync/pending.json` **逐欄核對**後的不可省略來源 URL、SHA、模組路徑。初次觀測不代表文件真的發生變更；未正式核准前 `sync/reviewed.json` 必須保持未改動，PR #6 保持 Draft / Gate BLOCKED。

**本輪現況：** 29 筆官方機器觀測、0 筆正式簽核、精確引用缺口 0；兩個全球入口仍 DEGRADED（Issue #7）。若下一輪 GitHub Runner SHA 漂移，必須使用新的 `pending.json`，下列舊 SHA 不可沿用。來源預核對另見 [官方公開來源預核對](pr6-public-official-evidence-precheck.md)，只涵蓋指定主張，不等於全文人審。

## 各來源實際審核條件

1. **真人直接開啟原始官方 URL**，核對正文／技術條款／產品範圍與對應 Skill 模組；明確記錄是否需要改文、改了哪些內容、或無需改動的理由。先確認 `pending.json` 和 `observed.json` 的 SHA 與下表相符。
2. RSS 僅證明類別中的公告指標存在，**Official、Release Candidate、Early Access、具體機型、下載可用性必須逐一另找官方原始貼文或規格證據**；不能把未知渠道自動核准成正式版。
3. 維護者於審核後，以 `scripts/approve_official_update.py` **依來源逐筆登錄**真實 reviewer、notes、精確原始 URL 與證據 Markdown。該工具只檢查紀錄格式，**無法驗證實際審核者身分**；仍必須另經 GitHub PR 真人 Review。
4. 完成之後再執行 `python3 scripts/check_review_gate.py` 及 PR CI；即便 Gate PASS，沒有真人 PR Review 仍不得宣稱人審完成或自動合併。

## 19 個 Help Center 公開文章（必須比對正文）（19 筆）

| 人員簽核 | Source ID / 模組證據 | 官方原始來源與完整 SHA-256 | 核對要點 |
|---|---|---|---|
| ☐ | `access` → `modules/M07-access.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/17452334269975-Getting-Started-with-UniFi-Access) · `40c012b59ca0781905e341db95cf2daffd293cd85ead742c958bcaaf2941cff2` | 全文版本與技術適用性；官方更新 2026-10-02 |
| ☐ | `adoption` → `modules/M09-backup-security.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/360012622613-UniFi-Device-Adoption) · `d453882cee8f12c50c123b16b68a4789f6e3f8c1bdfc10186256b49eb1297ae8` | 全文版本與技術適用性；官方更新 2026-10-14 |
| ☐ | `backup_migration` → `modules/M09-backup-security.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi) · `c52ff3e75245928140a0e2d378555a2dba55c6c07f97802e9c8ccb054f8c64d3` | 全文版本與技術適用性；官方更新 2026-10-15 |
| ☐ | `cloud_architecture` → `modules/M01-platform.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/30319146145175-Understanding-UniFi-Cloud-Architecture) · `c6a651bcf695e0876524edc49910b15bfc5d56d1cfce005bd3afc3b2e0414e0a` | 全文版本與技術適用性；官方更新 2026-10-14 |
| ☐ | `identity` → `modules/M08-identity-talk.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/16936895868823-UniFi-Endpoint-Overview) · `7f0d24e5ec415d4a8ed8c68a6c43b98b2c564c51e4287f700e242763725ddb75` | 全文版本與技術適用性；官方更新 2026-09-26 |
| ☐ | `isolation` → `modules/M02-networks.md`、`modules/M03-firewall-vpn.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi) · `f5c7f11eb29973db9fa002d1a64a63f4b7e3201979de80aa4316af4491211cd2` | 全文版本與技術適用性；官方更新 2026-10-11 |
| ☐ | `l3_routing` → `modules/M02-networks.md`、`modules/M05-switch.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/360042281174-Layer-3-Routing) · `d54c96a0efe47cd87a79e54684acd51a1bde4684455637a1becd962674700299` | 全文版本與技術適用性；官方更新 2026-08-26 |
| ☐ | `official_api` → `modules/M10-api-n8n.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API) · `ec591973b946f189b2331d234fe07559e02f89883f77f6c3f97fc9decd21bb79` | 全文版本與技術適用性；官方更新 2026-09-22 |
| ☐ | `official_hosting` → `modules/M01-platform.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/4415364143511-Getting-Started-with-Official-UniFi-Hosting) · `de5023a42ecea4723002c6955af990ee74eb0f74b14f26f0309a78f56b1e81b9` | 全文版本與技術適用性；官方更新 2026-09-24 |
| ☐ | `platform_intro` → `modules/M01-platform.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/360012192813-Introduction-to-UniFi) · `6e57b0a84530d484a6b8f89e54e2d3a91ace82cd6032859333492f023d76ec07` | 全文版本與技術適用性；官方更新 2026-10-15 |
| ☐ | `protect` → `modules/M06-protect.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/27878858632599-Getting-Started-with-UniFi-Protect) · `c375d90b001dbd1c0434c12478dfeabb5a83abfe41ba8b7dde316f6126bc8f8c` | 全文版本與技術適用性；官方更新 2026-10-09 |
| ☐ | `self_hosting` → `modules/M01-platform.md`、`modules/M09-backup-security.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi) · `4cc08843fe8694415f63e5ef99f7412d419810acb0a439d65d69d59ba1e08304` | 全文版本與技術適用性；官方更新 2026-10-16 |
| ☐ | `switch` → `modules/M05-switch.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/33402927617047-UniFi-Switch-Settings) · `1443f8667c293922d23f81a647d3d3fc1f9d5efd439d1b372e1c1fc89a697597` | 全文版本與技術適用性；官方更新 2026-10-14 |
| ☐ | `talk` → `modules/M08-identity-talk.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/27057211577751-Getting-Started-with-UniFi-Talk) · `7c26b546f6dcdce2d4e028876233025227571c93efcb7826303b9744fec94b3a` | 全文版本與技術適用性；官方更新 2026-10-12 |
| ☐ | `unifi_updates` → `modules/M01-platform.md`、`modules/M09-backup-security.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/7605005245975-UniFi-Updates) · `87fdad1b32f9ff1756061bb465359b2c03806bef374e1b255acd9d06f90fd37a` | 全文版本與技術適用性；官方更新 2026-10-17 |
| ☐ | `vlan` → `modules/M02-networks.md`、`modules/M05-switch.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/9761080275607-Creating-Virtual-Networks-VLANs) · `66224041e9be3cb9624d3aadce877e347debc172deaea79d8431dc2f2eafeaae` | 全文版本與技術適用性；官方更新 2026-09-21 |
| ☐ | `vpn` → `modules/M03-firewall-vpn.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/7951513517079-UniFi-Gateway-Introduction-to-VPNs) · `456eb1bc796392c20cca480afc76f3f057de70183e75374a589951acbb310c3e` | 全文版本與技術適用性；官方更新 2026-10-16 |
| ☐ | `wifi` → `modules/M04-wifi.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/32065480092951-UniFi-WiFi-SSID-and-AP-Settings-Overview) · `9aa9d109a4940bc5f3b5a64f63d3c57ac2280186d83524c518c71024c6d69958` | 全文版本與技術適用性；官方更新 2026-10-08 |
| ☐ | `zbf` → `modules/M03-firewall-vpn.md` | [原始官方頁](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi) · `f2f8be48341259b592d629df4750d357dd14e5d008dbdcfa34771577ef272cc6` | 全文版本與技術適用性；官方更新 2026-10-17 |

## 3 個固定版本 API 文件（必須核對版本邊界）（3 筆）

| 人員簽核 | Source ID / 模組證據 | 官方原始來源與完整 SHA-256 | 核對要點 |
|---|---|---|---|
| ☐ | `network_api` → `modules/M10-api-n8n.md` | [原始官方頁](https://developer.ui.com/network/v10.6.106/ai-gettingstarted.md) · `88cf35e00634eee14a2fc3d09ffa709542f75be448c89e12bd05f63870f30dad` | 固定版號文件，不等於最新 API 或設備實測 |
| ☐ | `protect_api` → `modules/M06-protect.md`、`modules/M10-api-n8n.md` | [原始官方頁](https://developer.ui.com/protect/v7.3.70/ai-gettingstarted.md) · `dff1f52d8589f453b9696d3026319fa15931b95e2b61411a2d97d94f690e5157` | 固定版號文件，不等於最新 API 或設備實測 |
| ☐ | `site_manager_api` → `modules/M10-api-n8n.md` | [原始官方頁](https://developer.ui.com/site-manager/v1.0.0/ai-gettingstarted.md) · `73af65213331dd502c3e0b63bc6ca4487617a1c362538ad49c9d047964640a62` | 固定版號文件，不等於最新 API 或設備實測 |

## 7 個產品範圍 RSS（渠道／機型仍未知）（7 筆）

| 人員簽核 | Source ID / 模組證據 | 官方原始來源與完整 SHA-256 | 核對要點 |
|---|---|---|---|
| ☐ | `cloud_keys_release_rss` → `modules/M01-platform.md`、`modules/M09-backup-security.md` | [原始官方頁](https://community.ui.com/rss/releases/UniFi-Cloud-Key-Firmware/c4ccd194-4cbf-4738-b07d-0aa6f04d178e) · `97871a7cd01b5c0d9747af9365bd714075db975ef0d323c423930e0db36ad6ff` | 逐貼文核對 Official/RC/EA、機型、資產與升級限制；目前均 UNKNOWN |
| ☐ | `dream_machines_release_rss` → `modules/M01-platform.md`、`modules/M09-backup-security.md` | [原始官方頁](https://community.ui.com/rss/releases/UniFi-OS-Dream-Machines/b0f0a740-021e-4027-a778-ceba983be74b) · `15124a3e2c69682eb71061b89d168b22472417b315971353bbe1e776d9ee388b` | 逐貼文核對 Official/RC/EA、機型、資產與升級限制；目前均 UNKNOWN |
| ☐ | `network_application_release_rss` → `modules/M02-networks.md`、`modules/M10-api-n8n.md` | [原始官方頁](https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe) · `5f8cd0f2483eaba63b4351614e234e82119284c9727d99296c90122e905d42c0` | 逐貼文核對 Official/RC/EA、機型、資產與升級限制；目前均 UNKNOWN |
| ☐ | `os_server_release_rss` → `modules/M01-platform.md`、`modules/M09-backup-security.md`、`modules/M10-api-n8n.md` | [原始官方頁](https://community.ui.com/rss/releases/UniFi-OS-Server/76650b06-fc47-4892-9c12-25c64c39f842) · `d36c715a502a8540855180d9c974329605aeb7b74b44b121ed589e989bad2a16` | 逐貼文核對 Official/RC/EA、機型、資產與升級限制；目前均 UNKNOWN |
| ☐ | `protect_application_release_rss` → `modules/M06-protect.md`、`modules/M10-api-n8n.md` | [原始官方頁](https://community.ui.com/rss/releases/UniFi-Protect-Application/aada5f38-35d4-4525-9235-b14bd320e4d0) · `a2a42f82a6c2b234bdab6593f9e7583a2d87506bc7ef240db33027d31034dad0` | 逐貼文核對 Official/RC/EA、機型、資產與升級限制；目前均 UNKNOWN |
| ☐ | `switch_firmware_release_rss` → `modules/M05-switch.md` | [原始官方頁](https://community.ui.com/rss/releases/UniFi-Switch/f5882c6b-e77f-45c1-b019-68fd20000c31) · `aa18b6761df93aaefe6e3b63d284fc1709162cbd9cfbd83fd1a1b969347d75b8` | 逐貼文核對 Official/RC/EA、機型、資產與升級限制；目前均 UNKNOWN |
| ☐ | `wifi_firmware_release_rss` → `modules/M04-wifi.md` | [原始官方頁](https://community.ui.com/rss/releases/UAP-USW-Firmware/9fc3b2fa-9e73-449a-924f-470e79884470) · `4235ed0aec951f9f64dacb1c073a69a773c096b045ae8b5853f38e6c891f00d7` | 逐貼文核對 Official/RC/EA、機型、資產與升級限制；目前均 UNKNOWN |

## 人工簽核範例（僅示意，勿直接作為完成記錄）

```bash
python3 scripts/approve_official_update.py \
  --source access \
  --digest 40c012b59ca0781905e341db95cf2daffd293cd85ead742c958bcaaf2941cff2 \
  --reviewer "實際完成審核的 GitHub 人員" \
  --notes "核對現行 Access 原始官方文章全文與 M07，記錄具體變動與適用性判斷（請替換為真實審核筆記）" \
  --evidence modules/M07-access.md
```

**不可直接執行上述示意文字作為假人審**，也不得將 `SOURCE_OBSERVED_UNREVIEWED` 擅改為 Approved。完整 64 位 SHA 是本次機器指紋，不是廠商發布簽章。正常 CI 的 Review Gate 在真人完成核對前**必須維持 BLOCKED**。
