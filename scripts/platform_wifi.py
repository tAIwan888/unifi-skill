#!/usr/bin/env python3
"""One-shot, read-only current WiFi link probes for Windows/macOS/Linux.

No persistent agent, background jobs, scans, interface reconfiguration, credentials,
SSID/BSSID/MAC exports, telemetry upload or network server. Fails closed.
"""
import math
import re
import shutil
import subprocess
import sys

SOURCES = {
    "WINDOWS_WLAN_API_ASSOCIATED_BSS",
    "WINDOWS_NETSH_EXPLICIT_CURRENT_INTERFACE",
    "MACOS_COREWLAN_CURRENT_INTERFACE",
    "LINUX_IW_CURRENT_LINK",
}
STATUS = {
    "OBSERVED", "NOT_CONNECTED", "NATIVE_API_UNAVAILABLE",
    "LOCATION_PERMISSION_REQUIRED", "AMBIGUOUS_MULTIPLE_CONNECTIONS",
    "NO_SUPPORTED_WIFI_FIELDS", "UNSUPPORTED_PLATFORM",
}


def frequency_band(frequency_mhz):
    if type(frequency_mhz) not in (float, int) or not math.isfinite(frequency_mhz):
        return None
    if 2400 <= frequency_mhz <= 2500:
        return 2.4
    if 4900 <= frequency_mhz < 5925:
        return 5.0
    if 5925 <= frequency_mhz <= 7125:
        return 6.0
    return None


def sanitized_link(source, band=None, rssi=None, frequency=None, tx_phy=None):
    if source not in SOURCES:
        return {"status": "NATIVE_API_UNAVAILABLE"}
    if band not in (2.4, 5.0, 6.0):
        band = None
    if type(rssi) not in (int, float) or not math.isfinite(rssi) or not -110 <= rssi <= -15:
        rssi = None
    if type(tx_phy) not in (int, float) or not math.isfinite(tx_phy) or not 0 < tx_phy <= 100000:
        tx_phy = None
    if band is None and rssi is None:
        return {"status": "NO_SUPPORTED_WIFI_FIELDS"}
    out = {"status": "OBSERVED", "source": source, "band_ghz": band,
           "rssi_dbm": int(rssi) if rssi is not None else None,
           "tx_phy_mbps": float(tx_phy) if tx_phy is not None else None,
           "not_throughput": True}
    if (type(frequency) in (int, float) and math.isfinite(frequency)
            and 2400 <= frequency <= 7125
            and band == frequency_band(frequency)):
        out["bss_center_frequency_mhz"] = float(frequency)
    return out


def windows_link():
    from windows_wlan_native import sample
    from windows_netsh_localized import read
    try:
        result = sample()
        if result.get("status") != "OBSERVED":
            second = read()
            if second.get("status") == "OBSERVED":
                result = second
        return result
    except (OSError, ValueError, TypeError, AttributeError):
        return {"status": "NATIVE_API_UNAVAILABLE"}


def macos_link():
    # CoreWLAN is native Apple API via PyObjC, bundled only in the macOS binary.
    # Calling CWWiFiClient does not scan, associate or change the WLAN config.
    try:
        import CoreWLAN
        client = CoreWLAN.CWWiFiClient.sharedWiFiClient()
        interfaces = list(client.interfaces())
        connected = []
        for item in interfaces:
            channel = item.wlanChannel()
            if channel is not None and item.serviceActive():
                connected.append((item, channel))
        if not connected:
            return {"status": "NOT_CONNECTED"}
        if len(connected) != 1:
            return {"status": "AMBIGUOUS_MULTIPLE_CONNECTIONS"}
        interface, channel = connected[0]
        # Use the *current* channel band, not supportedWLANChannels.
        known = [
            ("kCWChannelBand2GHz", 2.4), ("kCWChannelBand5GHz", 5.0),
            ("kCWChannelBand6GHz", 6.0),
        ]
        band = next((ghz for name, ghz in known
                     if hasattr(CoreWLAN, name)
                     and channel.channelBand() == getattr(CoreWLAN, name)), None)
        return sanitized_link("MACOS_COREWLAN_CURRENT_INTERFACE",
                              band=band, rssi=interface.rssiValue(),
                              tx_phy=interface.transmitRate())
    except (ImportError, OSError, AttributeError, ValueError, TypeError):
        return {"status": "NATIVE_API_UNAVAILABLE"}


def linux_interface_names(text):
    if not isinstance(text, str) or len(text) > 65536:
        return []
    names = re.findall(r"^\s+Interface\s+([A-Za-z0-9_.-]{1,32})\s*$",
                       text, flags=re.MULTILINE)
    if len(names) > 16 or len(names) != len(set(names)):
        return []
    return names


def parse_iw_link(text):
    if not isinstance(text, str) or len(text) > 65536:
        return {"status": "NO_SUPPORTED_WIFI_FIELDS"}
    if not re.search(r"^\s*Connected to\s+[0-9a-f:]{17}\s+\(", text,
                     re.IGNORECASE | re.MULTILINE):
        return {"status": "NOT_CONNECTED"}
    freq = re.findall(r"^\s*freq:\s*(\d+(?:\.\d+)?)\s*$", text, re.MULTILINE)
    rssis = re.findall(r"^\s*signal:\s*(-?\d+(?:\.\d+)?)\s*dBm\s*$",
                       text, re.MULTILINE)
    txrates = re.findall(r"^\s*tx bitrate:\s*(\d+(?:\.\d+)?)\s*MBit/s(?:\s|$)",
                         text, re.MULTILINE)
    if len(freq) > 1 or len(rssis) > 1:
        return {"status": "NO_SUPPORTED_WIFI_FIELDS"}
    mhz = float(freq[0]) if len(freq) == 1 else None
    band = frequency_band(mhz) if mhz is not None else None
    rssi = float(rssis[0]) if len(rssis) == 1 else None
    tx = float(txrates[0]) if len(txrates) == 1 else None
    return sanitized_link("LINUX_IW_CURRENT_LINK", band, rssi, mhz, tx)


def linux_link(runner=subprocess.run, which=shutil.which):
    binary = which("iw")
    if not binary:
        return {"status": "NATIVE_API_UNAVAILABLE"}
    try:
        discover = runner([binary, "dev"], capture_output=True, text=True,
                          timeout=5, check=False)
        if discover.returncode != 0 or len(discover.stdout) > 65536:
            return {"status": "NATIVE_API_UNAVAILABLE"}
        names = linux_interface_names(discover.stdout)
        if not names:
            return {"status": "NO_SUPPORTED_WIFI_FIELDS"}
        associated = []
        for interface in names:
            result = runner([binary, "dev", interface, "link"],
                            capture_output=True, text=True, timeout=5, check=False)
            if result.returncode != 0 or len(result.stdout) > 65536:
                continue
            parsed = parse_iw_link(result.stdout)
            if parsed["status"] != "NOT_CONNECTED":
                associated.append(parsed)
        if not associated:
            return {"status": "NOT_CONNECTED"}
        if len(associated) != 1:
            return {"status": "AMBIGUOUS_MULTIPLE_CONNECTIONS"}
        return associated[0]
    except (OSError, subprocess.TimeoutExpired, UnicodeError, ValueError):
        return {"status": "NATIVE_API_UNAVAILABLE"}


def current_link(system=None):
    name = system or sys.platform
    if name == "win32":
        return windows_link()
    if name == "darwin":
        return macos_link()
    if name.startswith("linux"):
        return linux_link()
    return {"status": "UNSUPPORTED_PLATFORM"}


if __name__ == "__main__":
    import json
    print(json.dumps(current_link(), ensure_ascii=False))
