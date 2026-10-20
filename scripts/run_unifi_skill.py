#!/usr/bin/env python3
"""Generic task-selected UniFi Skill one-shot CLI; WiFi v6 interface preserved.

Never starts a service, installs a package, changes devices, or uploads reports.
"""
import argparse
import getpass
import json
from pathlib import Path
import sys

from check_diagnostic_evidence import validate, git_blob_sha
from convert_v6_wifi_evidence import SKILL_FILES, convert, read_skill_version
from collect_unifi import (
    CAPABILITIES, NOT_IMPLEMENTED, PROFILES, ReadOnlyClient,
    capability_report, measure, selection
)
from collect_wifi_lan_local import collect_local, mock_fixture
from validate_capability_catalog import load as load_capability_catalog, query_model, query_endpoint, load_official_index
import run_v6_wifi_skill as legacy

MODULES = {
    "network": ("M01-platform", "M02-networks", "M05-switch", "M10-api-n8n"),
    "inventory": ("M01-platform", "M02-networks", "M10-api-n8n"),
    "networks": ("M02-networks", "M10-api-n8n"),
    "clients": ("M02-networks", "M10-api-n8n"),
    "ports": ("M05-switch", "M10-api-n8n"),
    "wifi": ("M04-wifi", "M05-switch", "M10-api-n8n"),
    "gateway": ("M01-platform", "M02-networks", "M10-api-n8n"),
    "firewall": ("M03-firewall-vpn", "M10-api-n8n"),
    "vpn": ("M03-firewall-vpn", "M10-api-n8n"),
    "protect": ("M06-protect", "M10-api-n8n"),
    "access": ("M07-access", "M10-api-n8n"),
    "backup": ("M09-backup-security", "M10-api-n8n"),
    "identity": ("M08-identity-talk", "M10-api-n8n"),
    "talk": ("M08-identity-talk", "M10-api-n8n"),
    "connect": ("M08-identity-talk", "M10-api-n8n"),
    "ev": ("M08-identity-talk", "M10-api-n8n"),
    "site-manager": ("M01-platform", "M10-api-n8n"),
}


def _report(root, profile, result, mock=False, wifi=None):
    active, unsupported = selection(profile)
    covered = active + unsupported
    if profile == "all":
        covered = tuple(MODULES)
    needed_modules = sorted({"modules/" + n + ".md"
                             for p in covered for n in MODULES[p]})
    runbooks = ["runbooks/RB05-n8n-api-readonly.md"]
    if "ports" in active or "wifi" in active:
        runbooks += ["runbooks/RB03-link-poe-inventory.md"]
    if "wifi" in active:
        runbooks += ["runbooks/RB04-wifi6-ssid-staging.md"]
    observations = result["observations"][:]
    missing_reasons = dict(result["missing_evidence_reasons"])
    if wifi is not None:
        observations += wifi["observations"]
        missing_reasons.update(wifi.get("missing_evidence_reasons", {}))
    names = [o["metric"] for o in observations]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate metric from collector profiles")
    missing = sorted(o["metric"] for o in observations if o["state"] != "OBSERVED")
    # All profile always contains unsupported families with explicit evidence
    # gaps, so it never asserts full-network acceptance.
    loaded = []
    for path in SKILL_FILES:
        target = root / path
        if not target.is_file() or target.is_symlink():
            raise ValueError("Trusted Skill snapshot missing: " + path)
        loaded.append({"path": path, "blob_sha": git_blob_sha(target.read_bytes())})
    report = {
        "schema_version": 1,
        "skill": {
            "repository": "tAIwan888/unifi-skill",
            "version": read_skill_version(root),
            "loaded_files": loaded,
        },
        "scope": "unifi-generic-" + profile,
        "collector_profile": profile,
        "modules": needed_modules,
        "runbooks": sorted(set(runbooks)),
        "device_access": "NONE" if mock or (not set(active) & set(CAPABILITIES)) else "AUTHORIZED_READ_ONLY",
        "test_tier": "MOCK_TESTED" if mock else "DOC_REVIEWED",
        "verification_status": "INCOMPLETE" if missing else "EVIDENCE_READY",
        "required_metrics": sorted(names),
        "observations": observations,
        "missing_metrics": missing,
        "missing_evidence_reasons": missing_reasons,
        "capability_status": result["collector_status"],
        "limitations": [
            "Only version-verified Network GET profiles are executed; other application API families are not connected.",
            "Aggregate data does not prove packet loss, throughput, VLAN/firewall state or exact AP remote Switch port.",
            "EVIDENCE_READY means only this selected profile's required data was observed, not validated network performance.",
            "No UniFi device settings were modified.",
        ],
        "configuration_change_proposals": [],
    }
    errors = validate(report, root)
    if errors:
        raise ValueError("Evidence gate blocked generic report: " + "; ".join(errors))
    return report


