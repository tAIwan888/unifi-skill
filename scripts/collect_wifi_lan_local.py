#!/usr/bin/env python3
"""UniFi Skill integrated M04/M05/M10 GET-only local collector (synthetic testable).

Local Windows process only. Never stores private identifiers, raw API JSON,
client addresses, SSID, credentials or switch-to-AP topology. No WAN tests.
"""
import collections
import ipaddress
import json
import math
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 3_000_000
MAX_SITES = 8
MAX_DEVICES = 150
PAGE_SIZE = 50
MAX_PAGES = 12
SCHEMA = "unifi-m04-wifi-evidence-lan-only-v6"  # existing adapter compatibility

class ReadError(Exception):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReadError("HTTP redirect blocked; no API key forwarded")


def local_api_url(address):
    try:
        u = urllib.parse.urlsplit(address)
        if (u.scheme != "https" or not u.hostname or u.username or u.password
                or u.query or u.fragment or u.port not in (None, 443, 8443)):
            raise ValueError()
        if u.path.rstrip("/") not in ("/proxy/network/integration/v1", "/integration/v1"):
            raise ValueError()
        host = u.hostname.lower()
        try:
            ip = ipaddress.ip_address(host)
            allowed = (ipaddress.ip_network("10.0.0.0/8"),
                       ipaddress.ip_network("172.16.0.0/12"),
                       ipaddress.ip_network("192.168.0.0/16"))
            if ip.version != 4 or not any(ip in network for network in allowed):
                raise ValueError()
        except ValueError:
            if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,244}\.local", host):
                raise ValueError()
        return address.rstrip("/")
    except (TypeError, ValueError):
        raise ReadError("Only authorized private LAN HTTPS Network API endpoints accepted") from None


def number(value, low, high):
    return value if type(value) in (int, float) and math.isfinite(value) and low <= value <= high else None


def nonident_text(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+ -]{0,60}", value) else None


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) is not None


class ReadOnlyClient:
    def __init__(self, url, key, ca_cert=None):
        self.base = local_api_url(url)
        if not isinstance(key, str) or not key.strip():
            raise ReadError("Local API key missing")
        self.key = key.strip()
        context = ssl.create_default_context(cafile=ca_cert)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=context), NoRedirect())

    def get(self, path):
        if not path.startswith("/") or ".." in path or "//" in path or "#" in path:
            raise ReadError("Invalid API endpoint")
        req = urllib.request.Request(self.base + path,
            method="GET", headers={"X-API-Key": self.key, "Accept": "application/json"})
        try:
            with self.opener.open(req, timeout=12) as resp:
                if resp.headers.get_content_type() != "application/json":
                    raise ReadError("Unexpected non-JSON response")
                data = resp.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ReadError("Response exceeds size bound")
                result = json.loads(data)
                if not isinstance(result, dict):
                    raise ReadError("Expected API object")
                return result
        except urllib.error.HTTPError as exc:
            raise ReadError("UniFi Network GET HTTP " + str(exc.code)) from None
        except urllib.error.URLError:
            raise ReadError("Cannot reach authorized local API or verify TLS") from None
        except (ValueError, json.JSONDecodeError):
            raise ReadError("Invalid JSON returned by API") from None

    def paged(self, path, cap=MAX_DEVICES):
        items = []
        expected_total = None
        for _ in range(MAX_PAGES):
            suffix = "?" if "?" not in path else "&"
            data = self.get(path + suffix + urllib.parse.urlencode(
                {"offset": len(items), "limit": PAGE_SIZE}))
            rows = data.get("data")
            total = data.get("totalCount")
            if not isinstance(rows, list) or type(total) is not int or total < 0 or total > cap:
                raise ReadError("Invalid or over-limit paginated response")
            if data.get("offset") != len(items) or data.get("count") != len(rows):
                raise ReadError("API pagination mismatch")
            if expected_total is None:
                expected_total = total
            elif total != expected_total:
                raise ReadError("API pagination changed during audit")
            if not rows and len(items) < total:
                raise ReadError("Incomplete API pagination")
            items.extend(rows)
            if len(items) > total or len(items) > cap:
                raise ReadError("API list exceeded bound")
            if len(items) == total:
                return items
        raise ReadError("Partial pagination: max pages exceeded")


