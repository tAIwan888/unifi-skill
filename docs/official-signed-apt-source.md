# 官方簽章來源：UniFi Legacy Network APT（受限範圍）

**狀態：** 2026-10-18 GitHub Runner 已驗證 HTTPS 讀取、PGP 簽章、索引欄位。**目前套件清單是空的，不可作為最新版偵測。**

## 官方出處及適用產品

Ubiquiti 官方自架 Network Server (Linux) 更新指南描述此 APT Repository：
https://help.ui.com/hc/en-us/articles/220066768--Legacy-Updating-and-Installing-Self-Hosted-UniFi-Network-Servers-Linux

來源只關於 **Legacy UniFi Network self-hosted Debian/Ubuntu packages**，不適用於 UniFi OS Server、Cloud Gateway、Switch/AP firmware、Protect、Access、Talk、Connect。這不是全產品版本 RSS/API。

- 簽署索引（公開唯讀）：`https://www.ui.com/downloads/unifi/debian/dists/stable/InRelease`
- 官方公開金鑰：`https://dl.ui.com/unifi/unifi-repo.gpg`
- 已核對的新金鑰指紋：`FCF764DFE6488B0F899E91A17C84148C6904B09E`
- 歷史舊金鑰指紋：`4A228B2D358A5094178285BE06E85760C0A52C50`

以上兩個指紋不能互換；任何今後新輪替都應 **Fail-Closed、停用來源擷取、要求人工重新核對**。不能因 HTTPS 下載成功就自動信任新公鑰。

## 安全驗證流程

`python3 scripts/apt_official_index.py`：

1. Respect robots.txt、僅連線 `ui.com`、`www.ui.com`、`dl.ui.com` 的 HTTPS 官方網址，僅接受白名單內重新導向。
2. 限制文件大小與逾時，不需任何個人 Controller、Secret、Site ID。
3. 從官方網址下載公鑰，用事先記錄的 **40 碼主鑰 Fingerprint** 驗證。
4. 在暫存目錄中透過 `gpgv` 驗證 `InRelease`。官方 2026-07 版本包含新、舊雙簽章；即使舊鑰不在現行金鑰檔中，**必須**有固定新鑰的完整 `VALIDSIG`、不得有壞簽或未知的錯誤簽署者。不可略過簽章檢查。
5. 核對 `Origin`、`Suite`、`SHA256` 內明列的 `ubiquiti/binary-amd64/Packages` 路徑。內容非空才可能下載並驗證 **size + SHA256**，從 `Package: unifi` 欄位取版本。
6. 任何版本只標 `UNREVIEWED_CANDIDATE`；不能因此宣稱該版本是目前所有 UniFi 產品的 Official/穩定版。
7. 不把 PGP 索引下載檔、Package 內容或二進位軟體鏡像上傳 GitHub；僅提交結構化驗證狀態與摘要。

## 已確認的實際觀察

2026-10-18，官方 APT `InRelease`：

- 可以取得以 `Hash: SHA512` 開頭的 OpenPGP Clearsigned 文件。
- 新舊兩筆簽章；**新指紋簽章 Good / VALIDSIG**，舊鑰未在目前官方公鑰檔中，所以普通 gpgv 命令整體可能返回非零。
- `Codename: unifi-10.5`，簽署索引文件日期 2026-07-27。
- 官方簽署的 `ubiquiti/binary-amd64/Packages` `size=0` 且 SHA-256 為空文件的摘要，因此 **沒有可取得的 UniFi Network APT Package 版本**。
- 程式記為 `verification=PINNED_PGP_SIGNATURE_VALID`、`content_status=SIGNED_EMPTY_PACKAGES`、`review_status=NO_NEW_KNOWLEDGE`，非成功更新。退出碼 2 由排程捕捉、保留健康紀錄。

審核證據：
- [官方 APT 網路探測](https://github.com/tAIwan888/unifi-skill/actions/runs/39105576358)
- [官方簽章／空清單回歸驗收](https://github.com/tAIwan888/unifi-skill/actions/runs/39106345092)
- 公開來源參考：https://community.ui.com/questions/https-www-ui-com-downloads-unifi-debian-dists-stable-InRelease-signed-with-empty-Packages-files/8e547486-af67-438e-b320-1f541ca7465d （社群為背景資訊；不能作為取代官方簽章驗證的證據）

## GitHub Actions 整合

在 `official-knowledge-sync.yml` 的每週二／五 UTC 02:17 排程加入本獨立來源，輸出 `sync/legacy-network-apt-status.json`。

- 來源被擋、GPG 指紋改變、簽章無效、Package Digest 不符 → `FAILED_CLOSED`，不得更新知識。
- 簽章有效而 Packages 為空 → `SIGNED_EMPTY_PACKAGES`，不得發布版本候選。
- 簽章有效、Package 非空且 SHA256 驗證完畢 → `UNREVIEWED_CANDIDATE`，另經官方 Release Channel 與人員審核。
- 24 個 Help Center／Developer／Release HTML 來源若仍不可驗證，同步整體仍維持 `DEGRADED`；APT 來源不能「洗白」其他服務失敗。

**安全界線：** 本文不是軟體安裝手冊，也不授權任何人的 UniFi 設備下載、安裝或升級。
