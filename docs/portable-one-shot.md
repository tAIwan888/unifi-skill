# UniFi Skill portable one-shot CLI

Status: PROTOTYPE / MOCK_TESTED, NOT SIGNED, NOT REAL-DEVICE VERIFIED.
Reference: SKILL.md; M01/M04/M05/M09/M10; RB03/RB04/RB05;
docs/evidence-and-acceptance.md and diagnostic-evidence-contract.md.

## Run-to-completion contract

- One self-contained CLI binary per platform/CPU: Windows x64, macOS Intel/ARM64,
  Linux x64/ARM64. No target Python, git, package manager or system installer.
- User or authorized AI-Agent executor starts a child process only on demand;
  waits for sanitized JSON; child exits. No background daemon, scheduled task,
  autorun, launchd/systemd/Windows service, listener or privileged helper.
- On-demand commands (output file in a private location, not public repository):

    unifi-skill --mock --out <private-output.json>
    unifi-skill --local https://unifi.local/proxy/network/integration/v1 --out <private-output.json>
    unifi-skill --local https://unifi.local/proxy/network/integration/v1 --ca-cert <trusted-CA.pem> --out <private-output.json>

- Device access only via explicitly authorized RFC1918/.local local HTTPS,
  checked TLS, bounded GET API calls. API key entered by hidden local prompt,
  not command-line, report, GitHub or CI. Zero device setting writes.
- Offline mock makes no device call. No WAN measurement or diagnostic upload.
- Raw SSID/BSSID/MAC/IP/topology never serialized. Evidence unknown if
  unsupported. PHY link Mbps and WAN speed never substitute LAN throughput.

## OS-specific, on-demand read-only adapters

| OS | Probe | Limits |
| --- | --- | --- |
| Windows | Native WLAN BSS matched in memory; localized netsh fallback | Privacy permission/driver may block |
| macOS | CWWiFiClient/CoreWLAN via packaged PyObjC | OS version/permissions and 6 GHz band enum vary |
| Linux | Existing iw utility, current associated link only | Requires already installed iw/nl80211; never auto-installs |
| Any | UniFi official local GET + shared Evidence Gate | Exact Switch remote port absent from documented API |

Source IDs allow the converter to accept actual current client band and
RSSI dBm from known OS adapters only. Signal % and channel number cannot
substitute native RSSI or observed band; unsupported metrics remain absent.
If multiple connected WiFi interfaces, reject ambiguous identification.

## Embedded source and frozen SHA gate

At build time, PyInstaller includes the exact known-good SKILL_FILES list
from scripts/convert_v6_wifi_evidence.py (Skill docs, source, modules,
runbooks and validator). On one-file start, the executable unpacks into
PyInstaller's temporary runtime directory; the existing gate computes
40-digit Git Blob SHAs for all bundled sources. No outside source checkout
is required. After termination, no resident service is retained; OS/process
crashes may leave temporary extraction files.

Source code and the bundled public Skill snapshot are *fixed at build time*.
Offline success does NOT imply this binary is the latest reviewed release.

## On-launch updates: planned, not yet enabled

Do not download/execute arbitrary GitHub main branch code or let an unsigned
manifest declare its own trusted SHA. A later iteration may update **data-only**
reviewed Skill documents at invocation, after these release gates exist:

1. A pinned publisher verification key and signed manifest (with key rotation
   and revocation), exact release commit, file SHA256 and compatible schema.
2. Bounded HTTPS download, signature + all file integrity validation, no
   dynamic Python/script imports, fail closed for unknown manifest.
3. Stage in private data cache, validate file paths/source SHAs and schema,
   then atomically promote with last-known-good rollback.
4. Offline mode reports the exact cached/embedded version and stale status;
   no false "latest" claims; no background sync.
5. Binary upgrades only after Windows code signing, macOS notarization,
   and Linux artifact signature verification are established.

Until this exists, using a changed binary necessarily requires obtaining
the newer reviewed build. Unsigned CI artifacts are for test use only and
must not be portrayed as production releases.

## CI and acceptance

- 5 architecture-specific hosted runners build one-file artifacts with
  PyInstaller; artifacts are unsigned short-retention prototypes.
- Offline Python adapter mocks plus executing the compiled one-file binary
  in --mock mode must all PASS before PR acceptance.
- No real host WiFi or UniFi device is queried in CI.
- Real Windows/macOS/Linux adapter success requires documented hardware,
  OS, driver/permission, Network app/API version, timestamps and observations.
- LAB_TESTED and PRODUCTION_VERIFIED remain blocked until separate on-device
  evidence, authorization and rollback arrangements.

References:
- https://developer.ui.com/network/v10.6.106/getadopteddevicedetails
- https://developer.apple.com/documentation/corewlan/cwinterface
- https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw.html
- https://pyinstaller.org/en/stable/runtime-information.html

## Generic UniFi Skill Collector — task-driven one-shot (prototype)

The same portable binary is task-selected, not limited to WiFi. Default invocation preserves the legacy WiFi evidence contract.

Supported offline capabilities query: `unifi-skill --capabilities`

Command examples (no device access):

```sh
unifi-skill --collect inventory --mock --out -
unifi-skill --collect network --mock --out -
unifi-skill --collect networks --mock --out -
unifi-skill --collect clients --mock --out -
unifi-skill --collect ports --mock --out -
unifi-skill --collect wifi --mock --out -
unifi-skill --collect all --mock --out -
```

When locally authorized, replace --mock with --local pointing to a verified private LAN Network Integration HTTPS API endpoint; enter its key at the terminal, never upload it to GitHub or chat. The --out - option prints a single sanitized JSON for approved local AI Agent subprocess use.

- inventory: site and adopted-device counts from documented paginated Sites/Devices GET.
- networks: paginated site Network counts; no SSID, VLAN names, IDs or configurations.
- clients: paginated currently connected client counts; no identities, MACs or IPs.
- ports: adopted-device aggregate total port count and UP count from documented device details; NOT specific switch mapping or verified uplink throughput.
- network: combines inventory, networks, clients and ports in one GET-only pass.
- wifi: retains current AP RF statistics and Windows/macOS/Linux local radio probe.
- all: executes the supported Network/WiFi profiles and explicitly states gaps for unsupported app families. No Protect, Access or Cloud Site Manager API is contacted.

Gateway/WAN health, Firewall, VPN, Protect, Access, Backup, Identity, Talk, Connect, EV and Site Manager are **version-gated, not implemented**. The tool reports these gaps without pretending the API can never expose them; it does not request privileged personal/video/door state.

Generic task reports reuse the same Evidence Gate: complete source Git Blob SHAs, module/runbook references, per-metric OBSERVED/NOT_OBSERVED, reasons, test tier and INCOMPLETE/EVIDENCE_READY. A measured aggregate count never proves real LAN throughput, network health or permission to change settings.

All network queries are HTTPS GET-only to authorized RFC1918/.local endpoints, bounded and fully paginated. Missing pages and malformed metrics fail closed. No installation, service, scheduler, network listener, device write or automatic upload. Five-platform CI remains mock-only and is not hardware acceptance.


## Offline model and API-version capability lookup

The single-file CLI embeds docs/product-capabilities.json, docs/api-capabilities.json and docs/catalog-evidence-contract.md. Offline commands --catalog-model MODEL and --catalog-api DOCUMENTED_GET_PATH --catalog-version EXACT_VERSION return public facts only. They never contact a private Controller, and source/docs evidence alone does not authorize execution. See docs/catalog-evidence-contract.md.
