#!/usr/bin/env python3
"""Convert one local-only v6 WiFi report into a UniFi Skill evidence-gated report.

Strict allowlist: no input strings (SSID, MAC, IP, topology, site or client ID)
are copied to output. This script never accesses a controller or the Internet.
"""
import argparse
import json
import math
import re
from pathlib import Path

from check_diagnostic_evidence import WIFI_LAN_METRICS, git_blob_sha, validate

SOURCE_SCHEMA = "unifi-m04-wifi-evidence-lan-only-v6"
SKILL_FILES = (
    "SKILL.md", "README.md", "docs/evidence-and-acceptance.md",
    "docs/diagnostic-evidence-contract.md",
    "docs/portable-one-shot.md", "docs/catalog-evidence-contract.md", "docs/product-capabilities.json",
    "sync/official-product-index.json",
    "modules/M01-platform.md", "modules/M02-networks.md", "modules/M03-firewall-vpn.md",
    "modules/M04-wifi.md", "modules/M05-switch.md", "modules/M06-protect.md",
    "modules/M07-access.md", "modules/M08-identity-talk.md",
    "modules/M09-backup-security.md", "modules/M10-api-n8n.md",
    "docs/api-capabilities.json",
    "runbooks/RB03-link-poe-inventory.md",
    "runbooks/RB04-wifi6-ssid-staging.md", "runbooks/RB05-n8n-api-readonly.md",
    "scripts/check_diagnostic_evidence.py",
    "scripts/convert_v6_wifi_evidence.py",
    "scripts/run_v6_wifi_skill.py", "scripts/run_wifi_skill.py",
    "scripts/collect_wifi_lan_local.py", "scripts/platform_wifi.py",
    "scripts/collect_unifi.py", "scripts/run_unifi_skill.py",
    "scripts/validate_capability_catalog.py",
    "scripts/discover_official_products.py",
    "scripts/windows_wlan_native.py", "scripts/windows_netsh_localized.py",
)


def bounded(value, lower, upper):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper


def read_skill_version(root):
    text = (root / "README.md").read_text(encoding="utf-8")
    match = re.search(r"\*\*版本\*\*[:：]\s*(v\d+\.\d+\.\d+-[a-z0-9-]+)", text)
    if not match:
        raise ValueError("Skill version not found in repository README.md")
    return match.group(1)


def observation(metric, value=None, source=None):
    if value is None:
        return {"metric": metric, "state": "NOT_OBSERVED"}
    return {"metric": metric, "state": "OBSERVED", "value": value, "source": source}


def extract_radio_retries(payload):
    """A per-radio AP sample; NOT a per-client retry measurement."""
    sites = payload.get("sites")
    if not isinstance(sites, list) or len(sites) != 1:
        return None
    aps = sites[0].get("access_points") if isinstance(sites[0], dict) else None
    if not isinstance(aps, list) or len(aps) != 1:
        return None
    ap = aps[0]
    stats = ap.get("stats") if isinstance(ap, dict) else None
    radios = stats.get("radio_samples") if isinstance(stats, dict) else None
    if not isinstance(radios, list) or not radios:
        return None
    samples = []
    seen = set()
    for radio in radios:
        if not isinstance(radio, dict):
            continue
        band, retry = radio.get("band_ghz"), radio.get("tx_retries_percent")
        if not bounded(band, 2, 7) or not bounded(retry, 0, 100):
            continue
        band = float(band)
        if band not in (2.4, 5.0, 6.0) or band in seen:
            continue
        seen.add(band)
        samples.append({"band_ghz": band, "retry_pct": float(retry)})
    return samples or None