def ports(detail):
    interfaces = detail.get("interfaces") if isinstance(detail, dict) else None
    rows = interfaces.get("ports") if isinstance(interfaces, dict) else None
    if not isinstance(rows, list):
        return []
    result = []
    for port in rows[:64]:
        if not isinstance(port, dict):
            continue
        index = port.get("idx")
        state = port.get("state")
        result.append({
            "port_index": index if type(index) is int and 0 <= index <= 4096 else None,
            "state": state if state in ("UP", "DOWN", "DISABLED") else "UNKNOWN",
            "negotiated_speed_mbps": number(port.get("speedMbps"), 1, 100000),
            "max_capability_mbps": number(port.get("maxSpeedMbps"), 1, 100000),
        })
    return result



def verified_ap_side_uplink_speed(detail, current_ports, parent_verified):
    """Only a single UP AP *local* port with an in-inventory parent is evidence.

    Never attribute any port on the upstream switch to an AP. This is the AP
    Ethernet PHY link speed, not a throughput test or LLDP neighbor mapping.
    """
    if not parent_verified or detail.get("state") != "ONLINE":
        return None, "AP_PARENT_OR_ONLINE_STATE_NOT_VERIFIED"
    # Reject malformed or missing API port rows, never infer from model caps.
    interfaces = detail.get("interfaces")
    rows = interfaces.get("ports") if isinstance(interfaces, dict) else None
    if not isinstance(rows, list) or not rows or len(rows) > 64:
        return None, "AP_PORT_DETAILS_UNAVAILABLE"
    if len(current_ports) != len(rows):
        return None, "AP_PORT_DETAILS_MALFORMED"
    up_ports = [p for p in current_ports if p["state"] == "UP"]
    if len(up_ports) != 1:
        return None, "AP_UP_PORT_COUNT_NOT_UNIQUE"
    ap_port = up_ports[0]
    idx, speed = ap_port["port_index"], ap_port["negotiated_speed_mbps"]
    if idx is None or sum(x["port_index"] == idx for x in current_ports) != 1:
        return None, "AP_LOCAL_PORT_INDEX_AMBIGUOUS"
    # Do not substitute maxSpeedMbps, or a Switch-side port speed.
    if speed is None:
        return None, "AP_UP_PORT_NEGOTIATED_SPEED_UNAVAILABLE"
    maximum = ap_port["max_capability_mbps"]
    if maximum is not None and speed > maximum:
        return None, "AP_PORT_SPEED_EXCEEDS_DECLARED_MAXIMUM"
    return speed, "AP_SIDE_SINGLE_UP_PORT_PARENT_VERIFIED"

def radios(detail):
    interfaces = detail.get("interfaces") if isinstance(detail, dict) else None
    rows = interfaces.get("radios") if isinstance(interfaces, dict) else None
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows[:4]:
        if isinstance(row, dict):
            freq = number(row.get("frequencyGHz"), 1, 8)
            if freq not in (2.4, 5, 6):
                continue
            result.append({"band_ghz": freq,
                           "channel": number(row.get("channel"), 1, 235),
                           "channel_width_mhz": number(row.get("channelWidthMHz"), 1, 320),
                           "wlan_standard": nonident_text(row.get("wlanStandard"))})
    return result


def stats_view(response):
    if not isinstance(response, dict):
        return None
    iface = response.get("interfaces")
    entries = iface.get("radios") if isinstance(iface, dict) else None
    observed = []
    if isinstance(entries, list):
        for row in entries[:4]:
            if not isinstance(row, dict):
                continue
            band = number(row.get("frequencyGHz"), 1, 8)
            if band not in (2.4, 5, 6):
                continue
            observed.append({
                "band_ghz": band,
                "tx_retries_percent": number(row.get("txRetriesPct"), 0, 100),
                "rx_errors": number(row.get("rxErrors"), 0, 1e12),
                "tx_errors": number(row.get("txErrors"), 0, 1e12),
            })
    return {
        "cpu_utilization_pct": number(response.get("cpuUtilizationPct"), 0, 100),
        "memory_utilization_pct": number(response.get("memoryUtilizationPct"), 0, 100),
        "radio_samples": observed,
        "observed_measurements": sum(x["tx_retries_percent"] is not None for x in observed),
    }


