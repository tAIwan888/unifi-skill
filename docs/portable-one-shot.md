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