def extract_ap_side_uplink_speed(payload):
    """Read only first-party AP *local* port evidence, not its parent Switch port.

    A legacy v6 report containing arbitrary active_port_speeds_mbps must NOT
    be accepted: it does not establish AP wired uplink vs some other port.
    """
    sites = payload.get("sites")
    if not isinstance(sites, list) or len(sites) != 1 or not isinstance(sites[0], dict):
        return None
    aps = sites[0].get("access_points")
    if not isinstance(aps, list) or len(aps) != 1 or not isinstance(aps[0], dict):
        return None
    ap = aps[0]
    if ap.get("uplink_speed_evidence") != "AP_SIDE_SINGLE_UP_PORT_PARENT_VERIFIED":
        return None
    if ap.get("uplink_mapping_evidence") != "PARENT_DEVICE_ONLY_NO_PORT_MAPPING":
        return None
    if not ap.get("uplink_parent_in_device_inventory") or ap.get("state") != "ONLINE":
        return None
    speed = ap.get("uplink_negotiated_speed_mbps")
    if not bounded(speed, 1, 100000):
        return None
    ports = ap.get("port_details")
    if not isinstance(ports, list) or not ports or len(ports) > 64:
        return None
    up = [p for p in ports if isinstance(p, dict) and p.get("state") == "UP"]
    if len(up) != 1:
        return None
    p = up[0]
    if (type(p.get("port_index")) is not int or p["port_index"] < 0
            or p["port_index"] > 4096):
        return None
    if p.get("negotiated_speed_mbps") != speed:
        return None
    if sum(1 for x in ports if isinstance(x, dict)
           and x.get("port_index") == p["port_index"]) != 1:
        return None
    maximum = p.get("max_capability_mbps")
    if maximum is not None and (not bounded(maximum, 1, 100000) or speed > maximum):
        return None
    return speed


def extract_lan_throughput(payload):
    item = payload.get("lan_tcp_throughput_test")
    if not isinstance(item, dict) or item.get("status") != "MEASURED":
        return None
    if item.get("scope") != "THIS_WINDOWS_PC_TO_EXPLICIT_PRIVATE_LAN_SERVER_ONLY":
        return None
    up, down = item.get("wifi_to_wired_mbps"), item.get("wired_to_wifi_mbps")
    if not bounded(up, 0.01, 100000) or not bounded(down, 0.01, 100000):
        return None
    return {"wifi_to_wired_mbps": float(up), "wired_to_wifi_mbps": float(down)}



def extract_windows_current_connection(payload):
    """Consume explicit CURRENT-link fields from known OS adapters; legacy v6 compatible."""
    obj = payload.get("client_wifi_link")
    if not isinstance(obj, dict):
        obj = payload.get("windows_native_wifi")
    if not isinstance(obj, dict) or obj.get("status") != "OBSERVED":
        return None
    if obj.get("source") not in (
        "WINDOWS_WLAN_API_ASSOCIATED_BSS", "WINDOWS_NETSH_EXPLICIT_CURRENT_INTERFACE",
        "MACOS_COREWLAN_CURRENT_INTERFACE", "LINUX_IW_CURRENT_LINK"
    ):
        return None
    band = obj.get("band_ghz")
    rssi = obj.get("rssi_dbm")
    if type(band) not in (int, float) or float(band) not in (2.4, 5.0, 6.0):
        band = None
    if not bounded(rssi, -110, -15):
        rssi = None
    return {
        "band": float(band) if band is not None else None,
        "rssi": int(rssi) if rssi is not None else None,
        "source": obj["source"],
    }


