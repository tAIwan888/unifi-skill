# UniFi Network 11.0.83 — RC migration gate (unreviewed advisory)

> **Status: `SOURCE_TRIAGE_UNREVIEWED` / `NO_PRODUCTION_APPROVAL`.** This is a public-source **review packet**, not an upgrade recommendation, human approval, compatible-device matrix, or validated migration/rollback procedure. Version and channel labels were inspected on 2026-10-18 through publicly indexed official Ubiquiti pages; **RSS alone does not establish Official / RC / EA**. The exact current release page and hardware state must be independently verified before use. Do not execute upgrades, restores, ZBF changes, or other device operations based on this document.

## Source-specific facts to verify before any upgrade decision

Official Ubiquiti Community release note: https://community.ui.com/releases/UniFi-Network-Application-11-0-83/d6940379-cd5a-4e61-8596-7e22d647a4ea

As indexed on 2026-10-18, **Network Application 11.0.83 is Release Candidate**, not a verified Official build. Its posted migration notes identify these **separate compatibility constraints**:

1. **Minimum platform:** Network Application **11.0.83 requires UniFi OS 6.0 or newer**. This is not permission to assume every UniFi device has a 6.0 update available.
2. **Separate feature requirement:** Live Flows, External Network Lists, WiFi Uplink and other named features can require **UniFi OS 6.0.10 or newer**, with additional explicit hardware-model limits. Do not confuse this feature requirement with the 6.0 application prerequisite.
3. **Database and history:** the application database migrates to **PostgreSQL** and an updated statistics engine; **existing statistics history is cleared**. A configuration-only backup does not prove past statistical history can be restored.
4. **Legacy USG gateways:** **USG support is removed** in Network 11; the note identifies **Network 10.6 as the last series supporting USG**. A site containing USG is a hard stop until an approved alternate device/software strategy is documented.
5. **Legacy self-hosting:** **Network Application Server support is removed**; the vendor directs such deployments toward **UniFi OS Server**. Verify target OS, migration path and licensing/hosting applicability independently.
6. **Firewall policy migration:** **all sites automatically migrate to Zone-Based Firewall (ZBF)** during the upgrade. Record pre/post policy parity for management access, Internet, inter-VLAN traffic, DHCP/DNS, VPN and special device zones. An existing general ZBF tutorial alone is not proof the migration is safe.
7. **Time and reversibility:** the release note warns the upgrade may take up to **20 minutes**. Do **not** infer rollback or database downgrade support from that estimate; obtain a vendor-supported recovery plan and test outside production.

Additional official evidence (general guidance, **not** guarantees of Network 11.0.83 rollback):

- ZBF policy model: https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- ZBF migration background: https://help.ui.com/hc/en-us/articles/28223082254743-Migrating-to-Zone-Based-Firewalls-in-UniFi
- Backups and migration: https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi
- Self-hosting UniFi: https://help.ui.com/hc/en-us/articles/34210126298775-Self-Hosting-UniFi

## Required reviewer decision record

For **each** proposed site, a real human reviewer must independently record the following (anonymized or synthetic examples only in public GitHub):

| Evidence field | PASS criterion | If unknown or failed |
|---|---|---|
| `release_channel_observed_at` + exact URL | The intended binary/build is confirmed **Official**, or an explicitly authorized isolated RC test is documented | **BLOCK** production upgrade |
| `console_model`, `network_version`, `unifi_os_version` | Actual console and OS support verified for the exact target build | **BLOCK** |
| `usg_present` + `legacy_host_type` | No unsupported USG; legacy Network Server migration accepted and scheduled | **BLOCK** |
| `backup_file_type` + `restore_drill_result` | Appropriate version-compatible backup and offline restore test; independent export of required history/data | **BLOCK** |
| `stats_retention_disposition` | Stakeholders formally accept loss of historical statistics, or a vetted archival alternative exists | **BLOCK** |
| `legacy_rule_inventory` + `zbf_policy_parity` | Every critical allow/deny path, management and VPN policy explicitly mapped and tested | **BLOCK** |
| `maintenance_window` + `recovery_plan` | Upgrade window and vendor-supported recovery path are understood and rehearsed | **BLOCK** |
| `reviewer_evidence` + PR decision | Actual independent human source review and formal GitHub evidence exist | **BLOCK** |

**Fail-closed rule:** if any required compatibility, history-retention, firewall, recovery, release-channel or human-approval field is unknown, leave the upgrade **NOT APPROVED**. Avoid collecting real controller IPs, tokens, client data, backup archives, door/camera media or production topology in this public repository.

## Repo integration and approval boundaries

- **M01** (`modules/M01-platform.md`) covers Controller and hosting topology, but does not currently incorporate this particular Network 11 RC removal of legacy Network Server and USG.
- **M03** (`modules/M03-firewall-vpn.md`) covers baseline ZBF prerequisites and manual rule migration, but should not be mistaken for a completed Network 11 **automatic** zone-policy parity test.
- **M09** (`modules/M09-backup-security.md`) covers backup/restore, but does not yet prove PostgreSQL data migration reversibility or historical-statistics retention.
- **M10** (`modules/M10-api-n8n.md`) references pinned Network API **v10.6.106** docs; these are not guarantees of Network 11 API behavior. The `network_application_release_rss` remains **`CANDIDATE_UNREVIEWED`** with channel `UNKNOWN_NOT_VALIDATED_FROM_RSS` in Draft PR #6.

Keep `sync/reviewed.json`, `sync/pending.json`, published module support labels and PR #6 Draft status **unchanged** until independent source analysis, real human review and separate owner-authorized PR actions. The 28/28 SHA recheck validates fingerprints, **not** the release note text/channel on this advisory or production readiness.
