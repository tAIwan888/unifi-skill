#!/usr/bin/env python3
"""Fail-closed, offline UniFi Skill diagnostic evidence checker.

Only validates sanitized report metadata; never connects to a controller.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

REPO_NAME = "tAIwan888/unifi-skill"
REQUIRED_FILES = {"SKILL.md", "docs/evidence-and-acceptance.md"}
WIFI_LAN_METRICS = {
    "ap_uplink_port_mapping",
    "ap_uplink_negotiated_mbps",
    "client_band",
    "client_rssi_dbm",
    "ap_radio_retry_pct",
    "lan_throughput_mbps",
}
GENERIC_COUNT_METRICS = {
    "site_count", "adopted_device_count", "network_count",
    "connected_client_count", "device_port_count", "device_up_port_count",
}

SENSITIVE_KEYS = {
    "api_key", "apikey", "access_token", "refresh_token", "password",
    "secret", "mac", "mac_address", "bssid", "ssid", "ip", "ip_address",
    "controller_ip", "serial", "serial_number", "private_key", "token",
}


def git_blob_sha(contents):
    payload = b"blob " + str(len(contents)).encode("ascii") + b"\0" + contents
    return hashlib.sha1(payload).hexdigest()


def _has_sensitive_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in SENSITIVE_KEYS:
                return True
            if _has_sensitive_keys(value):
                return True
    elif isinstance(obj, list):
        return any(_has_sensitive_keys(v) for v in obj)
    return False




def _bounded_number(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def _metric_value_valid(metric, value):
    """Schema sanity only: proves neither provenance nor correct RF interpretation."""
    if metric in GENERIC_COUNT_METRICS:
        return type(value) is int and 0 <= value <= 1000000
    if metric.endswith("_validated_status"):
        # These are version-gated placeholders, not an observed metric.
        return False
    if metric == "client_band":
        return type(value) in (int, float) and float(value) in (2.4, 5.0, 6.0)
    if metric == "client_rssi_dbm":
        return _bounded_number(value, -110, -15)
    if metric == "ap_uplink_negotiated_mbps":
        return _bounded_number(value, 10, 100000)
    if metric == "ap_uplink_port_mapping":
        return (isinstance(value, dict)
                and type(value.get("switch_port_number")) is int
                and 1 <= value["switch_port_number"] <= 4096
                and value.get("method") in ("LLDP_VERIFIED", "PHYSICAL_VERIFIED"))
    if metric == "ap_radio_retry_pct":
        return (isinstance(value, list) and len(value) in (1, 2, 3)
                and all(isinstance(x, dict)
                        and type(x.get("band_ghz")) in (int, float)
                        and float(x["band_ghz"]) in (2.4, 5.0, 6.0)
                        and _bounded_number(x.get("retry_pct"), 0, 100) for x in value))
    if metric == "lan_throughput_mbps":
        return (isinstance(value, dict)
                and _bounded_number(value.get("wifi_to_wired_mbps"), 0.01, 100000)
                and _bounded_number(value.get("wired_to_wifi_mbps"), 0.01, 100000))
    return True


def validate(report, root):
    errors = []
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    if _has_sensitive_keys(report):
        errors.append("sensitive field name present; do not publish private device data")
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    skill = report.get("skill")
    if not isinstance(skill, dict):
        return errors + ["skill object missing"]
    if skill.get("repository") != REPO_NAME:
        errors.append("wrong skill repository")
    version = skill.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+-[a-z0-9-]+", version):
        errors.append("skill version missing or invalid")
    files = skill.get("loaded_files")
    if not isinstance(files, list):
        return errors + ["skill.loaded_files missing"]
    found = set()
    for item in files:
        if not isinstance(item, dict):
            errors.append("loaded_file must be an object")
            continue
        name, sha = item.get("path"), item.get("blob_sha")
        if not isinstance(name, str) or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            errors.append("loaded_file requires path and 40-character blob_sha")
            continue
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or str(rel).startswith("."):
            errors.append("unsafe file path")
            continue
        if name in found:
            errors.append("duplicate loaded_file " + name)
            continue
        found.add(name)
        target = root / rel
        if not target.is_file():
            errors.append("file missing from checkout: " + name)
        elif git_blob_sha(target.read_bytes()) != sha:
            errors.append("Git Blob SHA mismatch: " + name)
    if not REQUIRED_FILES.issubset(found):
        errors.append("SKILL.md and evidence-and-acceptance.md must both be loaded")
    for field, prefix in (("modules", "modules/"), ("runbooks", "runbooks/")):
        names = report.get(field)
        if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n.startswith(prefix) or n not in found for n in names):
            errors.append(field + " must reference loaded Skill files")
    if report.get("device_access") not in ("NONE", "AUTHORIZED_READ_ONLY"):
        errors.append("device_access must be NONE or AUTHORIZED_READ_ONLY")
    if report.get("test_tier") not in ("DOC_REVIEWED", "MOCK_TESTED", "LAB_TESTED", "PRODUCTION_VERIFIED"):
        errors.append("invalid test_tier")
    scope = report.get("scope")
    status = report.get("verification_status")
    if status not in ("INCOMPLETE", "EVIDENCE_READY"):
        errors.append("verification_status must be INCOMPLETE or EVIDENCE_READY")
    items = report.get("observations")
    if not isinstance(items, list):
        return errors + ["observations must be a list"]
    observed = {}
    for item in items:
        if not isinstance(item, dict):
            errors.append("observation must be an object")
            continue
        metric, state, source = item.get("metric"), item.get("state"), item.get("source")
        if not isinstance(metric, str) or not metric or metric in observed:
            errors.append("duplicate or invalid observation metric")
            continue
        if state not in ("OBSERVED", "NOT_OBSERVED"):
            errors.append("invalid observation state for " + metric)
        if state == "OBSERVED" and (not isinstance(source, str) or not source.strip() or item.get("value") is None):
            errors.append("observed metric requires source and value: " + metric)
        if state == "OBSERVED" and not _metric_value_valid(metric, item.get("value")):
            errors.append("invalid WiFi LAN measurement value: " + metric)
            state = "NOT_OBSERVED"
        observed[metric] = state
    supplied = report.get("required_metrics")
    if scope == "wifi-lan-performance":
        required = WIFI_LAN_METRICS
    elif isinstance(supplied, list) and all(isinstance(x, str) for x in supplied):
        required = set(supplied)
    else:
        required = set()
    if not required:
        errors.append("no required metrics specified")
    missing = {m for m in required if observed.get(m) != "OBSERVED"}
    declared_missing = report.get("missing_metrics")
    if not isinstance(declared_missing, list) or not all(isinstance(x, str) for x in declared_missing) or set(declared_missing) != missing:
        errors.append("missing_metrics does not match unobserved required metrics")
    if status == "EVIDENCE_READY" and missing:
        errors.append("EVIDENCE_READY forbidden while required measurements are missing")
    if status == "INCOMPLETE" and not missing:
        errors.append("INCOMPLETE must identify a real required evidence gap")
    proposals = report.get("configuration_change_proposals", [])
    if not isinstance(proposals, list):
        errors.append("configuration_change_proposals must be a list")
    elif proposals:
        if status != "EVIDENCE_READY":
            errors.append("configuration changes forbidden with incomplete evidence")
        for proposal in proposals:
            if not isinstance(proposal, dict) or not all(isinstance(proposal.get(k), str) and proposal[k].strip() for k in ("basis", "baseline", "validation_plan", "rollback_plan")):
                errors.append("change proposal needs basis, baseline, validation_plan and rollback_plan")
            elif proposal.get("execution_status") != "NOT_EXECUTED_REQUIRES_APPROVAL":
                errors.append("proposed changes cannot be marked executed")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate a sanitized UniFi Skill diagnostic report offline")
    parser.add_argument("report", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error("cannot load report JSON: " + str(exc))
    problems = validate(report, args.repo_root)
    for problem in problems:
        print("FAIL: " + problem)
    if problems:
        raise SystemExit(1)
    print("PASS: Skill source SHA and diagnostic evidence contract")


if __name__ == "__main__":
    main()