def site_snapshot(client):
    """Read only official Network Integration API v10.6.106 GET endpoints."""
    try:
        info = client.get("/info")
        app_version = nonident_text(info.get("applicationVersion"))
    except ReadError:
        app_version = None
    try:
        sites = client.paged("/sites", cap=MAX_SITES)
    except ReadError as exc:
        raise ReadError("GET /sites failed: " + str(exc)) from None
    if not sites:
        raise ReadError("No authorized site returned")
    result = []
    for site in sites:
        site_id = site.get("id") if isinstance(site, dict) else None
        if not identifier(site_id):
            raise ReadError("Invalid site identifier shape")
        prefix = "/sites/" + urllib.parse.quote(site_id, safe="")
        all_devices = client.paged(prefix + "/devices")
        inventory = []
        for item in all_devices:
            device_id = item.get("id") if isinstance(item, dict) else None
            if not identifier(device_id):
                continue
            path = prefix + "/devices/" + urllib.parse.quote(device_id, safe="")
            try:
                device = client.get(path)
            except ReadError:
                continue
            try:
                stats = stats_view(client.get(path + "/statistics/latest"))
            except ReadError:
                stats = None
            if not isinstance(device, dict):
                continue
            uplink = device.get("uplink")
            parent_id = uplink.get("deviceId") if isinstance(uplink, dict) else None
            inventory.append((device_id, parent_id, device, stats))
        ids = {identity for identity, _, _, _ in inventory}
        aps, others = [], []
        for identity, parent, detail, stats in inventory:
            visible_radios = radios(detail)
            current_ports = ports(detail)
            if visible_radios:
                parent_verified = bool(identifier(parent) and parent in ids and parent != identity)
                ap_link_mbps, ap_link_reason = verified_ap_side_uplink_speed(
                    detail, current_ports, parent_verified
                )
                aps.append({
                    "ap_number": len(aps) + 1,
                    "model": nonident_text(detail.get("model")),
                    "firmware_version": nonident_text(detail.get("firmwareVersion")),
                    "state": detail.get("state") if detail.get("state") in ("ONLINE", "OFFLINE", "ISOLATED") else "OTHER",
                    "radios": visible_radios,
                    "active_port_speeds_mbps": [p["negotiated_speed_mbps"] for p in current_ports
                                                if p["state"] == "UP" and p["negotiated_speed_mbps"] is not None],
                    "port_details": current_ports,
                    "uplink_parent_visible": identifier(parent),
                    "uplink_parent_in_device_inventory": parent in ids if identifier(parent) else False,
                    # This speed describes the AP's own PHY port only.
                    # v10.6.106 uplink.deviceId does NOT identify a Switch port.
                    "uplink_negotiated_speed_mbps": ap_link_mbps,
                    "uplink_speed_evidence": ap_link_reason,
                    "uplink_mapping_evidence": "PARENT_DEVICE_ONLY_NO_PORT_MAPPING",
                    "stats": stats,
                    "stats_status": "RADIO_RETRIES_AVAILABLE" if stats and stats["observed_measurements"] else "UNAVAILABLE",
                })
            else:
                others.append({
                    "model": nonident_text(detail.get("model")),
                    "state": detail.get("state") if detail.get("state") in ("ONLINE", "OFFLINE") else "OTHER",
                    "ports": current_ports, "upstream_device_declared": identifier(parent),
                })
        # Strictly return a sanitized subset. No siteId, deviceId, IP, MAC, BSSID,
        # client list, full topology or API response survives this function.
        result.append({
            "site_number": len(result) + 1,
            "unifi_network_version": app_version,
            "total_adopted_devices": len(all_devices),
            "access_points": aps,
            "access_point_details_unavailable": max(0, len(all_devices) - len(inventory)),
            "other_unifi_devices": others,
            "device_statistics_unavailable": sum(st is None for _, _, _, st in inventory),
            "wireless_broadcasts": None, "connected_client_counts": None,
            "unavailable_data": ["broadcasts_and_clients_not_collected"],
        })
    return result


def collect_local(url, key, ca_cert=None):
    from platform_wifi import current_link
    client = ReadOnlyClient(url, key, ca_cert)
    sites = site_snapshot(client)
    try:
        link = current_link()
    except (ValueError, OSError, TypeError, AttributeError):
        link = {"status": "NATIVE_API_UNAVAILABLE"}
    return {
        "report_schema": SCHEMA, "collection_mode": "local",
        "sites": sites, "client_wifi_link": link,
        "lan_tcp_throughput_test": {"status": "NOT_RUN", "scope": "LOCAL_PRIVATE_LAN_ONLY"},
    }


def mock_fixture():
    return {
        "report_schema": SCHEMA, "collection_mode": "mock",
        "sites": [{"site_number": 1, "access_points": [], "other_unifi_devices": [],
                   "total_adopted_devices": 0, "unifi_network_version": "SYNTHETIC_ONLY"}],
        "windows_native_wifi": {"status": "MOCK"},  # legacy v6 fixture compatibility
        "client_wifi_link": {"status": "MOCK"},
        "lan_tcp_throughput_test": {"status": "NOT_RUN"},
    }
