#!/usr/bin/env python3
"""Generic, task-scoped UniFi Network Integration API collector.

Only documented versioned GET endpoints from docs/api-capabilities.json.
All collected metrics are aggregate non-identifying values. No raw API data,
IDs, names, MACs, IPs, client lists, settings or topology are emitted.
"""
from collections import Counter
import urllib.parse

from collect_wifi_lan_local import (
    ReadError, ReadOnlyClient, MAX_SITES, MAX_DEVICES, identifier, ports
)

CAPABILITIES = {
    "network": ("M01", "M02", "M05", "M10"),
    "inventory": ("M01", "M02", "M10"),
    "networks": ("M02", "M10"),
    "clients": ("M02", "M10"),
    "ports": ("M05", "M10"),
    "wifi": ("M04", "M05", "M10"),
}
NOT_IMPLEMENTED = {
    "gateway": "GATEWAY_WAN_METRICS_NOT_VALIDATED_FOR_THIS_API_VERSION",
    "firewall": "FIREWALL_POLICY_READ_SCHEMA_NOT_VERIFIED",
    "vpn": "VPN_STATUS_READ_SCHEMA_NOT_VERIFIED",
    "protect": "SEPARATE_PROTECT_API_REQUIRES_VERSION_AND_PERMISSION_VALIDATION",
    "access": "SEPARATE_SAFETY_CRITICAL_ACCESS_API_NOT_ENABLED",
    "backup": "BACKUP_STATUS_READ_SCHEMA_NOT_VERIFIED",
    "identity": "IDENTITY_READ_API_NOT_CONNECTED",
    "talk": "TALK_READ_API_NOT_VERIFIED",
    "connect": "CONNECT_READ_API_NOT_VERIFIED",
    "ev": "EV_READ_API_NOT_VERIFIED",
    "site-manager": "CLOUD_SITE_MANAGER_DISABLED_LOCAL_ONLY",
}
PROFILES = tuple(CAPABILITIES) + tuple(NOT_IMPLEMENTED) + ("all",)
METRICS = {
    "network": ("site_count", "adopted_device_count", "network_count",
                "connected_client_count", "device_port_count", "device_up_port_count"),
    "inventory": ("site_count", "adopted_device_count"),
    "networks": ("network_count",),
    "clients": ("connected_client_count",),
    "ports": ("device_port_count", "device_up_port_count"),
}
DOCUMENTED_GET = {
    "/sites", "/sites/{siteId}/devices", "/sites/{siteId}/networks",
    "/sites/{siteId}/clients", "/sites/{siteId}/devices/{deviceId}",
}
MAX_CLIENTS = 500
MAX_NETWORKS = 150


def capability_report():
    return {
        "schema": "unifi-skill-collector-capabilities-v1",
        "api": "UniFi Network Integration v10.6.106",
        "implemented_profiles": list(CAPABILITIES),
        "unimplemented_profiles": dict(NOT_IMPLEMENTED),
        "all": "Implemented GET-only profiles; unsupported families return explicit gaps",
        "access": "LOCAL_AUTHORIZED_GET_ONLY",
        "no_persistent_service": True,
    }


def selection(profile):
    if profile not in PROFILES:
        raise ValueError("Unknown collector profile")
    if profile == "all":
        return tuple(CAPABILITIES), tuple(NOT_IMPLEMENTED)
    return ((profile,), ()) if profile in CAPABILITIES else ((), (profile,))


def _site_key(site):
    key = site.get("id") if isinstance(site, dict) else None
    if not identifier(key):
        raise ReadError("Malformed site identity")
    return urllib.parse.quote(key, safe="")


def _device_key(item):
    key = item.get("id") if isinstance(item, dict) else None
    if not identifier(key):
        raise ReadError("Malformed device identity")
    return urllib.parse.quote(key, safe="")


