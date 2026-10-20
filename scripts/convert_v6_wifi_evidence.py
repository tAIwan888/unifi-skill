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
    "modules/M04-wifi.md", "modules/M05-switch.md", "modules/M10-api-n8n.md",
    "runbooks/RB03-link-poe-inventory.md",
    "runbooks/RB04-wifi6-ssid-staging.md", "runbooks/RB05-n8n-api-readonly.md",
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
    lan = extract_lan_throughput(payload) if mode == "local" else None
    values = {
        # V6 never proves an exact AP-to-switch port/LLDP association.
        "ap_uplink_port_mapping": observation("ap_uplink_port_mapping"),
        "ap_uplink_negotiated_mbps": observation("ap_uplink_negotiated_mbps"),
        # V6 Windows netsh parser supplies channel/signal%, not band or dBm.
        # Channel numbers and signal% must never be guessed into those units.
        "client_band": observation("client_band"),
        "client_rssi_dbm": observation("client_rssi_dbm"),
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
        "configuration_change_proposals": [],
        "limitations": [
            "A v6 snapshot cannot prove AP uplink mapping or negotiated speed.",
            "Windows signal percent is not RSSI in dBm; channel is not proof of 6 GHz.",
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