def execute(args, *, client_factory=ReadOnlyClient, wifi_collector=collect_local):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    if args.collect == "wifi":
        return legacy.execute(args)
    stdout_only = str(args.out) == "-"
    if not stdout_only and (not legacy._outside_repo(args.out, root) or args.out.is_symlink()):
        raise ValueError("Private report output must be outside repository and not a symlink")
    if args.collector_dir is not None:
        raise ValueError("Legacy external collector is only valid for WiFi profile")
    active, unsupported = selection(args.collect)
    needs_client = bool(set(active) & {"network", "inventory", "networks", "clients", "ports"})
    client = None
    key = None
    if not args.mock and (needs_client or "wifi" in active):
        if not legacy._authorized_lan_api(args.local):
            raise ValueError("Authorized private LAN Network HTTPS API URL required")
        key = getpass.getpass("Local UniFi Network API key (never stored): ").strip()
        if not key:
            raise ValueError("Local API key required")
        if needs_client:
            client = client_factory(args.local, key,
                                    str(args.ca_cert.resolve()) if args.ca_cert else None)
    result = measure(args.collect, mock=args.mock, client=client)
    wifi = None
    if "wifi" in active:
        raw = mock_fixture() if args.mock else wifi_collector(
            args.local, key, str(args.ca_cert.resolve()) if args.ca_cert else None)
        wifi = convert(raw, root)
    del key
    report = _report(root, args.collect, result, mock=args.mock, wifi=wifi)
    text = json.dumps(report, ensure_ascii=False, indent=None if stdout_only else 2)
    if stdout_only:
        print(text)
        print("Skill evidence validated; no device changes", file=sys.stderr)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print("Validated sanitized report saved locally; status: " +
              report["verification_status"])
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Portable one-shot UniFi Skill Collector")
    parser.add_argument("--catalog-index-status", action="store_true", help="Official product listing index validation status; no network")
    parser.add_argument("--catalog-model", help="Offline official Tech Specs model ID; never touches a device")
    parser.add_argument("--catalog-api", help="Offline exact documented API path; never executes endpoint")
    parser.add_argument("--catalog-version", default="10.6.106",
                        help="Exact API doc version for --catalog-api")
    parser.add_argument("--catalog-family", default="network",
                        help="Exact API family for --catalog-api")
    parser.add_argument("--capabilities", action="store_true",
                        help="Print implemented and version-gated capability list offline")
    parser.add_argument("--collect", choices=PROFILES, default="network",
                        help="Task profile: network (default), wifi, inventory, networks, clients, ports, all ...")
    parser.add_argument("--out", type=Path, help="Private JSON path, or '-' for JSON stdout")
    parser.add_argument("--collector-dir", type=Path, help="Legacy WiFi-only external v6 folder")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true")
    mode.add_argument("--local", help="Authorized local Network HTTPS Integration API endpoint")
    parser.add_argument("--ca-cert", type=Path)
    args = parser.parse_args(argv)
    if args.catalog_index_status:
        if (args.catalog_api or args.catalog_model or args.local or args.mock
                or args.out or args.ca_cert or args.capabilities or args.collector_dir):
            parser.error("Index status is offline-only")
        try:
            root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
            index = load_official_index(root)
            print(json.dumps({"status": index["snapshot_status"],
                              "unique_product_links": index["unique_product_links"],
                              "category_count": len(index["sources"]),
                              "source_status_reason": index.get("source_status_reason"),
                              "scope": index["catalog_scope"]}))
            return 0
        except (ValueError, OSError, json.JSONDecodeError):
            print("STOP: product index source evidence invalid", file=sys.stderr)
            return 2
    if args.catalog_model or args.catalog_api:
        if (args.mock or args.local or args.out or args.ca_cert
                or args.collector_dir or args.capabilities
                or (args.catalog_model and args.catalog_api)):
            parser.error("Offline catalog lookup cannot be combined with device collection")
        try:
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
            load_capability_catalog(base)
            row = (query_model(args.catalog_model, base) if args.catalog_model
                   else query_endpoint(args.catalog_family, args.catalog_version,
                                       args.catalog_api, base))
            print(json.dumps(row if row is not None else
                             {"status": "UNKNOWN_NOT_IN_DOCUMENTED_CATALOG",
                              "agent_next_action": "SEARCH_OFFICIAL_PUBLIC_TECHSPECS_AND_VERIFY",
                              "manual_user_lookup_required": False},
                             ensure_ascii=False))
            return 0
        except (OSError, ValueError, json.JSONDecodeError):
            print("STOP: offline capability catalog failed validation", file=sys.stderr)
            return 2
    if args.capabilities:
        if args.mock or args.local or args.out or args.ca_cert or args.collector_dir:
            parser.error("--capabilities is offline and cannot be combined with collection")
        print(json.dumps(capability_report(), ensure_ascii=False))
        return 0
    if args.out is None or (not args.mock and not args.local):
        parser.error("Choose --mock or --local, and --out")
    try:
        return execute(args)
    except (OSError, ValueError) as error:
        # No API response body, secret, URL or private identifier is printed.
        print("STOP: collection or evidence verification failed (" +
              type(error).__name__ + ")", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