def collect_network_sections(client, active):
    """One bounded, site-scoped GET traversal for all selected API families.

    Query failures do not invent zero observations. A failure stays missing.
    No user-owned ID or server response text leaves this function.
    """
    needed = set(active) & set(METRICS)
    if "network" in needed:
        needed.discard("network")
        needed.update(("inventory", "networks", "clients", "ports"))
    if not needed:
        return {}, {}
    values, statuses = {}, {}
    # Site listing is the common trust anchor. Any error blocks all requested
    # counts; never turn an unauthorized/incomplete page into a zero count.
    try:
        sites = client.paged("/sites", cap=MAX_SITES)
        if not sites:
            raise ReadError("No site")
        prefixes = ["/sites/" + _site_key(s) for s in sites]
    except (ReadError, KeyError, TypeError, ValueError):
        for profile in set(needed) | set(active):
            statuses[profile] = "SITE_LIST_NOT_VERIFIED"
        return values, statuses

    if "inventory" in needed:
        values["site_count"] = len(prefixes)
    for profile in needed:
        statuses[profile] = "OBSERVED"

    device_total = 0
    network_total = 0
    client_total = 0
    port_total = 0
    port_up_total = 0
    port_data_seen = False
    for prefix in prefixes:
        if "inventory" in needed or "ports" in needed:
            try:
                devices = client.paged(prefix + "/devices", cap=MAX_DEVICES)
                device_total += len(devices)
                if "ports" in needed:
                    for d in devices:
                        key = _device_key(d)
                        detail = client.get(prefix + "/devices/" + key)
                        iface = detail.get("interfaces") if isinstance(detail, dict) else None
                        rows = iface.get("ports") if isinstance(iface, dict) else None
                        if not isinstance(rows, list):
                            # A device without wired interfaces is expected.
                            continue
                        if len(rows) > 64:
                            raise ReadError("Device ports truncated")
                        if not all(isinstance(p, dict) and
                                   type(p.get("idx")) is int and
                                   p.get("state") in ("UP", "DOWN", "DISABLED")
                                   for p in rows):
                            raise ReadError("Malformed port rows")
                        if len({p["idx"] for p in rows}) != len(rows):
                            raise ReadError("Duplicate local port index")
                        port_data_seen = True
                        port_total += len(rows)
                        port_up_total += sum(p["state"] == "UP" for p in rows)
            except (ReadError, KeyError, TypeError, ValueError):
                if "inventory" in needed:
                    statuses["inventory"] = "DEVICES_QUERY_FAILED"
                if "ports" in needed:
                    statuses["ports"] = "DEVICE_PORT_DETAILS_UNVERIFIED"
        if "networks" in needed:
            try:
                network_total += len(client.paged(prefix + "/networks", cap=MAX_NETWORKS))
            except (ReadError, KeyError, TypeError, ValueError):
                statuses["networks"] = "NETWORK_LIST_QUERY_FAILED"
        if "clients" in needed:
            try:
                client_total += len(client.paged(prefix + "/clients", cap=MAX_CLIENTS))
            except (ReadError, KeyError, TypeError, ValueError):
                statuses["clients"] = "CLIENT_LIST_QUERY_FAILED"

    if statuses.get("inventory") == "OBSERVED":
        values["adopted_device_count"] = device_total
    else:
        values.pop("site_count", None)
    if statuses.get("networks") == "OBSERVED":
        values["network_count"] = network_total
    if statuses.get("clients") == "OBSERVED":
        values["connected_client_count"] = client_total
    if statuses.get("ports") == "OBSERVED" and port_data_seen:
        values["device_port_count"] = port_total
        values["device_up_port_count"] = port_up_total
    elif "ports" in needed and statuses["ports"] == "OBSERVED":
        statuses["ports"] = "NO_VERIFIED_PORT_ARRAYS"
    if "network" in active:
        statuses["network"] = ("OBSERVED" if all(
            statuses.get(p) == "OBSERVED" for p in
            ("inventory", "networks", "clients", "ports"))
            else "NETWORK_AGGREGATE_INCOMPLETE")
    return values, statuses


def measure(profile, *, mock=False, client=None):
    """Structured, sanitized numeric observation contract for generic profiles."""
    active, unsupported = selection(profile)
    wanted = {metric for p in active for metric in METRICS.get(p, ())}
    if profile in NOT_IMPLEMENTED:
        wanted.add(profile + "_validated_status")
    if profile == "all":
        wanted.update(p + "_validated_status" for p in unsupported)
    values, status = ({}, {}) if mock else collect_network_sections(client, active)
    observations = []
    reasons = {}
    for metric in sorted(wanted):
        if metric in values and type(values[metric]) is int and values[metric] >= 0:
            observations.append({
                "metric": metric, "state": "OBSERVED", "value": values[metric],
                "source": "UniFi Network Integration API v10.6.106 documented GET; full pagination; aggregate only",
            })
        else:
            observations.append({"metric": metric, "state": "NOT_OBSERVED"})
            p = next((p for p, keys in METRICS.items() if metric in keys), None)
            reasons[metric] = ("MOCK_NO_DEVICE_ACCESS" if mock else
                               NOT_IMPLEMENTED.get(metric.removesuffix("_validated_status"),
                               status.get(p, "API_EVIDENCE_UNAVAILABLE")))
    return {
        "observations": observations,
        "required_metrics": sorted(wanted),
        "missing_evidence_reasons": reasons,
        "collector_status": {
            p: "NOT_IMPLEMENTED_VERSION_GATED" if p in NOT_IMPLEMENTED else
               ("MOCK_NO_DEVICE_ACCESS" if mock else status.get(p, "NOT_RUN"))
            for p in (*active, *unsupported)
        },
    }
