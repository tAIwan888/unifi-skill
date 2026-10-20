#!/usr/bin/env python3
"""Explicit current Windows netsh WiFi fields, including Traditional Chinese.

Local read-only fallback when Windows WLAN Native BSS lookup is unavailable.
SSID/BSSID/MAC/IP are never emitted. Do not confuse co-located 6 GHz BSS with
the CURRENT Windows band; channel number alone is insufficient evidence.
"""
import codecs
import re
import subprocess
import sys

KEYS = {
    "band": ("Band", "頻帶", "频带"),
    "rssi": ("RSSI", "Rssi"),
    "rx": ("Receive rate (Mbps)", "接收速率 (Mbps)", "接收速率"),
    "tx": ("Transmit rate (Mbps)", "傳輸速率 (Mbps)", "傳送速率 (Mbps)", "传输速率 (Mbps)"),
    "quality": ("Signal", "訊號", "信号"),
    "channel": ("Channel", "通道", "頻道", "信道"),
}
def field(text, names):
    options = "|".join(re.escape(x) for x in names)
    # Start-of-line anchor prevents using "co-located APs" BSSID lines.
    match = re.search(r"^\s*(?:" + options + r")\s*[:：]\s*([^\r\n]{1,32})\s*$",
                      text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse(text):
    if not isinstance(text, str):
        return {"status": "NO_SUPPORTED_WIFI_FIELDS"}
    # A multi-interface netsh response cannot be safely attributed to the
    # single WiFi client under diagnosis. Reject rather than select first.
    band_headings = re.findall(r"^\s*(?:Band|頻帶|频带)\s*[:：]", text,
                               re.MULTILINE | re.IGNORECASE)
    if len(band_headings) > 1:
        return {"status": "AMBIGUOUS_MULTIPLE_CONNECTIONS"}
    state = field(text, ("State", "狀態", "状态"))
    if state and state.casefold() not in ("connected", "已連線", "已连接", "已連接"):
        return {"status": "NOT_CONNECTED"}
    band_raw = field(text, KEYS["band"])
    rss_raw = field(text, KEYS["rssi"])
    rx_raw = field(text, KEYS["rx"])
    tx_raw = field(text, KEYS["tx"])
    quality_raw = field(text, KEYS["quality"])
    channel_raw = field(text, KEYS["channel"])

    band_match = re.fullmatch(r"([256])(?:\.0)?\s*GHz", band_raw or "", re.I)
    # Some Windows versions explicitly print 2.4 GHz.
    if not band_match and band_raw and re.fullmatch(r"2[.,]4\s*GHz", band_raw, re.I):
        band = 2.4
    else:
        band = float(band_match.group(1)) if band_match else None
    if band == 2.0:
        band = None

    def number(raw, pattern, low, high):
        if not raw:
            return None
        m = re.fullmatch(pattern, raw, re.I)
        if not m:
            return None
        try:
            value = float(m.group(1))
        except ValueError:
            return None
        return value if low <= value <= high else None

    rssi = number(rss_raw, r"(-?\d+(?:\.\d+)?)\s*(?:dBm)?", -110, -15)
    quality = number(quality_raw, r"(\d+(?:\.\d+)?)\s*%", 0, 100)
    rx = number(rx_raw, r"(\d+(?:\.\d+)?)", 1, 100000)
    tx = number(tx_raw, r"(\d+(?:\.\d+)?)", 1, 100000)
    channel = number(channel_raw, r"(\d+)", 1, 235)
    if band is None and rssi is None:
        return {"status": "NO_SUPPORTED_WIFI_FIELDS"}
    return {
        "status": "OBSERVED", "source": "WINDOWS_NETSH_EXPLICIT_CURRENT_INTERFACE",
        "band_ghz": band, "rssi_dbm": int(rssi) if rssi is not None else None,
        "signal_quality_percent": quality,
        "rx_phy_mbps": rx, "tx_phy_mbps": tx,
        "channel": int(channel) if channel is not None else None, "not_throughput": True,
    }


def read():
    if sys.platform != "win32":
        return {"status": "NOT_WINDOWS"}
    try:
        result = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "NETSH_UNAVAILABLE"}
    if result.returncode != 0:
        return {"status": "NETSH_ACCESS_OR_POLICY_BLOCKED"}
    # Windows OEM/ANSI/UTF-8 vary. A translation must be decodable before parsing;
    # never include raw output in diagnostics.
    import ctypes
    candidates = ["utf-8-sig"]
    try:
        candidates += ["cp" + str(ctypes.windll.kernel32.GetConsoleOutputCP()),
                       "cp" + str(ctypes.windll.kernel32.GetOEMCP()),
                       "cp" + str(ctypes.windll.kernel32.GetACP())]
    except (OSError, AttributeError):
        pass
    for encoding in dict.fromkeys(candidates):
        try:
            text = result.stdout.decode(encoding, errors="strict")
        except (UnicodeError, LookupError):
            continue
        parsed = parse(text)
        if parsed["status"] == "OBSERVED":
            return parsed
    return {"status": "NO_SUPPORTED_WIFI_FIELDS"}


if __name__ == "__main__":
    import json
    print(json.dumps(read(), ensure_ascii=False))