def convert(payload, repo_root):
    if not isinstance(payload, dict) or payload.get("report_schema") != SOURCE_SCHEMA:
        raise ValueError("Only UniFi WiFi v6 local-only report schema is accepted")
    mode = payload.get("collection_mode")
    if mode not in ("local", "mock"):
        raise ValueError("Unsupported collection mode")
    if not isinstance(payload.get("sites"), list) or not payload["sites"]:
        raise ValueError("No site collection in source report")

    root = Path(repo_root)
    loaded = []
    for name in SKILL_FILES:
        file = root / name
        if not file.is_file():
            raise ValueError("Missing required Skill file: " + name)
        loaded.append({"path": name, "blob_sha": git_blob_sha(file.read_bytes())})

    retry = extract_radio_retries(payload) if mode == "local" else None
    ap_speed = extract_ap_side_uplink_speed(payload) if mode == "local" else None
    lan = extract_lan_throughput(payload) if mode == "local" else None
    win = extract_windows_current_connection(payload) if mode == "local" else None
    values = {
        # V6 never proves an exact AP-to-switch port/LLDP association.
        "ap_uplink_port_mapping": observation("ap_uplink_port_mapping"),
        "ap_uplink_negotiated_mbps": observation(
            "ap_uplink_negotiated_mbps", ap_speed,
            "UniFi Network v10.6.106 GET adopted device details; AP's unique UP local port speedMbps; parent deviceId verified; NOT Switch port mapping or LAN throughput",
        ),
        # Only explicit currently associated BSS evidence; not capability or
        # "co-located AP" 6 GHz listings from Windows, nor channel->band guesses.
        "client_band": observation("client_band",
                                   win["band"] if win else None,
                                   win["source"] if win else None),
        "client_rssi_dbm": observation("client_rssi_dbm",
                                       win["rssi"] if win else None,
                                       win["source"] if win else None),
        "ap_radio_retry_pct": observation(
            "ap_radio_retry_pct", retry,
            "UniFi Network GET /sites/{siteId}/devices/{deviceId}/statistics/latest; one AP; per-radio only",
        ),
        "lan_throughput_mbps": observation(
            "lan_throughput_mbps", lan,
            "v6 explicit private-LAN TCP peer test; two directions; not WAN",
        ),
    }
    missing = sorted(metric for metric in WIFI_LAN_METRICS if values[metric]["state"] != "OBSERVED")
    result = {
        "schema_version": 1,
        "skill": {
            "repository": "tAIwan888/unifi-skill",
            "version": read_skill_version(root),
            "loaded_files": loaded,
        },
        "modules": ["modules/M04-wifi.md", "modules/M05-switch.md", "modules/M10-api-n8n.md"],
        "runbooks": [
            "runbooks/RB03-link-poe-inventory.md",
            "runbooks/RB04-wifi6-ssid-staging.md",
            "runbooks/RB05-n8n-api-readonly.md",
        ],
        "scope": "wifi-lan-performance",
        "device_access": "AUTHORIZED_READ_ONLY" if mode == "local" else "NONE",
        "test_tier": "DOC_REVIEWED" if mode == "local" else "MOCK_TESTED",
        "verification_status": "INCOMPLETE",
        "observations": [values[k] for k in sorted(WIFI_LAN_METRICS)],
        "missing_metrics": missing,
        "missing_evidence_reasons": {
            metric: {
                "ap_uplink_port_mapping": "OFFICIAL_API_PARENT_DEVICE_ID_ONLY_NO_REMOTE_SWITCH_PORT",
                "ap_uplink_negotiated_mbps": "AP_SINGLE_UP_PORT_OR_UPSTREAM_DEVICE_NOT_UNIQUELY_VERIFIED",
                "client_band": "CURRENT_OS_ASSOCIATED_BSS_BAND_UNAVAILABLE",
                "client_rssi_dbm": "CURRENT_OS_ASSOCIATED_RSSI_UNAVAILABLE",
                "ap_radio_retry_pct": "AP_RADIO_STATISTICS_NOT_AVAILABLE_OR_AMBIGUOUS",
                "lan_throughput_mbps": "NO_VERIFIED_PRIVATE_LAN_TEST_ENDPOINT",
            }[metric] for metric in missing
        },
        "automated_next_actions": {
            "ap_uplink_negotiated_mbps": "RECHECK_DOCUMENTED_AP_DEVICE_DETAILS_GET_ONLY",
            "ap_uplink_port_mapping": "WAIT_FOR_SUPPORTED_LLDP_PORT_EVIDENCE_SOURCE",
            "lan_throughput_mbps": "REQUIRES_AUTHORIZED_VERIFIED_LAN_TEST_SERVER_NOT_WAN",
        },
        "configuration_change_proposals": [],
        "limitations": [
            "The official API does not identify the upstream Switch port; AP-side negotiated speed is accepted only with a verified unique UP AP Ethernet port and parent device, never from Switch port speed.",
            "Signal percent or channel number alone is not proof of RSSI dBm or 6 GHz; only an OS-observed current link band or BSS frequency counts.",
            "AP radio retries are not client-specific retries.",
            "PHY rate, console TCP connect latency and WAN speed are not LAN throughput.",
            "No configuration changes are authorized or executed.",
            "DOC_REVIEWED/MOCK_TESTED are not a lab or production acceptance.",
        ],
    }
    problems = validate(result, root)
    if problems:
        raise ValueError("Evidence gate rejected report: " + "; ".join(problems))
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline, fail-closed UniFi Skill v6 evidence adapter")
    p.add_argument("--source", required=True, type=Path, help="Local v6 redacted report")
    p.add_argument("--out", required=True, type=Path, help="Local sanitized Skill evidence output")
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = p.parse_args(argv)
    if args.source.resolve() == args.out.resolve():
        p.error("Source and output must differ")
    repo_root = args.repo_root.resolve()
    output_target = args.out.resolve()
    if output_target == repo_root or repo_root in output_target.parents:
        p.error("Private diagnostic outputs must be saved OUTSIDE the public Skill repository")
    if args.out.is_symlink():
        p.error("Refuse to overwrite a symbolic link")
    try:
        payload = json.loads(args.source.read_text(encoding="utf-8"))
        result = convert(payload, args.repo_root)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    print("Evidence report saved locally; status: INCOMPLETE. No settings were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
